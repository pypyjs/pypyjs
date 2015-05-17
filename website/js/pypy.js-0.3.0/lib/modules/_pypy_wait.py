from resource import _struct_rusage, struct_rusage
from ctypes import CDLL, c_int, POINTER, byref
from ctypes.util import find_library

__all__ = ["wait3", "wait4"]

libc = CDLL(find_library("c"))
c_wait3 = libc.wait3
c_wait3.argtypes = [POINTER(c_int), c_int, POINTER(_struct_rusage)]
c_wait3.restype = c_int

c_wait4 = libc.wait4
c_wait4.argtypes = [c_int, POINTER(c_int), c_int, POINTER(_struct_rusage)]
c_wait4.restype = c_int

def create_struct_rusage(c_struct):
    return struct_rusage((
        float(c_struct.ru_utime),
        float(c_struct.ru_stime),
        c_struct.ru_maxrss,
        c_struct.ru_ixrss,
        c_struct.ru_idrss,
        c_struct.ru_isrss,
        c_struct.ru_minflt,
        c_struct.ru_majflt,
        c_struct.ru_nswap,
        c_struct.ru_inblock,
        c_struct.ru_oublock,
        c_struct.ru_msgsnd,
        c_struct.ru_msgrcv,
        c_struct.ru_nsignals,
        c_struct.ru_nvcsw,
        c_struct.ru_nivcsw))

def wait3(options):
    status = c_int()
    _rusage = _struct_rusage()
    pid = c_wait3(byref(status), c_int(options), byref(_rusage))

    rusage = create_struct_rusage(_rusage)

    return pid, status.value, rusage

def wait4(pid, options):
    status = c_int()
    _rusage = _struct_rusage()
    pid = c_wait4(c_int(pid), byref(status), c_int(options), byref(_rusage))

    rusage = create_struct_rusage(_rusage)

    return pid, status.value, rusage
