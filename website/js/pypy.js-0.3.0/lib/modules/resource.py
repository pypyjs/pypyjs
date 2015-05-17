import sys
if sys.platform == 'win32':
    raise ImportError('resource module not available for win32')

# load the platform-specific cache made by running resource.ctc.py
from ctypes_config_cache._resource_cache import *

from ctypes_support import standard_c_lib as libc
from ctypes_support import get_errno
from ctypes import Structure, c_int, c_long, byref, POINTER
from errno import EINVAL, EPERM
import _structseq

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


class error(Exception):
    pass


# Read required libc functions
_getrusage = libc.getrusage
_getrlimit = libc.getrlimit
_setrlimit = libc.setrlimit
try:
    _getpagesize = libc.getpagesize
    _getpagesize.argtypes = ()
    _getpagesize.restype = c_int
except AttributeError:
    from os import sysconf
    _getpagesize = None


class timeval(Structure):
    _fields_ = (
        ("tv_sec", c_long),
        ("tv_usec", c_long),
    )
    def __str__(self):
        return "(%s, %s)" % (self.tv_sec, self.tv_usec)

    def __float__(self):
        return self.tv_sec + self.tv_usec/1000000.0

class _struct_rusage(Structure):
    _fields_ = (
        ("ru_utime", timeval),
        ("ru_stime", timeval),
        ("ru_maxrss", c_long),
        ("ru_ixrss", c_long),
        ("ru_idrss", c_long),
        ("ru_isrss", c_long),
        ("ru_minflt", c_long),
        ("ru_majflt", c_long),
        ("ru_nswap", c_long),
        ("ru_inblock", c_long),
        ("ru_oublock", c_long),
        ("ru_msgsnd", c_long),
        ("ru_msgrcv", c_long),
        ("ru_nsignals", c_long),
        ("ru_nvcsw", c_long),
        ("ru_nivcsw", c_long),
    )

_getrusage.argtypes = (c_int, POINTER(_struct_rusage))
_getrusage.restype = c_int


class struct_rusage:
    __metaclass__ = _structseq.structseqtype

    ru_utime = _structseq.structseqfield(0)
    ru_stime = _structseq.structseqfield(1)
    ru_maxrss = _structseq.structseqfield(2)
    ru_ixrss = _structseq.structseqfield(3)
    ru_idrss = _structseq.structseqfield(4)
    ru_isrss = _structseq.structseqfield(5)
    ru_minflt = _structseq.structseqfield(6)
    ru_majflt = _structseq.structseqfield(7)
    ru_nswap = _structseq.structseqfield(8)
    ru_inblock = _structseq.structseqfield(9)
    ru_oublock = _structseq.structseqfield(10)
    ru_msgsnd = _structseq.structseqfield(11)
    ru_msgrcv = _structseq.structseqfield(12)
    ru_nsignals = _structseq.structseqfield(13)
    ru_nvcsw = _structseq.structseqfield(14)
    ru_nivcsw = _structseq.structseqfield(15)

@builtinify
def rlimit_check_bounds(rlim_cur, rlim_max):
    if rlim_cur > rlim_t_max:
        raise ValueError("%d does not fit into rlim_t" % rlim_cur)
    if rlim_max > rlim_t_max:
        raise ValueError("%d does not fit into rlim_t" % rlim_max)

class rlimit(Structure):
    _fields_ = (
        ("rlim_cur", rlim_t),
        ("rlim_max", rlim_t),
    )

_getrlimit.argtypes = (c_int, POINTER(rlimit))
_getrlimit.restype = c_int
_setrlimit.argtypes = (c_int, POINTER(rlimit))
_setrlimit.restype = c_int


@builtinify
def getrusage(who):
    ru = _struct_rusage()
    ret = _getrusage(who, byref(ru))
    if ret == -1:
        errno = get_errno()
        if errno == EINVAL:
            raise ValueError("invalid who parameter")
        raise error(errno)
    return struct_rusage((
        float(ru.ru_utime),
        float(ru.ru_stime),
        ru.ru_maxrss,
        ru.ru_ixrss,
        ru.ru_idrss,
        ru.ru_isrss,
        ru.ru_minflt,
        ru.ru_majflt,
        ru.ru_nswap,
        ru.ru_inblock,
        ru.ru_oublock,
        ru.ru_msgsnd,
        ru.ru_msgrcv,
        ru.ru_nsignals,
        ru.ru_nvcsw,
        ru.ru_nivcsw,
        ))

@builtinify
def getrlimit(resource):
    if not(0 <= resource < RLIM_NLIMITS):
        return ValueError("invalid resource specified")

    rlim = rlimit()
    ret = _getrlimit(resource, byref(rlim))
    if ret == -1:
        errno = get_errno()
        raise error(errno)
    return (rlim.rlim_cur, rlim.rlim_max)

@builtinify
def setrlimit(resource, rlim):
    if not(0 <= resource < RLIM_NLIMITS):
        return ValueError("invalid resource specified")
    rlimit_check_bounds(*rlim)
    rlim = rlimit(rlim[0], rlim[1])

    ret = _setrlimit(resource, byref(rlim))
    if ret == -1:
        errno = get_errno()
        if errno == EINVAL:
            return ValueError("current limit exceeds maximum limit")
        elif errno == EPERM:
            return ValueError("not allowed to raise maximum limit")
        else:
            raise error(errno)

@builtinify
def getpagesize():
    if _getpagesize:
        return _getpagesize()
    else:
        try:
            return sysconf("SC_PAGE_SIZE")
        except ValueError:
            # Irix 5.3 has _SC_PAGESIZE, but not _SC_PAGE_SIZE
            return sysconf("SC_PAGESIZE")

__all__ = ALL_CONSTANTS + (
    'error', 'timeval', 'struct_rusage', 'rlimit',
    'getrusage', 'getrlimit', 'setrlimit', 'getpagesize',
)

del ALL_CONSTANTS
