# Copyright (c) 2004 Divmod.
# See LICENSE for details.


from twisted.internet import defer

from nevow import context, inevow
from nevow import testutil
from nevow.flat import twist
from nevow.util import Deferred

from nevow import rend, loaders, tags



def deferit(data):
    return data.d


def deferdot(data):
    return data.d2


class RenderHelper(testutil.TestCase):
    def renderIt(self):
        req = testutil.FakeRequest()
        self.r.renderHTTP(context.PageContext(tag=self.r, parent=context.RequestContext(tag=req)))
        return req


class LaterRenderTest(RenderHelper):
    def setUp(self):
        self.d = Deferred()
        self.d2 = Deferred()
        self.r = rend.Page(
            docFactory=loaders.stan(
                tags.html(data=self)[
                    'Hello ', tags.invisible[tags.invisible[tags.invisible[tags.invisible[deferit]]]],
                    deferdot,
                    ]
                )
            )

    def test_deferredSupport(self):
        req = self.renderIt()
        self.assertEquals(req.v, '<html>Hello ')
        self.d.callback("world")
        self.assertEquals(req.v, '<html>Hello world')
        self.d2.callback(".")
        self.assertEquals(req.v, '<html>Hello world.</html>')


    def test_deferredSupport2(self):
        req = self.renderIt()
        self.assertEquals(req.v, '<html>Hello ')
        self.d2.callback(".")
        self.assertEquals(req.v, '<html>Hello ')
        self.d.callback("world")
        self.assertEquals(req.v, '<html>Hello world.</html>')

    def test_deferredSupport3(self):
        self.r.buffered = True
        req = self.renderIt()
        self.assertEquals(req.v, '')
        self.d.callback("world")
        self.assertEquals(req.v, '')
        self.d2.callback(".")
        self.assertEquals(req.v, '<html>Hello world.</html>')

    def test_renderNestedDeferredCallables(self):
        """
        Test flattening of a renderer which returns a Deferred which fires with
        a renderer which returns a Deferred.
        """
        def render_inner(ctx, data):
            return defer.succeed('')

        def render_outer(ctx, data):
            return defer.succeed(render_inner)

        ctx = context.WovenContext()
        ctx.remember(None, inevow.IData)

        out = []
        d = twist.deferflatten(render_outer, ctx, out.append)
        def flattened(ign):
            self.assertEquals(out, [''])
        d.addCallback(flattened)
        return d


    def test_renderNestedDeferredErrorHandling(self):
        """
        Test that flattening a renderer which returns a Deferred which fires
        with a renderer which raises an exception causes the outermost Deferred
        to errback.
        """
        class NestedException(Exception):
            pass

        def render_inner(ctx, data):
            raise NestedException()

        def render_outer(ctx, data):
            return defer.succeed(render_inner)

        ctx = context.WovenContext()
        ctx.remember(None, inevow.IData)

        out = []
        d = twist.deferflatten(render_outer, ctx, out.append)
        return self.assertFailure(d, NestedException)


class LaterDataTest(RenderHelper):
    def data_later(self, context, data):
        return self.d

    def data_later2(self, context, data):
        return self.d2

    def setUp(self):
        self.d = Deferred()
        self.d2 = Deferred()
        self.r = rend.Page(docFactory=loaders.stan(
            tags.html(data=self.data_later)[
                'Hello ', str, ' and '
                'goodbye ',str,
                tags.span(data=self.data_later2, render=str)]))

    def test_deferredSupport(self):
        req = self.renderIt()
        self.assertEquals(req.v, '')
        self.d.callback("world")
        self.assertEquals(req.v, '<html>Hello world and goodbye world')
        self.d2.callback(".")
        self.assertEquals(req.v, '<html>Hello world and goodbye world.</html>')


class SuperLaterDataTest(RenderHelper):
    def test_reusedDeferredSupport(self):
        """
        Two occurrences of a particular slot are each replaced with the
        result of the Deferred which is used to fill that slot.
        """
        doc = tags.html[
            tags.slot('foo'), tags.slot('foo')]
        doc.fillSlots('foo', defer.succeed(tags.span['Foo!!!']))
        self.r = rend.Page(docFactory=loaders.stan(doc))
        req = self.renderIt()
        self.assertEquals(req.v, '<html><span>Foo!!!</span><span>Foo!!!</span></html>')


    def test_rendererCalledOnce(self):
        """
        Make sure that if a Deferred fires with a render function that the
        render function is called only once.
        """
        calls = []
        def recorder(ctx, data):
            calls.append(None)
            return str(len(calls))
        doc = tags.html[tags.directive('renderer')]
        class RendererPage(rend.Page):
            docFactory = loaders.stan(doc)
            def render_renderer(self, ctx, data):
                return defer.succeed(recorder)
        self.r = RendererPage()
        req = self.renderIt()
        self.assertEquals(req.v, '<html>1</html>')
