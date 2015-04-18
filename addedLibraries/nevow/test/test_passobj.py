# Copyright (c) 2004 Divmod.
# See LICENSE for details.

import formless
from zope.interface import implements

class IBar(formless.TypedInterface):
    bar = formless.String()


class Bar:
    implements(IBar)

    def __init__(self, bar):
        self.bar = bar

    def __str__(self):
        return "A Bar: %s" % self.bar


class IFrob(formless.TypedInterface):
    integer = formless.Integer()


class Frob:
    implements(IFrob)

    def __init__(self, integer):
        self.integer = integer

    def frobazz(self, other):
        return Frob(self.integer ** other.integer)

    def __str__(self):
        return "A frob of value %s" % self.integer


class IObjectTest(formless.TypedInterface):
    def someMethod(one=formless.Object(interface=IBar), two=formless.Integer(description="an integer please")):
        """Some Method.
        
        This method takes an IBar instance.
        """
        return None
    someMethod = formless.autocallable(someMethod)

    def frobber(frobber=formless.Object(interface=IFrob), frobee=formless.Object(IFrob)):
        """Frobber.
        
        Takes two frobs and raises one to the power of the other.
        """
        return IFrob
    frobber = formless.autocallable(frobber)

    someList = formless.List()


class ObjectTester:
    implements(IObjectTest)

    def __init__(self):
        self.someList = [
            Bar("boop"), Bar("bap"),
            Frob(5), Frob(9), Frob(23), Frob(1234)
        ]

    def someMethod(self, one, two):
        print "ONE TWO", `one`, `two`

    def frobber(self, frobber, frobee):
        return frobber.frobazz(frobee)


class CompoundChecker(formless.Compound):
    def coerce(self, data):
        one, two = data
        if (one, two) != (6, 9):
            raise formless.InputError("What do you get when you multiply six by nine?")


class IAnotherTest(formless.TypedInterface):
    def aBarMethod(abar=formless.Object(interface=IBar)):
        """A Bar Method
        
        This method takes a bar, but there are no bar instances on this page.
        You'll have to use the shelf.
        """
        return str
    aBarMethod = formless.autocallable(aBarMethod)

    def aFrobMethod(aFrob=formless.Object(interface=IFrob)):
        """A Frob Method
        
        This method takes a frob, but there are no frob instances on this page.
        You'll have to use the shelf.
        """
        return str
    aFrobMethod = formless.autocallable(aFrobMethod)

    def whatIsMyClass(anObj=formless.Object()):
        """What is my class?
        
        Pass an object and get back the class in your hand.
        """
        return formless.Object()
    whatIsMyClass = formless.autocallable(whatIsMyClass)

    def setBreakpoint(breakpoint=formless.String()):
        """Set a breakpoint

        Set a breakpoint at the given filename and line number. String passed is equivalent
        to doing b(reak) ([file:]lineno | function) in pdb.
        """
        return None
    setBreakpoint = formless.autocallable(setBreakpoint)

    breakpoints = formless.List()

    def compoundTest(
        aCompound = formless.Compound(
            [formless.String(label="firstname"), formless.String(label="lastname")],
            label="Full Name"),
        anInt = formless.Integer()):
        """Compound Test
        
        A test of a widget/controller which renders multiple fields, triggers multiple
        validators, but gathers the result into one method argument. There can
        be an additional validation step which validates that the compound data
        as a whole is valid.
        """
        return str
    compoundTest = formless.autocallable(compoundTest)

    def compoundChecker(
        theAnswer = CompoundChecker(
            [formless.Integer(label="six"), formless.Integer(label="nine")],
            label="The Answer",
            description="What is the meaning of life, the universe, and everything?")
        ):
        """The Answer
        
        Please type the integer six in the first box, and nine in the second.
        """
        return formless.Object(label="The Answer", interface=formless.Integer)
    compoundChecker = formless.autocallable(compoundChecker)


class AnotherTest:
    implements(IAnotherTest)

    def aBarMethod(self, abar):
        return "You passed me %s" % abar

    def aFrobMethod(self, aFrob):
        return "You passed me %s" % aFrob

    def whatIsMyClass(self, anObj):
        if hasattr(anObj, '__class__'):
            return anObj.__class__
        return type(anObj)

    def _getDebugger(self):
        import sys, pdb
        debugInstance = sys.modules.get('debugInstance')
        if debugInstance is None:
            sys.modules['debugInstance'] = debugInstance = pdb.Pdb()
            debugInstance.reset()
        return debugInstance

    def setBreakpoint(self, breakpoint):
        import sys
        debugInstance = self._getDebugger()
        debugInstance.do_break(debugInstance.precmd(breakpoint))
        debugInstance.quitting = True
        sys.settrace(debugInstance.trace_dispatch)
        debugInstance.quitting = False

    def _currentBreakpoints(self):
        debugInstance = self._getDebugger()
        class BreakpointRemover(list):
            def remove(self, removal):
                debugInstance.breaks[removal.fn].remove(removal.ln)
                if not debugInstance.breaks[removal.fn]:
                    del debugInstance.breaks[removal.fn]
                list.remove(self, removal)
        class Dummy(formless.TypedInterface): pass
        class BP:
            implements(Dummy)
            def __init__(self, fn, ln):
                self.fn=fn
                self.ln=ln
            def __str__(self):
                return "Breakpoint in file %s at line %s" % (self.fn, self.ln)

        breakpoints = BreakpointRemover()
        for fn in debugInstance.breaks.keys():
            for lineno in debugInstance.breaks[fn]:
                breakpoints.append(BP(fn, lineno))
        return breakpoints
    breakpoints = property(_currentBreakpoints)

    def compoundTest(self, aCompound, anInt):
        return "COMPOUND! %s %s" % (aCompound, anInt)

    def compoundChecker(self, theAnswer):
        return 42

