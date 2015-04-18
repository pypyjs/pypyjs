"""
Tests for on-the-fly content compression encoding.
"""
from StringIO import StringIO
from gzip import GzipFile

from zope.interface import implements

from twisted.trial.unittest import TestCase
from twisted.internet.defer import succeed

from nevow.inevow import IResource, IRequest
from nevow.testutil import FakeRequest
from nevow.context import RequestContext
from nevow.appserver import errorMarker
from nevow.rend import NotFound
from nevow.compression import CompressingResourceWrapper, CompressingRequestWrapper
from nevow.compression import parseAcceptEncoding, _ProxyDescriptor



class HeaderTests(TestCase):
    """
    Tests for header parsing.
    """
    def test_parseAcceptEncoding(self):
        """
        Test the parsing of a variety of Accept-Encoding field values.
        """
        cases = [
            ('compress, gzip',
             {'compress': 1.0, 'gzip': 1.0, 'identity': 0.0001}),
            ('',
             {'identity': 0.0001}),
            ('*',
             {'*': 1}),
            ('compress;q=0.5, gzip;q=1.0',
             {'compress': 0.5, 'gzip': 1.0, 'identity': 0.0001}),
            ('gzip;q=1.0, identity;q=0.5, *;q=0',
             {'gzip': 1.0, 'identity': 0.5, '*': 0})
            ]

        for value, result in cases:
            self.assertEqual(parseAcceptEncoding(value), result, msg='error parsing %r' % value)



class _Dummy(object):
    """
    Dummy object just to get an instance dict.
    """



class _Wrapper(object):
    """
    Test wrapper.
    """
    x = _ProxyDescriptor('x')
    y = _ProxyDescriptor('y')

    def __init__(self, underlying):
        self.underlying = underlying



class ProxyDescriptorTests(TestCase):
    """
    Tests for L{_ProxyDescriptor}.
    """
    def setUp(self):
        """
        Set up a dummy object and a wrapper for it.
        """
        self.dummy = _Dummy()
        self.dummy.x = object()
        self.dummy.y = object()
        self.wrapper = _Wrapper(self.dummy)


    def test_proxyGet(self):
        """
        Getting a proxied attribute should retrieve the underlying attribute.
        """
        self.assertIdentical(self.wrapper.x, self.dummy.x)
        self.assertIdentical(self.wrapper.y, self.dummy.y)
        self.dummy.x = object()
        self.assertIdentical(self.wrapper.x, self.dummy.x)


    def test_proxyClassGet(self):
        """
        Getting a proxied attribute from the class should just retrieve the
        descriptor.
        """
        self.assertIdentical(_Wrapper.x, _Wrapper.__dict__['x'])


    def test_proxySet(self):
        """
        Setting a proxied attribute should set the underlying attribute.
        """
        self.wrapper.x = object()
        self.assertIdentical(self.dummy.x, self.wrapper.x)
        self.wrapper.y = 5
        self.assertEqual(self.dummy.y, 5)


    def test_proxyDelete(self):
        """
        Deleting a proxied attribute should delete the underlying attribute.
        """
        self.assertTrue(hasattr(self.dummy, 'x'))
        del self.wrapper.x
        self.assertFalse(hasattr(self.dummy, 'x'))



class RequestWrapperTests(TestCase):
    """
    Tests for L{CompressingRequestWrapper}.
    """
    def setUp(self):
        """
        Wrap a request fake to test the wrapper.
        """
        self.request = FakeRequest()
        self.wrapper = CompressingRequestWrapper(self.request)


    def test_attributes(self):
        """
        Attributes on the wrapper should be forwarded to the underlying
        request.
        """
        attributes = ['method', 'uri', 'path', 'args', 'received_headers']
        for attrName in attributes:
            self.assertIdentical(getattr(self.wrapper, attrName),
                                 getattr(self.request, attrName))


    def test_missingAttributes(self):
        """
        Attributes that are not part of the interfaces being proxied should not
        be proxied.
        """
        self.assertRaises(AttributeError, getattr, self.wrapper, 'doesntexist')
        self.request._privateTestAttribute = 42
        self.assertRaises(AttributeError, getattr, self.wrapper, '_privateTestAttribute')


    def test_contentLength(self):
        """
        Content-Length header should be discarded when compression is in use.
        """
        self.assertNotIn('content-length', self.request.headers)
        self.wrapper.setHeader('content-length', 1234)
        self.assertNotIn('content-length', self.request.headers)

        self.request.setHeader('content-length', 1234)
        self.wrapper = CompressingRequestWrapper(self.request)
        self.assertNotIn('content-length', self.request.headers)


    def test_responseHeaders(self):
        """
        Content-Encoding header should be set appropriately.
        """
        self.assertEqual(self.request.headers['content-encoding'], 'gzip')


    def test_lazySetup(self):
        """
        The gzip prelude should only be written once real data is written.

        This is necessary to avoid terminating the header too quickly.
        """
        self.assertEqual(self.request.accumulator, '')
        self.wrapper.write('foo')
        self.assertNotEqual(self.request.accumulator, '')


    def _ungzip(self, data):
        """
        Un-gzip some data.
        """
        s = StringIO(data)
        return GzipFile(fileobj=s, mode='rb').read()


    def test_encoding(self):
        """
        Response content should be written out in compressed format.
        """
        self.wrapper.write('foo')
        self.wrapper.write('bar')
        self.wrapper.finishRequest(True)
        self.assertEqual(self._ungzip(self.request.accumulator), 'foobar')


    def test_finish(self):
        """
        Calling C{finishRequest()} on the wrapper should cause the underlying
        implementation to be called.
        """
        self.wrapper.finishRequest(True)
        self.assertTrue(self.request.finished)



class TestResource(object):
    """
    L{IResource} implementation for testing.

    @ivar lastRequest: The last request we were rendered with.
    @type lastRequest: L{IRequest} or C{None}
    @ivar segments: The segments we were constructed with.
    @type segments: C{list}
    @ivar html: The data to return from C{renderHTTP}.
    """
    implements(IResource)

    lastRequest = None

    def __init__(self, segments=[], html='o hi'):
        self.segments = segments
        self.html = html


    def locateChild(self, ctx, segments):
        """
        Construct a new resource of our type.

        We hand out child resources for any segments, as this is the simplest
        thing to do.
        """
        return type(self)(segments), []


    def renderHTTP(self, ctx):
        """
        Stash the request for later inspection.
        """
        self.lastRequest = IRequest(ctx)
        return self.html



class TestChildlessResource(object):
    """
    L{IResource} implementation with no children.
    """
    implements(IResource)

    def locateChild(self, ctx, segments):
        """
        Always return C{NotFound}.
        """
        return NotFound



class TestDeferredResource(object):
    """
    L{IResource} implementation with children.
    """
    implements(IResource)

    def locateChild(self, ctx, segments):
        """
        Construct a new resource of our type.

        We hand out child resources for any segments, but the resource itself
        is wrapped in a deferred.
        """
        return succeed(type(self)()), []



class TestResourceWrapper(CompressingResourceWrapper):
    """
    Subclass for testing purposes, just to create a new type.
    """


class TestBrokenResource(object):
    """
    L{IResource} implementation that returns garbage from C{locateChild}.
    """
    implements(IResource)

    def locateChild(self, ctx, segments):
        """
        Return some garbage.
        """
        return 42



class ResourceWrapper(TestCase):
    """
    Tests for L{CompressingResourceWrapper}.

    @ivar resource: The underlying resource for testing.
    @type resource: L{TestResource}
    @ivar wrapped: The wrapped resource.
    @type wrapped: L{CompressingResourceWrapper}
    @ivar request: A fake request.
    @type request: L{FakeRequest}
    @ivar ctx: A dummy context.
    @type ctx: L{RequestContext}
    """
    def setUp(self):
        self.resource = TestResource()
        self.wrapped = CompressingResourceWrapper(self.resource)
        self.request = FakeRequest()
        self.ctx = RequestContext(tag=self.request)


    def test_rendering(self):
        """
        Rendering a wrapped resource renders the underlying resource with a
        wrapped request if compression is available.
        """
        self.wrapped.canCompress = lambda req: True
        self.wrapped.renderHTTP(self.ctx)
        self.assertEqual(type(self.resource.lastRequest), CompressingRequestWrapper)
        self.assertIdentical(self.resource.lastRequest.underlying, self.request)


    def test_renderingUnwrapped(self):
        """
        Rendering a wrapped resource renders the underlying resource with an
        unwrapped request if compression is not available.
        """
        self.wrapped.canCompress = lambda req: False
        self.wrapped.renderHTTP(self.ctx)
        self.assertIdentical(self.resource.lastRequest, self.request)


    def test_awfulHack(self):
        """
        Rendering a wrapped resource should finish off the request, and return
        a special sentinel value to prevent the Site machinery from trying to
        finish it again.
        """
        def _cbCheckReturn(result):
            self.rendered = True
            self.assertIdentical(result, errorMarker)
            self.assertTrue(self.request.finished)

        self.rendered = False
        self.wrapped.canCompress = lambda req: True
        self.wrapped.renderHTTP(self.ctx).addCallback(_cbCheckReturn)
        # The callback should run synchronously
        self.assertTrue(self.rendered)


    def test_rendering(self):
        """
        Returning something other than C{str} causes the value to be passed
        through.
        """
        def _cbResult(result):
            self.result = result

        marker = object()
        self.resource.html = marker
        self.wrapped.canCompress = lambda req: True
        self.wrapped.renderHTTP(self.ctx).addCallback(_cbResult)
        self.assertIdentical(marker, self.result)


    def _cbCheckChild(self, result):
        """
        Check that the child resource is wrapped correctly.
        """
        self.checked = True


    def _locateChild(self, resource, segments):
        """
        Helper function for retrieving a child synchronously.
        """
        def _cbGotChild(result):
            self.gotChild = True
            self.result = result

        def _ebChild(f):
            self.gotChild = 'error'
            self.f = f

        self.gotChild = False
        resource.locateChild(None, segments).addCallbacks(_cbGotChild, _ebChild)
        self.assertTrue(self.gotChild)
        if self.gotChild == 'error':
            self.f.raiseException()
        return self.result


    def test_wrapChildren(self):
        """
        Any children of the wrapped resource should also be wrapped.
        """
        self.checked = False
        child, segments = self._locateChild(self.wrapped, ['some', 'child', 'segments'])
        self.assertIdentical(type(child), type(self.wrapped))
        self.assertEqual(child.underlying.segments, ['some', 'child', 'segments'])


    def test_wrapChildrenSubclass(self):
        """
        The request wrapper should wrap children with the same type.
        """
        self.wrapped = TestResourceWrapper(self.resource)
        self.test_wrapChildren()


    def test_childNotFound(self):
        """
        The request wrapper should pass C{NotFound} through.
        """
        wrapped = CompressingResourceWrapper(TestChildlessResource())
        result = self._locateChild(wrapped, ['foo'])
        self.assertEqual(result, NotFound)


    def test_deferredChild(self):
        """
        The wrapper should deal with a resource wrapped in a deferred returned
        from locateChild.
        """
        wrapped = CompressingResourceWrapper(TestDeferredResource())
        child, segments = self._locateChild(wrapped, ['foo'])
        self.assertEqual(type(child.underlying), TestDeferredResource)
        self.assertEqual(segments, [])


    def test_brokenChild(self):
        """
        C{ValueError} should be raised if the underlying C{locateChild} returns
        something bogus.
        """
        wrapped = CompressingResourceWrapper(TestBrokenResource())
        self.assertRaises(ValueError, self._locateChild, wrapped, ['foo'])


    def test_negotiation(self):
        """
        Request wrapping should only occur when the client has indicated they
        can accept compression.
        """
        self.assertFalse(self.wrapped.canCompress(self.request))

        self.request.received_headers['accept-encoding'] = 'foo;q=1.0, bar;q=0.5, baz'
        self.assertFalse(self.wrapped.canCompress(self.request))

        self.request.received_headers['accept-encoding'] = 'gzip'
        self.assertTrue(self.wrapped.canCompress(self.request))

        self.request.received_headers['accept-encoding'] = 'gzip;q=0.5'
        self.assertTrue(self.wrapped.canCompress(self.request))

        self.request.received_headers['accept-encoding'] = 'gzip;q=0'
        self.assertFalse(self.wrapped.canCompress(self.request))
