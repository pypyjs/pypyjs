# Copyright (c) 2004 Divmod.
# See LICENSE for details.


from nevow.accessors import convertToData, NoAccessor
from nevow import context
from nevow import inevow
from nevow.stan import directive
from nevow.tags import invisible, slot
from nevow.flat import precompile
from nevow import rend
from nevow.testutil import TestCase


class Base(TestCase):
    def makeContext(self, *args):
        ctx = context.WovenContext()
        ctx.remember(convertToData(self.remember, ctx), inevow.IData)
        for a in args:
            ctx = context.WovenContext(ctx, invisible())
            ctx.remember(convertToData(a, ctx), inevow.IData)
        return ctx


class TestBasics(Base):
    remember = None

    def test_dict_directive(self):
        d = directive('one')
        ctx = self.makeContext({'one': 1, 'two': 2})
        self.assertEquals(1, convertToData(d, ctx))
        self.assertRaises(KeyError, convertToData, directive('asdfasdf'), ctx)

    def test_list_directive(self):
        d= directive('2')
        ctx = self.makeContext([0, 1, 42, 3, 4])
        self.assertEquals(42, convertToData(d, ctx))
        self.assertRaises(IndexError, convertToData, directive('9999'), ctx)
        self.assertRaises(ValueError, convertToData, directive('HAHAHAHA'), ctx)

    def test_function_accessor(self):
        def foo(context, data):
            return 42
        ctx = self.makeContext()
        self.assertEquals(42, convertToData(foo, ctx))
        d = directive('this wont work')
        ctx2 = self.makeContext(foo)
        self.assertRaises(NoAccessor, convertToData, d, ctx2)


thefoo = "foo"

class Factory(rend.DataFactory):
    original = None
    
    def data_foo(self, context, data):
        return thefoo

    def data_dict(self, context, data):
        return {"one": 1, "two": 2}

    def data_list(self, context, data):
        return [1, 99, 43]

    def data_factory(self, context, data):
        return [self]


f = Factory()


class TestThroughDirective(Base):
    remember = f

    def test_simple(self):
        d = directive('foo')
        ctx = self.makeContext()
        self.assertEquals(thefoo, convertToData(d, ctx))

    def test_dict_through_directive(self):
        d1, d2 = directive('dict'), directive('one')
        ctx = self.makeContext(d1)
        self.assertEquals(1, convertToData(d2, ctx))

    def test_list_through_directive(self):
        d1, d2 = directive('list'), directive('1')
        ctx = self.makeContext(d1)
        self.assertEquals(99, convertToData(d2, ctx))

    def test_roundAndRound(self):
        ctx = self.makeContext(
            directive('factory'), directive('0'), directive('factory')
        )
        self.assertEquals(f, convertToData(directive('0'), ctx))
        
    def test_missing(self):
        self.assertRaises(rend.DataNotFoundError, self.makeContext, directive('missing'))


class APage(rend.Page):
    def data_foo(self, ctx, data):
        return "foo"


class TestPageData(Base):
    def test_1_noneOriginal(self):
        data = None
        ctx = context.WovenContext()
        ctx.remember(APage(data), inevow.IData)
        self.assertEquals(data, convertToData(ctx.locate(inevow.IData), ctx))
        self.assertEquals('foo', convertToData(directive('foo'), ctx))

    def test_2_dictOriginal(self):
        data = {'hello': 'world'}
        ctx = context.WovenContext()
        ctx.remember(APage(data), inevow.IData)
        # IGettable should return our dictionary
        self.assertEquals(data, convertToData(ctx.locate(inevow.IData), ctx))
        # IContainer on the *Page*, not the dictionary, should work
        self.assertEquals('foo', convertToData(directive('foo'), ctx))
        # IContainer on the Page should delegate to IContainer(self.original) if no data_ method
        self.assertEquals('world', convertToData(directive('hello'), ctx))



class SlotAccessorTestCase(TestCase):
    def _accessorTest(self, obj):
        ctx = context.WovenContext()
        ctx.fillSlots('slotname', 'foo')
        data = inevow.IGettable(obj).get(ctx)
        self.assertEqual(data, 'foo')


    def test_slotAccessor(self):
        return self._accessorTest(slot('slotname'))


    def test_precompiledSlotAccessor(self):
        return self._accessorTest(precompile(slot('slotname'))[0])
