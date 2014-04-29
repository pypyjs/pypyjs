try:
    import cpyext
except ImportError:
    raise ImportError("No module named '_testcapi'")
else:
    import _pypy_testcapi
    _pypy_testcapi.compile_shared('_testcapimodule.c', '_testcapi')
