import imp
import os

try:
    import cpyext
except ImportError:
    raise ImportError("No module named '_testcapi'")

import _pypy_testcapi
cfile = '_testcapimodule.c'
thisdir = os.path.dirname(__file__)
output_dir = _pypy_testcapi.get_hashed_dir(os.path.join(thisdir, cfile))

try:
    fp, filename, description = imp.find_module('_testcapi', path=[output_dir])
    with fp:
        imp.load_module('_testcapi', fp, filename, description)
except ImportError:
    _pypy_testcapi.compile_shared(cfile, '_testcapi', output_dir)
