# -*- test-case-name: nevow.test.test_nit -*-
# Copyright (c) 2008 Divmod.  See LICENSE for details.

"""
Implementation of the command line I{nit} tool
"""

import sys

from twisted.python.log import startLogging
from twisted.python.usage import UsageError, Options
from twisted.internet import reactor

from nevow.appserver import NevowSite
from nevow.livetrial.runner import TestFrameworkRoot
from nevow.livetrial.testcase import TestLoader, TestSuite


class NitOptions(Options):
    optParameters = [
        ('port', None, '8080',
         'Specify the TCP port to which to bind the test server')]

    def parseArgs(self, *args):
        self['testmodules'] = args


    def postOptions(self):
        self['port'] = int(self['port'])



def _getSuite(modules):
    """
    Given an iterable of Python modules, return a nit test suite which
    contains all the tests in those modules.
    """
    loader = TestLoader()
    suite = TestSuite('root')
    for module in modules:
        suite.addTest(loader.loadByName(module, True))
    return suite



def run():
    """
    Parse nit options from the command line and start a nit server.
    """
    config = NitOptions()
    try:
        config.parseOptions()
    except UsageError, ue:
        raise SystemExit("%s: %s" % (sys.argv[0], ue))
    else:
        if not config['testmodules']:
            raise SystemExit("Specify at least one module name to test")
        startLogging(sys.stdout)
        suite = _getSuite(config['testmodules'])
        site = NevowSite(TestFrameworkRoot(suite))
        reactor.listenTCP(config['port'], site)
        reactor.run()
