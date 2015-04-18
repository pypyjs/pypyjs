"""
This module provides helpers to define and manage live components, that
is taglibrary components whose instances are client-side JS objects.

Each component must have a unique name in the livepage context.  This
name is usually the same as (or derived from) the 'name' field in the
data given to the tag renderer.  The 'livetags' object on the client
side is used as a mapping between those names and the underlying
object.  The server will rely on this mapping to 'access' the
javascript objects.  To make use of the livetags framework, the
livepage must include the component glue, by injecting
"componentGlue.inlineGlue" or "componentGlue.fileGlue" in the stan tree.
Component-specific glue (usually object definitions) must also
be added as needed.

"component" is a special object used to create javascript literals for
dealing with client components::

   component.<name>.init(<initializer>)
   
      Generate the JS command to associate <name> to the object
      designated by the initializer literal.  This sequence is usually
      put in the stan tree by the live component renderer, after
      having constructed the widget.  The initializer is supposed to
      construct a controller bound to the widget.
   
   component.<name>.delete
   
      Generate the JS command to remove the given component.
      If the controller has a del method, it will be called.
      The name is then removed from the mapping.

   All other uses construct normal livepage literals:
   
   component.<name>.<attribute>

      Generate the JS command to retrieve the given attribute on the
      named object.

   component.<name>.<method>(...)
   
      Generate the JS command to call the given method on the object.

Note that the <name>, <attribute>, <method> can also be retrieved using
the getitem notation. (e.g. component['foo'])
"""

from nevow import livepage, tags as t, static

class _livetag(object):
    def __init__(self, name):
        self.name = name
    def __getitem__(self, key):
        if key == 'init':
            def _init(value):
                return livepage.js("livetags[%r] = %s;"%(self.name,value))
            return _init
        if key == 'delete':
            return livepage.js("delComponent(%r);"%self.name)
        return livepage.js("livetags[%r].%s"%(self.name, key))
    __getattr__ = __getitem__
    
class _component(object):
    """This object provides a wrapper to manage live components"""
    
    def __getitem__(self, name):
        return _livetag(name)
    __getattr__ = __getitem__

component = _component()

class componentGlue(object):
    
    _js = """
livetags = new Object();

function delComponent(name) {
    o = livetags[name];
    if(o) {
        if(o.del) {
            o.del();
        }
        livetags[name] = null;
    }
}
"""
    fileJS     = static.Data(_js, 'text/javascript')
    
    inlineGlue = t.script(type_='text/javascript')[ t.xml(_js) ]
    fileGlue   = t.script(type_='text/javascript', src='/componentGlue.js')


__all__ = [ 'component', 'componentGlue'  ]
