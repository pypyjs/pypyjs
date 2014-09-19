import imp
import os

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
    cfile = '_ctypes_test.c'
    thisdir = os.path.dirname(__file__)
    output_dir = _pypy_testcapi.get_hashed_dir(os.path.join(thisdir, cfile))
    try:
        fp, filename, description = imp.find_module('_ctypes_test', path=[output_dir])
        with fp:
            imp.load_module('_ctypes_test', fp, filename, description)
    except ImportError:
        print('could not find _ctypes_test in %s' % output_dir)
        _pypy_testcapi.compile_shared('_ctypes_test.c', '_ctypes_test', output_dir)
