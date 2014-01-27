# ctypes implementation: Victor Stinner, 2008-05-08
"""
This module provides access to the Unix password database.
It is available on all Unix versions.

Password database entries are reported as 7-tuples containing the following
items from the password database (see `<pwd.h>'), in order:
pw_name, pw_passwd, pw_uid, pw_gid, pw_gecos, pw_dir, pw_shell.
The uid and gid items are integers, all others are strings. An
exception is raised if the entry asked for cannot be found.
"""

import sys
if sys.platform == 'win32':
    raise ImportError("No pwd module on Windows")

from ctypes_support import standard_c_lib as libc
from ctypes import Structure, POINTER, c_int, c_char_p, c_long
from _structseq import structseqtype, structseqfield

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


uid_t = c_int
gid_t = c_int
time_t = c_long

if sys.platform == 'darwin':
    class passwd(Structure):
        _fields_ = (
            ("pw_name", c_char_p),
            ("pw_passwd", c_char_p),
            ("pw_uid", uid_t),
            ("pw_gid", gid_t),
            ("pw_change", time_t),
            ("pw_class", c_char_p),
            ("pw_gecos", c_char_p),
            ("pw_dir", c_char_p),
            ("pw_shell", c_char_p),
            ("pw_expire", time_t),
            ("pw_fields", c_int),
        )
        def __iter__(self):
            yield self.pw_name
            yield self.pw_passwd
            yield self.pw_uid
            yield self.pw_gid
            yield self.pw_gecos
            yield self.pw_dir
            yield self.pw_shell
else:
    class passwd(Structure):
        _fields_ = (
            ("pw_name", c_char_p),
            ("pw_passwd", c_char_p),
            ("pw_uid", uid_t),
            ("pw_gid", gid_t),
            ("pw_gecos", c_char_p),
            ("pw_dir", c_char_p),
            ("pw_shell", c_char_p),
        )
        def __iter__(self):
            yield self.pw_name
            yield self.pw_passwd
            yield self.pw_uid
            yield self.pw_gid
            yield self.pw_gecos
            yield self.pw_dir
            yield self.pw_shell

class struct_passwd:
    """
    pwd.struct_passwd: Results from getpw*() routines.

    This object may be accessed either as a tuple of
      (pw_name,pw_passwd,pw_uid,pw_gid,pw_gecos,pw_dir,pw_shell)
    or via the object attributes as named in the above tuple.
    """
    __metaclass__ = structseqtype
    name = "pwd.struct_passwd"
    pw_name = structseqfield(0)
    pw_passwd = structseqfield(1)
    pw_uid = structseqfield(2)
    pw_gid = structseqfield(3)
    pw_gecos = structseqfield(4)
    pw_dir = structseqfield(5)
    pw_shell = structseqfield(6)

passwd_p = POINTER(passwd)

_getpwuid = libc.getpwuid
_getpwuid.argtypes = (uid_t,)
_getpwuid.restype = passwd_p

_getpwnam = libc.getpwnam
_getpwnam.argtypes = (c_char_p,)
_getpwnam.restype = passwd_p

_setpwent = libc.setpwent
_setpwent.argtypes = None
_setpwent.restype = None

_getpwent = libc.getpwent
_getpwent.argtypes = None
_getpwent.restype = passwd_p

_endpwent = libc.endpwent
_endpwent.argtypes = None
_endpwent.restype = None

@builtinify
def mkpwent(pw):
    pw = pw.contents
    return struct_passwd(pw)

@builtinify
def getpwuid(uid):
    """
    getpwuid(uid) -> (pw_name,pw_passwd,pw_uid,
                      pw_gid,pw_gecos,pw_dir,pw_shell)
    Return the password database entry for the given numeric user ID.
    See pwd.__doc__ for more on password database entries.
    """
    pw = _getpwuid(uid)
    if not pw:
        raise KeyError("getpwuid(): uid not found: %s" % uid)
    return mkpwent(pw)

@builtinify
def getpwnam(name):
    """
    getpwnam(name) -> (pw_name,pw_passwd,pw_uid,
                        pw_gid,pw_gecos,pw_dir,pw_shell)
    Return the password database entry for the given user name.
    See pwd.__doc__ for more on password database entries.
    """
    if not isinstance(name, str):
        raise TypeError("expected string")
    pw = _getpwnam(name)
    if not pw:
        raise KeyError("getpwname(): name not found: %s" % name)
    return mkpwent(pw)

@builtinify
def getpwall():
    """
    getpwall() -> list_of_entries
    Return a list of all available password database entries, in arbitrary order.
    See pwd.__doc__ for more on password database entries.
    """
    users = []
    _setpwent()
    while True:
        pw = _getpwent()
        if not pw:
            break
        users.append(mkpwent(pw))
    _endpwent()
    return users

__all__ = ('struct_passwd', 'getpwuid', 'getpwnam', 'getpwall')

if __name__ == "__main__":
# Uncomment next line to test CPython implementation
#    from pwd import getpwuid, getpwnam, getpwall
    from os import getuid
    uid = getuid()
    pw = getpwuid(uid)
    print("uid %s: %s" % (pw.pw_uid, pw))
    name = pw.pw_name
    print("name %r: %s" % (name, getpwnam(name)))
    print("All:")
    for pw in getpwall():
        print(pw)

