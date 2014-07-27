# The TkApp class.

from .tklib import tklib, tkffi
from . import TclError
from .tclobj import TclObject, FromObj, AsObj, TypeCache

import contextlib
import sys
import threading
import time


class _DummyLock(object):
    "A lock-like object that does not do anything"
    def acquire(self):
        pass
    def release(self):
        pass
    def __enter__(self):
        pass
    def __exit__(self, *exc):
        pass


def varname_converter(input):
    if isinstance(input, TclObject):
        return input.string
    return input


def Tcl_AppInit(app):
    if tklib.Tcl_Init(app.interp) == tklib.TCL_ERROR:
        app.raiseTclError()
    skip_tk_init = tklib.Tcl_GetVar(
        app.interp, "_tkinter_skip_tk_init", tklib.TCL_GLOBAL_ONLY)
    if skip_tk_init and tkffi.string(skip_tk_init) == "1":
        return

    if tklib.Tk_Init(app.interp) == tklib.TCL_ERROR:
        app.raiseTclError()

class _CommandData(object):
    def __new__(cls, app, name, func):
        self = object.__new__(cls)
        self.app = app
        self.name = name
        self.func = func
        handle = tkffi.new_handle(self)
        app._commands[name] = handle  # To keep the command alive
        return tkffi.cast("ClientData", handle)

    @tkffi.callback("Tcl_CmdProc")
    def PythonCmd(clientData, interp, argc, argv):
        self = tkffi.from_handle(clientData)
        assert self.app.interp == interp
        with self.app._tcl_lock_released():
            try:
                args = [tkffi.string(arg) for arg in argv[1:argc]]
                result = self.func(*args)
                obj = AsObj(result)
                tklib.Tcl_SetObjResult(interp, obj)
            except:
                self.app.errorInCmd = True
                self.app.exc_info = sys.exc_info()
                return tklib.TCL_ERROR
            else:
                return tklib.TCL_OK

    @tkffi.callback("Tcl_CmdDeleteProc")
    def PythonCmdDelete(clientData):
        self = tkffi.from_handle(clientData)
        app = self.app
        del app._commands[self.name]
        return


class TkApp(object):
    _busywaitinterval = 0.02  # 20ms.

    def __new__(cls, screenName, baseName, className,
                interactive, wantobjects, wantTk, sync, use):
        if not wantobjects:
            raise NotImplementedError("wantobjects=True only")
        self = object.__new__(cls)
        self.interp = tklib.Tcl_CreateInterp()
        self._wantobjects = wantobjects
        self.threaded = bool(tklib.Tcl_GetVar2Ex(
            self.interp, "tcl_platform", "threaded",
            tklib.TCL_GLOBAL_ONLY))
        self.thread_id = tklib.Tcl_GetCurrentThread()
        self.dispatching = False
        self.quitMainLoop = False
        self.errorInCmd = False

        if not self.threaded:
            # TCL is not thread-safe, calls needs to be serialized.
            self._tcl_lock = threading.Lock()
        else:
            self._tcl_lock = _DummyLock()

        self._typeCache = TypeCache()
        self._commands = {}

        # Delete the 'exit' command, which can screw things up
        tklib.Tcl_DeleteCommand(self.interp, "exit")

        if screenName is not None:
            tklib.Tcl_SetVar2(self.interp, "env", "DISPLAY", screenName,
                              tklib.TCL_GLOBAL_ONLY)

        if interactive:
            tklib.Tcl_SetVar(self.interp, "tcl_interactive", "1",
                             tklib.TCL_GLOBAL_ONLY)
        else:
            tklib.Tcl_SetVar(self.interp, "tcl_interactive", "0",
                             tklib.TCL_GLOBAL_ONLY)

        # This is used to get the application class for Tk 4.1 and up
        argv0 = className.lower()
        tklib.Tcl_SetVar(self.interp, "argv0", argv0,
                         tklib.TCL_GLOBAL_ONLY)

        if not wantTk:
            tklib.Tcl_SetVar(self.interp, "_tkinter_skip_tk_init", "1",
                             tklib.TCL_GLOBAL_ONLY)

        # some initial arguments need to be in argv
        if sync or use:
            args = ""
            if sync:
                args += "-sync"
            if use:
                if sync:
                    args += " "
                args += "-use " + use

            tklib.Tcl_SetVar(self.interp, "argv", args,
                             tklib.TCL_GLOBAL_ONLY)

        Tcl_AppInit(self)
        # EnableEventHook()
        return self

    def __del__(self):
        tklib.Tcl_DeleteInterp(self.interp)
        # DisableEventHook()

    def raiseTclError(self):
        if self.errorInCmd:
            self.errorInCmd = False
            raise self.exc_info[0], self.exc_info[1], self.exc_info[2]
        raise TclError(tkffi.string(tklib.Tcl_GetStringResult(self.interp)))

    def wantobjects(self):
        return self._wantobjects

    def _check_tcl_appartment(self):
        if self.threaded and self.thread_id != tklib.Tcl_GetCurrentThread():
            raise RuntimeError("Calling Tcl from different appartment")

    @contextlib.contextmanager
    def _tcl_lock_released(self):
        "Context manager to temporarily release the tcl lock."
        self._tcl_lock.release()
        yield
        self._tcl_lock.acquire()

    def loadtk(self):
        # We want to guard against calling Tk_Init() multiple times
        err = tklib.Tcl_Eval(self.interp, "info exists     tk_version")
        if err == tklib.TCL_ERROR:
            self.raiseTclError()
        tk_exists = tklib.Tcl_GetStringResult(self.interp)
        if not tk_exists or tkffi.string(tk_exists) != "1":
            err = tklib.Tk_Init(self.interp)
            if err == tklib.TCL_ERROR:
                self.raiseTclError()

    def _var_invoke(self, func, *args, **kwargs):
        if self.threaded and self.thread_id != tklib.Tcl_GetCurrentThread():
            # The current thread is not the interpreter thread.
            # Marshal the call to the interpreter thread, then wait
            # for completion.
            raise NotImplementedError("Call from another thread")
        return func(*args, **kwargs)

    def _getvar(self, name1, name2=None, global_only=False):
        name1 = varname_converter(name1)
        if not name2:
            name2 = tkffi.NULL
        flags=tklib.TCL_LEAVE_ERR_MSG
        if global_only:
            flags |= tklib.TCL_GLOBAL_ONLY
        with self._tcl_lock:
            res = tklib.Tcl_GetVar2Ex(self.interp, name1, name2, flags)
            if not res:
                self.raiseTclError()
            assert self._wantobjects
            return FromObj(self, res)

    def _setvar(self, name1, value, global_only=False):
        name1 = varname_converter(name1)
        # XXX Acquire tcl lock???
        newval = AsObj(value)
        flags=tklib.TCL_LEAVE_ERR_MSG
        if global_only:
            flags |= tklib.TCL_GLOBAL_ONLY
        with self._tcl_lock:
            res = tklib.Tcl_SetVar2Ex(self.interp, name1, tkffi.NULL,
                                      newval, flags)
            if not res:
                self.raiseTclError()

    def _unsetvar(self, name1, name2=None, global_only=False):
        name1 = varname_converter(name1)
        if not name2:
            name2 = tkffi.NULL
        flags=tklib.TCL_LEAVE_ERR_MSG
        if global_only:
            flags |= tklib.TCL_GLOBAL_ONLY
        with self._tcl_lock:
            res = tklib.Tcl_UnsetVar2(self.interp, name1, name2, flags)
            if res == tklib.TCL_ERROR:
                self.raiseTclError()

    def getvar(self, name1, name2=None):
        return self._var_invoke(self._getvar, name1, name2)

    def globalgetvar(self, name1, name2=None):
        return self._var_invoke(self._getvar, name1, name2, global_only=True)

    def setvar(self, name1, value):
        return self._var_invoke(self._setvar, name1, value)

    def globalsetvar(self, name1, value):
        return self._var_invoke(self._setvar, name1, value, global_only=True)

    def unsetvar(self, name1, name2=None):
        return self._var_invoke(self._unsetvar, name1, name2)

    def globalunsetvar(self, name1, name2=None):
        return self._var_invoke(self._unsetvar, name1, name2, global_only=True)

    # COMMANDS

    def createcommand(self, cmdName, func):
        if not callable(func):
            raise TypeError("command not callable")

        if self.threaded and self.thread_id != tklib.Tcl_GetCurrentThread():
            raise NotImplementedError("Call from another thread")

        clientData = _CommandData(self, cmdName, func)

        if self.threaded and self.thread_id != tklib.Tcl_GetCurrentThread():
            raise NotImplementedError("Call from another thread")

        with self._tcl_lock:
            res = tklib.Tcl_CreateCommand(
                self.interp, cmdName, _CommandData.PythonCmd,
                clientData, _CommandData.PythonCmdDelete)
        if not res:
            raise TclError("can't create Tcl command")

    def deletecommand(self, cmdName):
        if self.threaded and self.thread_id != tklib.Tcl_GetCurrentThread():
            raise NotImplementedError("Call from another thread")

        with self._tcl_lock:
            res = tklib.Tcl_DeleteCommand(self.interp, cmdName)
        if res == -1:
            raise TclError("can't delete Tcl command")

    def call(self, *args):
        flags = tklib.TCL_EVAL_DIRECT | tklib.TCL_EVAL_GLOBAL

        # If args is a single tuple, replace with contents of tuple
        if len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]

        if self.threaded and self.thread_id != tklib.Tcl_GetCurrentThread():
            # We cannot call the command directly. Instead, we must
            # marshal the parameters to the interpreter thread.
            raise NotImplementedError("Call from another thread")

        objects = tkffi.new("Tcl_Obj*[]", len(args))
        argc = len(args)
        try:
            for i, arg in enumerate(args):
                if arg is None:
                    argc = i
                    break
                obj = AsObj(arg)
                tklib.Tcl_IncrRefCount(obj)
                objects[i] = obj

            with self._tcl_lock:
                res = tklib.Tcl_EvalObjv(self.interp, argc, objects, flags)
                if res == tklib.TCL_ERROR:
                    self.raiseTclError()
                else:
                    result = self._callResult()
        finally:
            for obj in objects:
                if obj:
                    tklib.Tcl_DecrRefCount(obj)
        return result

    def _callResult(self):
        assert self._wantobjects
        value = tklib.Tcl_GetObjResult(self.interp)
        # Not sure whether the IncrRef is necessary, but something
        # may overwrite the interpreter result while we are
        # converting it.
        tklib.Tcl_IncrRefCount(value)
        res = FromObj(self, value)
        tklib.Tcl_DecrRefCount(value)
        return res

    def eval(self, script):
        self._check_tcl_appartment()
        with self._tcl_lock:
            res = tklib.Tcl_Eval(self.interp, script)
            if res == tklib.TCL_ERROR:
                self.raiseTclError()
            return tkffi.string(tklib.Tcl_GetStringResult(self.interp))

    def evalfile(self, filename):
        self._check_tcl_appartment()
        with self._tcl_lock:
            res = tklib.Tcl_EvalFile(self.interp, filename)
            if res == tklib.TCL_ERROR:
                self.raiseTclError()
            return tkffi.string(tklib.Tcl_GetStringResult(self.interp))

    def split(self, arg):
        if isinstance(arg, TclObject):
            objc = tkffi.new("int*")
            objv = tkffi.new("Tcl_Obj***")
            status = tklib.Tcl_ListObjGetElements(self.interp, arg._value, objc, objv)
            if status == tklib.TCL_ERROR:
                return FromObj(self, arg._value)
            if objc == 0:
                return ''
            elif objc == 1:
                return FromObj(self, objv[0][0])
            result = []
            for i in range(objc[0]):
                result.append(FromObj(self, objv[0][i]))
            return tuple(result)
        elif isinstance(arg, tuple):
            return self._splitObj(arg)
        elif isinstance(arg, unicode):
            arg = arg.encode('utf8')
        return self._split(arg)

    def splitlist(self, arg):
        if isinstance(arg, TclObject):
            objc = tkffi.new("int*")
            objv = tkffi.new("Tcl_Obj***")
            status = tklib.Tcl_ListObjGetElements(self.interp, arg._value, objc, objv)
            if status == tklib.TCL_ERROR:
                self.raiseTclError()
            result = []
            for i in range(objc[0]):
                result.append(FromObj(self, objv[0][i]))
            return tuple(result)
        elif isinstance(arg, tuple):
            return arg
        elif isinstance(arg, unicode):
            arg = arg.encode('utf8')

        argc = tkffi.new("int*")
        argv = tkffi.new("char***")
        res = tklib.Tcl_SplitList(self.interp, arg, argc, argv)
        if res == tklib.TCL_ERROR:
            self.raiseTclError()

        result = tuple(tkffi.string(argv[0][i])
                       for i in range(argc[0]))
        tklib.Tcl_Free(argv[0])
        return result

    def _splitObj(self, arg):
        if isinstance(arg, tuple):
            size = len(arg)
            result = None
            # Recursively invoke SplitObj for all tuple items.
            # If this does not return a new object, no action is
            # needed.
            for i in range(size):
                elem = arg[i]
                newelem = self._splitObj(elem)
                if result is None:
                    if newelem == elem:
                        continue
                    result = [None] * size
                    for k in range(i):
                        result[k] = arg[k]
                result[i] = newelem
            if result is not None:
                return tuple(result)
        elif isinstance(arg, basestring):
            argc = tkffi.new("int*")
            argv = tkffi.new("char***")
            if isinstance(arg, unicode):
                arg = arg.encode('utf-8')
            list_ = str(arg)
            res = tklib.Tcl_SplitList(tkffi.NULL, list_, argc, argv)
            if res != tklib.TCL_OK:
                return arg
            tklib.Tcl_Free(argv[0])
            if argc[0] > 1:
                return self._split(list_)
        return arg

    def _split(self, arg):
        argc = tkffi.new("int*")
        argv = tkffi.new("char***")
        res = tklib.Tcl_SplitList(tkffi.NULL, arg, argc, argv)
        if res == tklib.TCL_ERROR:
            # Not a list.
            # Could be a quoted string containing funnies, e.g. {"}.
            # Return the string itself.
            return arg

        try:
            if argc[0] == 0:
                return ""
            elif argc[0] == 1:
                return tkffi.string(argv[0][0])
            else:
                return tuple(self._split(argv[0][i])
                             for i in range(argc[0]))
        finally:
            tklib.Tcl_Free(argv[0])

    def getboolean(self, s):
        if isinstance(s, int):
            return s
        v = tkffi.new("int*")
        res = tklib.Tcl_GetBoolean(self.interp, s, v)
        if res == tklib.TCL_ERROR:
            self.raiseTclError()

    def mainloop(self, threshold):
        self._check_tcl_appartment()
        self.dispatching = True
        while (tklib.Tk_GetNumMainWindows() > threshold and
               not self.quitMainLoop and not self.errorInCmd):

            if self.threaded:
                result = tklib.Tcl_DoOneEvent(0)
            else:
                with self._tcl_lock:
                    result = tklib.Tcl_DoOneEvent(tklib.TCL_DONT_WAIT)
                if result == 0:
                    time.sleep(self._busywaitinterval)

            if result < 0:
                break
        self.dispatching = False
        self.quitMainLoop = False
        if self.errorInCmd:
            self.errorInCmd = False
            raise self.exc_info[0], self.exc_info[1], self.exc_info[2]

    def quit(self):
        self.quitMainLoop = True
