# Copyright (c) 2004-2009 Divmod.
# See LICENSE for details.

from xml.sax import make_parser, handler
import xml as pyxml

from nevow.stan import xml, Tag, directive, slot
import nevow

## Require PyXML 0.8.2 or later, or, if PyXML isn't installed
## python2.3 or later, because that includes approximately the
## same code (but doesn't share a version number *!@#$@!@#)

try:
    ## pyxml package has a version_info attribute
    bad_version = pyxml.version_info < (0,8,2)
    ## before 0.8.3, startDTD was passed the args in the wrong order
    bad_startdtd_args = pyxml.version_info < (0,8,3)
except:
    ## we're using core python xml library
    import sys
    bad_version = sys.version_info < (2,3)
    # python < 2.4 has the startDTD bug
    bad_startdtd_args = sys.version_info < (2,4)


class nscontext(object):

    def __init__(self, parent=None):
        self.parent = parent
        if parent is not None:
            self.nss = dict(parent.nss)
        else:
            self.nss = {'http://www.w3.org/XML/1998/namespace':'xml'}

    def get(self, k, d=None):
        return self.nss.get(k, d)

    def __setitem__(self, k, v):
        self.nss.__setitem__(k, v)

    def __getitem__(self, k):
        return self.nss.__getitem__(k)


class ToStan(handler.ContentHandler, handler.EntityResolver):
    directiveMapping = {
        'render': 'render',
        'data': 'data',
        'macro': 'macro',
    }
    attributeList = [
        'pattern', 'key',
    ]

    def __init__(self, ignoreDocType, ignoreComment, sourceFilename):
        self.ignoreDocType = ignoreDocType
        self.ignoreComment = ignoreComment
        self.sourceFilename = sourceFilename
        self.prefixMap = nscontext()
        self.inCDATA = False


    def setDocumentLocator(self, locator):
        self.locator = locator

    def resolveEntity(self, publicId, systemId):
        ## This doesn't seem to get called, which is good.
        raise Exception("resolveEntity should not be called. We don't use external DTDs.")

    def skippedEntity(self, name):
        self.current.append(xml("&%s;"%name))

    def startDocument(self):
        self.document = []
        self.current = self.document
        self.stack = []
        self.xmlnsAttrs = []

    def endDocument(self):
        pass

    def processingInstruction(self, target, data):
        self.current.append(xml("<?%s %s?>\n" % (target, data)))

    def startPrefixMapping(self, prefix, uri):

        self.prefixMap = nscontext(self.prefixMap)
        self.prefixMap[uri] = prefix

        # Ignore Nevow's namespace, we'll replace those during parsing.
        if uri == nevow.namespace:
            return

        # Add to a list that will be applied once we have the element.
        if prefix is None:
            self.xmlnsAttrs.append(('xmlns',uri))
        else:
            self.xmlnsAttrs.append(('xmlns:%s'%prefix,uri))

    def endPrefixMapping(self, prefix):
        self.prefixMap = self.prefixMap.parent

    def startElementNS(self, ns_and_name, qname, attrs):

        filename = self.sourceFilename
        lineNumber = self.locator.getLineNumber()
        columnNumber = self.locator.getColumnNumber()

        ns, name = ns_and_name
        if ns == nevow.namespace:
            if name == 'invisible':
                name = ''
            elif name == 'slot':
                try:
                    # Try to get the default value for the slot
                    default = attrs[(None, 'default')]
                except KeyError:
                    # If there wasn't one, then use None to indicate no
                    # default.
                    default = None
                el = slot(
                    attrs[(None, 'name')], default=default,
                    filename=filename, lineNumber=lineNumber,
                    columnNumber=columnNumber)
                self.stack.append(el)
                self.current.append(el)
                self.current = el.children
                return

        attrs = dict(attrs)
        specials = {}
        attributes = self.attributeList
        directives = self.directiveMapping
        for k, v in attrs.items():
            att_ns, nons = k
            if att_ns != nevow.namespace:
                continue
            if nons in directives:
                ## clean this up by making the names more consistent
                specials[directives[nons]] = directive(v)
                del attrs[k]
            if nons in attributes:
                specials[nons] = v
                del attrs[k]

        no_ns_attrs = {}
        for (attrNs, attrName), v in attrs.items():
            nsPrefix = self.prefixMap.get(attrNs)
            if nsPrefix is None:
                no_ns_attrs[attrName] = v
            else:
                no_ns_attrs['%s:%s'%(nsPrefix,attrName)] = v

        if ns == nevow.namespace and name == 'attr':
            if not self.stack:
                # TODO: define a better exception for this?
                raise AssertionError( '<nevow:attr> as top-level element' )
            if 'name' not in no_ns_attrs:
                # TODO: same here
                raise AssertionError( '<nevow:attr> requires a name attribute' )
            el = Tag('', specials=specials, filename=filename,
                     lineNumber=lineNumber, columnNumber=columnNumber)
            self.stack[-1].attributes[no_ns_attrs['name']] = el
            self.stack.append(el)
            self.current = el.children
            return

        # Apply any xmlns attributes
        if self.xmlnsAttrs:
            no_ns_attrs.update(dict(self.xmlnsAttrs))
            self.xmlnsAttrs = []

        # Add the prefix that was used in the parsed template for non-Nevow
        # namespaces (which Nevow will consume anyway).
        if ns != nevow.namespace and ns is not None:
            prefix = self.prefixMap[ns]
            if prefix is not None:
                name = '%s:%s' % (self.prefixMap[ns],name)
        el = Tag(
            name, attributes=dict(no_ns_attrs), specials=specials,
            filename=filename, lineNumber=lineNumber,
            columnNumber=columnNumber)
        self.stack.append(el)
        self.current.append(el)
        self.current = el.children

    def characters(self, ch):
        # CDATA characters should be passed through as is.
        if self.inCDATA:
            ch = xml(ch)
        self.current.append(ch)

    def endElementNS(self, name, qname):
        me = self.stack.pop()
        if self.stack:
            self.current = self.stack[-1].children
        else:
            self.current = self.document

    def startDTD(self, name, publicId, systemId):
        if self.ignoreDocType:
            return
        # Check for broken startDTD
        if bad_startdtd_args:
            systemId, publicId = publicId, systemId
        doctype = '<!DOCTYPE %s\n  PUBLIC "%s"\n  "%s">\n' % (name, publicId, systemId)
        self.current.append(xml(doctype))

    def endDTD(self, *args):
        pass

    def startCDATA(self):
        self.inCDATA = True
        self.current.append(xml('<![CDATA['))

    def endCDATA(self):
        self.inCDATA = False
        self.current.append(xml(']]>'))

    def comment(self, content):
        if self.ignoreComment:
            return
        self.current.append( (xml('<!--'),xml(content),xml('-->')) )


def parse(fl, ignoreDocType=False, ignoreComment=False):
    ## Earlier PyXMLs don't handle non-standard entities (e.g. &copy;)
    ## correctly. They will either give an error or simply ignore the
    ## entity producing bad output.

    if bad_version:
        raise Exception("Please use PyXML later than 0.8.2 or python later than 2.3. Earlier ones are too buggy.")

    parser = make_parser()
    parser.setFeature(handler.feature_validation, 0)
    parser.setFeature(handler.feature_namespaces, 1)
    parser.setFeature(handler.feature_external_ges, 0)
    parser.setFeature(handler.feature_external_pes, 0)

    s = ToStan(ignoreDocType, ignoreComment, getattr(fl, "name", None))
    parser.setContentHandler(s)
    parser.setEntityResolver(s)
    parser.setProperty(handler.property_lexical_handler, s)

    parser.parse(fl)

    return s.document

def parseString(t, ignoreDocType=False, ignoreComment=False):
    from cStringIO import StringIO
    return parse(StringIO(t), ignoreDocType, ignoreComment)
