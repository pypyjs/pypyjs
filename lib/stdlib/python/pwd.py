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

import _structseq

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


class struct_passwd:
    """
    pwd.struct_passwd: Results from getpw*() routines.

    This object may be accessed either as a tuple of
      (pw_name,pw_passwd,pw_uid,pw_gid,pw_gecos,pw_dir,pw_shell)
    or via the object attributes as named in the above tuple.
    """
    name = "pwd.struct_passwd"

    pw_name = "pypyjs"
    pw_uid = 1000
    pw_gid = 1000
    pw_dir = '/'
    pw_shell = '/lib/pypyjs/pypyjs.js'


@builtinify
def getpwuid(uid):
    """
    getpwuid(uid) -> (pw_name,pw_passwd,pw_uid,
                      pw_gid,pw_gecos,pw_dir,pw_shell)
    Return the password database entry for the given numeric user ID.
    See pwd.__doc__ for more on password database entries.
    """
    return struct_passwd()

@builtinify
def getpwnam(name):
    """
    getpwnam(name) -> (pw_name,pw_passwd,pw_uid,
                        pw_gid,pw_gecos,pw_dir,pw_shell)
    Return the password database entry for the given user name.
    See pwd.__doc__ for more on password database entries.
    """
    if not isinstance(name, basestring):
        raise TypeError("expected string")
    name = str(name)
    raise KeyError("getpwname(): name not found: %s" % name)

@builtinify
def getpwall():
    """
    getpwall() -> list_of_entries
    Return a list of all available password database entries, in arbitrary order.
    See pwd.__doc__ for more on password database entries.
    """
    users = []
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
