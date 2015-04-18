# Copyright (c) 2004 Divmod.
# See LICENSE for details.


"""
Easy to use box layout model. Works cross-browser on IE 6, Safari, Opera, and Mozilla (using Evil Hack(tm)).
Until a known bug in Mozilla is fixed, the Evil Hack will be in place. This evil hack prevents text inside of a Block from
being selected.

 - line: a horizontal box grouping
 - block: a vertical, flowing box grouping

Example::

  text = "Hello lots of text " * 20

  line(width='100%')[
    box(width='50%')[text],
    box(width='50%')[text]]
  # Note there is a mozilla bug right now where the second, flowing percentage is calculated using only
  # the empty space, so the second value here would have to be 100%; This module will soon add browser
  # sniffing to detect if mozilla is being used and adjust percentages accordingly. For now, use pixel, em, or
  # point values instead.

Experimental feature: Keyword arguments to the line and box protos are converted into css styles:
box(color='red') => <span style="color: red" />

Known Mozilla bugs
==================

If you use border, padding, or margin, mozilla shows weird rendering artifacts. background color and
background images generally appear to be safe.

It doesn't appear to be possible to set the vertical-align in some cases in mozilla.
"""

from zope.interface import implements

from nevow import static
from nevow import inevow
from nevow import tags

boxStyle = tags.xml("""
span.nevow-blocks-block {
    display: inline-block;
    -moz-binding: url('/mozbinding#inlineblock'); }

div.nevow-blocks-line {
    margin: 0px; padding: 0px }

.expanded {
    display: block; }

.collapsed {
    display: none; }

.visibilityImage {
    margin-right: 5px; }
""")

js = tags.xml( """
function collapse(node, collapsedText, expandedText) {
    for (var i = 0; i < node.childNodes.length; i++) {
        var childNode = node.childNodes[i]
        if (childNode.className == 'visibilityImage') {
            var img = childNode;
        } else if (childNode.className == 'headText') {
            var head = childNode;
        }
    }
    for (var i = 0; i < node.parentNode.childNodes.length; i++) {
        var childNode = node.parentNode.childNodes[i]
        if (childNode.className == 'collapsed' || childNode.className == 'expanded') {
            var next = childNode;
        }
    }
    if (next.className == 'collapsed') {
        img.src = '/images/outline-expanded.png';
        next.className = 'expanded';
        head.innerHTML = expandedText;
    } else {
        img.src = '/images/outline-collapsed.png';
        next.className = 'collapsed';
        head.innerHTML = collapsedText;
    }
}//""")

blocks_glue = [
    tags.style(type="text/css")[ boxStyle ],
    tags.script(type="text/javascript")[ tags.comment[js] ]]


mozBinding = """<?xml version="1.0"?>

<bindings xmlns="http://www.mozilla.org/xbl"
          xmlns:xbl="http://www.mozilla.org/xbl"
          xmlns:html="http://www.w3.org/1999/xhtml"
          xmlns:xul="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">

<binding id="inlineblock">
  <content>
  <html:style type="text/css">
    .nevow-inline-table { display: inline-table; }
    .nevow-inline-table-row { display: table-row; }
    .nevow-inline-table-cell { display: table-cell; }
  </html:style>
    <html:span class="nevow-inline-table">
    <html:span class="nevow-inline-table-row">
     <html:span class="nevow-inline-table-cell" xbl:inherits="style">
          <children/>
     </html:span>
     </html:span>
     </html:span>
  </content>
</binding>

</bindings>
"""

blocks_child = static.Data(mozBinding, 'text/xml; name="inline-block.xml"')


class _Blocks(object):
    def __init__(self, tag, className):
        self.tag = tag
        self.className = className

    def __call__(self, **kw):
        """Make and return a new block. If height or width is specified, they may be
        of any css-supported measurement format, such as '200px' or '50%'.
        
        If height or width is not specified, the block will "shrink wrap".
        
        Interesting experiment: kw arguments to __call__ are treated like css style key
        value pairs. For example, block(color='blue', background_color='red') will translate
        to style="color: blue; background-color: red". _ is mapped to -. Not sure if this will
        work but it will be interesting to see if it is useful to use.
        """
        return self.tag(
            _class=self.className,
            style='; '.join(
                [': '.join((k.replace('_', '-'), v))
                for (k, v) in kw.items()]))


block = _Blocks(tags.span, 'nevow-blocks-block')
line = _Blocks(tags.div, 'nevow-blocks-line')


class collapser(object):
    """Render a fragment of html with a head and a body.
    The body can be in two states, expanded and collapsed.
    When the body is in collapsed state, it is not visible in the browser.
    Clicking on the head area causes the visibility state of the body
    to toggle.

    TODO: This should be rewritten to check for patterns and slots so you
    could have it use table or paragraph tags or whatever instead of a span
    and a div, and you can omit the visibility image if desired (js would have 
    to change too)
    """
    implements(inevow.IRenderer)

    def __init__(self, headCollapsed, headExpanded, body, collapsed=True):
        self.headCollapsed = headCollapsed
        self.headExpanded = headExpanded
        self.body = body
        if collapsed:
            self.collapsed = 'collapsed'
        else:
            self.collapsed = 'expanded'

    def rend(self, ctx, data):
        return (tags.span(
            _class="collapser-line",
            onclick=(
                "collapse(this, '",
                self.headCollapsed,
                "', '",
                self.headExpanded,
                "');"))[
            tags.img(_class="visibilityImage", src="/images/outline-%s.png" % self.collapsed),
            tags.span(_class="headText", style="color: blue; text-decoration: underline; cursor: pointer;")[
                self.collapsed == 'collapsed' and self.headCollapsed or self.headExpanded ]
        ],
        tags.xml('&nbsp;'),
        tags.div(_class=self.collapsed)[
            self.body
        ])

