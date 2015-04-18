# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from zope.interface import implements

from twisted.python import components

from nevow import tags
from nevow import inevow
from nevow import context
from nevow import util

import formless
from formless import webform
from formless import iformless
from formless import configurable

from nevow.test import test_flatstan

class Base(test_flatstan.Base):
    implements(iformless.IConfigurableFactory)

    synchronousLocateConfigurable = False

    def locateConfigurable(self, *args, **kw):
        r = iformless.IConfigurable(self.conf)
        if not self.synchronousLocateConfigurable:
            r = util.succeed(r)
        return r

    def setupContext(self, *args, **kw):
        ctx = test_flatstan.Base.setupContext(self, *args, **kw)
        return context.PageContext(tag=tags.html(), parent=ctx)

    def render(self, tag, setupContext=lambda c:c):
        return test_flatstan.Base.render(
            self, tag, setupContext=setupContext,
            wantDeferred=True)

    def renderForms(self, configurable, ctx=None, *args, **kwargs):
        self.conf = configurable
        if ctx is None:
            ctx = self.setupContext(False)
        ctx.remember(self, iformless.IConfigurableFactory)
        return self.render(
            webform.renderForms(*args, **kwargs),
            setupContext=lambda c: ctx)

    def postForm(self, ctx, obj, bindingName, args):
        self.conf = obj
        ctx.remember(self, iformless.IConfigurableFactory)

        def trapValidate(f):
            f.trap(formless.ValidateError)
            e = f.value
            errors = ctx.locate(iformless.IFormErrors)
            ## Set the overall error for this form
            errors.setError(bindingName, e.formErrorMessage)
            errors.updateErrors(bindingName, e.errors)
            ctx.locate(iformless.IFormDefaults).getAllDefaults(bindingName).update(e.partialForm)

        return util.maybeDeferred(self.locateConfigurable,obj).addCallback(lambda x: x.postForm(
            ctx, bindingName, args
            )).addErrback(trapValidate)


class Complete(Base):
    def test_configureProperty(self):
        class IStupid(formless.TypedInterface):
            foo = formless.String()

        class StupidThing(configurable.Configurable):
            implements(IStupid)

            def __init__(self):
                configurable.Configurable.__init__(self, None)
                self.foo = 'foo'

        dumb = StupidThing()

        def doasserts(val):
            self.assertSubstring('freeform_post!!foo', val)
            self.assertSubstring('foo', val)
            self.assertSubstring('type="text"', val)
            self.assertSubstring('<input type="submit"', val)
        return self.renderForms(dumb).addCallback(doasserts)


    def test_configureMethod(self):
        class IDumb(formless.TypedInterface):
            def foo(bar=formless.String()):
                return formless.String()
            foo = formless.autocallable(foo)

        class DumbThing(configurable.Configurable):
            implements(IDumb)

            def foo(self, bar):
                return "baz"

        stupid = DumbThing(1)

        def doasserts(val):
            self.assertSubstring('freeform_post!!foo', val)
            self.assertSubstring('foo', val)
            self.assertSubstring('bar', val)
        return self.renderForms(stupid).addCallback(doasserts)


class BuildingBlocksTest(Base):
    def test_1_renderTyped(self):
        binding = formless.Property('hello', formless.String(
            label="Hello",
            description="Hello, world."))

        ## Look up a renderer specific to the type of our binding, typedValue;
        renderer = iformless.ITypedRenderer(
            binding.typedValue, None)

        ## But render the binding itself with this renderer
        ## The binding has the ".name" attribute we need
        def later(val):
            self.assertSubstring('hello', val)
            self.assertSubstring('Hello', val)
            self.assertSubstring('Hello, world.', val)
            self.failIfSubstring('</form>', val)
            self.failIfSubstring('<input type="submit"', val)
        return self.render(tags.invisible(data=binding, render=renderer)).addCallback(later)

    test_1_renderTyped.todo = "Render binding"

    def test_2_renderPropertyBinding(self):
        binding = formless.Property('goodbye', formless.String(
            label="Goodbye",
            description="Goodbye cruel world"))

        # Look up an IBindingRenderer, which will render the form and the typed
        renderer = iformless.IBindingRenderer(binding)
        def later(val):
            self.assertSubstring('<form ', val)
            self.assertSubstring('<input type="submit"', val)
            self.assertSubstring('name="goodbye"', val)
            self.assertSubstring('Goodbye', val)
            self.assertSubstring('Goodbye cruel world', val)
        return self.render(tags.invisible(data=binding, render=renderer)).addCallback(later)

    def test_3_renderMethodBinding(self):
        binding = formless.MethodBinding('doit', formless.Method(
            returnValue=None,
            arguments=[formless.Argument('foo', formless.String(label="Foo"))],
            label="Do It",
            description="Do it to 'em all"))

        renderer = iformless.IBindingRenderer(binding)

        def later(val):
            self.assertSubstring('<form ', val)
            self.assertSubstring('Do It', val)
            self.assertSubstring("Do it to 'em all", val)
            self.assertSubstring("Foo", val)
            self.assertSubstring('name="foo"', val)
        return self.render(tags.invisible(data=binding, render=renderer)).addCallback(later)


class TestDefaults(Base):
    def test_1_renderWithDefaultValues(self):
        binding = formless.MethodBinding('haveFun', formless.Method(
            returnValue=None,
            arguments=[formless.Argument('funValue', formless.Integer(label="Fun Value", default=0))]
        ))

        def setupCtx(ctx):
            ctx.locate(iformless.IFormDefaults).setDefault('funValue', 15)
            return ctx

        renderer = iformless.IBindingRenderer(binding)
        def later(val):
            self.failIfSubstring('0', val)
            self.assertSubstring('15', val)
        return self.render(tags.invisible(data=binding, render=renderer), setupContext=setupCtx).addCallback(
            later)

    def test_2_renderWithObjectPropertyValues(self):
        class IDefaultProperty(formless.TypedInterface):
            default = formless.Integer(default=2)

        class Foo(configurable.Configurable):
            implements(IDefaultProperty)
            default = 54

        def later(val):
            self.failIfSubstring('2', val)
            self.assertSubstring('54', val)
        return self.renderForms(Foo(None)).addCallback(later)

    def test_3_renderWithAdapteeAttributeValues(self):
        class IDefaultProperty(formless.TypedInterface):
            default = formless.Integer(default=2)

        class Adaptee(object):
            default = 69

        class Bar(configurable.Configurable):
            implements(IDefaultProperty)

        def later(val):
            self.failIfSubstring('2', val)
            self.assertSubstring('69', val)
        return self.renderForms(Bar(Adaptee())).addCallback(later)

    def test_4_testBindingDefaults(self):
        class IBindingDefaults(formless.TypedInterface):
            def aMethod(foo=formless.String(default="The foo")):
                pass
            aMethod = formless.autocallable(aMethod)

            aProperty = formless.String(default="The property")

        class Implements(configurable.Configurable):
            implements(IBindingDefaults)

        def later(val):
            self.assertSubstring("The foo", val)
            self.assertSubstring("The property", val)
        return self.renderForms(Implements(None)).addCallback(later)

    def test_5_testDynamicDefaults(self):
        class IDynamicDefaults(formless.TypedInterface):
            def aMethod(foo=formless.String(default="NOTFOO")):
                pass
            def bMethod(foo=formless.String(default="NOTBAR")):
                pass
            aMethod = formless.autocallable(aMethod)
            bMethod = formless.autocallable(bMethod)

        class Implements(configurable.Configurable):
            implements(IDynamicDefaults)

        def later(val):
            self.assertSubstring("YESFOO", val)
            self.assertSubstring("YESBAR", val)
            self.assertNotSubstring("NOTFOO", val)
            self.assertNotSubstring("NOTBAR", val)

        return self.renderForms(Implements(None), bindingDefaults={
                'aMethod': {'foo': 'YESFOO'},
                'bMethod': {'foo': 'YESBAR'}}).addCallback(later)


class TestNonConfigurableSubclass(Base):
    def test_1_testSimple(self):
        class ISimpleTypedInterface(formless.TypedInterface):
            anInt = formless.Integer()
            def aMethod(aString = formless.String()):
                return None
            aMethod = formless.autocallable(aMethod)

        class ANonConfigurable(object): # Not subclassing Configurable
            implements(ISimpleTypedInterface) # But implements a TypedInterface

        def later(val):
            self.assertSubstring('anInt', val)
            self.assertSubstring('aMethod', val)

        return self.renderForms(ANonConfigurable()).addCallback(later)



class TestPostAForm(Base):
    def test_1_failAndSucceed(self):
        class IAPasswordMethod(formless.TypedInterface):
            def password(pword = formless.Password(), integer=formless.Integer()):
                pass
            password = formless.autocallable(password)

        class APasswordImplementation(object):
            implements(IAPasswordMethod)
            matched = False
            def password(self, pword, integer):
                self.matched = True
                return "password matched"

        theObj = APasswordImplementation()
        ctx = self.setupContext()

        D = self.postForm(ctx, theObj, "password", {"pword": ["these passwords"], "pword____2": ["don't match"], 'integer': ['Not integer']})
        def after(result):
            self.assertEquals(theObj.matched, False)
            def later(val):
                self.assertSubstring("Passwords do not match. Please reenter.", val)
                self.assertSubstring('value="Not integer"', val)
            return self.renderForms(theObj, ctx).addCallback(later)
        return D.addCallback(after)

    def test_2_propertyFailed(self):
        class IAProperty(formless.TypedInterface):
            prop = formless.Integer()

        class Impl(object):
            implements(IAProperty)
            prop = 5

        theObj = Impl()
        ctx = self.setupContext()
        D = self.postForm(ctx, theObj, 'prop', {'prop': ['bad']})
        def after(result):
            def later(val):
                self.assertSubstring('value="bad"', val)
            return self.renderForms(theObj, ctx).addCallback(later)
        return D.addCallback(after)


class TestRenderPropertyGroup(Base):
    def test_1_propertyGroup(self):
        class Outer(formless.TypedInterface):
            class Inner(formless.TypedInterface):
                one = formless.Integer()
                two = formless.Integer()

                def buckleMyShoe():
                    pass
                buckleMyShoe = formless.autocallable(buckleMyShoe)

                def buriedAlive():
                    pass
                buriedAlive = formless.autocallable(buriedAlive)

        class Implementation(object):
            implements(Outer)
            one = 1
            two = 2
            buckled = False
            buried = False
            def buckleMyShoe(self):
                self.buckled = True
            def buriedAlive(self):
                self.buried = True

        impl = Implementation()
        ctx = self.setupContext()

        def later(val):
            D = self.postForm(ctx, impl, "Inner", {'one': ['Not an integer'], 'two': ['22']})

            def after(result):

                self.assertEquals(impl.one, 1)
                self.assertEquals(impl.two, 2)
                self.assertEquals(impl.buckled, False)
                self.assertEquals(impl.buried, False)

                def evenlater(moreval):
                    self.assertSubstring("is not an integer", moreval)
                    # TODO: Get default values for property groups displaying properly.
                    #self.assertSubstring('value="Not an integer"', moreval)
                    DD = self.postForm(ctx, impl, "Inner", {'one': ['11'], 'two': ['22']})
                    def afterafter(ign):
                        self.assertEquals(impl.one, 11)
                        self.assertEquals(impl.two, 22)
                        self.assertEquals(impl.buckled, True)
                        self.assertEquals(impl.buried, True)
                    return DD.addCallback(afterafter)
                return self.renderForms(impl, ctx).addCallback(evenlater)
            return D.addCallback(after)
        return self.renderForms(impl).addCallback(later)

class TestRenderMethod(Base):

    def testDefault(self):

        class IFoo(formless.TypedInterface):
            def foo(abc=formless.String()):
                pass
            foo = formless.autocallable(foo)

        class Impl:
            implements(IFoo)

        def later(val):
            self.assertSubstring('value="Foo"', val)
            self.assertSubstring('name="abc"', val)
        return self.renderForms(Impl(), bindingNames=['foo']).addCallback(later)


    def testActionLabel(self):

        class IFoo(formless.TypedInterface):
            def foo(abc=formless.String()):
                pass
            foo = formless.autocallable(foo, action='FooFooFoo')

        class Impl:
            implements(IFoo)

        def later(val):
            self.assertSubstring('value="FooFooFoo"', val)
            self.assertSubstring('name="abc"', val)
        return self.renderForms(Impl(), bindingNames=['foo']).addCallback(later)

    def testOneSigMultiCallables(self):

        class IFoo(formless.TypedInterface):
            def sig(abc=formless.String()):
                pass
            foo = formless.autocallable(sig)
            bar = formless.autocallable(sig, action='FooFooFOo')

        class Impl:
            implements(IFoo)

        def later1(val):
            self.assertSubstring('value="Foo"', val)
            def later2(val):
                self.assertSubstring('value="FooFooFoo"', val)
            return self.renderForms(Impl(), bindingNames=['bar']).addCallback(later2)
        return self.renderForms(Impl(), bindingNames=['foo']).addCallback(later1)
    testOneSigMultiCallables.todo = 'autocallable should not set attributes directly on the callable'


class TestCustomTyped(Base):
    def test_typedCoerceWithBinding(self):
        class MyTyped(formless.Typed):
            passed = False
            wasBoundTo = None
            def coerce(self, val, boundTo):
                self.passed = True
                self.wasBoundTo = boundTo
                return "passed"

        typedinst = MyTyped()

        class IMyInterface(formless.TypedInterface):
            def theFunc(test=typedinst):
                pass
            theFunc = formless.autocallable(theFunc)

        class Implementation(object):
            implements(IMyInterface)
            called = False
            def theFunc(self, test):
                self.called = True

        inst = Implementation()
        ctx = self.setupContext()
        D = self.postForm(ctx, inst, 'theFunc', {'test': ['a test value']})
        def after(result):
            self.assertEquals(typedinst.passed, True)
            self.assertEquals(typedinst.wasBoundTo, inst)
            self.assertEquals(inst.called, True)
        return D.addCallback(after)


class TestUneditableProperties(Base):
    def test_uneditable(self):
        class Uneditable(formless.TypedInterface):
            aProp = formless.String(description="the description", immutable=True)

        class Impl(object):
            implements(Uneditable)

            aProp = property(lambda self: "HELLO")

        inst = Impl()

        def later(val):
            self.assertSubstring('HELLO', val)
            self.failIfSubstring('type="text"', val)
        return self.renderForms(inst).addCallback(later)


class TestAfterValidation(Base):
    """Test post-validation rendering"""

    def test_property(self):
        """Test that, when validation fails, the value just entered is redisplayed"""

        class IThing(formless.TypedInterface):
            foo = formless.Integer()

        class Thing:
            implements(IThing)
            foo = 1

        inst = Thing()
        ctx = self.setupContext()
        D = self.postForm(ctx, inst, 'foo', {'foo': ['abc']})
        def after(result):
            def later(val):
                def morelater(noval):
                    self.assertSubstring('value="abc"', val)
                return self.renderForms(inst, ctx).addCallback(morelater)
            return self.renderForms(inst)
        return D.addCallback(after)


class TestHandAndStatus(Base):
    """Test that the method result is available as the hand, and that
    a reasonable status message string is available"""
    def test_hand(self):
        """Test that the hand and status message are available before redirecting the post
        """
        returnResult = object()
        class IMethod(formless.TypedInterface):
            def foo(): pass
            foo = formless.autocallable(foo)

        class Method(object):
            implements(IMethod)
            def foo(self):
                return returnResult

        inst = Method()
        ctx = self.setupContext()
        D = self.postForm(ctx, inst, 'foo', {})
        def after(result):
            self.assertEquals(ctx.locate(inevow.IHand), returnResult)
            self.assertEquals(ctx.locate(inevow.IStatusMessage), "'foo' success.")
        return D.addCallback(after)

    def test_handFactory(self):
        """Test that the hand and status message are available after redirecting the post
        """
        returnResult = object()
        status = 'horray'
        def setupRequest(r):
            r.args['_nevow_carryover_'] = ['abc']
            from nevow import rend
            c = components.Componentized()
            c.setComponent(inevow.IHand, returnResult)
            c.setComponent(inevow.IStatusMessage, status)
            rend._CARRYOVER['abc'] = c
            return r
        ctx = self.setupContext(setupRequest=setupRequest)

        self.assertEquals(ctx.locate(inevow.IHand), returnResult)
        self.assertEquals(ctx.locate(inevow.IStatusMessage), status)


class TestCharsetDetectionSupport(Base):

    def test_property(self):

        class ITest(formless.TypedInterface):
            foo = formless.String()

        class Impl:
            implements(ITest)

        impl = Impl()
        ctx = self.setupContext()
        def later(val):
            self.assertIn('<input type="hidden" name="_charset_" />', val)
            self.assertIn('accept-charset="utf-8"', val)
        return self.renderForms(impl, ctx).addCallback(later)


    def test_group(self):

        class ITest(formless.TypedInterface):
            class Group(formless.TypedInterface):
                foo = formless.String()

        class Impl:
            implements(ITest)

        impl = Impl()
        ctx = self.setupContext()
        def later(val):
            self.assertIn('<input type="hidden" name="_charset_" />', val)
            self.assertIn('accept-charset="utf-8"', val)
        return self.renderForms(impl, ctx).addCallback(later)


    def test_method(self):

        class ITest(formless.TypedInterface):
            def foo(foo = formless.String()):
                pass
            foo = formless.autocallable(foo)

        class Impl:
            implements(ITest)

        impl = Impl()
        ctx = self.setupContext()
        def later(val):
            self.assertIn('<input type="hidden" name="_charset_" />', val)
            self.assertIn('accept-charset="utf-8"', val)
        return self.renderForms(impl, ctx).addCallback(later)


class TestUnicode(Base):

    def test_property(self):

        class IThing(formless.TypedInterface):
            aString = formless.String(unicode=True)

        class Impl(object):
            implements(IThing)
            aString = None

        inst = Impl()
        ctx = self.setupContext()
        D = self.postForm(ctx, inst, 'aString', {'aString':['\xc2\xa3']})
        return D.addCallback(lambda result: self.assertEquals(inst.aString, u'\xa3'))

class TestChoice(Base):
    """Test various behaviors of submitting values to a Choice Typed.
    """

    def test_reject_missing(self):
        # Ensure that if a Choice is not specified, the form is not submitted.

        self.called = []

        class IFormyThing(formless.TypedInterface):
            def choiceyFunc(arg = formless.Choice(["one", "two"], required=True)):
                pass
            choiceyFunc = formless.autocallable(choiceyFunc)

        class Impl(object):
            implements(IFormyThing)

            def choiceyFunc(innerSelf, arg):
                self.called.append(arg)

        inst = Impl()
        ctx = self.setupContext()
        D = self.postForm(ctx, inst, 'choiceyFunc', {})
        return D.addCallback(lambda result: self.assertEquals(self.called, []))


class mg(Base):

    def test_leakyForms(self):

        class ITest(formless.TypedInterface):
            """Test that a property value on one form does not 'leak' into
            a property of the same name on another form.
            """
            foo = formless.String()

            def meth(foo = formless.String()):
                pass
            meth = formless.autocallable(meth)

        class Impl:
            implements(ITest)
            foo = 'fooFOOfoo'

        impl = Impl()
        ctx = self.setupContext()
        def later(val):
            self.assertEquals(val.count('fooFOOfoo'), 1)
        return self.renderForms(impl, ctx)


# What the *hell* is this?!?

#DeferredTestCases = type(Base)(
#    'DeferredTestCases',
#    tuple([v for v in locals().values()
#     if isinstance(v, type(Base)) and issubclass(v, Base)]),
#    {'synchronousLocateConfigurable': True})

