# _tkinter package -- low-level interface to libtk and libtcl.
#
# This is an internal module, applications should "import Tkinter" instead.
#
# This version is based on cffi, and is a translation of _tkinter.c
# from CPython, version 2.7.4.

class TclError(Exception):
    pass

import cffi
try:
    from .tklib import tklib, tkffi
except cffi.VerificationError:
    raise ImportError("Tk headers and development libraries are required")

from .app import TkApp

TK_VERSION = tkffi.string(tklib.get_tk_version())
TCL_VERSION = tkffi.string(tklib.get_tcl_version())

READABLE = tklib.TCL_READABLE
WRITABLE = tklib.TCL_WRITABLE
EXCEPTION = tklib.TCL_EXCEPTION
DONT_WAIT = tklib.TCL_DONT_WAIT

def create(screenName=None, baseName=None, className=None,
           interactive=False, wantobjects=False, wantTk=True,
           sync=False, use=None):
    return TkApp(screenName, baseName, className,
                 interactive, wantobjects, wantTk, sync, use)

def _flatten(item):
    def _flatten1(output, item, depth):
        if depth > 1000:
            raise ValueError("nesting too deep in _flatten")
        if not isinstance(item, (list, tuple)):
            raise TypeError("argument must be sequence")
        # copy items to output tuple
        for o in item:
            if isinstance(o, (list, tuple)):
                _flatten1(output, o, depth + 1)
            elif o is not None:
                output.append(o)

    result = []
    _flatten1(result, item, 0)
    return tuple(result)
    
