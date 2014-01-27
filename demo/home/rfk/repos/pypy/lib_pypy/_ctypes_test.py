try:
    import cpyext
except ImportError:
    raise ImportError("No module named '_ctypes_test'")
try:
    import _ctypes
    _ctypes.PyObj_FromPtr = None
    del _ctypes
except ImportError:
    pass    # obscure condition of _ctypes_test.py being imported by py.test
else:
    import _pypy_testcapi
    _pypy_testcapi.compile_shared('_ctypes_test.c', '_ctypes_test')
