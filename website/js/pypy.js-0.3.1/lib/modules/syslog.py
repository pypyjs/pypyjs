# this cffi version was rewritten based on the
# ctypes implementation: Victor Stinner, 2008-05-08
"""
This module provides an interface to the Unix syslog library routines.
Refer to the Unix manual pages for a detailed description of the
syslog facility.
"""

import sys
if sys.platform == 'win32':
    raise ImportError("No syslog on Windows")

from cffi import FFI

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f

ffi = FFI()

ffi.cdef("""
/* mandatory constants */
#define LOG_EMERG ...
#define LOG_ALERT ...
#define LOG_CRIT ...
#define LOG_ERR ...
#define LOG_WARNING ...
#define LOG_NOTICE ...
#define LOG_INFO ...
#define LOG_DEBUG ...

#define LOG_PID ...
#define LOG_CONS ...
#define LOG_NDELAY ...

#define LOG_KERN ...
#define LOG_USER ...
#define LOG_MAIL ...
#define LOG_DAEMON ...
#define LOG_AUTH ...
#define LOG_LPR ...
#define LOG_LOCAL0 ...
#define LOG_LOCAL1 ...
#define LOG_LOCAL2 ...
#define LOG_LOCAL3 ...
#define LOG_LOCAL4 ...
#define LOG_LOCAL5 ...
#define LOG_LOCAL6 ...
#define LOG_LOCAL7 ...

/* optional constants, gets defined to -919919 if missing */
#define LOG_NOWAIT ...
#define LOG_PERROR ...

/* aliased constants, gets defined as some other constant if missing */
#define LOG_SYSLOG ...
#define LOG_CRON ...
#define LOG_UUCP ...
#define LOG_NEWS ...

/* functions */
void openlog(const char *ident, int option, int facility);
void syslog(int priority, const char *format, const char *string);
// NB. the signature of syslog() is specialized to the only case we use
void closelog(void);
int setlogmask(int mask);
""")

lib = ffi.verify("""
#include <syslog.h>

#ifndef LOG_NOWAIT
#define LOG_NOWAIT -919919
#endif
#ifndef LOG_PERROR
#define LOG_PERROR -919919
#endif
#ifndef LOG_SYSLOG
#define LOG_SYSLOG LOG_DAEMON
#endif
#ifndef LOG_CRON
#define LOG_CRON LOG_DAEMON
#endif
#ifndef LOG_UUCP
#define LOG_UUCP LOG_MAIL
#endif
#ifndef LOG_NEWS
#define LOG_NEWS LOG_MAIL
#endif
""")


_S_log_open = False
_S_ident_o = None

def _get_argv():
    try:
        import sys
        script = sys.argv[0]
        if isinstance(script, str):
            return script[script.rfind('/')+1:] or None
    except Exception:
        pass
    return None

@builtinify
def openlog(ident=None, logoption=0, facility=lib.LOG_USER):
    global _S_ident_o, _S_log_open
    if ident is None:
        ident = _get_argv()
    if ident is None:
        _S_ident_o = ffi.NULL
    elif isinstance(ident, str):
        _S_ident_o = ffi.new("char[]", ident)    # keepalive
    else:
        raise TypeError("'ident' must be a string or None")
    lib.openlog(_S_ident_o, logoption, facility)
    _S_log_open = True

@builtinify
def syslog(arg1, arg2=None):
    if arg2 is not None:
        priority, message = arg1, arg2
    else:
        priority, message = LOG_INFO, arg1
    # if log is not opened, open it now
    if not _S_log_open:
        openlog()
    lib.syslog(priority, "%s", message)

@builtinify
def closelog():
    global _S_log_open, S_ident_o
    if _S_log_open:
        lib.closelog()
        _S_log_open = False
        _S_ident_o = None

@builtinify
def setlogmask(mask):
    return lib.setlogmask(mask)

@builtinify
def LOG_MASK(pri):
    return (1 << pri)

@builtinify
def LOG_UPTO(pri):
    return (1 << (pri + 1)) - 1

__all__ = []

for name in sorted(lib.__dict__):
    if name.startswith('LOG_'):
        value = getattr(lib, name)
        if value != -919919:
            globals()[name] = value
            __all__.append(name)

__all__ = tuple(__all__) + (
    'openlog', 'syslog', 'closelog', 'setlogmask',
    'LOG_MASK', 'LOG_UPTO')
