# Copyright (c) 2004 Divmod.
# See LICENSE for details.

"""Compatibility wrapper over new twisted.python.components,
so that nevow works with it. 
"""

import warnings

from zope.interface import Interface, implements as zimplements, Attribute

from twisted.python.components import *

warnings.warn("compy.py module is deprecated, use zope.interface and twisted.python.components.registerAdapter directly.",
              stacklevel=2)

# Backwards compat code
CannotAdapt = TypeError

_registerAdapter = registerAdapter
def registerAdapter(adapterFactory, origInterface, *interfaceClasses):
    from nevow.util import _namedAnyWithBuiltinTranslation, _NamedAnyError
    
    isStr = type(adapterFactory) is str
    if (type(origInterface) is str) != isStr:
        raise ValueError("Either all arguments must be strings or all must be objects.")
    
    for interfaceClass in interfaceClasses:
        if (type(interfaceClass) is str) != isStr:
            raise ValueError("Either all arguments must be strings or all must be objects.")

    if isStr:
        # print "registerAdapter:",adapterFactory, origInterface, interfaceClasses
        adapterFactory = _namedAnyWithBuiltinTranslation(adapterFactory)
        origInterface = _namedAnyWithBuiltinTranslation(origInterface)
        interfaceClasses = [_namedAnyWithBuiltinTranslation(x) for x in interfaceClasses]

    if 'nevow.inevow.ISerializable' in interfaceClasses or filter(
            lambda o: getattr(o, '__name__', None) == 'ISerializable', interfaceClasses):
        warnings.warn("ISerializable is deprecated. Please use nevow.flat.registerFlattener instead.", stacklevel=2)
        from nevow import flat
        flat.registerFlattener(adapterFactory, origInterface)
    _registerAdapter(adapterFactory, origInterface, *interfaceClasses)


class IComponentized(Interface):
    pass

_Componentized = Componentized
class Componentized(_Componentized):
    zimplements(IComponentized)
    
    def __init__(self, adapterCache=None):
        _Componentized.__init__(self)
        if adapterCache:
            for k, v in adapterCache.items():
                self.setComponent(k, v)


__all__ = ['globalRegistry', 'registerAdapter', 'backwardsCompatImplements', 'fixClassImplements',
           'getInterfaces', 'IComponentized', 'Componentized', 'Adapter', 'CannotAdapt']
