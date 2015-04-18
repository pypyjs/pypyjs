# Copyright (c) 2008 Divmod.  See LICENSE for details.

"""
Tests for L{nevow.livetrial} and L{nevow.scripts.nit}.
"""

import sys

from twisted.trial.unittest import TestCase
from twisted.python.failure import Failure

from nevow.appserver import NevowSite
from nevow.testutil import FragmentWrapper, renderLivePage
from nevow.livetrial.testcase import TestSuite, TestError
from nevow.livetrial.runner import TestFrameworkRoot
from nevow.scripts import nit

MESSAGE = u'I am an error'



class _DummyErrorHolder(object):
    """
    A dummy object that implements the parts of the ErrorHolder API we use,
    supplying an appropriate Failure.
    """

    def createFailure(self):
        """Create a Failure with traceback and all."""
        try:
            raise Exception(MESSAGE)
        except Exception:
            return Failure()


    def run(self, thing):
        thing.addError(self, self.createFailure())



class _DummySuite(TestSuite):
    """A dummy test suite containing a dummy Failure holder."""

    holderType = _DummyErrorHolder

    def __init__(self):
        self.name = 'Dummy Suite'
        holder = _DummyErrorHolder()
        self.tests = [holder]



class NevowInteractiveTesterTest(TestCase):

    def test_gatherError(self):
        """
        Attempt collection of tests in the presence of an Failure that has
        occurred during trial's collection.
        """
        suite = _DummySuite()
        instances = suite.gatherInstances()
        te = instances[0]
        self.assertIdentical(type(te), TestError)


    def test_errorRendering(self):
        te = TestError(_DummyErrorHolder())
        return renderLivePage(FragmentWrapper(te)).addCallback(
            lambda output: self.assertIn(MESSAGE, output))


    def test_portOption(self):
        """
        L{nit.NitOptions.parseOptions} accepts the I{--port} option and sets
        the port number based on it.
        """
        options = nit.NitOptions()
        options.parseOptions(['--port', '1234'])
        self.assertEqual(options['port'], 1234)


    def test_portOptionDefault(self):
        """
        If no I{--port} option is given, a default port number is used.
        """
        options = nit.NitOptions()
        options.parseOptions([])
        self.assertEqual(options['port'], 8080)


    def test_testModules(self):
        """
        All extra positional arguments are interpreted as test modules.
        """
        options = nit.NitOptions()
        options.parseOptions(['foo', 'bar'])
        self.assertEqual(options['testmodules'], ('foo', 'bar'))


    def test_getSuite(self):
        """
        L{nit._getSuite} returns a L{nevow.livetrial.testcase.TestSuite} with
        L{TestCase} instances added to it as specified by the list of module
        names passed to it.
        """
        suite = nit._getSuite(['nevow.test.livetest_athena'])
        self.assertTrue(suite.tests[0].tests)


    def test_runInvalidOptions(self):
        """
        L{nit.run} raises L{SystemExit} if invalid options are used.
        """
        self.patch(sys, 'argv', ["nit", "--foo"])
        self.assertRaises(SystemExit, nit.run)


    def test_runWithoutModules(self):
        """
        If no modules to test are given on the command line, L{nit.run} raises
        L{SystemExit}.
        """
        self.patch(sys, 'argv', ['nit'])
        self.assertRaises(SystemExit, nit.run)


    def test_run(self):
        """
        Given a valid port number and a test module, L{nit.run} starts logging
        to stdout, starts a L{NevowSite} listening on the specified port
        serving a L{TestFrameworkRoot}, and runs the reactor.
        """
        class FakeReactor:
            def listenTCP(self, port, factory):
                events.append(('listen', port, factory))

            def run(self):
                events.append(('run',))

        events = []
        self.patch(
            nit, 'startLogging', lambda out: events.append(('logging', out)))
        self.patch(nit, 'reactor', FakeReactor())
        self.patch(sys, 'argv', ['nit', '--port', '123', 'nevow'])
        nit.run()
        self.assertEqual(events[0], ('logging', sys.stdout))
        self.assertEqual(events[1][:2], ('listen', 123))
        self.assertTrue(isinstance(events[1][2], NevowSite))
        self.assertTrue(isinstance(events[1][2].resource, TestFrameworkRoot))
        self.assertEqual(events[2], ('run',))

