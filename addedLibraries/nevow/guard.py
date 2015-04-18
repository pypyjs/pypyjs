# -*- test-case-name: nevow.test.test_guard -*-
# Copyright (c) 2004-2008 Divmod.
# See LICENSE for details.

"""
Resource protection for Nevow. If you wish to use twisted.cred to protect your
Nevow application, you are probably most interested in
L{SessionWrapper}.
"""

__metaclass__ = type

import random
import time
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import StringIO

from zope.interface import implements

# Twisted Imports

from twisted.python import log, components
from twisted.internet import defer
from twisted.cred.error import UnauthorizedLogin
from twisted.cred.credentials import UsernamePassword, Anonymous

try:
    from twisted.web import http
except ImportError:
    from twisted.protocols import http

# Nevow imports
from nevow import inevow, url, stan


def _sessionCookie():
    return md5("%s_%s" % (str(random.random()) , str(time.time()))).hexdigest()


class GuardSession(components.Componentized):
    """A user's session with a system.

    This utility class contains no functionality, but is used to
    represent a session.
    """
    implements(inevow.ISession, inevow.IGuardSession)

    def __init__(self, guard, uid):
        """Initialize a session with a unique ID for that session.
        """
        components.Componentized.__init__(self)
        self.guard = guard
        self.uid = uid
        self.expireCallbacks = []
        self.checkExpiredID = None
        self.setLifetime(60)
        self.portals = {}
        self.touch()

    # New Guard Interfaces

    def getLoggedInRoot(self):
        """Get the most-recently-logged-in avatar.
        """
        # XXX TODO: need to actually sort avatars by login order!
        if len(self.portals) != 1:
            raise RuntimeError("Ambiguous request for current avatar.")
        return self.portals.values()[0][0]

    def resourceForPortal(self, port):
        return self.portals.get(port)

    def setDefaultResource(self, rsrc, logout):
        """

        Change the root-resource available to the user who has already
        authenticated anonymously.  This only works in applications that DO NOT
        use the multiple-simultaneous-portals feature.  If you do not know what
        this means, you may safely ignore it.

        """
        if len(self.portals) != 1:
            raise RuntimeError("Ambiguous request for current avatar.")
        self.setResourceForPortal(
            rsrc,
            self.portals.keys()[0],
            logout)

    def setResourceForPortal(self, rsrc, port, logout):
        """Change the root-resource available to a user authenticating against a given
        portal.

        If a user was already logged in to this session from that portal, first
        log them out.

        @param rsrc: an L{IResource} implementor.
        @param port: a cred Portal instance.
        @param logout: a 0-arg callable to be invoked upon logout.
        """
        self.portalLogout(port)
        self.portals[port] = rsrc, logout
        return rsrc

    def portalLogout(self, port):
        """
        If we have previously acccepted a login for this portal, call its
        logout method and de-associate that portal from this session, catching
        any errors from the logout method.

        Otherwise: do nothing.

        @param port: a cred Portal.
        """
        p = self.portals.get(port)
        if p:
            log.msg('Logout of portal %r' % port)
            r, l = p
            try:
                l()
            except:
                log.err()
            del self.portals[port]

    # timeouts and expiration

    def setLifetime(self, lifetime):
        """Set the approximate lifetime of this session, in seconds.

        This is highly imprecise, but it allows you to set some general
        parameters about when this session will expire.  A callback will be
        scheduled each 'lifetime' seconds, and if I have not been 'touch()'ed
        in half a lifetime, I will be immediately expired.
        """
        self.lifetime = lifetime

    def notifyOnExpire(self, callback):
        """Call this callback when the session expires or logs out.
        """
        self.expireCallbacks.append(callback)

    def expire(self):
        """Expire/logout of the session.
        """
        log.msg("expired session %s" % str(self.uid))
        del self.guard.sessions[self.uid]

        # Logout of all portals
        for portal in self.portals.keys():
            self.portalLogout(portal)

        for c in self.expireCallbacks:
            try:
                c()
            except:
                log.err()
        self.expireCallbacks = []
        if self.checkExpiredID:
            self.checkExpiredID.cancel()
            self.checkExpiredID = None

    def touch(self):
        self.lastModified = time.time()

    def checkExpired(self):
        # Import reactor here to avoid installing default at startup
        from twisted.internet import reactor
        self.checkExpiredID = None
        # If I haven't been touched in 15 minutes:
        if time.time() - self.lastModified > self.lifetime / 2:
            if self.guard.sessions.has_key(self.uid):
                self.expire()
            else:
                log.msg("no session to expire: %s" % str(self.uid))
        else:
            log.msg("session given the will to live for %s more seconds" % self.lifetime)
            self.checkExpiredID = reactor.callLater(self.lifetime,
                                                    self.checkExpired)
    def __getstate__(self):
        d = self.__dict__.copy()
        if d.has_key('checkExpiredID'):
            del d['checkExpiredID']
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self.touch()
        self.checkExpired()


def urlToChild(ctx, *ar, **kw):
    u = url.URL.fromContext(ctx)
    for segment in ar:
        u = u.child(stan.xml(segment))
    if inevow.IRequest(ctx).method == 'POST':
        u = u.clear()
    for k,v in kw.items():
        u = u.replace(k, v)

    return u


SESSION_KEY = '__session_key__'
LOGIN_AVATAR = '__login__'
LOGOUT_AVATAR = '__logout__'


def nomind(*args): return None

class Forbidden(object):
    implements(inevow.IResource)

    def locateChild(self, ctx, segments):
        return self

    def renderHTTP(self, ctx):
        request = inevow.IRequest(ctx)
        request.setResponseCode(http.FORBIDDEN)
        return ("<html><head><title>Forbidden</title></head>"
                "<body><h1>Forbidden</h1>Request was forbidden.</body></html>")

class SessionWrapper:
    """
    SessionWrapper

    The following class attributes can be modified on an instance
    of the class.

    @ivar secureCookies: Whether to use secure (TLS only) cookies or not. If
      C{True} (the default), make cookies secure when session is initiated
      in a secure (TLS) connection.  If C{False}, cookies will not be given
      the secure attribute.

    @ivar persistentCookies: Whether to use persistent (saved to disk)
        cookies or not.  If C{True}, make cookies persistent, so they are
        valid for the length of the C{sessionLifetime} even if the browser
        window is closed.  If C{False} (the default), cookies do not get
        saved to disk, and thus last only as long as the session does.  If
        the browser is closed before the session timeout, both the session
        and the cookie go away.
    """
    implements(inevow.IResource)

    sessionLifetime = 3600
    sessionFactory = GuardSession

    # The interface to cred for when logging into the portal
    credInterface = inevow.IResource

    useCookies = True
    secureCookies = True
    persistentCookies = False

    def __init__(self, portal, cookieKey=None, mindFactory=None, credInterface=None, useCookies=None):
        self.portal = portal
        if cookieKey is None:
            cookieKey = "woven_session_" + _sessionCookie()
        self.cookieKey = cookieKey
        self.sessions = {}
        if mindFactory is None:
            mindFactory = nomind
        self.mindFactory = mindFactory
        if credInterface is not None:
            self.credInterface = credInterface
        if useCookies is not None:
            self.useCookies = useCookies
        # Backwards compatibility; remove asap
        self.resource = self

    def renderHTTP(self, ctx):
        request = inevow.IRequest(ctx)
        d = defer.maybeDeferred(self._delegate, ctx, [])
        def _cb((resource, segments), ctx):
            assert not segments
            res = inevow.IResource(resource)
            return res.renderHTTP(ctx)
        d.addCallback(_cb, ctx)
        return d

    def locateChild(self, ctx, segments):
        request = inevow.IRequest(ctx)
        path = segments[0]
        if self.useCookies:
            cookie = request.getCookie(self.cookieKey)
        else:
            cookie = ''

        if path.startswith(SESSION_KEY):
            key = path[len(SESSION_KEY):]
            if key not in self.sessions:
                return urlToChild(ctx, *segments[1:], **{'__start_session__':1}), ()
            self.sessions[key].setLifetime(self.sessionLifetime)
            if cookie == key:
                # /sessionized-url/${SESSION_KEY}aef9c34aecc3d9148/foo
                #                  ^
                #                  we are this getChild
                # with a matching cookie
                self.sessions[key].sessionJustStarted = True
                return urlToChild(ctx, *segments[1:]), ()
            else:
                # We attempted to negotiate the session but failed (the user
                # probably has cookies disabled): now we're going to return the
                # resource we contain.  In general the getChild shouldn't stop
                # there.
                # /sessionized-url/${SESSION_KEY}aef9c34aecc3d9148/foo
                #                  ^ we are this getChild
                # without a cookie (or with a mismatched cookie)
                return self.checkLogin(ctx, self.sessions[key],
                                       segments[1:],
                                       sessionURL=segments[0])
        else:
            # /sessionized-url/foo
            #                 ^ we are this getChild
            # with or without a session
            return self._delegate(ctx, segments)

    def _delegate(self, ctx, segments):
        """Identify the session by looking at cookies and HTTP auth headers, use that
        session key to identify the wrapped resource, then return a deferred
        which fires a 2-tuple of (resource, segments) to the top-level
        redirection code code which will delegate IResource's renderHTTP or
        locateChild methods to it
        """
        request = inevow.IRequest(ctx)
        cookie = request.getCookie(self.cookieKey)
        # support HTTP auth, no redirections
        userpass = request.getUser(), request.getPassword()
        httpAuthSessionKey = 'HTTP AUTH: %s:%s' % userpass

        for sessionKey in cookie, httpAuthSessionKey:
            if sessionKey in self.sessions:
                session = self.sessions[sessionKey]
                return self.checkLogin(ctx, session, segments)
        # without a session

        if userpass != ('',''):
            # the user is trying to log in with HTTP auth, but they don't have
            # a session.  So, make them one.
            sz = self.sessions[httpAuthSessionKey] = self.sessionFactory(self, httpAuthSessionKey)
            # kick off the expiry timer.
            sz.checkExpired()
            return self.checkLogin(ctx, sz, segments, None, UsernamePassword(*userpass))

        # no, really, without a session
        ## Redirect to the URL with the session key in it, plus the segments of the url
        rd = self.createSession(ctx, segments)
        return rd, ()

    def createSession(self, ctx, segments):
        """
        Create a new session for this request, and redirect back to the path
        given by segments.
        """

        request = inevow.IRequest(ctx)

        newCookie = _sessionCookie()
        if self.useCookies:
            if self.secureCookies and request.isSecure():
                secure = True
            else:
                secure = False
            if self.persistentCookies and self.sessionLifetime:
                expires = http.datetimeToString(time.time() + self.sessionLifetime)
            else:
                expires = None
            request.addCookie(self.cookieKey, newCookie,
                              path="/%s" % '/'.join(request.prepath),
                              secure=secure, expires=expires,
                              domain=self.cookieDomainForRequest(request))
        sz = self.sessions[newCookie] = self.sessionFactory(self, newCookie)
        sz.args = request.args
        sz.fields = request.fields
        sz.method = request.method
        sz.received_headers = request.received_headers
        sz.checkExpired()
        return urlToChild(ctx, SESSION_KEY+newCookie, *segments)

    def checkLogin(self, ctx, session, segments, sessionURL=None, httpAuthCredentials=None):
        """
        Associate the given request with the given session and:

            - log the user in to our portal, if they are accessing a login URL

            - log the user out from our portal (calling their logout callback),
              if they are logged in and accessing a logout URL

            - Move the request parameters saved on the session, if there are
              any, onto the request if a session just started or a login
              just succeeded.

        @return:

            - if the user is already logged in: a 2-tuple of requestObject,
              C{segments} (i.e. the segments parameter)

            - if the user is not logged in and not logging in, call login() to
              initialize an anonymous session, and return a 2-tuple of
              (rootResource, segments-parameter) from that anonymous session.
              This counts as logging in for the purpose of future calls to
              checkLogin.

            - if the user is accessing a login URL: a 2-tuple of the logged in
              resource object root and the remainder of the segments (i.e. the
              URL minus __login__) to be passed to that resource.

        """
        request = inevow.IRequest(ctx)
        session.touch()
        request.session = session
        root = url.URL.fromContext(request)
        if sessionURL is not None:
            root = root.child(sessionURL)
        request.rememberRootURL(str(root))

        spoof = False
        if getattr(session, 'sessionJustStarted', False):
            del session.sessionJustStarted
            spoof = True
        if getattr(session, 'justLoggedIn', False):
            del session.justLoggedIn
            spoof = True
        if spoof and hasattr(session, 'args'):
            request.args = session.args
            request.fields = session.fields
            request.content = StringIO.StringIO()
            request.content.close()
            request.method = session.method
            request.received_headers = session.received_headers

            del session.args, session.fields, session.method, session.received_headers


        if segments and segments[0] in (LOGIN_AVATAR, LOGOUT_AVATAR):
            authCommand = segments[0]
        else:
            authCommand = None

        if httpAuthCredentials:
            # This is the FIRST TIME we have hit an HTTP auth session with our
            # credentials.  We are going to perform login.
            assert not authCommand, (
                "HTTP auth support isn't that robust.  "
                "Come up with something to do that makes sense here.")
            return self.login(request, session, httpAuthCredentials, segments).addErrback(
                self.authRequiredError, session
                )

        if authCommand == LOGIN_AVATAR:
            subSegments = segments[1:]
            def unmangleURL((res,segs)):
                # Tell the session that we just logged in so that it will
                # remember form values for us.
                session.justLoggedIn = True
                # Then, generate a redirect back to where we're supposed to be
                # by looking at the root of the site and calculating the path
                # down from there using the segments we were passed.
                u = url.URL.fromString(request.getRootURL())
                for seg in subSegments:
                    u = u.child(seg)
                return u, ()
            return self.login(request, session, self.getCredentials(request), subSegments).addCallback(
                unmangleURL).addErrback(
                self.incorrectLoginError, ctx, subSegments, "Incorrect login."
                )
        elif authCommand == LOGOUT_AVATAR:
            self.explicitLogout(session)
            return urlToChild(ctx, *segments[1:]), ()
        else:
            r = session.resourceForPortal(self.portal)
            if r:
                ## Delegate our getChild to the resource our portal says is the right one.
                return r[0], segments
            else:
                # XXX I don't think that the errback here will work at all,
                # because the redirect loop would be infinite.  Perhaps this
                # should be closer to the HTTP auth path?
                return self.login(request, session, Anonymous(), segments).addErrback(
                    self.incorrectLoginError, ctx, segments, 'Anonymous access not allowed.')

    def explicitLogout(self, session):
        """
        Hook to be overridden if you care about user-requested logout.

        Note: there is no return value from this method; it is purely a way to
        provide customized behavior that distinguishes between session-expiry
        logout, which is what 99% of code cares about, and explicit user
        logout, which you may need to be notified of if (for example) your
        application sets other HTTP cookies which refer to server-side state,
        and you want to expire that state in a manual logout but not with an
        automated logout.  (c.f. Quotient's persistent sessions.)

        If you want the user to see a customized logout page, just generate a
        logout link that looks like::

            http://your-site.example.com/__logout__/my/custom/logout/stuff

        and the user will see::

            http://your-site.example.com/my/custom/logout/stuff

        as their first URL after becoming anonymous again.
        """
        session.portalLogout(self.portal)

    def getCredentials(self, request):
        username = request.args.get('username', [''])[0]
        password = request.args.get('password', [''])[0]
        return UsernamePassword(username, password)

    def login(self, request, session, credentials, segments):
        """

        - Calls login() on our portal.

        - creates a mind from my mindFactory, with the request and credentials

        - Associates the mind with the given session.

        - Associates the resource returned from my portal's login() with my
          portal in the given session.

        @return: a Deferred which fires a 2-tuple of the resource returned from
        my portal's login() and the passed list of segments upon successful
        login.

        """
        mind = self.mindFactory(request, credentials)
        session.mind = mind
        return self.portal.login(credentials, mind, self.credInterface).addCallback(
            self._cbLoginSuccess, session, segments
        )

    def _cbLoginSuccess(self, (iface, res, logout), session, segments):
        session.setResourceForPortal(res, self.portal, logout)
        return res, segments

    def incorrectLoginError(self, error, ctx, segments, loginFailure):
        """ Used as an errback upon failed login, returns a 2-tuple of a failure URL
        with the query argument 'login-failure' set to the parameter
        loginFailure, and an empty list of segments, to redirect to that URL.
        The basis for this error URL, i.e. the part before the query string, is
        taken either from the 'referer' header from the given request if one
        exists, or a computed URL that points at the same page that the user is
        currently looking at to attempt login.  Any existing query string will
        be stripped.
        """
        request = inevow.IRequest(ctx)
        error.trap(UnauthorizedLogin)
        referer = request.getHeader("referer")
        if referer is not None:
            u = url.URL.fromString(referer)
        else:
            u = urlToChild(ctx, *segments)

        u = u.clear()
        u = u.add('login-failure', loginFailure)
        return u, ()

    def authRequiredError(self, error, session):
        session.expire()
        error.trap(UnauthorizedLogin)
        return Forbidden(), ()


    def cookieDomainForRequest(self, request):
        """
        Specify the domain restriction on the session cookie.

        @param request: The request object in response to which a cookie is
            being set.

        @return: C{None} or a C{str} giving the domain restriction to set on
            the cookie.
        """
        return None
