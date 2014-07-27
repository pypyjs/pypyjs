
import _rawffi
from _rawffi import alt as _ffi
from _ctypes.basics import _CData, _CDataMeta, cdata_from_address, ArgumentError
from _ctypes.basics import keepalive_key, store_reference, ensure_objects
from _ctypes.basics import sizeof, byref, as_ffi_pointer
from _ctypes.array import Array, array_get_slice_params, array_slice_getitem,\
     array_slice_setitem

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f

# This cache maps types to pointers to them.
_pointer_type_cache = {}

DEFAULT_VALUE = object()

class PointerType(_CDataMeta):
    def __new__(self, name, cls, typedict):
        d = dict(
            size       = _rawffi.sizeof('P'),
            align      = _rawffi.alignment('P'),
            length     = 1,
            _ffiargshape = 'P',
            _ffishape  = 'P',
            _fficompositesize = None,
        )
        # XXX check if typedict['_type_'] is any sane
        # XXX remember about paramfunc
        obj = type.__new__(self, name, cls, typedict)
        for k, v in d.iteritems():
            setattr(obj, k, v)
        if '_type_' in typedict:
            self.set_type(obj, typedict['_type_'])
        else:
            def __init__(self, value=None):
                raise TypeError("%s has no type" % obj)
            obj.__init__ = __init__
        return obj

    def from_param(self, value):
        if value is None:
            return self(None)
        # If we expect POINTER(<type>), but receive a <type> instance, accept
        # it by calling byref(<type>).
        if isinstance(value, self._type_):
            return byref(value)
        # Array instances are also pointers when the item types are the same.
        if isinstance(value, (_Pointer, Array)):
            if issubclass(type(value)._type_, self._type_):
                return value
        return _CDataMeta.from_param(self, value)

    def _sizeofinstances(self):
        return _rawffi.sizeof('P')

    def _alignmentofinstances(self):
        return _rawffi.alignment('P')

    def _is_pointer_like(self):
        return True

    def set_type(self, TP):
        ffiarray = _rawffi.Array('P')
        def __init__(self, value=None):
            if not hasattr(self, '_buffer'):
                self._buffer = ffiarray(1, autofree=True)
            if value is not None:
                self.contents = value
        self._ffiarray = ffiarray
        self.__init__ = __init__
        self._type_ = TP
        self._ffiargtype = _ffi.types.Pointer(TP.get_ffi_argtype())

    from_address = cdata_from_address

class _Pointer(_CData):
    __metaclass__ = PointerType

    def getcontents(self):
        addr = self._buffer[0]
        if addr == 0:
            raise ValueError("NULL pointer access")
        instance = self._type_.from_address(addr)
        instance.__dict__['_base'] = self
        return instance

    def setcontents(self, value):
        if not isinstance(value, self._type_):
            raise TypeError("expected %s instead of %s" % (
                self._type_.__name__, type(value).__name__))
        self._objects = {keepalive_key(1):value}
        if value._ensure_objects() is not None:
            self._objects[keepalive_key(0)] = value._objects
        value = value._buffer
        self._buffer[0] = value

    _get_slice_params = array_get_slice_params
    _slice_getitem = array_slice_getitem

    def _subarray(self, index=0):
        """Return a _rawffi array of length 1 whose address is the same as
        the index'th item to which self is pointing."""
        address = self._buffer[0]
        address += index * sizeof(self._type_)
        return self._type_.from_address(address)._buffer

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self._slice_getitem(index)
        return self._type_._CData_output(self._subarray(index), self, index)

    def __setitem__(self, index, value):
        cobj = self._type_.from_param(value)
        if ensure_objects(cobj) is not None:
            store_reference(self, index, cobj._objects)
        self._subarray(index)[0] = cobj._get_buffer_value()

    def __nonzero__(self):
        return self._buffer[0] != 0

    contents = property(getcontents, setcontents)
    _obj = property(getcontents) # byref interface

    def _as_ffi_pointer_(self, ffitype):
        return as_ffi_pointer(self, ffitype)


def _cast_addr(obj, _, tp):
    if not (isinstance(tp, _CDataMeta) and tp._is_pointer_like()):
        raise TypeError("cast() argument 2 must be a pointer type, not %s"
                        % (tp,))
    if isinstance(obj, (int, long)):
        result = tp()
        result._buffer[0] = obj
        return result
    elif obj is None:
        result = tp()
        return result
    elif isinstance(obj, Array):
        ptr = tp.__new__(tp)
        ptr._buffer = tp._ffiarray(1, autofree=True)
        ptr._buffer[0] = obj._buffer
        result = ptr
    elif not (isinstance(obj, _CData) and type(obj)._is_pointer_like()):
        raise TypeError("cast() argument 1 must be a pointer, not %s"
                        % (type(obj),))
    else:
        result = tp()
        result._buffer[0] = obj._buffer[0]

    # The casted objects '_objects' member:
    # From now on, both objects will use the same dictionary
    # It must certainly contain the source objects
    # It must contain the source object itself.
    if obj._ensure_objects() is not None:
        result._objects = obj._objects
        if isinstance(obj._objects, dict):
            result._objects[id(obj)] =  obj

    return result

@builtinify
def POINTER(cls):
    try:
        return _pointer_type_cache[cls]
    except KeyError:
        pass
    if type(cls) is str:
        klass = type(_Pointer)("LP_%s" % cls,
                               (_Pointer,),
                               {})
        _pointer_type_cache[id(klass)] = klass
        return klass
    else:
        name = "LP_%s" % cls.__name__
        klass = type(_Pointer)(name,
                               (_Pointer,),
                               {'_type_': cls})
        _pointer_type_cache[cls] = klass
    return klass

@builtinify
def pointer(inst):
    return POINTER(type(inst))(inst)

