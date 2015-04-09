#
# Reimplementation of cPickle, mostly as a copy of pickle.py
#

from pickle import Pickler, dump, dumps, PickleError, PicklingError, UnpicklingError, _EmptyClass
from pickle import __doc__, __version__, format_version, compatible_formats
from types import *
from copy_reg import dispatch_table
from copy_reg import _extension_registry, _inverted_registry, _extension_cache
import marshal, struct, sys

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f

# These are purely informational; no code uses these.
format_version = "2.0"                  # File format version we write
compatible_formats = ["1.0",            # Original protocol 0
                      "1.1",            # Protocol 0 with INST added
                      "1.2",            # Original protocol 1
                      "1.3",            # Protocol 1 with BINFLOAT added
                      "2.0",            # Protocol 2
                      ]                 # Old format versions we can read

# Keep in synch with cPickle.  This is the highest protocol number we
# know how to read.
HIGHEST_PROTOCOL = 2

BadPickleGet = KeyError
UnpickleableError = PicklingError

MARK            = ord('(')   # push special markobject on stack
STOP            = ord('.')   # every pickle ends with STOP
POP             = ord('0')   # discard topmost stack item
POP_MARK        = ord('1')   # discard stack top through topmost markobject
DUP             = ord('2')   # duplicate top stack item
FLOAT           = ord('F')   # push float object; decimal string argument
INT             = ord('I')   # push integer or bool; decimal string argument
BININT          = ord('J')   # push four-byte signed int
BININT1         = ord('K')   # push 1-byte unsigned int
LONG            = ord('L')   # push long; decimal string argument
BININT2         = ord('M')   # push 2-byte unsigned int
NONE            = ord('N')   # push None
PERSID          = ord('P')   # push persistent object; id is taken from string arg
BINPERSID       = ord('Q')   #  "       "         "  ;  "  "   "     "  stack
REDUCE          = ord('R')   # apply callable to argtuple, both on stack
STRING          = ord('S')   # push string; NL-terminated string argument
BINSTRING       = ord('T')   # push string; counted binary string argument
SHORT_BINSTRING = ord('U')   #  "     "   ;    "      "       "      " < 256 bytes
UNICODE         = ord('V')   # push Unicode string; raw-unicode-escaped'd argument
BINUNICODE      = ord('X')   #   "     "       "  ; counted UTF-8 string argument
APPEND          = ord('a')   # append stack top to list below it
BUILD           = ord('b')   # call __setstate__ or __dict__.update()
GLOBAL          = ord('c')   # push self.find_class(modname, name); 2 string args
DICT            = ord('d')   # build a dict from stack items
EMPTY_DICT      = ord('}')   # push empty dict
APPENDS         = ord('e')   # extend list on stack by topmost stack slice
GET             = ord('g')   # push item from memo on stack; index is string arg
BINGET          = ord('h')   #   "    "    "    "   "   "  ;   "    " 1-byte arg
INST            = ord('i')   # build & push class instance
LONG_BINGET     = ord('j')   # push item from memo on stack; index is 4-byte arg
LIST            = ord('l')   # build list from topmost stack items
EMPTY_LIST      = ord(']')   # push empty list
OBJ             = ord('o')   # build & push class instance
PUT             = ord('p')   # store stack top in memo; index is string arg
BINPUT          = ord('q')   #   "     "    "   "   " ;   "    " 1-byte arg
LONG_BINPUT     = ord('r')   #   "     "    "   "   " ;   "    " 4-byte arg
SETITEM         = ord('s')   # add key+value pair to dict
TUPLE           = ord('t')   # build tuple from topmost stack items
EMPTY_TUPLE     = ord(')')   # push empty tuple
SETITEMS        = ord('u')   # modify dict by adding topmost key+value pairs
BINFLOAT        = ord('G')   # push float; arg is 8-byte float encoding

TRUE            = 'I01\n'  # not an opcode; see INT docs in pickletools.py
FALSE           = 'I00\n'  # not an opcode; see INT docs in pickletools.py

# Protocol 2

PROTO           = ord('\x80')  # identify pickle protocol
NEWOBJ          = ord('\x81')  # build object by applying cls.__new__ to argtuple
EXT1            = ord('\x82')  # push object from extension registry; 1-byte index
EXT2            = ord('\x83')  # ditto, but 2-byte index
EXT4            = ord('\x84')  # ditto, but 4-byte index
TUPLE1          = ord('\x85')  # build 1-tuple from stack top
TUPLE2          = ord('\x86')  # build 2-tuple from two topmost stack items
TUPLE3          = ord('\x87')  # build 3-tuple from three topmost stack items
NEWTRUE         = ord('\x88')  # push True
NEWFALSE        = ord('\x89')  # push False
LONG1           = ord('\x8a')  # push long from < 256 bytes
LONG4           = ord('\x8b')  # push really big long

_tuplesize2code = [EMPTY_TUPLE, TUPLE1, TUPLE2, TUPLE3]


# ____________________________________________________________
# XXX some temporary dark magic to produce pickled dumps that are
#     closer to the ones produced by cPickle in CPython

from pickle import StringIO

PythonPickler = Pickler
class Pickler(PythonPickler):
    def __init__(self, *args, **kw):
        self.__f = None
        if len(args) == 1 and isinstance(args[0], int):
            self.__f = StringIO()
            PythonPickler.__init__(self, self.__f, args[0], **kw)
        else:
            PythonPickler.__init__(self, *args, **kw)

    def memoize(self, obj):
        self.memo[id(None)] = None   # cPickle starts counting at one
        return PythonPickler.memoize(self, obj)

    def getvalue(self):
        return self.__f and self.__f.getvalue()

@builtinify
def dump(obj, file, protocol=None):
    Pickler(file, protocol).dump(obj)

@builtinify
def dumps(obj, protocol=None):
    file = StringIO()
    Pickler(file, protocol).dump(obj)
    return file.getvalue()

# Why use struct.pack() for pickling but marshal.loads() for
# unpickling?  struct.pack() is 40% faster than marshal.dumps(), but
# marshal.loads() is twice as fast as struct.unpack()!
mloads = marshal.loads

# Unpickling machinery

class _Stack(list):
    def pop(self, index=-1):
        try:
            return list.pop(self, index)
        except IndexError:
            raise UnpicklingError("unpickling stack underflow")

class Unpickler(object):

    def __init__(self, file):
        """This takes a file-like object for reading a pickle data stream.

        The protocol version of the pickle is detected automatically, so no
        proto argument is needed.

        The file-like object must have two methods, a read() method that
        takes an integer argument, and a readline() method that requires no
        arguments.  Both methods should return a string.  Thus file-like
        object can be a file object opened for reading, a StringIO object,
        or any other custom object that meets this interface.
        """
        self.readline = file.readline
        self.read = file.read
        self.memo = {}

    def load(self):
        """Read a pickled object representation from the open file.

        Return the reconstituted object hierarchy specified in the file.
        """
        self.mark = object() # any new unique object
        self.stack = _Stack()
        self.append = self.stack.append
        try:
            key = ord(self.read(1))
            while key != STOP:
                self.dispatch[key](self)
                key = ord(self.read(1))
        except TypeError:
            if self.read(1) == '':
                raise EOFError
            raise
        return self.stack.pop()

    # Return largest index k such that self.stack[k] is self.mark.
    # If the stack doesn't contain a mark, eventually raises IndexError.
    # This could be sped by maintaining another stack, of indices at which
    # the mark appears.  For that matter, the latter stack would suffice,
    # and we wouldn't need to push mark objects on self.stack at all.
    # Doing so is probably a good thing, though, since if the pickle is
    # corrupt (or hostile) we may get a clue from finding self.mark embedded
    # in unpickled objects.
    def marker(self):
        k = len(self.stack)-1
        while self.stack[k] is not self.mark: k -= 1
        return k

    dispatch = {}

    def load_proto(self):
        proto = ord(self.read(1))
        if not 0 <= proto <= 2:
            raise ValueError, "unsupported pickle protocol: %d" % proto
    dispatch[PROTO] = load_proto

    def load_persid(self):
        pid = self.readline()[:-1]
        self.append(self.persistent_load(pid))
    dispatch[PERSID] = load_persid

    def load_binpersid(self):
        pid = self.stack.pop()
        self.append(self.persistent_load(pid))
    dispatch[BINPERSID] = load_binpersid

    def load_none(self):
        self.append(None)
    dispatch[NONE] = load_none

    def load_false(self):
        self.append(False)
    dispatch[NEWFALSE] = load_false

    def load_true(self):
        self.append(True)
    dispatch[NEWTRUE] = load_true

    def load_int(self):
        data = self.readline()
        if data == FALSE[1:]:
            val = False
        elif data == TRUE[1:]:
            val = True
        else:
            val = int(data)
        self.append(val)
    dispatch[INT] = load_int

    def load_binint(self):
        self.append(mloads('i' + self.read(4)))
    dispatch[BININT] = load_binint

    def load_binint1(self):
        self.append(ord(self.read(1)))
    dispatch[BININT1] = load_binint1

    def load_binint2(self):
        self.append(mloads('i' + self.read(2) + '\000\000'))
    dispatch[BININT2] = load_binint2

    def load_long(self):
        self.append(long(self.readline()[:-1], 0))
    dispatch[LONG] = load_long

    def load_long1(self):
        n = ord(self.read(1))
        bytes = self.read(n)
        self.append(decode_long(bytes))
    dispatch[LONG1] = load_long1

    def load_long4(self):
        n = mloads('i' + self.read(4))
        bytes = self.read(n)
        self.append(decode_long(bytes))
    dispatch[LONG4] = load_long4

    def load_float(self):
        self.append(float(self.readline()[:-1]))
    dispatch[FLOAT] = load_float

    def load_binfloat(self, unpack=struct.unpack):
        self.append(unpack('>d', self.read(8))[0])
    dispatch[BINFLOAT] = load_binfloat

    def load_string(self):
        rep = self.readline()
        if len(rep) < 3:
            raise ValueError, "insecure string pickle"
        if rep[0] == "'" == rep[-2]:
            rep = rep[1:-2]
        elif rep[0] == '"' == rep[-2]:
            rep = rep[1:-2]
        else:
            raise ValueError, "insecure string pickle"
        self.append(rep.decode("string-escape"))
    dispatch[STRING] = load_string

    def load_binstring(self):
        L = mloads('i' + self.read(4))
        self.append(self.read(L))
    dispatch[BINSTRING] = load_binstring

    def load_unicode(self):
        self.append(unicode(self.readline()[:-1],'raw-unicode-escape'))
    dispatch[UNICODE] = load_unicode

    def load_binunicode(self):
        L = mloads('i' + self.read(4))
        self.append(unicode(self.read(L),'utf-8'))
    dispatch[BINUNICODE] = load_binunicode

    def load_short_binstring(self):
        L = ord(self.read(1))
        self.append(self.read(L))
    dispatch[SHORT_BINSTRING] = load_short_binstring

    def load_tuple(self):
        k = self.marker()
        self.stack[k:] = [tuple(self.stack[k+1:])]
    dispatch[TUPLE] = load_tuple

    def load_empty_tuple(self):
        self.stack.append(())
    dispatch[EMPTY_TUPLE] = load_empty_tuple

    def load_tuple1(self):
        self.stack[-1] = (self.stack[-1],)
    dispatch[TUPLE1] = load_tuple1

    def load_tuple2(self):
        self.stack[-2:] = [(self.stack[-2], self.stack[-1])]
    dispatch[TUPLE2] = load_tuple2

    def load_tuple3(self):
        self.stack[-3:] = [(self.stack[-3], self.stack[-2], self.stack[-1])]
    dispatch[TUPLE3] = load_tuple3

    def load_empty_list(self):
        self.stack.append([])
    dispatch[EMPTY_LIST] = load_empty_list

    def load_empty_dictionary(self):
        self.stack.append({})
    dispatch[EMPTY_DICT] = load_empty_dictionary

    def load_list(self):
        k = self.marker()
        self.stack[k:] = [self.stack[k+1:]]
    dispatch[LIST] = load_list

    def load_dict(self):
        k = self.marker()
        d = {}
        items = self.stack[k+1:]
        for i in range(0, len(items), 2):
            key = items[i]
            value = items[i+1]
            d[key] = value
        self.stack[k:] = [d]
    dispatch[DICT] = load_dict

    # INST and OBJ differ only in how they get a class object.  It's not
    # only sensible to do the rest in a common routine, the two routines
    # previously diverged and grew different bugs.
    # klass is the class to instantiate, and k points to the topmost mark
    # object, following which are the arguments for klass.__init__.
    def _instantiate(self, klass, k):
        args = tuple(self.stack[k+1:])
        del self.stack[k:]
        instantiated = 0
        if (not args and
                type(klass) is ClassType and
                not hasattr(klass, "__getinitargs__")):
            try:
                value = _EmptyClass()
                value.__class__ = klass
                instantiated = 1
            except RuntimeError:
                # In restricted execution, assignment to inst.__class__ is
                # prohibited
                pass
        if not instantiated:
            try:
                value = klass(*args)
            except TypeError, err:
                raise TypeError, "in constructor for %s: %s" % (
                    klass.__name__, str(err)), sys.exc_info()[2]
        self.append(value)

    def load_inst(self):
        module = self.readline()[:-1]
        name = self.readline()[:-1]
        klass = self.find_class(module, name)
        self._instantiate(klass, self.marker())
    dispatch[INST] = load_inst

    def load_obj(self):
        # Stack is ... markobject classobject arg1 arg2 ...
        k = self.marker()
        klass = self.stack.pop(k+1)
        self._instantiate(klass, k)
    dispatch[OBJ] = load_obj

    def load_newobj(self):
        args = self.stack.pop()
        cls = self.stack[-1]
        obj = cls.__new__(cls, *args)
        self.stack[-1] = obj
    dispatch[NEWOBJ] = load_newobj

    def load_global(self):
        module = self.readline()[:-1]
        name = self.readline()[:-1]
        klass = self.find_class(module, name)
        self.append(klass)
    dispatch[GLOBAL] = load_global

    def load_ext1(self):
        code = ord(self.read(1))
        self.get_extension(code)
    dispatch[EXT1] = load_ext1

    def load_ext2(self):
        code = mloads('i' + self.read(2) + '\000\000')
        self.get_extension(code)
    dispatch[EXT2] = load_ext2

    def load_ext4(self):
        code = mloads('i' + self.read(4))
        self.get_extension(code)
    dispatch[EXT4] = load_ext4

    def get_extension(self, code):
        nil = []
        obj = _extension_cache.get(code, nil)
        if obj is not nil:
            self.append(obj)
            return
        key = _inverted_registry.get(code)
        if not key:
            raise ValueError("unregistered extension code %d" % code)
        obj = self.find_class(*key)
        _extension_cache[code] = obj
        self.append(obj)

    def find_class(self, module, name):
        # Subclasses may override this
        __import__(module)
        mod = sys.modules[module]
        klass = getattr(mod, name)
        return klass

    def load_reduce(self):
        args = self.stack.pop()
        func = self.stack[-1]
        value = self.stack[-1](*args)
        self.stack[-1] = value
    dispatch[REDUCE] = load_reduce

    def load_pop(self):
        del self.stack[-1]
    dispatch[POP] = load_pop

    def load_pop_mark(self):
        k = self.marker()
        del self.stack[k:]
    dispatch[POP_MARK] = load_pop_mark

    def load_dup(self):
        self.append(self.stack[-1])
    dispatch[DUP] = load_dup

    def load_get(self):
        self.append(self.memo[self.readline()[:-1]])
    dispatch[GET] = load_get

    def load_binget(self):
        i = ord(self.read(1))
        self.append(self.memo[repr(i)])
    dispatch[BINGET] = load_binget

    def load_long_binget(self):
        i = mloads('i' + self.read(4))
        self.append(self.memo[repr(i)])
    dispatch[LONG_BINGET] = load_long_binget

    def load_put(self):
        self.memo[self.readline()[:-1]] = self.stack[-1]
    dispatch[PUT] = load_put

    def load_binput(self):
        i = ord(self.read(1))
        self.memo[repr(i)] = self.stack[-1]
    dispatch[BINPUT] = load_binput

    def load_long_binput(self):
        i = mloads('i' + self.read(4))
        self.memo[repr(i)] = self.stack[-1]
    dispatch[LONG_BINPUT] = load_long_binput

    def load_append(self):
        value = self.stack.pop()
        self.stack[-1].append(value)
    dispatch[APPEND] = load_append

    def load_appends(self):
        stack = self.stack
        mark = self.marker()
        lst = stack[mark - 1]
        lst.extend(stack[mark + 1:])
        del stack[mark:]
    dispatch[APPENDS] = load_appends

    def load_setitem(self):
        stack = self.stack
        value = stack.pop()
        key = stack.pop()
        dict = stack[-1]
        dict[key] = value
    dispatch[SETITEM] = load_setitem

    def load_setitems(self):
        stack = self.stack
        mark = self.marker()
        dict = stack[mark - 1]
        for i in range(mark + 1, len(stack), 2):
            dict[stack[i]] = stack[i + 1]

        del stack[mark:]
    dispatch[SETITEMS] = load_setitems

    def load_build(self):
        stack = self.stack
        state = stack.pop()
        inst = stack[-1]
        setstate = getattr(inst, "__setstate__", None)
        if setstate:
            setstate(state)
            return
        slotstate = None
        if isinstance(state, tuple) and len(state) == 2:
            state, slotstate = state
        if state:
            try:
                d = inst.__dict__
                try:
                    for k, v in state.iteritems():
                        d[intern(k)] = v
                # keys in state don't have to be strings
                # don't blow up, but don't go out of our way
                except TypeError:
                    d.update(state)

            except RuntimeError:
                # XXX In restricted execution, the instance's __dict__
                # is not accessible.  Use the old way of unpickling
                # the instance variables.  This is a semantic
                # difference when unpickling in restricted
                # vs. unrestricted modes.
                # Note, however, that cPickle has never tried to do the
                # .update() business, and always uses
                #     PyObject_SetItem(inst.__dict__, key, value) in a
                # loop over state.items().
                for k, v in state.items():
                    setattr(inst, k, v)
        if slotstate:
            for k, v in slotstate.items():
                setattr(inst, k, v)
    dispatch[BUILD] = load_build

    def load_mark(self):
        self.append(self.mark)
    dispatch[MARK] = load_mark

#from pickle import decode_long

def decode_long(data):
    r"""Decode a long from a two's complement little-endian binary string.

    >>> decode_long('')
    0L
    >>> decode_long("\xff\x00")
    255L
    >>> decode_long("\xff\x7f")
    32767L
    >>> decode_long("\x00\xff")
    -256L
    >>> decode_long("\x00\x80")
    -32768L
    >>> decode_long("\x80")
    -128L
    >>> decode_long("\x7f")
    127L
    """

    nbytes = len(data)
    if nbytes == 0:
        return 0L
    ind = nbytes - 1
    while ind and ord(data[ind]) == 0:
        ind -= 1
    n = ord(data[ind])
    while ind:
        n <<= 8
        ind -= 1
        if ord(data[ind]):
            n += ord(data[ind])
    if ord(data[nbytes - 1]) >= 128:
        n -= 1L << (nbytes << 3)
    return n

def load(f):
    return Unpickler(f).load()

def loads(str):
    f = StringIO(str)
    return Unpickler(f).load()
