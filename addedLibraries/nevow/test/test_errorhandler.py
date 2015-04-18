
from zope.interface import implements
from twisted.python import log
from twisted.internet import defer
from nevow import appserver, context, inevow, loaders, rend, tags as T, testutil


class Root(rend.Page):
    docFactory = loaders.stan(T.html[T.p['Root']])



class NotFoundHandler(object):
    implements(inevow.ICanHandleNotFound)
    html = 'NotFoundHandler'
    def renderHTTP_notFound(self, ctx):
        return self.html

class BrokenException(Exception):
    pass

class BadNotFoundHandler(object):
    implements(inevow.ICanHandleNotFound)
    html = 'NotFoundHandler'
    exceptionType = BrokenException
    exceptionMessage ='Error from BadNotFoundHandler'
    def __init__(self, exceptionType=None):
        if exceptionType is not None:
            self.exceptionType = exceptionType
    def renderHTTP_notFound(self, ctx):
        raise self.exceptionType(self.exceptionMessage)


def getResource(root, path):
    ctx = context.RequestContext(tag=testutil.FakeRequest(uri=path))
    return appserver.NevowSite(root).getPageContextForRequestContext(ctx).addCallback(
        lambda newctx: newctx.tag)

def renderResource(uri, notFoundHandler=None):
    """Render a resource at some uri and return the response code and html.
    """

    root = Root()
    if notFoundHandler is not None:
        root.remember(notFoundHandler, inevow.ICanHandleNotFound)
    site = appserver.NevowSite(root)
    ctx = context.SiteContext(tag=site)

    request = testutil.FakeRequest(uri=uri)
    ctx = context.RequestContext(parent=ctx, tag=request)

    def waitmore(newctx):
        return defer.maybeDeferred(newctx.tag.renderHTTP, newctx).addCallback(lambda html: (request.code, html))
    return site.getPageContextForRequestContext(ctx).addCallback(waitmore)


class Test404(testutil.TestCase):

    def test_standard404(self):
        """Test the standard 404 handler.
        """
        root = Root()
        def later(resource):
            self.failUnless(isinstance(resource, rend.FourOhFour))
            def morelater((code, html)):
                self.assertEquals(rend.FourOhFour.notFound, html)
                self.assertEquals(code, 404)
            return renderResource('/foo').addCallback(morelater)
        return getResource(root, '/foo').addCallback(later)

    def test_remembered404Handler(self):
        def later((code, html)):
            self.assertEquals(html, NotFoundHandler.html)
            self.assertEquals(code, 404)

        return renderResource('/foo', notFoundHandler=NotFoundHandler()).addCallback(later)

    def test_keyErroringNotFoundHandler(self):
        def later((code, html)):
            self.assertEquals(rend.FourOhFour.notFound, html)
            self.assertEquals(code, 404)
            fe = self.flushLoggedErrors(BrokenException)
            self.assertEquals(len(fe), 1)
        return renderResource('/foo', notFoundHandler=BadNotFoundHandler()).addCallback(later)

