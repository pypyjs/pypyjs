import sys
_size = 32 if sys.maxint <= 2**32 else 64
# XXX relative import, should be removed together with
# XXX the relative imports done e.g. by lib_pypy/pypy_test/test_hashlib
_mod = __import__("_locale_%s_" % (_size,),
                  globals(), locals(), ["*"])
globals().update(_mod.__dict__)
