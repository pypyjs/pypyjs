# Copyright 2008 Divmod, Inc.  See LICENSE file for details

"""
Axiom plugins for Twisted.
"""

from zope.interface import classProvides

from twisted.plugin import IPlugin, getPlugins
from twisted.python.usage import Options
from twisted.application.service import IServiceMaker, IService, Service


class _CheckSystemVersion(Service):
    """
    A service which, when started, updates the stored version information in a
    store.

    @ivar store: The L{Store} in which to update version information.
    """
    def __init__(self, store):
        self.store = store


    def startService(self):
        from axiom.listversions import checkSystemVersion
        checkSystemVersion(self.store)



class AxiomaticStart(object):
    """
    L{IServiceMaker} plugin which gets an L{IService} from an Axiom store.
    """
    classProvides(IPlugin, IServiceMaker)

    tapname = "axiomatic-start"
    description = "Run an Axiom database (use 'axiomatic start' instead)"

    class options(Options):
        optParameters = [
            ('dbdir', 'd', None, 'Path containing Axiom database to start')]

        optFlags = [('debug', 'b', 'Enable Axiom-level debug logging')]


    def makeService(cls, options):
        """
        Create an L{IService} for the database specified by the given
        configuration.
        """
        from axiom.store import Store
        store = Store(options['dbdir'], debug=options['debug'])
        service = IService(store)
        _CheckSystemVersion(store).setServiceParent(service)
        return service
    makeService = classmethod(makeService)


__all__ = ['AxiomaticStart']
