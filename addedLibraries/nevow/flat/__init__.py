# Copyright (c) 2004 Divmod.
# See LICENSE for details.

'''The flat package contains modules responsible for converting to and from DOM
and serialized XML.'''

from nevow.flat.ten import flatten, precompile, iterflatten, getSerializer, serialize, registerFlattener, getFlattener, partialflatten


try:
    import twisted
    def flattenFactory(stan, ctx, writer, finisher):
        from nevow.flat.twist import deferflatten
        return deferflatten(stan, ctx, writer).addCallback(finisher)
except ImportError:
    def flattenFactory(stan, ctx, writer, finisher):
        list(iterflatten(stan, ctx, writer))
        return finisher('')

