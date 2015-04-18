# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from __future__ import generators

import types
import warnings
from zope.interface import declarations, interface

import twisted.python.components as tpc

from nevow import inevow
from nevow import tags
from nevow import util
from nevow.inevow import ISerializable

"""
# NOTE:
# If you're about to import something from this module then you probably want
# to get it from nevow.flat instead. The idea is that flat's __init__.py may
# get smarter about the version of serialize/flatten/etc that is used,
# depending on what else is available. For instance, non-Twisted versions of
# these function may be imported into nevow.flat if Twisted is not installed.
"""

def registerFlattener(flattener, forType):
    """Register a function, 'flattener', which will be invoked when an object of type 'forType'
    is encountered in the stan dom. This function should return or yield strings, or objects
    for which there is also a flattener registered.
    
    flattener should take (original, ctx) where original is the object to flatten.
    """
    if type(flattener) is str or type(forType) is str:
        assert type(flattener) is str and type(forType) is str, "Must pass both strings or no strings to registerFlattener"
        flattener = util._namedAnyWithBuiltinTranslation(flattener)
        forType = util._namedAnyWithBuiltinTranslation(forType)

    if not isinstance(forType, interface.InterfaceClass):
        forType = declarations.implementedBy(forType)
        
    tpc.globalRegistry.register([forType], ISerializable, 'nevow.flat', flattener)

def getFlattener(original):
    """Get a flattener function with signature (ctx, original) for the object original.
    """
    return tpc.globalRegistry.lookup1(declarations.providedBy(original), ISerializable, 'nevow.flat')

def getSerializer(obj):
    warnings.warn('getSerializer is deprecated; It has been renamed getFlattener.', stacklevel=2)
    return getFlattener(obj)


def partialflatten(context, obj):
    """Run a flattener on the object 'obj' in the context 'context'.
    
    The return results from this function will not necessarily be a string, but will probably
    need further processing.
    """
    flattener = getFlattener(obj)
    if flattener is not None:
        return flattener(obj, context)

    raise NotImplementedError(
        'There is no flattener function registered for object %r of type %s.' %
        (obj, type(obj)))


def serialize(obj, context):
    #warnings.warn('serialize is deprecated; it has been renamed partialflatten.', stacklevel=2)
    return partialflatten(context, obj)


def iterflatten(stan, ctx, writer, shouldYieldItem=None):
    """This is the main meat of the nevow renderer. End-user programmers should
    instead use either flatten or precompile.
    """
    # 'rest' is a list of generators.
    # initialize as one-element list of a one-element generator of 
    rest = [ iter([partialflatten(ctx, stan)]) ]
    straccum = []
    while rest:
        gen = rest.pop()
        for item in gen:
            if isinstance(item, str):
                straccum.append(item)
            elif isinstance(item, unicode):
                straccum.append(item.encode('utf8'))
            elif isinstance(item, (list, types.GeneratorType)):
                # stop iterating this generator and put it back on the stack
                # and start iterating the new item instead.
                rest.append(gen)
                rest.append(iter(item))
                break
            else:
                if straccum:
                    writer(tags.raw(''.join(straccum)))
                    del straccum[:]
                if shouldYieldItem is not None and shouldYieldItem(item):
                    replacement = []
                    yield item, replacement.append
                    rest.append(gen)
                    rest.append(iter([replacement]))
                    break
                else:
                    if ctx.precompile:
                        ## We're precompiling and this is an item which can't be calculated until render time
                        ## add it to the list in 'precompile'
                        writer(item)
                    else:
                        rest.append(gen)
                        rest.append(iter([partialflatten(ctx, item)]))
                        break

    if straccum:
        writer(tags.raw(''.join(straccum)))


def flatten(stan, ctx=None):
    """Given the stan and the optional context, return a string containing the
    representation of the tree in the given context.
    """
    if ctx is None:
        from nevow.context import RequestContext, PageContext
        from nevow.testutil import FakeRequest
        ctx = PageContext(tag=None, parent=RequestContext(tag=FakeRequest()))
        ctx.remember(None, inevow.IData)
    result = []
    list(iterflatten(stan, ctx, result.append))
    return tags.raw(''.join(result))


def precompile(stan, ctx=None):
    """Given the stan and the optional context, return a list of strings and
    Context instances, optimizing as much static content as possible into contiguous
    string runs.

    The Context instances will have Tag instances whose .children have also been
    precompiled.
    """
    from nevow.context import WovenContext
    newctx = WovenContext(precompile=True)
    if ctx is not None:
        macroFactory = inevow.IMacroFactory(ctx, None)
        if macroFactory is not None:
            newctx.remember(macroFactory, inevow.IMacroFactory)
    doc = []
    list(iterflatten(stan, newctx, doc.append))
    return doc

