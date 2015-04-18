# Copyright (c) 2004 Divmod.
# See LICENSE for details.

"""An s-expression-like syntax for expressing xml in pure python.

Stan tags allow you to build XML documents using Python. Stan tags
have special attributes that enable the developer to insert hooks in
the document for locating data and custom rendering.

Stan is a DOM, or Document Object Model, implemented using
basic Python types and functions called "flatteners". A flattener is
a function that knows how to turn an object of a specific type
into something that is closer to an HTML string. Stan differs
from the W3C DOM by not being as cumbersome and heavy
weight. Since the object model is built using simple python types
such as lists, strings, and dictionaries, the API is simpler and
constructing a DOM less cumbersome.

Stan also makes it convenient to build trees of XML in pure python
code. See nevow.stan.Tag for details, and nevow.tags for tag
prototypes for all of the XHTML element types.
"""

from __future__ import generators
from zope.interface import implements

from nevow import inevow


class Proto(str):
    """Proto is a string subclass. Instances of Proto, which are constructed
    with a string, will construct Tag instances in response to __call__
    and __getitem__, delegating responsibility to the tag.
    """
    __slots__ = []

    def __call__(self, **kw):
        return Tag(self)(**kw)

    def __getitem__(self, children):
        return Tag(self)[children]

    def fillSlots(self, slotName, slotValue):
        return Tag(self).fillSlots(slotName, slotValue)

    def clone(self, deep=True):
        return self


class xml(object):
    """XML content marker.

    xml contains content that is already correct XML and should not be escaped
    to make it XML-safe. xml can contain unicode content and will be encoded to
    utf-8 when flattened.
    """
    __slots__ = ['content']

    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return '<xml %r>' % self.content


class raw(str):
    """Raw content marker.

    Raw content is never altered in any way. It is a sequence of bytes that will
    be passed through unchanged to the XML output.

    You probably don't want this - look at xml first.
    """
    __slots__ = []


def cdata(data):
    """CDATA section. data must be a string
    """
    return xml('<![CDATA[%s]]>' % data)


class directive(object):
    """Marker for a directive in a template
    """
    __slots__ = ['name']
    def __init__(self, name):
        self.name = name


    def __repr__(self):
        return "directive('%s')" % self.name


    def __hash__(self):
        return hash((directive, self.name))


    def __cmp__(self, other):
        if isinstance(other, directive):
            return cmp(self.name, other.name)
        return NotImplemented



class slot(object):
    """
    Marker for markup insertion in a template.

    @type filename: C{str} or C{NoneType}
    @ivar filename: The name of the XML file from which this tag was parsed.
        If it was not parsed from an XML file, C{None}.

    @type lineNumber: C{int} or C{NoneType}
    @ivar lineNumber: The line number on which this tag was encountered in the
        XML file from which it was parsed.  If it was not parsed from an XML
        file, C{None}.

    @type columnNumber: C{int} or C{NoneType}
    @ivar columnNumber: The column number at which this tag was encountered in
        the XML file from which it was parsed.  If it was not parsed from an
        XML file, C{None}.
    """
    __slots__ = ['name', 'children', 'default', 'filename', 'lineNumber', 'columnNumber']

    def __init__(self, name, default=None, filename=None, lineNumber=None, columnNumber=None):
        self.name = name
        self.children = []
        self.default = default
        self.filename = filename
        self.lineNumber = lineNumber
        self.columnNumber = columnNumber

    def __repr__(self):
        return "slot('%s')" % self.name

    def __getitem__(self, children):
        """Allow slots to have children. These children will not show up in the
        output, but they will be searched for patterns.
        """
        if not isinstance(children, (list, tuple)):
            children = [children]
        self.children.extend(children)
        return self

    def __iter__(self):
        """Prevent an infinite loop if someone tries to do
            for x in slot('foo'):
        """
        raise NotImplementedError, "Stan slot instances are not iterable."



class _PrecompiledSlot(object):
    """
    Marker for slot insertion into a template which has been precompiled.

    This differs from a normal slot in that it captures some attributes of its
    context at precompilation time so that it can be rendered properly (as
    these attributes are typically lost during precompilation).

    @type filename: C{str} or C{NoneType}
    @ivar filename: The name of the XML file from which this tag was parsed.
        If it was not parsed from an XML file, C{None}.

    @type lineNumber: C{int} or C{NoneType}
    @ivar lineNumber: The line number on which this tag was encountered in the
        XML file from which it was parsed.  If it was not parsed from an XML
        file, C{None}.

    @type columnNumber: C{int} or C{NoneType}
    @ivar columnNumber: The column number at which this tag was encountered in
        the XML file from which it was parsed.  If it was not parsed from an
        XML file, C{None}.
    """
    __slots__ = [
        'name', 'children', 'default', 'isAttrib',
        'inURL', 'inJS', 'inJSSingleQuoteString',
        'filename', 'lineNumber', 'columnNumber']

    def __init__(self, name, children, default, isAttrib, inURL, inJS, inJSSingleQuoteString, filename, lineNumber, columnNumber):
        self.name = name
        self.children = children
        self.default = default
        self.isAttrib = isAttrib
        self.inURL = inURL
        self.inJS = inJS
        self.inJSSingleQuoteString = inJSSingleQuoteString
        self.filename = filename
        self.lineNumber = lineNumber
        self.columnNumber = columnNumber


    def __repr__(self):
        return (
            '_PrecompiledSlot('
            '%r, isAttrib=%r, inURL=%r, inJS=%r, '
            'inJSSingleQuoteString=%r)') % (
            self.name, self.isAttrib, self.inURL, self.inJS,
            self.inJSSingleQuoteString)



class Tag(object):
    """
    Tag instances represent XML tags with a tag name, attributes, and
    children. Tag instances can be constructed using the Prototype tags in the
    'tags' module, or may be constructed directly with a tag name. Tags have
    two special methods, __call__ and __getitem__, which make representing
    trees of XML natural using pure python syntax. See the docstrings for these
    methods for more details.

    @type filename: C{str} or C{NoneType}
    @ivar filename: The name of the XML file from which this tag was parsed.
        If it was not parsed from an XML file, C{None}.

    @type lineNumber: C{int} or C{NoneType}
    @ivar lineNumber: The line number on which this tag was encountered in the
        XML file from which it was parsed.  If it was not parsed from an XML
        file, C{None}.

    @type columnNumber: C{int} or C{NoneType}
    @ivar columnNumber: The column number at which this tag was encountered in
        the XML file from which it was parsed.  If it was not parsed from an
        XML file, C{None}.
    """
    implements(inevow.IQ)

    specials = ['data', 'render', 'remember', 'pattern', 'key', 'macro']

    slotData = None
    filename = None
    lineNumber = None
    columnNumber = None

    def __init__(self, tag, attributes=None, children=None, specials=None, filename=None, lineNumber=None, columnNumber=None):
        self.tagName = tag
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
        if children is None:
            self.children = []
        else:
            self.children = children
        if specials is None:
            self._specials = {}
        else:
            self._specials = specials
        if filename is not None:
            self.filename = filename
        if lineNumber is not None:
            self.lineNumber = lineNumber
        if columnNumber is not None:
            self.columnNumber = columnNumber


    def fillSlots(self, slotName, slotValue):
        """Remember the stan 'slotValue' with the name 'slotName' at this position
        in the DOM. During the rendering of children of this node, slots with
        the name 'slotName' will render themselves as 'slotValue'.
        """
        if self.slotData is None:
            self.slotData = {}
        self.slotData[slotName] = slotValue
        return self

    def patternGenerator(self, pattern, default=None):
        """Returns a psudeo-Tag which will generate clones of matching
        pattern tags forever, looping around to the beginning when running
        out of unique matches.

        If no matches are found, and default is None, raise an exception,
        otherwise, generate clones of default forever.

        You can use the normal stan syntax on the return value.

        Useful to find repeating pattern elements. Example rendering function:

        >>> def simpleSequence(context, data):
        ...   pattern = context.patternCloner('item')
        ...   return [pattern(data=element) for element in data]
        """
        patterner = _locatePatterns(self, pattern, default)
        return PatternTag(patterner)

    def allPatterns(self, pattern):
        """Return a list of all matching pattern tags, cloned.

        Useful if you just want to insert them in the output in one
        place.

        E.g. the sequence renderer's header and footer are found with this.
        """
        return [tag.clone(deep=False, clearPattern=True) for tag in
                specialMatches(self, 'pattern', pattern)]

    def onePattern(self, pattern):
        """
        Return a single matching pattern, cloned.

        If there is more than one matching pattern or no matching patterns,
        raise an exception.

        Useful in the case where you want to locate one and only one sub-tag
        and do something with it.
        """
        data = getattr(self, 'pattern', Unset)
        if data == pattern:
            result = self
        else:
            result = _locateOne(
                pattern,
                lambda pattern: specialMatches(self, 'pattern', pattern),
                'pattern')
        return result.clone(deep=False, clearPattern=True)


    def __call__(self, **kw):
        """Change attributes of this tag. This is implemented using
        __call__ because it then allows the natural syntax::

          table(width="100%", height="50%", border="1")

        Attributes may be 'invisible' tag instances (so that
        C{a(href=invisible(data="foo", render=myhrefrenderer))} works),
        strings, functions, or any other object which has a registered
        flattener.

        If the attribute is a python keyword, such as 'class', you can
        add an underscore to the name, like 'class_'.

        A few magic attributes have values other than these, as they
        are not serialized for output but rather have special purposes
        of their own:

         - data: The value is saved on the context stack and passed to
           render functions.

         - render: A function to call that may modify the tag in any
           way desired.

         - remember: Remember the value on the context stack with
           context.remember(value) for later lookup with
           context.locate()

         - pattern: Value should be a key that can later be used to
           locate this tag with context.patternGenerator() or
           context.allPatterns()

         - key: A string used to give the node a unique label.  This
           is automatically namespaced, so in C{span(key="foo")[span(key="bar")]}
           the inner span actually has a key of 'foo.bar'.  The key is
           intended for use as e.g. an html 'id' attribute, but will
           is not automatically output.

         - macro - A function which will be called once in the lifetime
           of the template, when the template is loaded. The return
           result from this function will replace this Tag in the template.
        """
        if not kw:
            return self

        for name in self.specials:
            if kw.has_key(name):
                setattr(self, name, kw[name])
                del kw[name]

        for k, v in kw.iteritems():
            if k[-1] == '_':
                k = k[:-1]
            elif k[0] == '_':
                k = k[1:]
            self.attributes[k] = v
        return self

    def __getitem__(self, children):
        """Add children to this tag. Multiple children may be added by
        passing a tuple or a list. Children may be other tag instances,
        strings, functions, or any other object which has a registered
        flatten.

        This is implemented using __getitem__ because it then allows
        the natural syntax::

          html[
              head[
                  title["Hello World!"]
              ],
              body[
                  "This is a page",
                  h3["How are you!"],
                  div(style="color: blue")["I hope you are fine."]
              ]
          ]
        """
        if not isinstance(children, (list, tuple)):
            children = [children]
        self.children.extend(children)
        return self

    def __iter__(self):
        """Prevent an infinite loop if someone tries to do
            for x in stantaginstance:
        """
        raise NotImplementedError, "Stan tag instances are not iterable."

    def _clearSpecials(self):
        """Clears all the specials in this tag. For use by flatstan.
        """
        self._specials = {}

    # FIXME: make this function actually be used.
    def precompilable(self):
        """Is this tag precompilable?

        Tags are precompilable if they will not be modified by a user
        render function.

        Currently, the following attributes prevent the tag from being
        precompiled:

         - render (because the function can modify its own tag)
         - pattern (because it is locatable and thus modifiable by an
                    enclosing renderer)
        """
        return self.render is Unset and self.pattern is Unset

    def _clone(self, obj, deep):
        if hasattr(obj, 'clone'):
            return obj.clone(deep)
        elif isinstance(obj, (list, tuple)):
            return [self._clone(x, deep)
                    for x in obj]
        else:
            return obj

    def clone(self, deep=True, clearPattern=False):
        """Return a clone of this tag. If deep is True, clone all of this
        tag's children. Otherwise, just shallow copy the children list
        without copying the children themselves.
        """
        if deep:
            newchildren = [self._clone(x, True) for x in self.children]
        else:
            newchildren = self.children[:]
        newattrs = self.attributes.copy()
        for key in newattrs:
            newattrs[key]=self._clone(newattrs[key], True)

        newslotdata = None
        if self.slotData:
            newslotdata = self.slotData.copy()
            for key in newslotdata:
                newslotdata[key] = self._clone(newslotdata[key], True)

        newtag = Tag(
            self.tagName,
            attributes=newattrs,
            children=newchildren,
            specials=self._specials.copy(),
            filename=self.filename,
            lineNumber=self.lineNumber,
            columnNumber=self.columnNumber)
        newtag.slotData = newslotdata
        if clearPattern:
            newtag.pattern = None

        return newtag

    def clear(self):
        """Clear any existing children from this tag.
        """
        self._specials = {}
        self.children = []
        return self

    def __repr__(self):
        rstr = ''
        if self.attributes:
            rstr += ', attributes=%r' % self.attributes
        if self._specials:
            rstr += ', specials=%r' % self._specials
        if self.children:
            rstr += ', children=%r' % self.children
        return "Tag(%r%s)" % (self.tagName, rstr)

    def freeze(self):
        """Freeze this tag so that making future calls to __call__ or __getitem__ on the
        return value will result in clones of this tag.
        """
        def forever():
            while True:
                yield self.clone()
        return PatternTag(forever())


class UnsetClass:
    def __nonzero__(self):
        return False
    def __repr__(self):
        return "Unset"
Unset=UnsetClass()

def makeAccessors(special):
    def getSpecial(self):
        return self._specials.get(special, Unset)

    def setSpecial(self, data):
        self._specials[special] = data

    return getSpecial, setSpecial

for name in Tag.specials:
    setattr(Tag, name, property(*makeAccessors(name)))
del name



def visit(root, visitor):
    """
    Invoke C{visitor} with each Tag in the stan DOM represented by C{root}.
    """
    if isinstance(root, list):
        for t in root:
            visit(t, visitor)
    else:
        visitor(root)
        if isinstance(root, Tag):
            for ch in root.children:
                visit(ch, visitor)



### Pattern machinery
class NodeNotFound(KeyError):
    def __str__(self):
        return "The %s named %r wasn't found in the template." % tuple(self.args[:2])

class TooManyNodes(Exception):
    def __str__(self):
        return "More than one %r with the name %r was found." % tuple(self.args[:2])

class PatternTag(object):
    '''A pseudotag created by Tag.patternGenerator() which loops
    through a sequence of matching patterns.'''

    def __init__(self, patterner):
        self.pat = patterner.next()
        self.patterner = patterner

    def next(self):
        if self.pat:
            p, self.pat = self.pat, None
            return p
        return self.patterner.next()


def makeForwarder(name):
    return lambda self, *args, **kw: getattr(self.next(), name)(*args, **kw)

for forward in ['__call__', '__getitem__', 'fillSlots']:
    setattr(PatternTag, forward, makeForwarder(forward))

def _locatePatterns(tag, pattern, default, loop=True):
    """
    Find tags with the given pattern which are children of the given tag.

    @param tag: The L{Tag} the children of which to search.
    @param pattern: A C{str} giving the name of the patterns to find.
    @param default: The value to yield if no tags with the given pattern are
        found.
    @param loop: A C{bool} indicating whether to cycle through all results
        infinitely.
    """
    gen = specialMatches(tag, 'pattern', pattern)
    produced = []

    for x in gen:
        produced.append(x)
        cloned = x.clone(deep=False, clearPattern=True)
        yield cloned

    gen=None
    if produced:
        if not loop:
            return
        while True:
            for x in produced:
                cloned = x.clone(deep=False, clearPattern=True)
                yield cloned

    if default is None:
        raise NodeNotFound, ("pattern", pattern)
    if hasattr(default, 'clone'):
        while True:  yield default.clone(deep=False)
    else:
        while True:  yield default
Tag._locatePatterns = _locatePatterns


def _locateOne(name, locator, descr):
    found = False
    for node in locator(name):
        if found:
            raise TooManyNodes(descr, name)
        found = node
    if not found:
        raise NodeNotFound(descr, name)
    return found


def specials(tag, special):
    """Generate tags with special attributes regardless of attribute value.
    """
    for childOrContext in getattr(tag, 'children', []):
        child = getattr(childOrContext, 'tag', childOrContext)

        if getattr(child, special, Unset) is not Unset:
            yield child
        else:
            for match in specials(child, special):
                yield match


def specialMatches(tag, special, pattern):
    """
    Generate special attribute matches starting with the given tag; if a tag
    has special, do not look any deeper below that tag, whether it matches
    pattern or not. Returns an iterable.
    """
    for childOrContext in getattr(tag, 'children', []):
        child = getattr(childOrContext, 'tag', childOrContext)

        data = getattr(child, special, Unset)
        if data == pattern:
            yield child
        elif data is Unset:
            for match in specialMatches(child, special, pattern):
                yield match

## End pattern machinery


class CommentProto(Proto):
    __slots__ = []
    def __call__(self, **kw):
        return Comment(self)(**kw)

    def __getitem__(self, children):
        return Comment(self)[children]


class Comment(Tag):
    def __call__(self, **kw):
        raise NotImplementedError('comments are not callable')

invisible = Proto('')


class Entity(object):
    def __init__(self, name, num, description):
        self.name = name
        self.num = num
        self.description = description

    def __repr__(self):
        return "Entity(%r, %r, %r)" % (self.name, self.num, self.description)


class inlineJS(object):
    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return "inlineJS(%s)" % (self.children, )
