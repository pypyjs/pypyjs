import sys
import _continuation

__version__ = "0.4.5"

# ____________________________________________________________
# Exceptions

class GreenletExit(BaseException):
    """This special exception does not propagate to the parent greenlet; it
can be used to kill a single greenlet."""

error = _continuation.error

# ____________________________________________________________
# Helper function

def getcurrent():
    "Returns the current greenlet (i.e. the one which called this function)."
    try:
        return _tls.current
    except AttributeError:
        # first call in this thread: current == main
        _green_create_main()
        return _tls.current

# ____________________________________________________________
# The 'greenlet' class

_continulet = _continuation.continulet

class greenlet(_continulet):
    getcurrent = staticmethod(getcurrent)
    error = error
    GreenletExit = GreenletExit
    __main = False
    __started = False

    def __new__(cls, *args, **kwds):
        self = _continulet.__new__(cls)
        self.parent = getcurrent()
        return self

    def __init__(self, run=None, parent=None):
        if run is not None:
            self.run = run
        if parent is not None:
            self.parent = parent

    def switch(self, *args, **kwds):
        "Switch execution to this greenlet, optionally passing the values "
        "given as argument(s).  Returns the value passed when switching back."
        return self.__switch('switch', (args, kwds))

    def throw(self, typ=GreenletExit, val=None, tb=None):
        "raise exception in greenlet, return value passed when switching back"
        return self.__switch('throw', typ, val, tb)

    def __switch(target, methodname, *baseargs):
        current = getcurrent()
        #
        while not (target.__main or _continulet.is_pending(target)):
            # inlined __nonzero__ ^^^ in case it's overridden
            if not target.__started:
                if methodname == 'switch':
                    greenlet_func = _greenlet_start
                else:
                    greenlet_func = _greenlet_throw
                _continulet.__init__(target, greenlet_func, *baseargs)
                methodname = 'switch'
                baseargs = ()
                target.__started = True
                break
            # already done, go to the parent instead
            # (NB. infinite loop possible, but unlikely, unless you mess
            # up the 'parent' explicitly.  Good enough, because a Ctrl-C
            # will show that the program is caught in this loop here.)
            target = target.parent
            # convert a "raise GreenletExit" into "return GreenletExit"
            if methodname == 'throw':
                try:
                    raise baseargs[0], baseargs[1]
                except GreenletExit, e:
                    methodname = 'switch'
                    baseargs = (((e,), {}),)
                except:
                    baseargs = sys.exc_info()[:2] + baseargs[2:]
        #
        try:
            unbound_method = getattr(_continulet, methodname)
            args, kwds = unbound_method(current, *baseargs, to=target)
        finally:
            _tls.current = current
        #
        if kwds:
            if args:
                return args, kwds
            return kwds
        elif len(args) == 1:
            return args[0]
        else:
            return args

    def __nonzero__(self):
        return self.__main or _continulet.is_pending(self)

    @property
    def dead(self):
        return self.__started and not self

    @property
    def gr_frame(self):
        # xxx this doesn't work when called on either the current or
        # the main greenlet of another thread
        if self is getcurrent():
            return None
        if self.__main:
            self = getcurrent()
        f = _continulet.__reduce__(self)[2][0]
        if not f:
            return None
        return f.f_back.f_back.f_back   # go past start(), __switch(), switch()

# ____________________________________________________________
# Internal stuff

try:
    from threading import local as _local
except ImportError:
    class _local(object):    # assume no threads
        pass

_tls = _local()

def _green_create_main():
    # create the main greenlet for this thread
    _tls.current = None
    gmain = greenlet.__new__(greenlet)
    gmain._greenlet__main = True
    gmain._greenlet__started = True
    assert gmain.parent is None
    _tls.main = gmain
    _tls.current = gmain

def _greenlet_start(greenlet, args):
    args, kwds = args
    _tls.current = greenlet
    try:
        res = greenlet.run(*args, **kwds)
    except GreenletExit, e:
        res = e
    finally:
        _continuation.permute(greenlet, greenlet.parent)
    return ((res,), None)

def _greenlet_throw(greenlet, exc, value, tb):
    _tls.current = greenlet
    try:
        raise exc, value, tb
    except GreenletExit, e:
        res = e
    finally:
        _continuation.permute(greenlet, greenlet.parent)
    return ((res,), None)
