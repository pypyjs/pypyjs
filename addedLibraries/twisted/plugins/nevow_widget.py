# -*- test-case-name: nevow.test.test_athena -*-

"""
twistd subcommand plugin for launching an athena widget server.
"""

try:
    # Twisted 8.0.1 (r23252, to be precise) introduced a public API for
    # this.
    from twisted.application.service import ServiceMaker
except ImportError:
    # For versions of Twisted older than that, fallback to the private
    # version of the same thing.
    from twisted.scripts.mktap import _tapHelper as ServiceMaker

widgetServiceMaker = ServiceMaker(
    "Stand-alone Athena Widget runner",
    "nevow._widget_plugin",
    """
    Create a service which starts a NevowSite with a single page with a single
    athena widget.
    """,
    "athena-widget")
