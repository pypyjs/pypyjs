
""" This module provides ctypes version of cpython's grp module
"""

import sys
if sys.platform == 'win32':
    raise ImportError("No grp module on Windows")

from ctypes import Structure, c_char_p, c_int, POINTER
from ctypes_support import standard_c_lib as libc
import _structseq

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


gid_t = c_int

class GroupStruct(Structure):
    _fields_ = (
        ('gr_name', c_char_p),
        ('gr_passwd', c_char_p),
        ('gr_gid', gid_t),
        ('gr_mem', POINTER(c_char_p)),
        )

class struct_group:
    __metaclass__ = _structseq.structseqtype

    gr_name   = _structseq.structseqfield(0)
    gr_passwd = _structseq.structseqfield(1)
    gr_gid    = _structseq.structseqfield(2)
    gr_mem    = _structseq.structseqfield(3)

libc.getgrgid.argtypes = [gid_t]
libc.getgrgid.restype = POINTER(GroupStruct)

libc.getgrnam.argtypes = [c_char_p]
libc.getgrnam.restype = POINTER(GroupStruct)

libc.getgrent.argtypes = []
libc.getgrent.restype = POINTER(GroupStruct)

libc.setgrent.argtypes = []
libc.setgrent.restype = None

libc.endgrent.argtypes = []
libc.endgrent.restype = None

def _group_from_gstruct(res):
    i = 0
    mem = []
    while res.contents.gr_mem[i]:
        mem.append(res.contents.gr_mem[i])
        i += 1
    return struct_group((res.contents.gr_name, res.contents.gr_passwd,
                         res.contents.gr_gid, mem))

@builtinify
def getgrgid(gid):
    res = libc.getgrgid(gid)
    if not res:
        # XXX maybe check error eventually
        raise KeyError(gid)
    return _group_from_gstruct(res)

@builtinify
def getgrnam(name):
    if not isinstance(name, basestring):
        raise TypeError("expected string")
    name = str(name)
    res = libc.getgrnam(name)
    if not res:
        raise KeyError("'getgrnam(): name not found: %s'" % name)
    return _group_from_gstruct(res)

@builtinify
def getgrall():
    libc.setgrent()
    lst = []
    while 1:
        p = libc.getgrent()
        if not p:
            libc.endgrent()
            return lst
        lst.append(_group_from_gstruct(p))
