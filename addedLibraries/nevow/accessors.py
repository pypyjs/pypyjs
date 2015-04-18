# Copyright (c) 2004 Divmod.
# See LICENSE for details.


"""Standard IData introspection adapters.

Classes and functions in this module are responsible for resolving
data directives into the actual data to be rendered.

By default, Nevow knows how to I{look inside} Python's mapping (dict)
and sequence (tuple, list) types as well as call any functions and
methods found in the stan tree.
"""

from zope.interface import implements

import twisted.python.components as tpc

from nevow.inevow import IGettable, IContainer, IData
from nevow import util

def convertToData(data, context):
    """Recursively resolve the data until either a Twisted deferred or
    something that does not implement the IGettable interface is
    found.
    """
    newdata = IGettable(data, None)
    if newdata is not None:
        olddata = newdata
        newdata = olddata.get(context)
        if isinstance(newdata, util.Deferred):
            return newdata.addCallback(convertToData, context)
        elif newdata is olddata:
            return olddata
        else:
            return convertToData(newdata, context)
    else:
        return data

class NoAccessor(NotImplementedError):
    pass


class DirectiveAccessor(tpc.Adapter):
    implements(IGettable)

    def get(self, context):
        data = context.locate(IData)
        container = IContainer(data, None)
        if container is None:
            raise NoAccessor, "%r does not implement IContainer, and there is no registered adapter." % data
        child = container.child(context, self.original.name)
        return child


class SlotAccessor(tpc.Adapter):
    implements(IGettable)

    def get(self, context):
        return context.locateSlotData(self.original.name)


class FunctionAccessor(tpc.Adapter):
    implements(IGettable)
    def get(self, context):
        return self.original(context, context.locate(IData))


class DictionaryContainer(tpc.Adapter):
    implements(IContainer)
    
    def child(self, context, name):
        return self.original[name]


class ObjectContainer(tpc.Adapter):
    """Retrieve object attributes in response to a data directive; providing
    easy access to your application objects' attributes.

    ObjectContainer is not registered as an adapter for any objects by default.
    It must be registered for each type you want to adapt.

    The adapter will cowardly refuse to get any attributes that start with an
    underscore.
    
    For example:
    
    >>> class Image:
    ...     def __init__(self, filename, comments):
    ...         self.filename = filename    # A string
    ...         self.comments = comments    # A sequence of strings
    ... 
    >>> registerAdapter(ObjectContainer, Image, IContainer)
        
    Registering the adapter allows Nevow to retrieve attributes from the Image
    instance returned by the data_image method when rendering the following
    XHTML template::
        
        <div n:data="image">
          <p n:data="filename" n:render="string">filename</p>
          <ul n:data="comments" n:render="sequence">
            <li n:pattern="item" n:render="string">comment</li>
          </ul>
        </div>
    """
    
    implements(IContainer)
    
    def child(self, context, name):
        if name[:1] == '_':
            raise ValueError("ObjectContainer does not support attribute names starting with '_', got %r"%name)
        return getattr(self.original, name)


def intOrNone(s):
    try:
        return int(s)
    except ValueError:
        return None


class ListContainer(tpc.Adapter):
    implements(IContainer)

    def child(self, context, name):
        if ':' in name:
            return self.original[slice(*[intOrNone(x) for x in name.split(':')])]
        return self.original[int(name)]

