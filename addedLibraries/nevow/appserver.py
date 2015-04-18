# -*- test-case-name: nevow.test.test_appserver -*-
# Copyright (c) 2004-2008 Divmod.
# See LICENSE for details.

"""
A web application server built using twisted.web
"""

import cgi
from urllib import unquote

from zope.interface import implements, classImplements

import twisted.python.components as tpc
from twisted.web import server

try:
    from twisted.web import http
except ImportError:
    from twisted.protocols import http

from twisted.python import log
from twisted.internet import defer

from nevow import context
from nevow import inevow
from nevow import url
from nevow import flat
from nevow import stan


class UninformativeExceptionHandler:
    implements(inevow.ICanHandleException)

    def renderHTTP_exception(self, ctx, reason):
        request = inevow.IRequest(ctx)
        log.err(reason)
        request.write("<html><head><title>Internal Server Error</title></head>")
        request.write("<body><h1>Internal Server Error</h1>An error occurred rendering the requested page. To see a more detailed error message, enable tracebacks in the configuration.</body></html>")

        request.finishRequest( False )

    def renderInlineException(self, context, reason):
        log.err(reason)
        return """<div style="border: 1px dashed red; color: red; clear: both">[[ERROR]]</div>"""


class DefaultExceptionHandler:
    implements(inevow.ICanHandleException)

    def renderHTTP_exception(self, ctx, reason):
        log.err(reason)
        request = inevow.IRequest(ctx)
        request.setResponseCode(http.INTERNAL_SERVER_ERROR)
        request.write("<html><head><title>Exception</title></head><body>")
        from nevow import failure
        result = failure.formatFailure(reason)
        request.write(''.join(flat.flatten(result)))
        request.write("</body></html>")

        request.finishRequest( False )

    def renderInlineException(self, context, reason):
        from nevow import failure
        formatted = failure.formatFailure(reason)
        desc = str(reason)
        return flat.serialize([
            stan.xml("""<div style="border: 1px dashed red; color: red; clear: both" onclick="this.childNodes[1].style.display = this.childNodes[1].style.display == 'none' ? 'block': 'none'">"""),
            desc,
            stan.xml('<div style="display: none">'),
            formatted,
            stan.xml('</div></div>')
        ], context)


errorMarker = object()


def processingFailed(reason, request, ctx):
    try:
        handler = inevow.ICanHandleException(ctx)
        handler.renderHTTP_exception(ctx, reason)
    except:
        request.setResponseCode(http.INTERNAL_SERVER_ERROR)
        log.msg("Exception rendering error page:", isErr=1)
        log.err()
        log.err("Original exception:", isErr=1)
        log.err(reason)
        request.write("<html><head><title>Internal Server Error</title></head>")
        request.write("<body><h1>Internal Server Error</h1>An error occurred rendering the requested page. Additionally, an error occurred rendering the error page.</body></html>")
        request.finishRequest( False )

    return errorMarker


def defaultExceptionHandlerFactory(ctx):
    return DefaultExceptionHandler()


class NevowRequest(tpc.Componentized, server.Request):
    """
    A Request subclass which does additional
    processing if a form was POSTed. When a form is POSTed,
    we create a cgi.FieldStorage instance using the data posted,
    and set it as the request.fields attribute. This way, we can
    get at information about filenames and mime-types of
    files that were posted.

    TODO: cgi.FieldStorage blocks while decoding the MIME.
    Rewrite it to do the work in chunks, yielding from time to
    time.

    @ivar fields: C{None} or, if the HTTP method is B{POST}, a
        L{cgi.FieldStorage} instance giving the content of the POST.
    """
    implements(inevow.IRequest)

    fields = None

    def __init__(self, *args, **kw):
        server.Request.__init__(self, *args, **kw)
        tpc.Componentized.__init__(self)

    def process(self):
        # extra request parsing
        if self.method == 'POST':
            t = self.content.tell()
            self.content.seek(0)
            self.fields = cgi.FieldStorage(self.content, self.received_headers,
                                           environ={'REQUEST_METHOD': 'POST'})
            self.content.seek(t)

        # get site from channel
        self.site = self.channel.site

        # set various default headers
        self.setHeader('server', server.version)
        self.setHeader('date', server.http.datetimeToString())
        self.setHeader('content-type', "text/html; charset=UTF-8")

        # Resource Identification
        self.prepath = []
        self.postpath = map(unquote, self.path[1:].split('/'))
        self.sitepath = []

        self.deferred = defer.Deferred()

        requestContext = context.RequestContext(parent=self.site.context, tag=self)
        requestContext.remember( (), inevow.ICurrentSegments)
        requestContext.remember(tuple(self.postpath), inevow.IRemainingSegments)

        return self.site.getPageContextForRequestContext(
            requestContext
        ).addErrback(
            processingFailed, self, requestContext
        ).addCallback(
            self.gotPageContext
        )

    def gotPageContext(self, pageContext):
        if pageContext is not errorMarker:
            return defer.maybeDeferred(
                pageContext.tag.renderHTTP, pageContext
            ).addBoth(
                self._cbSetLogger, pageContext
            ).addErrback(
                processingFailed, self, pageContext
            ).addCallback(
                self._cbFinishRender, pageContext
            )

    def finish(self):
        self.deferred.callback("")

    def finishRequest( self, success ):
        server.Request.finish(self)

    def _cbFinishRender(self, html, ctx):
        if isinstance(html, str):
            self.write(html)
            self.finishRequest(  True )
        elif html is errorMarker:
            ## Error webpage has already been rendered and finish called
            pass
        else:
            res = inevow.IResource(html)
            pageContext = context.PageContext(tag=res, parent=ctx)
            return self.gotPageContext(pageContext)
        return html

    _logger = None
    def _cbSetLogger(self, result, ctx):
        try:
            logger = ctx.locate(inevow.ILogger)
        except KeyError:
            pass
        else:
            self._logger = lambda : logger.log(ctx)

        return result

    session = None

    def getSession(self, sessionInterface=None):
        if self.session is not None:
            self.session.touch()
            if sessionInterface:
                return sessionInterface(self.session)
            return self.session
        ## temporary until things settle down with the new sessions
        return server.Request.getSession(self, sessionInterface)

    def URLPath(self):
        return url.URL.fromContext(self)

    def rememberRootURL(self, url=None):
        """
        Remember the currently-processed part of the URL for later
        recalling.
        """
        if url is None:
            return server.Request.rememberRootURL(self)
        else:
            self.appRootURL = url


def sessionFactory(ctx):
    """Given a RequestContext instance with a Request as .tag, return a session
    """
    return ctx.tag.getSession()

requestFactory = lambda ctx: ctx.tag


class NevowSite(server.Site):
    requestFactory = NevowRequest

    def __init__(self, resource, *args, **kwargs):
        resource.addSlash = True
        server.Site.__init__(self, resource, *args, **kwargs)
        self.context = context.SiteContext()

    def remember(self, obj, inter=None):
        """Remember the given object for the given interfaces (or all interfaces
        obj implements) in the site's context.

        The site context is the parent of all other contexts. Anything
        remembered here will be available throughout the site.
        """
        self.context.remember(obj, inter)

    def getPageContextForRequestContext(self, ctx):
        """Retrieve a resource from this site for a particular request. The
        resource will be wrapped in a PageContext which keeps track
        of how the resource was located.
        """
        path = inevow.IRemainingSegments(ctx)
        res = inevow.IResource(self.resource)
        pageContext = context.PageContext(tag=res, parent=ctx)
        return defer.maybeDeferred(res.locateChild, pageContext, path).addCallback(
            self.handleSegment, ctx.tag, path, pageContext
        )

    def handleSegment(self, result, request, path, pageContext):
        if result is errorMarker:
            return errorMarker

        newres, newpath = result
        # If the child resource is None then display a 404 page
        if newres is None:
            from nevow.rend import FourOhFour
            return context.PageContext(tag=FourOhFour(), parent=pageContext)

        # If we got a deferred then we need to call back later, once the
        # child is actually available.
        if isinstance(newres, defer.Deferred):
            return newres.addCallback(
                lambda actualRes: self.handleSegment(
                    (actualRes, newpath), request, path, pageContext))


        #
        # FIX A GIANT LEAK. Is this code really useful anyway?
        #
        newres = inevow.IResource(newres)#, persist=True)
        if newres is pageContext.tag:
            assert not newpath is path, "URL traversal cycle detected when attempting to locateChild %r from resource %r." % (path, pageContext.tag)
            assert  len(newpath) < len(path), "Infinite loop impending..."

        ## We found a Resource... update the request.prepath and postpath
        for x in xrange(len(path) - len(newpath)):
            if request.postpath:
                request.prepath.append(request.postpath.pop(0))

        ## Create a context object to represent this new resource
        ctx = context.PageContext(tag=newres, parent=pageContext)
        ctx.remember(tuple(request.prepath), inevow.ICurrentSegments)
        ctx.remember(tuple(request.postpath), inevow.IRemainingSegments)

        res = newres
        path = newpath

        if not path:
            return ctx

        return defer.maybeDeferred(
            res.locateChild, ctx, path
        ).addErrback(
            processingFailed, request, ctx
        ).addCallback(
            self.handleSegment, request, path, ctx
        )

    def log(self, request):
        if request._logger is None:
            server.Site.log(self, request)
        else:
            request._logger()


## This should be moved somewhere else, it's cluttering up this module.

class OldResourceAdapter(object):
    implements(inevow.IResource)

    # This is required to properly handle the interaction between
    # original.isLeaf and request.postpath, from which PATH_INFO is set in
    # twcgi. Because we have no choice but to consume all elements in
    # locateChild to terminate the recursion, we do so, but first save the
    # length of prepath in real_prepath_len. Subsequently in renderHTTP, if
    # real_prepath_len is not None, prepath is correct to the saved length and
    # the extra segments moved to postpath. If real_prepath_len is None, then
    # locateChild has never been called, so we know not the real length, so we
    # do nothing, which is correct.
    real_prepath_len = None

    def __init__(self, original):
        self.original = original

    def __repr__(self):
        return "<%s @ 0x%x adapting %r>" % (self.__class__.__name__, id(self), self.original)

    def locateChild(self, ctx, segments):
        request = inevow.IRequest(ctx)
        if self.original.isLeaf:
            self.real_prepath_len = len(request.prepath)
            return self, ()
        name = segments[0]
        request.prepath.append(request.postpath.pop(0))
        res = self.original.getChildWithDefault(name, request)
        request.postpath.insert(0, request.prepath.pop())
        if isinstance(res, defer.Deferred):
            return res.addCallback(lambda res: (res, segments[1:]))
        return res, segments[1:]

    def _handle_NOT_DONE_YET(self, data, request):
        if data == server.NOT_DONE_YET:
            return request.deferred
        else:
            return data

    def renderHTTP(self, ctx):
        request = inevow.IRequest(ctx)
        if self.real_prepath_len is not None:
            request.postpath = request.prepath[self.real_prepath_len:]
            del request.prepath[self.real_prepath_len:]
        result = defer.maybeDeferred(self.original.render, request).addCallback(
            self._handle_NOT_DONE_YET, request)
        return result

    def willHandle_notFound(self, request):
        if hasattr(self.original, 'willHandle_notFound'):
            return self.original.willHandle_notFound(request)
        return False

    def renderHTTP_notFound(self, ctx):
        return self.original.renderHTTP_notFound(ctx)


from nevow import rend

NotFound = rend.NotFound
FourOhFour = rend.FourOhFour

classImplements(server.Session, inevow.ISession)
