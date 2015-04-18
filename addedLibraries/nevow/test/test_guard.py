# Copyright (c) 2004-2008 Divmod.
# See LICENSE for details.

"""
Tests for L{nevow.guard}.
"""

import gc

from zope.interface import implements

from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse, AllowAnonymousAccess, ANONYMOUS
from twisted.cred.portal import Portal, IRealm
from twisted.cred.credentials import IUsernamePassword, IAnonymous
from twisted.internet import address
from twisted.trial.unittest import TestCase

from nevow import rend
from nevow import inevow
from nevow import guard
from nevow import context
from nevow import appserver


class FakeHTTPChannel:
    # TODO: this should be an interface in twisted.protocols.http... lots of
    # things want to fake out HTTP
    def __init__(self):
        self.transport = self
        self.factory = self
        self.received_cookies = {}

    # 'factory' attribute needs this
    def log(self, req):
        pass

    # 'channel' of request needs this
    def requestDone(self, req):
        self.req = req

    # 'transport' attribute needs this
    def getPeer(self):
        return address.IPv4Address("TCP", "fake", 12345)
    def getHost(self):
        return address.IPv4Address("TCP", "fake", 80)

    def write(self, data):
        # print data
        pass
    def writeSequence(self, datas):
        for data in datas:
            self.write(data)

    # Utility for testing.

    def makeFakeRequest(self, path, username='',password='',
                        requestClass=None):
        if requestClass is None:
            requestClass = FakeHTTPRequest
        req = requestClass(self, queued=0)
        req.user = username
        req.password = password
        req.received_cookies.update(self.received_cookies)
        req.requestReceived("GET", path, "HTTP/1.0")
        return req


class FakeHTTPRequest(appserver.NevowRequest):
    def __init__(self, *args, **kw):
        appserver.NevowRequest.__init__(self, *args, **kw)
        self._pchn = self.channel
        self._cookieCache = {}
        from cStringIO import StringIO
        self.content = StringIO()
        self.received_headers['host'] = 'fake.com'
        self.written = StringIO()

    def followRedirect(self):
        L = self.headers['location']
        if L.startswith('http://'):
            L = L[len("http://"):]
            urlist = L.split('/')
            urlist[0] = ''
            nexturi = '/'.join(urlist)
        else:
            nexturi = L
        return self._pchn.makeFakeRequest(nexturi,
                                          requestClass=self.__class__)

    def followAllRedirects(self):
        R = self
        MAX_REDIRECTS = 5
        I = 1
        while R.headers.has_key('location'):
            assert I < MAX_REDIRECTS, "Too many redirects (to %s)" % R.headers['location']
            R = R.followRedirect()
            I += 1
        return R

    def write(self, data):
        self.written.write(data)
        appserver.NevowRequest.write(self, data)

    def addCookie(self, k, v, *args,**kw):
        appserver.NevowRequest.addCookie(self,k,v,*args,**kw)
        assert not self._cookieCache.has_key(k), "Should not be setting duplicate cookies!"
        self._cookieCache[k] = (v, args, kw)
        self.channel.received_cookies[k] = v

    def processingFailed(self, fail):
        raise fail

class FakeHTTPRequest_noCookies(FakeHTTPRequest):
    def addCookie(self, k, v, *args,**kw):
        pass

class FakeHTTPRequest_forceSSL(FakeHTTPRequest):
    _forceSSL = True


class SillyPage(rend.Page):
    def locateChild(self, context, segments):
        return self.__class__(), segments[1:]


class InspectfulPage(rend.Page):
    """
    IResource avatar which records important state from the request
    with which it is rendered.

    @ivar renders: A C{list} to which fields of the request will be appended
        when this page is rendered.
    """
    def __init__(self, renders):
        self.renders = renders
        rend.Page.__init__(self)


    def child_(self, context):
        """
        Give back this resource.  This lets this page work as the root
        resource.
        """
        return self


    def renderHTTP(self, context):
        request = inevow.IRequest(context)
        try:
            content = request.content.read()
        except ValueError:
            content = None
        self.renders.append((
                request.args,
                request.fields,
                content,
                request.method,
                request.received_headers))
        return ''


class SillyAvatar(SillyPage):
    def renderHTTP(self, context):
        return 'Yes'


class SillyAnonymous(SillyPage):
    def renderHTTP(self, ctx):
        return 'No'


class SillyRealm:
    implements(IRealm)

    def __init__(self, anonymousAvatarFactory=SillyAnonymous,
                 authenticatedAvatarFactory=SillyAvatar):
        self.anonymousAvatarFactory = anonymousAvatarFactory
        self.authenticatedAvatarFactory = authenticatedAvatarFactory


    def requestAvatar(self, avatarId, mind, *interfaces):
        if avatarId == ANONYMOUS:
            avatar = self.anonymousAvatarFactory()
        else:
            avatar = self.authenticatedAvatarFactory()
        return inevow.IResource, avatar, lambda: None



class GuardTestSuper(TestCase):
    """
    @ivar wrapperFactory: A callable which will be invoked with a portal and
        which should return a session wrapper resource.
    """
    wrapperFactory = guard.SessionWrapper

    sessions = {}

    def tearDown(self):
        for sz in self.sessions.values():
            sz.expire()

    def createPortal(self, realmFactory=None):
        if realmFactory is None:
            realmFactory = SillyRealm
        r = realmFactory()
        p = Portal(r)
        p.registerChecker(AllowAnonymousAccess(), IAnonymous)
        return p

    def createSessionWrapper(self, portal):
        swrap = self.wrapperFactory(portal)
        self.sessions = swrap.sessions
        return swrap

    def createChannel(self, resource):
        s = appserver.NevowSite(resource)
        c = FakeHTTPChannel()
        c.site = s
        return c

def getGuard(channel):
    resource = channel.site.resource
    while isinstance(resource, ParentPage):
        assert len(resource.children) == 1
        resource = resource.children.values()[0]
    return resource


class GetLoggedInAvatar(rend.Page):
    def child_(self, ctx):
        return self
    def renderHTTP(self, ctx):
        session = inevow.ISession(ctx)
        assert isinstance(session, guard.GuardSession)
        r = session.getLoggedInRoot()
        assert r is self
        return r.__class__.__name__

class GetLoggedInAnonymous(rend.Page):
    def child_(self, ctx): return self
    def renderHTTP(self, ctx):
        raise RuntimeError, "We weren't supposed to get here."

class GetLoggedInRealm:
    implements(IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        if avatarId == ANONYMOUS:
            return inevow.IResource, GetLoggedInAnonymous(), lambda: None
        else:
            return inevow.IResource, GetLoggedInAvatar(), lambda: None


class GuardTestFuncs:
    def createGuard(self, portal):
        if not self.guardPath:
            root = self.createSessionWrapper(portal)
        else:
            root = ParentPage('root')
            cur = root
            for segment in self.guardPath[:-1]:
                new = ParentPage(segment)
                cur.putChild(segment, new)
                cur = new
            cur.putChild(self.guardPath[-1],
                         self.createSessionWrapper(portal))
        chan = self.createChannel(root)
        return chan

    def getGuardPath(self):
        """
        Return a path to the guard. An empty string if guard is the root,
        otherwise guaranteed to start with a slash and end with a non-slash.
        """
        if not self.guardPath:
            return ''
        else:
            return '/' + '/'.join(self.guardPath)

    def test_httpAuthInit(self):
        """
        A request for a guarded URL which includes HTTP AUTH headers giving
        valid credentials is responded to with the resource given back by the
        realm for the avatar identified by those credentials and a single
        session is created for that avatar.
        """
        p = self.createPortal()
        chan = self.createGuard(p)
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'), IUsernamePassword)

        # Make the request three times.  The same resource should come back
        # each time, and there should only ever be one session.
        for x in range(3):
            req = chan.makeFakeRequest('%s/' % self.getGuardPath(), "test", "test")
            self.assertEquals(req.written.getvalue(), "Yes")
            self.assertEquals(len(self.sessions), 1)


    def test_sessionInit(self):
        """
        Without including credentials or a session cookie, a request for a
        guarded URL is responded to with a cookie and a redirect to an URL
        which includes a session key.  When requested with the cookie, the
        redirect target is responded to with a redirect back to the original
        URL.  When requested with the cookie, the original URL is responded to
        with the resource for the anonymous avatar.
        """
        p = self.createPortal()
        chan = self.createGuard(p)

        # The first thing that happens when we attempt to browse with no session
        # is a cookie being set and a redirect being issued to the session url
        req = chan.makeFakeRequest('%s/xxx/yyy/' % self.getGuardPath())
        self.assertEquals( len(req._cookieCache.values()), 1, "Bad number of cookies in response.")
        # The redirect is set immediately and should have a path segment at the beginning matching our cookie
        self.failUnless(req.headers.has_key('location'))
        cookie = req._cookieCache.values()[0][0]

        # The URL should have the cookie segment in it and the correct path segments at the end
        self.assertEquals(req.headers['location'],
            'http://fake.com%s/%s/xxx/yyy/' % (self.getGuardPath(), guard.SESSION_KEY+cookie, ))

        # Now, let's follow the redirect
        req = req.followRedirect()
        # Our session should now be set up and we will be redirected to our final destination
        self.assertEquals(req.headers['location'].split('?')[0],
            'http://fake.com%s/xxx/yyy/' % self.getGuardPath())

        # Let's follow the redirect to the final page
        req = req.followRedirect()
        self.failIf(req.headers.has_key('location'))

        # We should have the final resource, which is an anonymous resource
        self.assertEquals(req.written.getvalue(), "No")


    def test_sessionInit_noCookies(self):
        """
        Without including credentials or a session cookie, a request for a
        guarded URL is responded to with a cookie and a redirect to an URL
        which includes a session key.  When requested without the cookie, the
        redirect target is responded to with a redirect back to the original
        URL modified to include a session token.  When requested, again without
        the cookie, the new redirect target is responded to with the resource
        for the anonymous avatar.
        """
        p = self.createPortal()
        chan = self.createGuard(p)

        # The first thing that happens when we attempt to browse with no session
        # is a cookie being set and a redirect being issued to the session url
        req = chan.makeFakeRequest('%s/xxx/yyy/' % self.getGuardPath(), requestClass=FakeHTTPRequest_noCookies)
        # The redirect is set immediately and should have a path segment at the beginning matching our session id
        self.failUnless(req.headers.has_key('location'))

        # The URL should have the session id segment in it and the correct path segments at the end
        location = req.headers['location']
        prefix = 'http://fake.com%s/%s' % (self.getGuardPath(), guard.SESSION_KEY)
        suffix = '/xxx/yyy/'
        self.failUnless(location.startswith(prefix))
        self.failUnless(location.endswith(suffix))
        for c in location[len(prefix):-len(suffix)]:
            self.failUnless(c in '0123456789abcdef')

        # Now, let's follow the redirect
        req = req.followRedirect()
        self.failIf(req.headers.has_key('location'))

        # We should have the final resource, which is an anonymous resource
        self.assertEquals(req.written.getvalue(), "No")


    def testUsernamePassword(self):
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'), IUsernamePassword)
        chan = self.createGuard(p)

        # Check the anonymous page
        req = chan.makeFakeRequest('%s/' % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), "No")

        # Check the logged in page
        req = chan.makeFakeRequest('%s/__login__/?username=test&password=test' % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), "Yes")

        # Log out
        chan.makeFakeRequest("%s/__logout__" % self.getGuardPath()).followRedirect()

        # Get the anonymous page again
        k = chan.makeFakeRequest("%s/" % self.getGuardPath())
        self.assertEquals(k.written.getvalue(), "No")


    def testLoginWithNoSession(self):
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'), IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/__login__/?username=test&password=test' % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), "Yes")


    def test_sessionNegotiationSavesRequestParameters(self):
        """
        After a session has been negotiated, the GET arguments, POST arguments,
        body, method, and headers from the request which initiated session
        negotiation are set on the request which will be responded to with the
        guarded resource.
        """
        renders = []
        portal = self.createPortal(
            lambda: SillyRealm(
                anonymousAvatarFactory=lambda: InspectfulPage(renders)))
        channel = self.createGuard(portal)

        request = channel.makeFakeRequest(
            '%s/?foo=1&bar=2' % self.getGuardPath()).followAllRedirects()
        self.assertEquals(request.written.getvalue(), '')
        self.assertEqual(
            renders, [({'foo': ['1'], 'bar': ['2']},
                       None,
                       None,
                       'GET',
                       {'host': 'fake.com'})])


    def test_loginRestoresRequestParameters(self):
        """
        After login has succeeded, the GET arguments, POST arguments, body,
        method, and headers from the request which triggered the login are set
        on the request which will be responded to with the guarded resource.
        """
        renders = []
        portal = self.createPortal(
            lambda: SillyRealm(
                authenticatedAvatarFactory=lambda: InspectfulPage(renders)))
        portal.registerChecker(
            InMemoryUsernamePasswordDatabaseDontUse(test='test'),
            IUsernamePassword)
        channel = self.createGuard(portal)

        # Negotiate a session.
        request = channel.makeFakeRequest(self.getGuardPath())
        request = request.followAllRedirects()

        # Pretend to be a resource before login which requires login and saves
        # request state.
        request.session.args = {'foo': ['1'], 'bar': ['2']}
        request.session.fields = None
        request.session.method = 'GET'
        request.session.content = None
        request.session.received_headers = {'host': 'fake.com',
                                            'extra': 'bar'}

        # Perform the login.
        request = channel.makeFakeRequest(
            self.getGuardPath() + '/__login__?username=test&password=test')
        request = request.followAllRedirects()

        self.assertEquals(request.written.getvalue(), '')
        self.assertEqual(
            renders, [({'foo': ['1'], 'bar': ['2']},
                       None,
                       None,
                       'GET',
                       {'host': 'fake.com', 'extra': 'bar'})])


    def test_oldRequestParametersIgnored(self):
        """
        The request parameters from the initial session negotiation request are
        I{not} set on the login request.
        """
        renders = []
        portal = self.createPortal(
            lambda: SillyRealm(
                authenticatedAvatarFactory=lambda: InspectfulPage(renders)))
        portal.registerChecker(
            InMemoryUsernamePasswordDatabaseDontUse(test='test'),
            IUsernamePassword)
        channel = self.createGuard(portal)

        # Negotiate a session using a request with some parameters.
        request = channel.makeFakeRequest(
            self.getGuardPath() + "?foo=bar&bar=baz")
        request = request.followAllRedirects()

        # Perform the login.
        request = channel.makeFakeRequest(
            self.getGuardPath() + '/__login__?username=test&password=test')
        request = request.followAllRedirects()

        self.assertEquals(request.written.getvalue(), '')
        self.assertEqual(
            renders, [({'username': ['test'], 'password': ['test']},
                       None,
                       '',
                       'GET',
                       {'host': 'fake.com'})])


    def testNoSlash(self):
        """URL-based sessions do not fail even if there is no slash after the session key."""
        p = self.createPortal()
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/' % self.getGuardPath(), requestClass=FakeHTTPRequest_noCookies).followAllRedirects()
        # We should have the final resource, which is an anonymous resource
        self.assertEquals(req.written.getvalue(), "No")

        # now try requesting just the guard path
        self.failUnless(req.path.startswith('%s/%s' % (self.getGuardPath(), guard.SESSION_KEY)))
        self.failUnless(req.path.endswith('/'))
        req = chan.makeFakeRequest(req.path[:-1], requestClass=FakeHTTPRequest_noCookies).followAllRedirects()

        # it should work just as well as with the slash
        # (not actually the same page, but SillyPage always says the same thing here)
        self.assertEquals(req.written.getvalue(), "No")

    def testTrailingSlashMatters_noCookies(self):
        class TrailingSlashPage(rend.Page):
            def locateChild(self, context, segments):
                return self.__class__('%s/%s' % (self.original, segments[0])), segments[1:]

        class TrailingSlashAvatar(TrailingSlashPage):
            def renderHTTP(self, context):
                return 'Authenticated %s' % self.original

        class TrailingSlashAnonymous(TrailingSlashPage):
            def renderHTTP(self, ctx):
                return 'Anonymous %s' % self.original

        class TrailingSlashRealm:
            implements(IRealm)

            def __init__(self, path):
                self.path = path

            def requestAvatar(self, avatarId, mind, *interfaces):
                if avatarId == ANONYMOUS:
                    return inevow.IResource, TrailingSlashAnonymous(self.path), lambda: None
                else:
                    return inevow.IResource, TrailingSlashAvatar(self.path), lambda: None

        p = self.createPortal(realmFactory=lambda : TrailingSlashRealm(self.getGuardPath()))
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/' % self.getGuardPath(), requestClass=FakeHTTPRequest_noCookies).followAllRedirects()
        # We should have the final resource, which is an anonymous resource
        self.assertEquals(req.written.getvalue(), "Anonymous %s/" % self.getGuardPath())

        # now try requesting just the guard path
        self.failUnless(req.path.startswith('%s/%s' % (self.getGuardPath(), guard.SESSION_KEY)))
        self.failUnless(req.path.endswith('/'))
        req = chan.makeFakeRequest(req.path[:-1], requestClass=FakeHTTPRequest_noCookies).followAllRedirects()

        # it should no longer have the trailing slash
        self.assertEquals(req.written.getvalue(), "Anonymous %s" % self.getGuardPath())

    def testTrailingSlashMatters_withCookies(self):
        # omitting the trailing slash when not using session keys can
        # only be done when the guard is not the root resource
        if not self.guardPath:
            return
        
        class TrailingSlashPage(rend.Page):
            def locateChild(self, context, segments):
                return self.__class__('%s/%s' % (self.original, segments[0])), segments[1:]

        class TrailingSlashAvatar(TrailingSlashPage):
            def renderHTTP(self, context):
                return 'Authenticated %s' % self.original

        class TrailingSlashAnonymous(TrailingSlashPage):
            def renderHTTP(self, ctx):
                return 'Anonymous %s' % self.original

        class TrailingSlashRealm:
            implements(IRealm)

            def __init__(self, path):
                self.path = path

            def requestAvatar(self, avatarId, mind, *interfaces):
                if avatarId == ANONYMOUS:
                    return inevow.IResource, TrailingSlashAnonymous(self.path), lambda: None
                else:
                    return inevow.IResource, TrailingSlashAvatar(self.path), lambda: None

        p = self.createPortal(realmFactory=lambda : TrailingSlashRealm(self.getGuardPath()))
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/' % self.getGuardPath()).followAllRedirects()
        # We should have the final resource, which is an anonymous resource
        self.assertEquals(req.written.getvalue(), "Anonymous %s/" % self.getGuardPath())

        req = chan.makeFakeRequest('%s' % self.getGuardPath()).followAllRedirects()
        # We should have the final resource, which is an anonymous resource
        self.assertEquals(req.written.getvalue(), "Anonymous %s" % self.getGuardPath())

    def testPlainTextCookie(self):
        """Cookies from non-SSL sites have no secure attribute."""
        p = self.createPortal()
        chan = self.createGuard(p)
        req = chan.makeFakeRequest('%s/xxx/yyy/' % self.getGuardPath())
        self.assertEquals( len(req._cookieCache.values()), 1, "Bad number of cookies in response.")
        cookie, a, kw = req._cookieCache.values()[0]
        secure = kw.get('secure', None)
        self.failIf(secure)

    def testPlainTextCookie_evenWithSecureCookies(self):
        """Cookies from non-SSL sites have no secure attribute, even if secureCookie is true."""
        p = self.createPortal()
        chan = self.createGuard(p)
        gu = getGuard(chan)
        gu.secureCookies = False
        req = chan.makeFakeRequest('%s/xxx/yyy/' % self.getGuardPath())
        self.assertEquals( len(req._cookieCache.values()), 1, "Bad number of cookies in response.")
        cookie, a, kw = req._cookieCache.values()[0]
        secure = kw.get('secure', None)
        self.failIf(secure)

    def testSecureCookie_secureCookies(self):
        """Cookies from SSL sites have secure=True."""
        p = self.createPortal()
        chan = self.createGuard(p)
        req = chan.makeFakeRequest('%s/xxx/yyy/' % self.getGuardPath(),
                                   requestClass=FakeHTTPRequest_forceSSL)
        self.assertEquals( len(req._cookieCache.values()), 1, "Bad number of cookies in response.")
        cookie, a, kw = req._cookieCache.values()[0]
        secure = kw.get('secure', None)
        self.failUnless(secure)

    def testSecureCookie_noSecureCookies(self):
        """Cookies from SSL sites do not have secure=True if secureCookies is false."""
        p = self.createPortal()
        chan = self.createGuard(p)
        gu = getGuard(chan)
        gu.secureCookies = False
        req = chan.makeFakeRequest('%s/xxx/yyy/' % self.getGuardPath(),
                                   requestClass=FakeHTTPRequest_forceSSL)
        self.assertEquals( len(req._cookieCache.values()), 1, "Bad number of cookies in response.")
        cookie, a, kw = req._cookieCache.values()[0]
        secure = kw.get('secure', None)
        self.failIf(secure)

    def testPersistentCookie_persistentCookies(self):
        """Cookies from sites are saved to disk because SessionWrapper.persistentCookies=True."""
        p = self.createPortal()
        chan = self.createGuard(p)
        gu = getGuard(chan)
        gu.persistentCookies = True
        req = chan.makeFakeRequest('%s/xxx/yyy/' % self.getGuardPath(),
                                   requestClass=FakeHTTPRequest)
        self.assertEquals( len(req._cookieCache.values()), 1, "Bad number of cookies in response.")
        cookie, a, kw = req._cookieCache.values()[0]
        expires = kw.get('expires', None)
        self.failIfIdentical(expires, None)

    def testPersistentCookie_noPersistentCookies(self):
        """Cookies from sites are not saved to disk because SessionWrapper.persistentCookies=False."""
        p = self.createPortal()
        chan = self.createGuard(p)
        req = chan.makeFakeRequest('%s/xxx/yyy/' % self.getGuardPath(),
                                   requestClass=FakeHTTPRequest)
        self.assertEquals( len(req._cookieCache.values()), 1, "Bad number of cookies in response.")
        cookie, a, kw = req._cookieCache.values()[0]
        expires = kw.get('expires', None)
        self.failUnlessIdentical(expires, None)



    def testCookiePath(self):
        """Cookies get the correct path setting sites have no secure attribute."""
        p = self.createPortal()
        chan = self.createGuard(p)
        req = chan.makeFakeRequest('%s/xxx/yyy/' % self.getGuardPath())
        self.assertEquals( len(req._cookieCache.values()), 1, "Bad number of cookies in response.")
        cookie, a, kw = req._cookieCache.values()[0]
        path = kw.get('path', None)
        wanted = self.getGuardPath()
        if wanted == '':
            wanted = '/'
        self.failUnlessEqual(path, wanted)


    def test_defaultCookieDomain(self):
        """
        No domain restriction is set on a cookie by default.
        """
        portal = self.createPortal()
        channel = self.createGuard(portal)
        request = channel.makeFakeRequest('%s/abc' % (self.getGuardPath(),))
        cookie, args, kwargs = request._cookieCache.values()[0]
        self.assertEqual(kwargs['domain'], None)


    def test_specifiedCookieDomain(self):
        """
        The domain restriction defined by
        L{SessionWrapper.cookieDomainForRequest} is set on the cookie.
        """
        portal = self.createPortal()

        requests = []

        class SpecialSessionWrapper(guard.SessionWrapper):
            def cookieDomainForRequest(self, request):
                requests.append(request)
                return 'example.com'

        self.wrapperFactory = SpecialSessionWrapper
        channel = self.createGuard(portal)

        request = channel.makeFakeRequest('%s/abc' % (self.getGuardPath(),))
        cookie, args, kwargs = request._cookieCache.values()[0]
        self.assertEqual(kwargs['domain'], 'example.com')
        self.assertEqual(requests, [request])


    def testLoginExtraPath(self):
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'), IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/__login__/sub/path?username=test&password=test' % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), "Yes")
        self.assertEquals(req.path, '%s/sub/path' % self.getGuardPath())

    def testLoginExtraPath_withSlash(self):
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'), IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/__login__/sub/path/?username=test&password=test' % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), "Yes")
        self.assertEquals(req.path, '%s/sub/path/' % self.getGuardPath())

    def testLogoutExtraPath(self):
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'), IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/__login__?username=test&password=test' % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), "Yes")

        # Log out
        req2 = chan.makeFakeRequest("%s/__logout__/sub/path" % self.getGuardPath()).followRedirect()
        self.assertEquals(req2.written.getvalue(), "No")
        self.assertEquals(req2.path, '%s/sub/path' % self.getGuardPath())

    def testLogoutExtraPath_withSlash(self):
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'), IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/__login__?username=test&password=test' % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), "Yes")

        # Log out
        req2 = chan.makeFakeRequest("%s/__logout__/sub/path/" % self.getGuardPath()).followRedirect()
        self.assertEquals(req2.written.getvalue(), "No")
        self.assertEquals(req2.path, '%s/sub/path/' % self.getGuardPath())

    def testGetLoggedInRoot_getLogin(self):
        p = self.createPortal(realmFactory=GetLoggedInRealm)
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'), IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/__login__?username=test&password=test' % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), "GetLoggedInAvatar")

    def testGetLoggedInRoot_httpAuthLogin(self):

        p = self.createPortal(realmFactory=GetLoggedInRealm)
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'), IUsernamePassword)
        chan = self.createGuard(p)
        for x in range(4):
            req = chan.makeFakeRequest('%s/' % self.getGuardPath(), "test", "test")
            self.assertEquals(req.written.getvalue(), "GetLoggedInAvatar")
        self.assertEquals(len(self.sessions),1)

    def testErrorPage_httpAuth(self):
        """Failed HTTP Auth results in a 403 error."""
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'),
                          IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s' % self.getGuardPath(),
                                   "test", "invalid-password")
        self.assertEquals(req.headers.get('location', None), None)
        self.assertEquals(req.code, 403)
        self.assertEquals(req.written.getvalue(),
                          '<html><head><title>Forbidden</title></head>'
                          +'<body><h1>Forbidden</h1>Request was forbidden.'
                          +'</body></html>')
        self.assertEquals(req.path, self.getGuardPath())

    def testErrorPage_httpAuth_deep(self):
        """Failed HTTP Auth results in a 403 error."""
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'),
                          IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest('%s/quux/thud' % self.getGuardPath(),
                                   "test", "invalid-password")
        self.assertEquals(req.headers.get('location', None), None)
        self.assertEquals(req.code, 403)
        self.assertEquals(req.written.getvalue(),
                          '<html><head><title>Forbidden</title></head>'
                          +'<body><h1>Forbidden</h1>Request was forbidden.'
                          +'</body></html>')
        self.assertEquals(req.path, '%s/quux/thud' % self.getGuardPath())

    def testErrorPage_getLogin(self):
        """Failed normal login results in anonymous view of the same page."""
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'),
                          IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest(
            '%s/__login__?username=test&password=invalid-password'
            % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), 'No')
        wanted = self.getGuardPath()
        if wanted == '':
            wanted = '/'
        self.assertEquals(req.path, wanted)

    def testErrorPage_getLogin_deep(self):
        """Failed normal login results in anonymous view of the same page."""
        p = self.createPortal()
        p.registerChecker(InMemoryUsernamePasswordDatabaseDontUse(test='test'),
                          IUsernamePassword)
        chan = self.createGuard(p)

        req = chan.makeFakeRequest(
            '%s/__login__/quux/thud?username=test&password=invalid-password'
            % self.getGuardPath()).followAllRedirects()
        self.assertEquals(req.written.getvalue(), 'No')
        self.assertEquals(req.path, '%s/quux/thud' % self.getGuardPath())


class ParentPage(rend.Page):
    addSlash = True
    def renderHTTP(self, context):
        request = context.locate(inevow.IRequest)
        return 'This is %s at %s' % (self.original, request.URLPath())

class GuardTest(GuardTestSuper, GuardTestFuncs):
    guardPath = []

class GuardTest_NotAtRoot_oneLevel(GuardTestSuper, GuardTestFuncs):
    guardPath = ['foo']

class GuardTest_NotAtRoot_manyLevels(GuardTestSuper, GuardTestFuncs):
    guardPath = ['foo', 'bar', 'baz']
