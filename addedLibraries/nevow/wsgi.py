# TODO:
#  1. make exception renderer work (currently the code is in appserver.py)
# - srid

import warnings
warnings.warn("nevow.wsgi is deprecated.", category=DeprecationWarning)

import sys, socket, math, time
import cgi # for FieldStorage
import types
from urllib import unquote, quote

from zope.interface import implements

from twisted.web.http import stringToDatetime

from nevow import context, flat, inevow, util
from nevow import __version__ as nevowversion

def log(msg):
    print >>sys.stderr, "WSGI: {%s}" % str(msg)

errorMarker = object()

class NevowWSGISite(object):

    def __init__(self, request, resource):
        self.request = request
        self.resource = resource
        self.context = context.SiteContext()

    def remember(self, obj, inter=None):
        self.context.remember(obj, inter)

    def getPageContextForRequestContext(self, ctx):
        """Retrieve a resource from this site for a particular request. The
        resource will be wrapped in a PageContext which keeps track
        of how the resource was located.
        """
        path = inevow.IRemainingSegments(ctx)
        res = inevow.IResource(self.resource)
        pageContext = context.PageContext(tag=res, parent=ctx)
        return self.handleSegment(
            res.locateChild(pageContext, path),
            ctx.tag, path, pageContext)

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
        #if isinstance(newres, defer.Deferred):
        #    return newres.addCallback(
        #        lambda actualRes: self.handleSegment(
        #            (actualRes, newpath), request, path, pageContext))

        newres = inevow.IResource(newres, persist=True)
        if newres is pageContext.tag:
            assert not newpath is path, "URL traversal cycle detected when attempting to locateChild %r from resource %r." % (path, pageContext.tag)
            assert  len(newpath) < len(path), "Infinite loop impending..."

        ## We found a Resource... update the request.prepath and postpath
        for x in xrange(len(path) - len(newpath)):
            request.prepath.append(request.postpath.pop(0))

        ## Create a context object to represent this new resource
        ctx = context.PageContext(tag=newres, parent=pageContext)
        ctx.remember(tuple(request.prepath), inevow.ICurrentSegments)
        ctx.remember(tuple(request.postpath), inevow.IRemainingSegments)

        res = newres
        path = newpath

        if not path:
            return ctx

        return self.handleSegment(
                res.locateChild(ctx, path),
                request, path, ctx)


    
def createWSGIApplication(page, rootURL=None):
    """Given a Page instance, return a WSGI callable.
    `rootURL` - URL to be remembered as root
    """
    page.flattenFactory = flat.iterflatten
    siteCtx = context.SiteContext(tag=None)
    def application(environ, start_response):
        request = WSGIRequest(environ, start_response)
        prefixURL = rootURL
        if prefixURL is None:
            # Try to guess
            proto = request.isSecure() and 'https://' or 'http://'
            server = environ['SERVER_NAME']
            prefixURL = proto + server + environ.get('SCRIPT_NAME', '/')
        request.rememberRootURL(prefixURL)
        site = NevowWSGISite(request, page)
        request.site = site
        result = request.process()
        
        if not request.headersSent:
            request.write('') # send headers now
        if isinstance(result, str):
            yield str(result) # work around wsgiref using StringType 
        elif isinstance(result, util.Deferred):
            ## So we can use the wsgi module if twisted is installed
            ## TODO use render synchronously instead maybe? I'm pretty
            ## sure after the application callable returns, the request
            ## is "closed". Investigate with the latest wsgi spec and
            ## some implementations.
            #raise 'PH' + str(dir(result)) + '{{%s}}' % str(result.result)
            yield result.result
        else:
            for x in result:
                yield x
            
    return application

    
# TODO: convert interface comments
class WSGIRequest(object):
    implements(inevow.IRequest)
    
    """A HTTP request.

    Subclasses should override the process() method to determine how
    the request will be processed.
    
    @ivar method: The HTTP method that was used.
    @ivar uri: The full URI that was requested (includes arguments).
    @ivar path: The path only (arguments not included).
    @ivar args: All of the arguments, including URL and POST arguments.
    @type args: A mapping of strings (the argument names) to lists of values.
    @ivar received_headers: All received headers
    """

    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        self.outgoingHeaders = []
        self.received_headers = {}
        self.lastModified = None
        self.etag = None
        self.method = environ.get('REQUEST_METHOD', 'GET')
        self.args = self._parseQuery(environ.get('QUERY_STRING', ''))
        try:
            self.host = (self.environ['REMOTE_ADDR'], int(self.environ['REMOTE_PORT']))
        except KeyError:
            pass # TODO
        for k,v in environ.items():
            if k.startswith('HTTP_'):
                self.received_headers[k[5:].lower()] = v
        self.setResponseCode("200")
        self.headersSent = False
        self.appRootURL = None
        self.deferred = util.Deferred()

    def process(self):
        """When a form is POSTed,
        we create a cgi.FieldStorage instance using the data posted,
        and set it as the request.fields attribute. This way, we can
        get at information about filenames and mime-types of
        files that were posted."""
        if self.method == 'POST':
            self.fields = cgi.FieldStorage(
                            self.environ['wsgi.input'],
                            self.received_headers, 
                            environ={'REQUEST_METHOD': 'POST'})

        # set various default headers
        self.setHeader('server', nevowversion)
        year, month, day, hh, mm, ss, wd, y, z = time.gmtime(time.time())
        # HTTP date string format
        s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
                weekdayname[wd],
                day, monthname[month], year,
                hh, mm, ss)
        self.setHeader('date', s)
        self.setHeader('content-type', 'text/html; charset=UTF-8')

        # Resource Identification
        self.prepath = []
        self.postpath = map(unquote, self.path[1:].split('/'))
        self.sitepath = []

        requestContext = context.RequestContext(
            parent=self.site.context, tag=self)
        requestContext.remember( (), inevow.ICurrentSegments)
        requestContext.remember(tuple(self.postpath), inevow.IRemainingSegments)

        pageContext = self.site.getPageContextForRequestContext(requestContext)

        return self.gotPageContext(pageContext)

    def gotPageContext(self, pageContext):
        if pageContext is errorMarker:
            return None
        html = pageContext.tag.renderHTTP(pageContext)
        if isinstance(html, util.Deferred):
            # This is a deferred object
            # Let us return it synchronously
            # (wsgi has nothing to do with sync, async)
            # XXX: Is this correct?
            html = html.result
        
        # FIXME: I dunno what to do when a generator comes ..
        #      Perhaps, it may generate non-str? I dunno
        if type(html) is types.GeneratorType:
            html = ''.join(list(html))

        if html is errorMarker:
            ## Error webpage has already been rendered and finish called
            pass
        elif isinstance(html, str):
            return html
        else:
            res = inevow.IResource(html, None)
            if res is not None:
                pageContext = context.PageContext(tag=res, parent=pageContext)
                return self.gotPageContext(pageContext)
            else:              
                # import traceback; traceback.print_stack()
                print >>sys.stderr, "html is not a string: %s on %s" % (str(html), pageContext.tag)
        return html

    def _parseQuery(self, qs):
        d = {}
        items = [s2 for s1 in qs.split("&") for s2 in s1.split(";")]
        for item in items:
            try:
                k, v = item.split("=", 1)
            except ValueError:
                # no strict parsing
                continue
            k = unquote(k.replace("+", " "))
            v = unquote(v.replace("+", " "))
            if k in d:
                d[k].append(v)
            else:
                d[k] = [v]
        return d

    def _getPath(self):
        pth = self.environ.get('PATH_INFO', '')
        if not pth: pth = '/'
        return pth
    path = property(_getPath)
    
    def _getURI(self):
        query = self.environ.get('QUERY_STRING', '')
        if query:
            query = '?' + query
        uri = self.path + query
        log('URL:'+uri)
        return uri
    uri = property(_getURI)
    
    # Methods for received request
    def getHeader(self, key):
        """Get a header that was sent from the network.
        """
        return self.received_headers.get(key.lower())
        
    def getCookie(self, key):
        """Get a cookie that was sent from the network.
        """ 


    def getAllHeaders(self):
        """Return dictionary of all headers the request received."""
        return self.received_headers

    def getRequestHostname(self):
        """Get the hostname that the user passed in to the request.

        This will either use the Host: header (if it is available) or the
        host we are listening on if the header is unavailable.
        """
        return (self.getHeader('host') or
                socket.gethostbyaddr(self.getHost()[1])[0]
                ).split(':')[0]


    def getHost(self):
        """Get my originally requesting transport's host.

        Don't rely on the 'transport' attribute, since Request objects may be
        copied remotely.  For information on this method's return value, see
        twisted.internet.tcp.Port.
        """
        
    def getClientIP(self):
        return self.environ.get('REMOTE_ADDR', None)
        
    def getClient(self):
        pass
    def getUser(self):
        pass
    def getPassword(self):
        pass
    def isSecure(self):
        return self.environ['wsgi.url_scheme'] == 'https'

    def getSession(self, sessionInterface = None):
        pass
    
    def URLPath(self):
        from nevow import url
        return url.URL.fromString(self.appRootURL+self.uri)

    def prePathURL(self):
        if self.isSecure():
            default = 443
        else:
            default = 80
        # TODO: use getHost().port after getHost is implemented
        port = default 
        if port == default:
            hostport = ''
        else:
            hostport = ':%d' % port
        # FIXME: This hack, until url module is fixed to support RootURLs
        #        Or is this the right way to do?
        if self.appRootURL:
            if self.appRootURL[-1] == '/':
                rootURL = self.appRootURL
            else:
                rootURL = self.appRootURL + '/' # yuck!
            return quote('%s%s' % (rootURL, 
                            '/'.join(self.prepath)),
                        '/:')
        return quote('http%s://%s%s/%s' % (
            self.isSecure() and 's' or '',
            self.getRequestHostname(),
            hostport,
            '/'.join(self.prepath)), '/:')

    def rememberRootURL(self, url=None):
        # result = p.renderHTTP(pctx)
        """
        Remember the currently-processed part of the URL for later
        recalling.
        """
        if url is None:
            raise NotImplementedError
        self.appRootURL = url
        
    def getRootURL(self):
        """
        Get a previously-remembered URL.
        """
        return self.appRootURL
        
    # Methods for outgoing request
    def finish(self):
        """We are finished writing data."""

    def write(self, data):
        """
        Write some data as a result of an HTTP request.  The first
        time this is called, it writes out response data.
        """
        if self.headersSent:
            self._write(data)
            return
        headerkeys = [k for k,v in self.outgoingHeaders]
        self._write = self.start_response(
                    self.responseCode, self.outgoingHeaders, None)
        self.headersSent = True
        if data:
            self._write(data)
            
    def addCookie(self, k, v, expires=None, domain=None, path=None, max_age=None, comment=None, secure=None):
        """Set an outgoing HTTP cookie.

        In general, you should consider using sessions instead of cookies, see
        twisted.web.server.Request.getSession and the
        twisted.web.server.Session class for details.
        """

    def setResponseCode(self, code, message=None):
        """Set the HTTP response code.
        """
        self.responseCode = '%s %s' % (code, RESPONSES[int(str(code))])

    def setHeader(self, header, value):
        """Set an outgoing HTTP header.
        """
        self.outgoingHeaders.append((header.lower(), value))

    def redirect(self, url):
        """Utility function that does a redirect.

        The request should have finish() called after this.
        """
        log('REDIRECT to ' + str(url))
        self.setResponseCode(str(302))
        self.setHeader('location', url)

    def setLastModified(self, when):
        """Set the X{Last-Modified} time for the response to this request.

        If I am called more than once, I ignore attempts to set
        Last-Modified earlier, only replacing the Last-Modified time
        if it is to a later value.

        If I am a conditional request, I may modify my response code
        to L{NOT_MODIFIED} if appropriate for the time given.

        @param when: The last time the resource being returned was
            modified, in seconds since the epoch.
        @type when: number
        @return: If I am a X{If-Modified-Since} conditional request and
            the time given is not newer than the condition, I return
            L{http.CACHED<CACHED>} to indicate that you should write no
            body.  Otherwise, I return a false value.
        """
        # time.time() may be a float, but the HTTP-date strings are
        # only good for whole seconds.
        when = long(math.ceil(when))
        if (not self.lastModified) or (self.lastModified < when):
            self.lastModified = when

        modified_since = self.getHeader('if-modified-since')
        if modified_since:
            modified_since = stringToDatetime(modified_since)
            if modified_since >= when:
                self.setResponseCode(NOT_MODIFIED)
                return '' # TODO: return http.CACHED (requires Twisted)
        return None

    def setETag(self, etag):
        """Set an X{entity tag} for the outgoing response.

        That's \"entity tag\" as in the HTTP/1.1 X{ETag} header, \"used
        for comparing two or more entities from the same requested
        resource.\"

        If I am a conditional request, I may modify my response code
        to L{NOT_MODIFIED<twisted.protocols.http.NOT_MODIFIED>} or
        L{PRECONDITION_FAILED<twisted.protocols.http.PRECONDITION_FAILED>},
        if appropriate for the tag given.

        @param etag: The entity tag for the resource being returned.
        @type etag: string
        @return: If I am a X{If-None-Match} conditional request and
            the tag matches one in the request, I return
            L{CACHED<twisted.protocols.http.CACHED>} to indicate that
            you should write no body.  Otherwise, I return a false
            value.
        """
        if etag:
            self.etag = etag

        tags = self.getHeader("if-none-match")
        if tags:
            tags = tags.split()
            if (etag in tags) or ('*' in tags):
                self.setResponseCode(((self.method in ("HEAD", "GET"))
                                      and NOT_MODIFIED)
                                     or PRECONDITION_FAILED)
                return '' # TODO: return http.CACHED (requires Twisted)
        return None

    def setHost(self, host, port, ssl=0):
        """Change the host and port the request thinks it's using.

        This method is useful for working with reverse HTTP proxies (e.g.
        both Squid and Apache's mod_proxy can do this), when the address
        the HTTP client is using is different than the one we're listening on.

        For example, Apache may be listening on https://www.example.com, and then
        forwarding requests to http://localhost:8080, but we don't want HTML produced
        by Twisted to say 'http://localhost:8080', they should say 'https://www.example.com',
        so we do:

        >>> request.setHost('www.example.com', 443, ssl=1)

        This method is experimental.
        """

    # Methods not part of IRequest
    #

    producer = None
    def registerProducer(self, other, _):
        assert self.producer is None
        self.producer = other
        while self.producer is not None:
            self.producer.resumeProducing()

    def unregisterProducer(self):
        self.producer = None

    def finish(self):
        self.deferred.callback('')

# FIXME: copied from twisted.web.http
_CONTINUE = 100
SWITCHING = 101

OK                              = 200
CREATED                         = 201
ACCEPTED                        = 202
NON_AUTHORITATIVE_INFORMATION   = 203
NO_CONTENT                      = 204
RESET_CONTENT                   = 205
PARTIAL_CONTENT                 = 206
MULTI_STATUS                    = 207

MULTIPLE_CHOICE                 = 300
MOVED_PERMANENTLY               = 301
FOUND                           = 302
SEE_OTHER                       = 303
NOT_MODIFIED                    = 304
USE_PROXY                       = 305
TEMPORARY_REDIRECT              = 307

BAD_REQUEST                     = 400
UNAUTHORIZED                    = 401
PAYMENT_REQUIRED                = 402
FORBIDDEN                       = 403
NOT_FOUND                       = 404
NOT_ALLOWED                     = 405
NOT_ACCEPTABLE                  = 406
PROXY_AUTH_REQUIRED             = 407
REQUEST_TIMEOUT                 = 408
CONFLICT                        = 409
GONE                            = 410
LENGTH_REQUIRED                 = 411
PRECONDITION_FAILED             = 412
REQUEST_ENTITY_TOO_LARGE        = 413
REQUEST_URI_TOO_LONG            = 414
UNSUPPORTED_MEDIA_TYPE          = 415
REQUESTED_RANGE_NOT_SATISFIABLE = 416
EXPECTATION_FAILED              = 417

INTERNAL_SERVER_ERROR           = 500
NOT_IMPLEMENTED                 = 501
BAD_GATEWAY                     = 502
SERVICE_UNAVAILABLE             = 503
GATEWAY_TIMEOUT                 = 504
HTTP_VERSION_NOT_SUPPORTED      = 505
INSUFFICIENT_STORAGE_SPACE      = 507
NOT_EXTENDED                    = 510

RESPONSES = {
    # 100
    _CONTINUE: "Continue",
    SWITCHING: "Switching Protocols",

    # 200
    OK: "OK",
    CREATED: "Created",
    ACCEPTED: "Accepted",
    NON_AUTHORITATIVE_INFORMATION: "Non-Authoritative Information",
    NO_CONTENT: "No Content",
    RESET_CONTENT: "Reset Content.",
    PARTIAL_CONTENT: "Partial Content",
    MULTI_STATUS: "Multi-Status",

    # 300
    MULTIPLE_CHOICE: "Multiple Choices",
    MOVED_PERMANENTLY: "Moved Permanently",
    FOUND: "Found",
    SEE_OTHER: "See Other",
    NOT_MODIFIED: "Not Modified",
    USE_PROXY: "Use Proxy",
    # 306 not defined??
    TEMPORARY_REDIRECT: "Temporary Redirect",

    # 400
    BAD_REQUEST: "Bad Request",
    UNAUTHORIZED: "Unauthorized",
    PAYMENT_REQUIRED: "Payment Required",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    NOT_ALLOWED: "Method Not Allowed",
    NOT_ACCEPTABLE: "Not Acceptable",
    PROXY_AUTH_REQUIRED: "Proxy Authentication Required",
    REQUEST_TIMEOUT: "Request Time-out",
    CONFLICT: "Conflict",
    GONE: "Gone",
    LENGTH_REQUIRED: "Length Required",
    PRECONDITION_FAILED: "Precondition Failed",
    REQUEST_ENTITY_TOO_LARGE: "Request Entity Too Large",
    REQUEST_URI_TOO_LONG: "Request-URI Too Long",
    UNSUPPORTED_MEDIA_TYPE: "Unsupported Media Type",
    REQUESTED_RANGE_NOT_SATISFIABLE: "Requested Range not satisfiable",
    EXPECTATION_FAILED: "Expectation Failed",

    # 500
    INTERNAL_SERVER_ERROR: "Internal Server Error",
    NOT_IMPLEMENTED: "Not Implemented",
    BAD_GATEWAY: "Bad Gateway",
    SERVICE_UNAVAILABLE: "Service Unavailable",
    GATEWAY_TIMEOUT: "Gateway Time-out",
    HTTP_VERSION_NOT_SUPPORTED: "HTTP Version not supported",
    INSUFFICIENT_STORAGE_SPACE: "Insufficient Storage Space",
    NOT_EXTENDED: "Not Extended"
}

weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None,
             'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
