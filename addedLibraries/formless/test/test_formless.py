# Copyright (c) 2004 Divmod.
# See LICENSE for details.

import os

from nevow.testutil import TestCase

import formless
from formless import process as flpr


def process(typed, value):
    return flpr(typed, [value])


class Typed(TestCase):
    def testString(self):
        s = formless.String()
        self.assertEquals(process(s, ''), None)
        self.assertEquals(process(s, "Fooo"), "Fooo")
        self.assertEquals(process(s, "This is a string"), "This is a string")
        self.assertEquals(process(s, 'C\xc3\xa9sar'), 'C\xc3\xa9sar')

        s = formless.String(unicode=True)
        self.assertEquals(process(s, 'C\xc3\xa9sar'), u'C\u00e9sar')

        s = formless.String(required=True)
        self.assertRaises(formless.InputError, process, s, "")
        
        s = formless.String(required=False)
        self.assertEquals(process(s, "Bar"), "Bar")
        self.assertEquals(process(s, ""), None)
    
        s = formless.String()
        self.assertEquals(process(s, ' abc '), ' abc ')
        
        s = formless.String(strip=True, required=True)
        self.assertEquals(process(s, ' abc '), 'abc')
        self.assertEquals(process(s, '\t abc \t  \n '), 'abc')
        self.assertRaises(formless.InputError, process, s, ' ')
        
        s = formless.String(required=False, strip=True)
        self.assertEquals(process(s, ' abc '), 'abc')
        self.assertEquals(process(s, ' '), None)
        
    def testText(self):
        s = formless.Text()
        self.assertEquals(process(s, ""), None)
        self.assertEquals(process(s, "Fooo"), "Fooo")
        self.assertEquals(process(s, "This is a string"), "This is a string")
        self.assertEquals(process(s, 'C\xc3\xa9sar'), 'C\xc3\xa9sar')

        s = formless.Text(unicode=True)
        self.assertEquals(process(s, 'C\xc3\xa9sar'), u'C\u00e9sar')

        s = formless.Text(required=True)
        self.assertRaises(formless.InputError, process, s, "")
        
        s = formless.Text(required=False)
        self.assertEquals(process(s, "Bar"), "Bar")
        self.assertEquals(process(s, ""), None)
        
        s = formless.Text()
        self.assertEquals(process(s, ' abc '), ' abc ')
        
        s = formless.Text(strip=True, required=True)
        self.assertEquals(process(s, ' abc '), 'abc')
        self.assertRaises(formless.InputError, process, s, ' ')
        
        s = formless.Text(required=False, strip=True)
        self.assertEquals(process(s, ' abc '), 'abc')
        self.assertEquals(process(s, ' '), None)
        
    def testPassword(self):

        def process(pw, val, val2=None):
            if val2 is None: val2 = val
            return flpr(
                formless.Property('password', pw),
                {'password': [val], 'password____2': [val2]})['password']

        s = formless.Password()
        self.assertEquals(process(s, "Fooo"), "Fooo")
        self.assertEquals(process(s, "This is a string"), "This is a string")
        self.assertEquals(process(s, "This is a string"), "This is a string")
        self.assertEquals(process(s, 'C\xc3\xa9sar'), 'C\xc3\xa9sar')

        s = formless.Password(unicode=True)
        self.assertEquals(process(s, 'C\xc3\xa9sar'), u'C\u00e9sar')

        s = formless.Password(required=True)
        self.assertRaises(formless.ValidateError, process, s, "")
        
        s = formless.Password(required=False)
        self.assertEquals(process(s, "Bar"), "Bar")
        self.assertEquals(process(s, ""), None)
    
        s = formless.Password()
        self.assertEquals(process(s, ' abc '), ' abc ')
        
        s = formless.Password(strip=True, required=True)
        self.assertEquals(process(s, ' abc '), 'abc')
        self.assertRaises(formless.ValidateError, process, s, ' ')
        
        s = formless.Password(required=False, strip=True)
        self.assertEquals(process(s, ' abc '), 'abc')
        self.assertEquals(process(s, ' '), None)
        
    def testPasswordEntry(self):
        s = formless.PasswordEntry()
        self.assertEquals(process(s, ''), None)
        self.assertEquals(process(s, 'abc'), 'abc')
        self.assertEquals(process(s, ' blah blah blah  '), ' blah blah blah  ')
        self.assertEquals(process(s, 'C\xc3\xa9sar'), 'C\xc3\xa9sar')

        s = formless.PasswordEntry(unicode=True)
        self.assertEquals(process(s, 'C\xc3\xa9sar'), u'C\u00e9sar')

        s = formless.PasswordEntry(strip=True)
        self.assertEquals(process(s, ''), None)
        self.assertEquals(process(s, 'abc'), 'abc')
        self.assertEquals(process(s, ' blah blah blah  '), 'blah blah blah')

        s = formless.PasswordEntry(strip=True, required=True)
        self.assertRaises(formless.InputError, process, s, '')
        self.assertRaises(formless.InputError, process, s, '   ')
        self.assertEquals(process(s, 'abc'), 'abc')
        self.assertEquals(process(s, ' blah blah blah  '), 'blah blah blah')
        
    def testInteger(self):
        i = formless.Integer(required=True)
        self.assertEquals(process(i, "0"), 0)
        self.assertEquals(process(i, "3409823098"), 3409823098)
        self.assertRaises(formless.InputError, process, i, "")
        self.assertRaises(formless.InputError, process, i, "a string")
        self.assertRaises(formless.InputError, process, i, "1.5")
        
        i = formless.Integer(required=False)
        self.assertEquals(process(i, "1234567"), 1234567)
        self.assertEquals(process(i, ""), None)
        
    def testReal(self):
        i = formless.Real(required=True)
        self.assertApproximates(process(i, "0.0"), 0.0, 1e-10)
        self.assertApproximates(process(i, "34098.23098"), 34098.23098, 1e-10)
        self.assertRaises(formless.InputError, process, i, "")
        self.assertRaises(formless.InputError, process, i, "a string")
        self.assertRaises(formless.InputError, process, i, "1.5j")

        i = formless.Real(required=False)
        self.assertApproximates(process(i, "1234.567"), 1234.567, 1e-10)
        self.assertEquals(process(i, ""), None)

    def testBoolean(self):
        b = formless.Boolean(required=True)
        self.assertRaises(formless.InputError, process, b, "zoom")
        self.assertRaises(formless.InputError, process, b, True)
        self.assertRaises(formless.InputError, process, b, 54)
        self.assertRaises(formless.InputError, process, b, "")
        self.assertEquals(process(b, "True"), True)
        self.assertEquals(process(b, "False"), False)

        b = formless.Boolean(required=False)
        self.assertRaises(formless.InputError, process, b, "zoom")
        self.assertEquals(process(b, ""), None)
        self.assertEquals(process(b, "True"), True)
        self.assertEquals(process(b, "False"), False)
        
    def testFixedDigitInteger(self):
        d = formless.FixedDigitInteger(3, required=True)
        self.assertEquals(process(d, "123"), 123)
        self.assertEquals(process(d, "567"), 567)
        self.assertRaises(formless.InputError, process, d, "12")
        self.assertRaises(formless.InputError, process, d, "1234")
        self.assertRaises(formless.InputError, process, d, "012")
        self.assertRaises(formless.InputError, process, d, "foo")
        self.assertRaises(formless.InputError, process, d, "   ")
        self.assertRaises(formless.InputError, process, d, "")

        d = formless.FixedDigitInteger(3, required=False)
        self.assertEquals(process(d, "123"), 123)
        self.assertRaises(formless.InputError, process, d, "foo")
        self.assertEquals(process(d, ""), None)

    def testDirectory(self):
        p1 = self.mktemp()
        os.mkdir(p1)
        p2 = self.mktemp()
        
        d = formless.Directory(required=True)
        self.assertEquals(process(d, p1), p1)
        self.assertRaises(formless.InputError, process, d, p2)
        self.assertRaises(formless.InputError, process, d, "")
        
        d = formless.Directory(required=False)
        self.assertEquals(process(d, p1), p1)
        self.assertRaises(formless.InputError, process, d, p2)
        self.assertEquals(process(d, ""), None)


class Annotation(TestCase):
    def testTypedInterfaceProperties(self):
        class Other(formless.TypedInterface):
            pass
        _indirectOther = lambda: Other  # XXX work around Python issue1569356
        class Test(formless.TypedInterface):
            foo = formless.String()
            bar = formless.Text()
            baz = formless.Integer()
            quux = formless.Object(interface=_indirectOther())

        self.assertEquals(Test.__properties__, Test.__spec__)

        bfoo, bbar, bbaz, quux = Test.__properties__

        self.assertEquals(bfoo.name, 'foo')
        self.assertEquals(bbar.name, 'bar')
        self.assertEquals(bbaz.name, 'baz')

        self.assertEquals(bfoo.typedValue.__class__, formless.String)
        self.assertEquals(bbar.typedValue.__class__, formless.Text)
        self.assertEquals(bbaz.typedValue.__class__, formless.Integer)
        self.assertEquals(quux.typedValue.__class__, formless.Object)

        self.assertEquals(quux.typedValue.iface, Other)


    def testTypedInterfaceMethods(self):
        class IFoo(formless.TypedInterface):
            pass

        _indirectIFoo = lambda: IFoo    # XXX work around Python issue1569356
        class Test2(formless.TypedInterface):
            def foo(foobar=formless.String()):
                """This is a description of foo"""
                pass
            foo = formless.autocallable(foo)

            def bar(barbaz=formless.Integer(label="The Baz")):
                ## this has no docstring, make sure it doesn't fail
                return formless.String()
            bar = formless.autocallable(bar, someAttribute="Hello")

            def baz(bazfoo=formless.Boolean(label="The Foo", description="The foo to baz.")):
                """The Label

                The description"""
                IFoo = _indirectIFoo()
                return IFoo
            baz = formless.autocallable(baz)

        self.assertEquals(Test2.__methods__, Test2.__spec__)

        bfoo, bbar, bbaz = Test2.__methods__

        self.assertEquals(bfoo.name, 'foo')
        self.assertEquals(bbar.name, 'bar')
        self.assertEquals(bbar.getAttribute('someAttribute'), "Hello")
        self.assertEquals(bbaz.name, 'baz')

        self.assertEquals(bfoo.label, 'Foo')
        self.assertEquals(bfoo.description, 'This is a description of foo')

        self.assertEquals(bbar.label, 'Bar')
        self.assertEquals(bbar.description, '')

        self.assertEquals(bbaz.label, 'The Label')
        self.assertEquals(bbaz.description, 'The description')

        def getArgTypes(mbinding):
            return [x.typedValue.__class__ for x in mbinding.arguments]

        self.assertEquals(getArgTypes(bfoo), [formless.String])
        self.assertEquals(bfoo.returnValue.iface, None)

        self.assertEquals(getArgTypes(bbar), [formless.Integer])
        self.assertEquals(bbar.returnValue.__class__, formless.String)

        self.assertEquals(getArgTypes(bbaz), [formless.Boolean])
        self.assertEquals(bbaz.returnValue.iface, IFoo)

        def firstArg(mbinding):
            return mbinding.arguments[0]

        self.assertEquals(firstArg(bfoo).label, 'Foobar')
        self.assertEquals(firstArg(bfoo).description, '')

        self.assertEquals(firstArg(bbar).label, 'The Baz')
        self.assertEquals(firstArg(bbar).description, '')

        self.assertEquals(firstArg(bbaz).label, 'The Foo')
        self.assertEquals(firstArg(bbaz).description, 'The foo to baz.')

    def testTypedInterfaceMethods_actionLabel(self):
        """When no label was given, docstring is given preference compared to action."""
        class Test(formless.TypedInterface):
            def foo(foobar=formless.String()):
                """
                Label for foo
                Description for foo
                """
                pass
            foo = formless.autocallable(foo, action="Do something!")

        self.assertEquals(Test.__methods__, Test.__spec__)
        (bfoo,) = Test.__methods__

        self.assertEquals(bfoo.name, 'foo')

        self.assertEquals(bfoo.label, 'Label for foo')
        self.assertEquals(bfoo.description, 'Description for foo')

    def testTypedInterfaceMethods_explicitLabel(self):
        """When a label was given, it is given preference compared to docstring."""
        class Test(formless.TypedInterface):
            def foo(foobar=formless.String()):
                """
                Docstring label for foo
                Description for foo
                """
                pass
            foo = formless.autocallable(foo,
                                        action="Do something!",
                                        label="Explicit label for foo",
                                        )

        self.assertEquals(Test.__methods__, Test.__spec__)
        (bfoo,) = Test.__methods__

        self.assertEquals(bfoo.name, 'foo')

        self.assertEquals(bfoo.label, 'Explicit label for foo')
        self.assertEquals(bfoo.description, 'Description for foo')

    def testTypedInterfaceMethods_deprecated(self):
        class Test(formless.TypedInterface):
            def noArgs(self):
                pass
            noArgs = formless.autocallable(noArgs)

            def oneArg(self, someParam=formless.String()):
                pass
            oneArg = formless.autocallable(oneArg)

        self.assertEquals(Test.__methods__, Test.__spec__)
        m_noArgs, m_oneArg = Test.__methods__

        self.assertEquals(len(m_noArgs.arguments), 0)
        self.assertEquals(len(m_oneArg.arguments), 1)

    def testTypedInterfaceMethods_nonAutocallable(self):
        class Test(formless.TypedInterface):
            def notAutocallable(arg1, arg2):
                pass

        self.assertEquals(Test.__methods__, Test.__spec__)
        self.assertEquals(Test.__methods__, [])

class IListWithActions(formless.TypedInterface):
    def actionOne(theSubset = formless.List()):
        pass
    def actionTwo(theSubset = formless.List()):
        pass

    theListOfStuff = formless.List(actions=[actionOne, actionTwo])


class TestListActions(TestCase):
    def test_listActionMetadata(self):
        ## IListWithActions only has one binding, a Property binding
        ## of theListOfStuff to a List with some actions.
        actions = IListWithActions.__spec__[0].typedValue.actions
        self.failUnless(reduce, (lambda x: x.name == 'actionOne', actions))
        self.failUnless(reduce, (lambda x: x.name == 'actionTwo', actions))


class TestPropertyGroups(TestCase):
    def test_nestedTypedInterfaces(self):
        class Outer(formless.TypedInterface):
            aSimpleProperty = formless.Object()

            class Inner(formless.TypedInterface):
                """Docstring
                
                This is a docstring.
                """
                anInnerProperty = formless.Integer()

        self.assertEquals(Outer.__spec__[1].typedValue.iface, Outer.Inner)
        inn = Outer.__spec__[1].typedValue.iface
