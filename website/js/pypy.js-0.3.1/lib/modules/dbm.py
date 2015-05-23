from ctypes import Structure, c_char_p, c_int, c_void_p, CDLL, POINTER, c_char
import ctypes.util
import os, sys

class error(Exception):
    def __init__(self, msg):
        self.msg = msg  

    def __str__(self):
        return self.msg

class datum(Structure):
    _fields_ = [
    ('dptr', POINTER(c_char)),
    ('dsize', c_int),
    ]

    def __init__(self, text):
        if not isinstance(text, str):
            raise TypeError("datum: expected string, not %s" % type(text))
        Structure.__init__(self, text, len(text))

class dbm(object):
    def __init__(self, dbmobj):
        self._aobj = dbmobj

    def close(self):
        if not self._aobj:
            raise error('DBM object has already been closed')
        getattr(lib, funcs['close'])(self._aobj)
        self._aobj = None

    def __del__(self):
        if self._aobj:
            self.close()

    def keys(self):
        if not self._aobj:
            raise error('DBM object has already been closed')
        allkeys = []
        k = getattr(lib, funcs['firstkey'])(self._aobj)
        while k.dptr:
            allkeys.append(k.dptr[:k.dsize])
            k = getattr(lib, funcs['nextkey'])(self._aobj)
        return allkeys

    def get(self, key, default=None):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum(key)
        k = getattr(lib, funcs['fetch'])(self._aobj, dat)
        if k.dptr:
            return k.dptr[:k.dsize]
        if getattr(lib, funcs['error'])(self._aobj):
            getattr(lib, funcs['clearerr'])(self._aobj)
            raise error("")
        return default

    def __len__(self):
        return len(self.keys())

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        if not self._aobj: 
            raise error('DBM object has already been closed')
        dat = datum(key)
        data = datum(value)
        status = getattr(lib, funcs['store'])(self._aobj, dat, data, lib.DBM_REPLACE)
        if getattr(lib, funcs['error'])(self._aobj):
            getattr(lib, funcs['clearerr'])(self._aobj)
            raise error("")
        return status

    def setdefault(self, key, default=''):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum(key)
        k = getattr(lib, funcs['fetch'])(self._aobj, dat)
        if k.dptr:
            return k.dptr[:k.dsize]
        data = datum(default)
        status = getattr(lib, funcs['store'])(self._aobj, dat, data, lib.DBM_INSERT)
        if status < 0:
            getattr(lib, funcs['clearerr'])(self._aobj)
            raise error("cannot add item to database")
        return default

    def __contains__(self, key):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum(key)
        k = getattr(lib, funcs['fetch'])(self._aobj, dat)
        if k.dptr:
            return True
        return False
    has_key = __contains__

    def __delitem__(self, key):
        if not self._aobj:
            raise error('DBM object has already been closed')
        dat = datum(key)
        status = getattr(lib, funcs['delete'])(self._aobj, dat)
        if status < 0:
            raise KeyError(key)

### initialization: Berkeley DB versus normal DB

def _init_func(name, argtypes=None, restype=None):
    try:
        func = getattr(lib, '__db_ndbm_' + name)
        funcs[name] = '__db_ndbm_' + name
    except AttributeError:
        func = getattr(lib, 'dbm_' + name)
        funcs[name] = 'dbm_' + name
    if argtypes is not None:
        func.argtypes = argtypes
    if restype is not None:
        func.restype = restype

if sys.platform != 'darwin':
    libpath = ctypes.util.find_library('db')
    if not libpath:
        # XXX this is hopeless...
        for c in ['5.3', '5.2', '5.1', '5.0', '4.9', '4.8', '4.7', '4.6', '4.5']:
            libpath = ctypes.util.find_library('db-%s' % c)
            if libpath:
                break
        else:
            raise ImportError("Cannot find dbm library")
    lib = CDLL(libpath) # Linux
    _platform = 'bdb'
else:
    lib = CDLL("/usr/lib/libdbm.dylib") # OS X
    _platform = 'osx'

library = "GNU gdbm"

funcs = {}
_init_func('open', (c_char_p, c_int, c_int), restype=c_void_p)
_init_func('close', (c_void_p,), restype=c_void_p)
_init_func('firstkey', (c_void_p,), restype=datum)
_init_func('nextkey', (c_void_p,), restype=datum)
_init_func('fetch', (c_void_p, datum), restype=datum)
_init_func('store', (c_void_p, datum, datum, c_int), restype=c_int)
_init_func('error', (c_void_p,), restype=c_int)
_init_func('delete', (c_void_p, datum), restype=c_int)

lib.DBM_INSERT = 0
lib.DBM_REPLACE = 1

def open(filename, flag='r', mode=0666):
    "open a DBM database"
    if not isinstance(filename, str):
        raise TypeError("expected string")

    openflag = 0

    try:
        openflag = {
            'r': os.O_RDONLY,
            'rw': os.O_RDWR,
            'w': os.O_RDWR | os.O_CREAT,
            'c': os.O_RDWR | os.O_CREAT,
            'n': os.O_RDWR | os.O_CREAT | os.O_TRUNC,
            }[flag]
    except KeyError:
        raise error("arg 2 to open should be 'r', 'w', 'c', or 'n'")

    a_db = getattr(lib, funcs['open'])(filename, openflag, mode)
    if a_db == 0:
        raise error("Could not open file %s.db" % filename)
    return dbm(a_db)

__all__ = ('datum', 'dbm', 'error', 'funcs', 'open', 'library')

