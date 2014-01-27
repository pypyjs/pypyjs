import sys, os
from ctypes_configure import dumpcache

def dumpcache2(basename, config):
    size = 32 if sys.maxint <= 2**32 else 64
    filename = '_%s_%s_.py' % (basename, size)
    dumpcache.dumpcache(__file__, filename, config)
    #
    filename = os.path.join(os.path.dirname(__file__),
                            '_%s_cache.py' % (basename,))
    g = open(filename, 'w')
    print >> g, '''\
import sys
_size = 32 if sys.maxint <= 2**32 else 64
# XXX relative import, should be removed together with
# XXX the relative imports done e.g. by lib_pypy/pypy_test/test_hashlib
_mod = __import__("_%s_%%s_" %% (_size,),
                  globals(), locals(), ["*"])
globals().update(_mod.__dict__)\
''' % (basename,)
    g.close()
