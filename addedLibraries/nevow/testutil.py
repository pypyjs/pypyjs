# -*- test-case-name: nevow.test.test_testutil -*-
# Copyright (c) 2004-2010 Divmod.
# See LICENSE for details.

import os, sys, signal

#from subprocess import PIPE, Popen

from zope.interface import implements

try:
    import subunit
except ImportError:
    subunit = None

from twisted.python.log import msg
from twisted.trial.unittest import TestCase as TrialTestCase
from twisted.python.components import Componentized
from twisted.internet import defer
from twisted.web import http
from twisted.protocols.basic import LineReceiver

from formless import iformless

from nevow import inevow, context, athena, loaders, tags, appserver
from nevow.jsutil import findJavascriptInterpreter, generateTestScript

class FakeChannel:
    def __init__(self, site):
        self.site = site


class FakeSite:
    pass


class FakeSession(Componentized):
    implements(inevow.ISession)
    def __init__(self, avatar):
        Componentized.__init__(self)
        self.avatar = avatar
        self.uid = 12345
    def getLoggedInRoot(self):
        return self.avatar


fs = FakeSession(None)


class FakeRequest(Componentized):
    """
    Implementation of L{inevow.IRequest} which is convenient to use in unit
    tests.

    @ivar lastModified: The value passed to L{setLastModified} or C{None} if
        that method has not been called.

    @type accumulator: C{str}
    @ivar accumulator: The bytes written to the response body.

    @type deferred: L{Deferred}
    @ivar deferred: The deferred which represents rendering of the response
        to this request.  This is basically an implementation detail of
        L{NevowRequest}.  Application code should probably never use this.

    @ivar _appRootURL: C{None} or the object passed to L{rememberRootURL}.
    """
    implements(inevow.IRequest)

    fields = None
    failure = None
    context = None
    redirected_to = None
    lastModified = None
    content = ""
    method = 'GET'
    code = http.OK
    deferred = None
    accumulator = ''
    _appRootURL = None

    def __init__(self, headers=None, args=None, avatar=None,
                 uri='/', currentSegments=None, cookies=None,
                 user="", password="", isSecure=False):
        """
        Create a FakeRequest instance.

        @param headers: dict of request headers
        @param args: dict of args
        @param avatar: avatar to pass to the FakeSession instance
        @param uri: request URI
        @param currentSegments: list of segments that have "already been located"
        @param cookies: dict of cookies
        @param user: username (like in http auth)
        @param password: password (like in http auth)
        @param isSecure: whether this request represents an HTTPS url
        """
        Componentized.__init__(self)
        self.uri = uri
        if not uri.startswith('/'):
            raise ValueError('uri must be relative with absolute path')
        self.path = uri
        self.prepath = []
        postpath = uri.split('?')[0]
        assert postpath.startswith('/')
        self.postpath = postpath[1:].split('/')
        if currentSegments is not None:
            for seg in currentSegments:
                assert seg == self.postpath[0]
                self.prepath.append(self.postpath.pop(0))
        else:
            self.prepath.append('')
        self.headers = {}
        self.args = args or {}
        self.sess = FakeSession(avatar)
        self.site = FakeSite()
        self.received_headers = {}
        if headers:
            for k, v in headers.iteritems():
                self.received_headers[k.lower()] = v
        if cookies is not None:
            self.cookies = cookies
        else:
            self.cookies = {}
        self.user = user
        self.password = password
        self.secure = isSecure
        self.deferred = defer.Deferred()

    def URLPath(self):
        from nevow import url
        return url.URL.fromString('')

    def getSession(self):
        return self.sess

    def registerProducer(self, producer, streaming):
        """
        Synchronously cause the given producer to produce all of its data.

        This will not work with push producers.  Do not use it with them.
        """
        keepGoing = [None]
        self.unregisterProducer = keepGoing.pop
        while keepGoing:
            producer.resumeProducing()
        del self.unregisterProducer

    def v():
        def get(self):
            return self.accumulator
        return get,
    v = property(*v())

    def write(self, bytes):
        """
        Accumulate the given bytes as part of the response body.

        @type bytes: C{str}
        """
        self.accumulator += bytes


    finished = False
    def finishRequest(self, success):
        self.finished = True

    def finish(self):
        self.deferred.callback('')

    def getHeader(self, key):
        return self.received_headers.get(key.lower())

    def setHeader(self, key, val):
        self.headers[key.lower()] = val

    def redirect(self, url):
        self.redirected_to = url

    def processingFailed(self, f):
        self.failure = f

    def setResponseCode(self, code):
        self.code = code

    def setLastModified(self, when):
        self.lastModified = when

    def prePathURL(self):
        """
        The absolute URL up until the last handled segment of this request.

        @rtype: C{str}.
        """
        return 'http://%s/%s' % (self.getHeader('host') or 'localhost',
                                 '/'.join(self.prepath))

    def getClientIP(self):
        return '127.0.0.1'

    def addCookie(self, k, v, expires=None, domain=None, path=None, max_age=None, comment=None, secure=None):
        """
        Set a cookie for use in subsequent requests.
        """
        self.cookies[k] = v

    def getCookie(self, k):
        """
        Fetch a cookie previously set.
        """
        return self.cookies.get(k)

    def getUser(self):
        """
        Returns the HTTP auth username.
        """
        return self.user

    def getPassword(self):
        """
        Returns the HTTP auth password.
        """
        return self.password

    def getRootURL(self):
        """
        Return the previously remembered URL.
        """
        return self._appRootURL


    def rememberRootURL(self, url=None):
        """
        For compatibility with appserver.NevowRequest.
        """
        if url is None:
            raise NotImplementedError(
                "Default URL remembering logic is not implemented.")
        self._appRootURL = url


    def isSecure(self):
        """
        Returns whether this is an HTTPS request or not.
        """
        return self.secure


class TestCase(TrialTestCase):
    hasBools = (sys.version_info >= (2,3))
    _assertions = 0

    # This should be migrated to Twisted.
    def failUnlessSubstring(self, containee, container, msg=None):
        self._assertions += 1
        if container.find(containee) == -1:
            self.fail(msg or "%r not in %r" % (containee, container))
    def failIfSubstring(self, containee, container, msg=None):
        self._assertions += 1
        if container.find(containee) != -1:
            self.fail(msg or "%r in %r" % (containee, container))

    assertSubstring = failUnlessSubstring
    assertNotSubstring = failIfSubstring

    def assertNotIdentical(self, first, second, msg=None):
        self._assertions += 1
        if first is second:
            self.fail(msg or '%r is %r' % (first, second))

    def failIfIn(self, containee, container, msg=None):
        self._assertions += 1
        if containee in container:
            self.fail(msg or "%r in %r" % (containee, container))

    def assertApproximates(self, first, second, tolerance, msg=None):
        self._assertions += 1
        if abs(first - second) > tolerance:
            self.fail(msg or "%s ~== %s" % (first, second))


if not hasattr(TrialTestCase, 'mktemp'):
    def mktemp(self):
        import tempfile
        return tempfile.mktemp()
    TestCase.mktemp = mktemp


class AccumulatingFakeRequest(FakeRequest):
    """
    I am a fake IRequest that is also a stub implementation of
    IFormDefaults.

    This class is named I{accumulating} for historical reasons only.  You
    probably want to ignore this and use L{FakeRequest} instead.
    """
    implements(iformless.IFormDefaults)

    def __init__(self, *a, **kw):
        FakeRequest.__init__(self, *a, **kw)
        self.d = defer.Deferred()

    def getDefault(self, key, context):
        return ''

    def remember(self, object, interface):
        pass


class FragmentWrapper(athena.LivePage):
    """
    I wrap myself around an Athena fragment, providing a minimal amount of html
    scaffolding in addition to an L{athena.LivePage}.
    """
    docFactory = loaders.stan(
                    tags.html[
                        tags.body[
                            tags.directive('fragment')]])

    def __init__(self, f):
        super(FragmentWrapper, self).__init__()
        self.f = f

    def render_fragment(self, ctx, data):
        self.f.setFragmentParent(self)
        return self.f


def renderLivePage(res, topLevelContext=context.WebContext,
                   reqFactory=FakeRequest):
    """
    Render the given LivePage resource, performing LivePage-specific cleanup.
    Return a Deferred which fires when it has rendered.
    """
    D = renderPage(res, topLevelContext, reqFactory)
    return D.addCallback(lambda x: (res._messageDeliverer.close(), x)[1])


def renderPage(res, topLevelContext=context.WebContext,
               reqFactory=FakeRequest):
    """
    Render the given resource.  Return a Deferred which fires when it has
    rendered.
    """
    req = reqFactory()
    ctx = topLevelContext(tag=res)
    ctx.remember(req, inevow.IRequest)

    render = appserver.NevowRequest(None, True).gotPageContext

    result = render(ctx)
    result.addCallback(lambda x: req.accumulator)
    return result



class NotSupported(Exception):
    """
    Raised by L{JavaScriptTestCase} if the installation lacks a certain
    required feature.
    """



class TestProtocolLineReceiverServer(LineReceiver):
    """
    Subunit protocol which is also a Twisted LineReceiver so that it
    includes line buffering logic.
    """
    delimiter = '\n'

    def __init__(self, proto):
        self.proto = proto


    def lineReceived(self, line):
        """
        Forward the line on to the subunit protocol's lineReceived method,
        which expects it to be newline terminated.
        """
        self.proto.lineReceived(line + '\n')



class JavaScriptTestCase(TrialTestCase):
    def __init__(self, methodName='runTest'):
        TrialTestCase.__init__(self, methodName)
        self.testMethod = getattr(self, methodName)


    def findJavascriptInterpreter(self):
        """
        @see: L{nevow.jsutil.findJavascriptInterpreter}
        """
        return findJavascriptInterpreter()


    def checkDependencies(self):
        """
        Check that all the dependencies of the test are satisfied.

        @raise NotSupported: If any one of the dependencies is not satisfied.
        """
        js = self.findJavascriptInterpreter()
        if js is None:
            raise NotSupported("Could not find JavaScript interpreter")
        if subunit is None:
            raise NotSupported("Could not import 'subunit'")
        for name in ['WEXITSTATUS', 'WIFSIGNALED' ,'WTERMSIG']:
            if getattr(os, name, None) is None:
                raise NotSupported("os.%s unavailable" % (name,))


    def _writeToTemp(self, contents):
        fname = self.mktemp()
        fd = file(fname, 'w')
        try:
            fd.write(contents)
        finally:
            fd.close()
        return fname


    def createSource(self, testModule):
        """
        Return a string of JavaScript source code which, when executed, will
        run the JavaScript unit tests defined in the given module.

        @type testModule: C{str}
        @param testModule: The JavaScript module name which contains the
        tests to run.

        @rtype: C{str}
        """
        js = """
// import Divmod.UnitTest
// import %(module)s

Divmod.UnitTest.runRemote(Divmod.UnitTest.loadFromModule(%(module)s));
""" % {'module': testModule}
        return js


    def makeScript(self, testModule):
        """
        Write JavaScript source for executing the JavaScript unit tests in
        the given JavaScript module to a file and return the name of that
        file.

        @type testModule: C{str}
        @param testModule: The JavaScript module name which contains the
        tests to run.

        @rtype: C{str}
        """
        jsfile = self._writeToTemp(self.createSource(testModule))
        scriptFile = self._writeToTemp(generateTestScript(jsfile))
        return scriptFile


    def _runWithSigchild(self, f, *a, **kw):
        """
        Run the given function with an alternative SIGCHLD handler.
        """
        oldHandler = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        try:
            return f(*a, **kw)
        finally:
            signal.signal(signal.SIGCHLD, oldHandler)


    def run(self, result):
        try:
            self.checkDependencies()
        except NotSupported, e:
            result.startTest(self)
            result.addSkip(self, str(e))
            result.stopTest(self)
            return
        js = self.findJavascriptInterpreter()
        try:
            script = self.makeScript(self.testMethod())
        except KeyError:
            result.addError(self, sys.exc_info())
            return

        server = subunit.TestProtocolServer(result)
        protocol = TestProtocolLineReceiverServer(server)

        # What this *SHOULD BE*
        # spawnProcess(protocol, js, (script,))
        # return protocol.someDisconnectCallback()

        # However, *run cannot return a Deferred profanity profanity profanity
        # profanity*, so instead it is *profanity* this:
        def run():
            argv = [js, script]
            msg("Running JavaScript interpreter, argv = %r" % (argv,))
            child = Popen(argv, stdout=PIPE)
            while True:
                bytes = child.stdout.read(4096)
                if bytes:
                    protocol.dataReceived(bytes)
                else:
                    break
            returnCode = child.wait()
            if returnCode < 0:
                result.addError(
                    self,
                    (Exception,
                     "JavaScript interpreter exited due to signal %d" % (-returnCode,),
                     None))
            elif returnCode:
                result.addError(
                    self,
                    (Exception,
                     "JavaScript interpreter had error exit: %d" % (returnCode,),
                     None))
        self._runWithSigchild(run)



def setJavascriptInterpreterOrSkip(testCase):
    """
    If we're unable to find a javascript interpreter (currently we only look
    for smjs or js) then set the C{skip} attribute on C{testCase}. Otherwise
    assign the path to the interpreter executable to
    C{testCase.javascriptInterpreter}
    """
    script = findJavascriptInterpreter()
    if script is None:
        testCase.skip = "No JavaScript interpreter available."
    else:
        testCase.javascriptInterpreter = script



class CSSModuleTestMixin:
    """
    Mixin for L{unittest.TestCase} subclasses which are testing the Athena's
    CSS module functionality.
    """
    def _makeCSSRegistry(self):
        """
        Make a CSS registry with some modules in it.
        """
        def makeModule(contents=None):
            fname = self.mktemp()
            f = file(fname, 'w')
            if contents is not None:
                f.write(contents)
            f.close()
            return fname

        return athena.CSSRegistry(
            {u'TestCSSModuleDependencies': makeModule(),
             u'TestCSSModuleDependencies.Dependor': makeModule(
                '// import TestCSSModuleDependencies.Dependee\n'),
             u'TestCSSModuleDependencies.Dependee': makeModule()})
