"""
Tests for L{nevow.testutil} -- a module of utilities for testing Nevow
applications.
"""

import sys

from unittest import TestResult

from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase, SkipTest
from twisted.web.http import OK, BAD_REQUEST

from nevow.testutil import FakeRequest, renderPage, JavaScriptTestCase
from nevow.testutil import NotSupported
from nevow.url import root
from nevow.rend import Page
from nevow.loaders import stan


class TestFakeRequest(TestCase):
    """
    Bad tests for L{FakeRequest}.

    These tests verify that L{FakeRequest} has some behavior, but not that
    that behavior is the same as the behavior of an actual request object. 
    In other words, these tests do not actually verify the fake.  They
    should be replaced with something which verifies that L{FakeRequest} and
    L{NevowRequest} actually have the same behavior.
    """
    def test_fields(self):
        """
        L{FakeRequest.fields} is C{None} for all fake requests.
        """
        self.assertIdentical(FakeRequest().fields, None)


    def test_prePathURL(self):
        """
        Verify that L{FakeRequest.prePathURL} returns the prepath of the
        requested URL.
        """
        req = FakeRequest(currentSegments=['a'], uri='/a/b')
        self.assertEqual(req.prePathURL(), 'http://localhost/a')


    def test_prePathURLHost(self):
        """
        Verify that L{FakeRequest.prePathURL} will turn the C{Host} header of
        the request into the netloc of the returned URL, if it's present.
        """
        req = FakeRequest(currentSegments=['a', 'b'],
                          uri='/a/b/c/',
                          headers={'host': 'foo.bar'})
        self.assertEqual(req.prePathURL(), 'http://foo.bar/a/b')


    def test_getRootURL(self):
        """
        L{FakeRequest.getRootURL} returns C{None} when
        L{FakeRequest.rememberRootURL} has not yet been called.  After
        L{FakeRequest.rememberRootURL} has been called,
        L{FakeRequest.getRootURL} returns the value which was passed to it.
        """
        request = FakeRequest()
        self.assertIdentical(request.getRootURL(), None)
        request.rememberRootURL("foo/bar")
        self.assertEqual(request.getRootURL(), "foo/bar")


    def test_headers(self):
        """
        Check that setting a header with L{FakeRequest.setHeader} actually
        places it in the headers dictionary.
        """
        host = 'divmod.com'
        req = FakeRequest()
        req.setHeader('host', host)
        self.assertEqual(req.headers['host'], host)


    def test_caseInsensitiveHeaders(self):
        """
        L{FakeRequest.getHeader} will return the value of a header regardless
        of casing.
        """
        host = 'example.com'
        request = FakeRequest()
        request.received_headers['host'] = host
        self.assertEqual(request.getHeader('hOsT'), host)


    def test_smashInitialHeaderCase(self):
        """
        L{FakeRequest.getHeader} will return the value of a header specified to
        L{FakeRequest.__init__} even if the header names have differing case.
        """
        host = 'example.com'
        request = FakeRequest(headers={'HoSt': host})
        self.assertEqual(request.getHeader('hOsT'), host)


    def test_urls(self):
        """
        Check that rendering URLs via L{renderPage} actually works.
        """
        class _URLPage(Page):
            docFactory = stan(
                root.child('foo'))

        def _checkForUrl(result):
            return self.assertEquals('http://localhost/foo', result)

        return renderPage(_URLPage()).addCallback(_checkForUrl)


    def test_defaultResponseCode(self):
        """
        Test that the default response code of a fake request is success.
        """
        self.assertEqual(FakeRequest().code, OK)


    def test_setResponseCode(self):
        """
        Test that the response code of a fake request can be set.
        """
        req = FakeRequest()
        req.setResponseCode(BAD_REQUEST)
        self.assertEqual(req.code, BAD_REQUEST)


    def test_headerSeparation(self):
        """
        Request headers and response headers are different things.

        Test that they are handled separately.
        """
        req = FakeRequest()
        req.setHeader('foo', 'bar')
        self.assertNotIn('foo', req.received_headers)
        self.assertEqual(req.getHeader('foo'), None)
        req.received_headers['foo'] = 'bar'
        self.assertEqual(req.getHeader('foo'), 'bar')



    def test_path(self):
        """
        Test that the path attribute of a fake request is set.
        """
        req = FakeRequest(uri='/foo')
        self.assertEqual(req.path, '/foo')



class JavaScriptTests(TestCase):
    """
    Tests for the JavaScript UnitTest runner, L{JavaScriptTestCase}.
    """
    def setUp(self):
        """
        Create a L{JavaScriptTestCase} and verify that its dependencies are
        present (otherwise, skip the test).
        """
        self.case = JavaScriptTestCase()
        try:
            self.case.checkDependencies()
        except NotSupported:
            raise SkipTest("Missing JS dependencies")


    def test_unsuccessfulExit(self):
        """
        Verify that an unsuccessful exit status results in an error.
        """
        result = TestResult()
        self.case.createSource = lambda testMethod: "throw new TypeError();"
        self.case.run(result)
        self.assertEqual(len(result.errors), 1)
        self.assertTrue(
            result.errors[0][1].startswith(
                'Exception: JavaScript interpreter had error exit: '))


    def test_signalledExit(self):
        """
        An error should be reported if the JavaScript interpreter exits because
        it received a signal.
        """
        segfault = FilePath(self.mktemp())
        segfault.setContent("""\
#!/usr/bin/python
# Generate an unhandled SIGSEGV for this process immediately upon import.

import os, signal
os.kill(os.getpid(), signal.SIGSEGV)
""")

        def stubFinder():
            return sys.executable
        def stubScript(testModule):
            return segfault.path
        self.case.findJavascriptInterpreter = stubFinder
        self.case.makeScript = stubScript
        result = TestResult()
        self.case.run(result)
        self.assertEqual(len(result.errors), 1)
        self.assertEquals(
            result.errors[0][1],
            'Exception: JavaScript interpreter exited due to signal 11\n')


    def test_missingJavaScriptClass(self):
        """
        If a JavaScript class required by the test code is unavailable, an
        error is added to the result object by L{JavaScriptTestCase.run}.
        """
        result = TestResult()
        self.case.testMethod = lambda: "Nevow.Test.NoSuchModule"
        self.case.run(result)
        self.assertEqual(len(result.errors), 1)
