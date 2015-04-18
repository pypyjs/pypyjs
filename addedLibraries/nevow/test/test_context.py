# -*- test-case-name: nevow.test.test_context -*-
# Copyright (c) 2004 Divmod.
# See LICENSE for details.

import itertools
import time

import zope.interface as zi
from twisted.python.components import registerAdapter

from nevow import context
from nevow import tags
from nevow import inevow

from nevow.testutil import TestCase


class IStuff(zi.Interface): pass


class TestRememberLocate(TestCase):
    def test_basic(self):
        top = context.WovenContext()
        middle = context.WovenContext(top, tags.invisible())
        bottom = context.WovenContext(middle, tags.invisible())
        top.remember(0, IStuff)
        self.assertEquals(bottom.locate(IStuff), 0)
        middle.remember(1, IStuff)
        self.assertEquals(bottom.locate(IStuff), 1)
        self.assertEquals(bottom.locate(IStuff, depth=2), 0)

    def test_reverse(self):
        top = context.WovenContext().remember(0, IStuff)
        bottom = context.WovenContext(top, tags.invisible()).remember(1, IStuff)
        self.assertEquals(bottom.locate(IStuff, depth=-1), 0)

    def test_page(self):
        page = context.PageContext(tag=1)
        page.remember(1, inevow.IData)
        ctx = context.WovenContext(page, tags.invisible())
        self.assertEquals(ctx.locate(inevow.IData), 1)
        self.assertEquals(ctx.locate(inevow.IData, depth=-1), 1)

    def test_factoryContext(self):
        ctx = TestContext()
        self.assertEquals(IFoo(ctx), True)

    def test_factoryContextFromLocate(self):
        factory = TestContext()
        ctx = context.WovenContext(parent=factory)
        self.assertEquals(IFoo(ctx), True)

    def test_factoryContextRemembers(self):
        basectx = TestContext()
        ctx = context.WovenContext(parent=basectx)
        bar1 = IBar(ctx)
        ctx = context.WovenContext(parent=basectx)
        bar2 = IBar(ctx)
        self.assertEqual(bar1, bar2)

    def test_negativeLocate(self):
        ctx = context.WovenContext()
        self.assertRaises(KeyError, ctx.locate, IFoo)
        self.assertRaises(TypeError, IFoo, ctx)

    def test_negativeSomething(self):
        factory = TestContext()
        ctx = context.WovenContext(parent=factory)
        self.assertRaises(KeyError, ctx.locate, inevow.IData)

    def test_slots(self):
        ctx = context.WovenContext()
        ctx.fillSlots('foo', 'bar')
        ctx = context.WovenContext(parent=ctx)
        self.assertEquals(
            ctx.locateSlotData('foo'),
            'bar')

    def test_negativeSlots(self):
        ctx = context.WovenContext()
        self.assertRaises(KeyError, ctx.locateSlotData, 'foo')

    def benchmark_longContextChainArg(self):
        from nevow import testutil
        ctx = context.RequestContext(
            tag=testutil.FakeRequest(args=dict(foo=["foo"], bar=["bar"])))
        for x in range(5):
            ## Do some factory contexts
            ctx = TestContext(parent=ctx)
        for x in range(100):
            ## Do a bunch of crap
            ctx = context.WovenContext(parent=ctx)
        ## Look for some request arguments

        loops = 1e4
        before = time.clock()
        for x in xrange(loops):
            ignored = ctx.arg('foo')
            ignored = ctx.arg('bar')
        after = time.clock()

        self.recordStat({"arg/(cpu sec)": loops / (after - before)})

class TestContext(context.FactoryContext):
    """A target for registering adatpters.
    """

# IFoo interface/adapter that always adapts to True
class IFoo(zi.Interface):
    """A dummy interface.
    """

dummyAdapter = lambda x: True

registerAdapter(dummyAdapter, TestContext, IFoo)


# IBar interface that adapts to an incrementing value
class IBar(zi.Interface):
    """A dummy interface.
    """

nextBar = itertools.count()
def barFactory(ctx):
    return nextBar.next()

registerAdapter(barFactory, TestContext, IBar)

