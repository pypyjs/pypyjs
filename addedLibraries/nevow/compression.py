# -*- test-case-name: nevow.test.test_gzip -*-
"""
Implementation of on-the-fly content compression for HTTP resources.
"""
from gzip import GzipFile

from zope.interface import implements

from twisted.internet.defer import maybeDeferred, Deferred
from twisted.internet.interfaces import IConsumer

from nevow.inevow import IRequest, IResource
from nevow.appserver import errorMarker
from nevow.rend import NotFound



def parseAcceptEncoding(value):
    """
    Parse the value of an Accept-Encoding: request header.

    A qvalue of 0 indicates that the content coding is unacceptable; any
    non-zero value indicates the coding is acceptable, but the acceptable
    coding with the highest qvalue is preferred.

    @returns: A dict of content-coding: qvalue.
    @rtype: C{dict}
    """
    encodings = {}
    if value.strip():
        for pair in value.split(','):
            pair = pair.strip()
            if ';' in pair:
                params = pair.split(';')
                encoding = params[0]
                params = dict(param.split('=') for param in params[1:])
                priority = float(params.get('q', 1.0))
            else:
                encoding = pair
                priority = 1.0
            encodings[encoding] = priority

    if 'identity' not in encodings and '*' not in encodings:
        encodings['identity'] = 0.0001

    return encodings



class _ProxyDescriptor(object):
    """
    Forwarding proxy for attributes.
    """
    def __init__(self, name):
        self.name = name


    def __get__(self, oself, type=None):
        """
        Get the underlying attribute.
        """
        if oself is None:
            return self
        return getattr(oself.underlying, self.name)


    def __set__(self, oself, value):
        """
        Set the underlying attribute.
        """
        setattr(oself.underlying, self.name, value)


    def __delete__(self, oself):
        """
        Delete the underlying attribute.
        """
        delattr(oself.underlying, self.name)



def _makeBase():
    """
    Make a base class with proxies for attributes on the underlying request.
    """
    d = {}
    for iface in [IRequest, IConsumer]:
        for attrName in iface.names(all=True):
            d[attrName] = _ProxyDescriptor(attrName)
    return type('_CompressionRequestWrapperBase', (object,), d)

class CompressingRequestWrapper(_makeBase()):
    """
    A request wrapper with support for transport encoding compression.

    @ivar underlying: the request being wrapped.
    @type underlying: L{IRequest}
    @ivar encoding: the IANA-assigned name of the encoding.
    @type encoding: C{str}
    @ivar compressLevel: the level of gzip compression to apply.
    @type compressLevel: C{int}
    """
    implements(IRequest)

    encoding = 'gzip'
    compressLevel = 6


    def __init__(self, underlying):
        self.underlying = underlying
        self.setHeader('content-encoding', self.encoding)
        self._gzipFile = None

        # See setHeader docstring for more commentary.
        self.underlying.headers.pop('content-length', None)


    def setHeader(self, name, value):
        """
        Discard the Content-Length header.

        When compression encoding is in use, the Content-Length header must
        indicate the length of the compressed content; since we are doing the
        compression on the fly, we don't actually know what the length is after
        compression, so we discard this header. If this is an HTTP/1.1 request,
        chunked transfer encoding should be used, softening the impact of
        losing this header.
        """
        if name.lower() == 'content-length':
            return
        else:
            return self.underlying.setHeader(name, value)


    def write(self, data):
        """
        Pass data through to the gzip layer.
        """
        if self._gzipFile is None:
            self._gzipFile = GzipFile(fileobj=self.underlying, mode='wb', compresslevel=self.compressLevel)
        self._gzipFile.write(data)


    def finishRequest(self, success):
        """
        Finish off gzip stream.
        """
        if self._gzipFile is None:
            self.write('')
        self._gzipFile.close()
        self.underlying.finishRequest(success)



class CompressingResourceWrapper(object):
    """
    A resource wrapper with support for transport encoding compression.

    @ivar underlying: the resource being wrapped.
    @type underlying: L{IResource}
    """
    implements(IResource)

    def __init__(self, underlying):
        self.underlying = underlying


    def canCompress(self, req):
        """
        Check whether the client has negotiated a content encoding we support.
        """
        value = req.getHeader('accept-encoding')
        if value is not None:
            encodings = parseAcceptEncoding(value)
            return encodings.get('gzip', 0.0) > 0.0
        return False


    # IResource
    def renderHTTP(self, ctx):
        """
        Render the underlying resource with a wrapped request.
        """
        req = IRequest(ctx)
        if not self.canCompress(req):
            return self.underlying.renderHTTP(ctx)

        req = CompressingRequestWrapper(req)
        ctx.remember(req, IRequest)

        def _cbDoneRendering(html):
            if isinstance(html, str):
                req.write(html)
                req.finishRequest(True)
                return errorMarker
            return html

        return maybeDeferred(self.underlying.renderHTTP, ctx).addCallback(_cbDoneRendering)


    def locateChild(self, ctx, segments):
        """
        Retrieve wrapped child resources via the underlying resource.
        """
        def _cbWrapChild(result):
            if result in [NotFound, errorMarker]:
                return result

            if isinstance(result, tuple):
                res, segments = result
                if isinstance(res, Deferred):
                    return res.addCallback(lambda res: _cbWrapChild((res, segments)))
                return type(self)(IResource(res)), segments

            raise ValueError('Broken resource; locateChild returned %r' % (result,))

        return maybeDeferred(self.underlying.locateChild, ctx, segments).addCallback(_cbWrapChild)
