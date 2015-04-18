# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from __future__ import generators

from nevow.flat import serialize, precompile
from nevow.stan import Tag, xml, directive, slot, cdata
from nevow import util


def MicroDomTextSerializer(original, context):
    if original.raw:
        return original.nodeValue
    else:
        return util.escapeToXML(original.nodeValue)


def MicroDomCDATASerializer(original, context):
    return cdata(original.data)


def MicroDomCommentSerializer(original, context):
    return xml("<!--%s-->" % original.data)


def MicroDomEntityReferenceSerializer(original, context):
    return xml(original.nodeValue)


def MicroDomElementSerializer(element, context):
    directiveMapping = {
        'render': 'render',
        'data': 'data',
        'macro': 'macro',
    }
    attributeList = [
        'pattern', 'key',
    ]

    name = element.tagName
    if name.startswith('nevow:'):
        _, name = name.split(':')
        if name == 'invisible':
            name = ''
        elif name == 'slot':
            return slot(element.attributes['name'])[
                precompile(serialize(element.childNodes, context), context)]
    
    attrs = dict(element.attributes) # get rid of CaseInsensitiveDict
    specials = {}
    attributes = attributeList
    directives = directiveMapping
    for k, v in attrs.items():
        # I know, this is totally not the way to do xml namespaces but who cares right now
        ## I'll fix it later -dp
        ### no you won't *I'll* fix it later -glyph
        if isinstance(k, tuple):
            if k[0] != 'http://nevow.com/ns/nevow/0.1':
                continue
            else:
                nons = k[1]
        elif not k.startswith('nevow:'):
            continue
        else:
            _, nons = k.split(':')
        if nons in directives:
            ## clean this up by making the names more consistent
            specials[directives[nons]] = directive(v)
            del attrs[k]
        if nons in attributes:
            specials[nons] = v
            del attrs[k]
            
    # TODO: there must be a better way than this ...
    # Handle any nevow:attr elements. If we don't do it now then this tag will
    # be serialised and it will too late.
    childNodes = []
    for child in element.childNodes:
        if getattr(child,'tagName',None) == 'nevow:attr':
            attrs[child.attributes['name']] = child.childNodes
        else:
            childNodes.append(child)

    tag = Tag(
            name,
            attributes=attrs,
            children=childNodes,
            specials=specials
            )

    return serialize(tag, context)


def MicroDomDocumentSerializer(original, context):
    if original.doctype:
        yield "<!DOCTYPE %s>\n" % original.doctype
    for n in original.childNodes:
        yield serialize(n, context)


