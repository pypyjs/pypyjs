# Copyright (c) 2004 Divmod.
# See LICENSE for details.


"""XHTML stan tags and utilities.

This module defines all valid XHTML tags to make constructing XHTML
documents in stan trivial. An example of a simple HTML document in
stan is::

    html[
        head[
            title["Simple stan example"],
            ],
        body[
            p["Clever isn't it!"],
            ],
        ]

For convenience, the tags module also includes the more useful members
of the stan module, i.e. xml, invisible, directive, slot, cdata etc.

Note: when a tag name conflicts with a Python builtin, the tag name is
prefixed with '_'.
"""


from nevow.stan import Proto, Tag, directive, raw, xml, CommentProto, invisible, slot, cdata, inlineJS


comment = CommentProto()

tags = [
'a','abbr','acronym','address','applet','area','b','base','basefont','bdo','big','blockquote',
'body','br','button','caption','center','cite','code','col','colgroup','dd','dfn','div',
'dl','dt','em','fieldset','font','form','frame','frameset','h1','h2','h3','h4','h5','h6','head',
'hr','html','i','iframe','img','input','ins','isindex','kbd','label','legend','li','link','menu',
'meta','noframes','noscript','ol','optgroup','option','p','param','pre','q','s','samp',
'script','select','small','span','strike','strong','style','sub','sup','table','tbody','td','textarea',
'tfoot','th','thead','title','tr','tt','u','ul','var'
]


_dir = Proto('dir')
_del = Proto('del')
_object = Proto('object')
_map = Proto('map')


globs = globals()
for t in tags:
    globs[t] = Proto(t)


for x in range(100):
    globs['_%s' % x] = directive(x)


def drange(x):
    return [globs['_%s' % i] for i in range(x)]


__all__ = tags + ['invisible', 'comment', '_dir', '_del', '_object', '_map', 'drange', 'Tag', 'directive', 'xml', 'raw', 'slot', 'cdata', 'inlineJS'] + ['_%s' % x for x in range(100)]


########################
####
########################
####
########################
####
########################
