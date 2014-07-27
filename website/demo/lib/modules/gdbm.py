import cffi, os

ffi = cffi.FFI()
ffi.cdef('''
#define GDBM_READER ...
#define GDBM_WRITER ...
#define GDBM_WRCREAT ...
#define GDBM_NEWDB ...
#define GDBM_FAST ...
#define GDBM_SYNC ...
#define GDBM_NOLOCK ...
#define GDBM_REPLACE ...

void* gdbm_open(char *, int, int, int, void (*)());
void gdbm_close(void*);

typedef struct {
    char *dptr;
    int   dsize;
} datum;

datum gdbm_fetch(void*, datum);
int gdbm_delete(void*, datum);
int gdbm_store(void*, datum, datum, int);
int gdbm_exists(void*, datum);

int gdbm_reorganize(void*);

datum gdbm_firstkey(void*);
datum gdbm_nextkey(void*, datum);
void gdbm_sync(void*);

char* gdbm_strerror(int);
int gdbm_errno;

void free(void*);
''')

try:
    lib = ffi.verify('''
    #include "gdbm.h"
    ''', libraries=['gdbm'])
except cffi.VerificationError as e:
    # distutils does not preserve the actual message,
    # but the verification is simple enough that the
    # failure must be due to missing gdbm dev libs
    raise ImportError('%s: %s' %(e.__class__.__name__, e))

class error(Exception):
    pass

def _fromstr(key):
    if not isinstance(key, str):
        raise TypeError("gdbm mappings have string indices only")
    return {'dptr': ffi.new("char[]", key), 'dsize': len(key)}

class gdbm(object):
    ll_dbm = None

    def __init__(self, filename, iflags, mode):
        res = lib.gdbm_open(filename, 0, iflags, mode, ffi.NULL)
        self.size = -1
        if not res:
            self._raise_from_errno()
        self.ll_dbm = res

    def close(self):
        if self.ll_dbm:
            lib.gdbm_close(self.ll_dbm)
            self.ll_dbm = None

    def _raise_from_errno(self):
        if ffi.errno:
            raise error(os.strerror(ffi.errno))
        raise error(lib.gdbm_strerror(lib.gdbm_errno))

    def __len__(self):
        if self.size < 0:
            self.size = len(self.keys())
        return self.size

    def __setitem__(self, key, value):
        self._check_closed()
        self._size = -1
        r = lib.gdbm_store(self.ll_dbm, _fromstr(key), _fromstr(value),
                           lib.GDBM_REPLACE)
        if r < 0:
            self._raise_from_errno()

    def __delitem__(self, key):
        self._check_closed()
        res = lib.gdbm_delete(self.ll_dbm, _fromstr(key))
        if res < 0:
            raise KeyError(key)

    def __contains__(self, key):
        self._check_closed()
        return lib.gdbm_exists(self.ll_dbm, _fromstr(key))
    has_key = __contains__

    def __getitem__(self, key):
        self._check_closed()
        drec = lib.gdbm_fetch(self.ll_dbm, _fromstr(key))
        if not drec.dptr:
            raise KeyError(key)
        res = str(ffi.buffer(drec.dptr, drec.dsize))
        lib.free(drec.dptr)
        return res

    def keys(self):
        self._check_closed()
        l = []
        key = lib.gdbm_firstkey(self.ll_dbm)
        while key.dptr:
            l.append(str(ffi.buffer(key.dptr, key.dsize)))
            nextkey = lib.gdbm_nextkey(self.ll_dbm, key)
            lib.free(key.dptr)
            key = nextkey
        return l

    def firstkey(self):
        self._check_closed()
        key = lib.gdbm_firstkey(self.ll_dbm)
        if key.dptr:
            res = str(ffi.buffer(key.dptr, key.dsize))
            lib.free(key.dptr)
            return res

    def nextkey(self, key):
        self._check_closed()
        key = lib.gdbm_nextkey(self.ll_dbm, _fromstr(key))
        if key.dptr:
            res = str(ffi.buffer(key.dptr, key.dsize))
            lib.free(key.dptr)
            return res

    def reorganize(self):
        self._check_closed()
        if lib.gdbm_reorganize(self.ll_dbm) < 0:
            self._raise_from_errno()

    def _check_closed(self):
        if not self.ll_dbm:
            raise error("GDBM object has already been closed")

    __del__ = close

    def sync(self):
        self._check_closed()
        lib.gdbm_sync(self.ll_dbm)

def open(filename, flags='r', mode=0666):
    if flags[0] == 'r':
        iflags = lib.GDBM_READER
    elif flags[0] == 'w':
        iflags = lib.GDBM_WRITER
    elif flags[0] == 'c':
        iflags = lib.GDBM_WRCREAT
    elif flags[0] == 'n':
        iflags = lib.GDBM_NEWDB
    else:
        raise error("First flag must be one of 'r', 'w', 'c' or 'n'")
    for flag in flags[1:]:
        if flag == 'f':
            iflags |= lib.GDBM_FAST
        elif flag == 's':
            iflags |= lib.GDBM_SYNC
        elif flag == 'u':
            iflags |= lib.GDBM_NOLOCK
        else:
            raise error("Flag '%s' not supported" % flag)
    return gdbm(filename, iflags, mode)

open_flags = "rwcnfsu"
