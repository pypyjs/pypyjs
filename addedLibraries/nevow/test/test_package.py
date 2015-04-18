# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for Nevow package sundries.
"""

from twisted.python.versions import Version
from twisted.trial.unittest import SynchronousTestCase

import nevow

class VersionTests(SynchronousTestCase):
    """
    Tests for the version information exposed by the top-level L{nevow}
    package.
    """
    def test_version(self):
        """
        L{nevow.version} is a L{Version} instance
        """
        self.assertIsInstance(nevow.version, Version)


    def test_name(self):
        """
        L{nevow.version} names Nevow.
        """
        self.assertEqual("nevow", nevow.version.package)


    def test_versionComponents(self):
        """
        L{nevow.version} gives the major, minor, and micro version numbers as
        integers.
        """
        self.assertEqual(
            (int, int, int),
            tuple(
                type(info) for info
                in [nevow.version.major, nevow.version.minor, nevow.version.micro]))


    def test_versionInfo(self):
        """
        L{nevow.__version_info__} is a L{tuple} giving the same version numbers
        as L{nevow.version}.
        """
        self.assertEqual(
            nevow.__version_info__,
            (nevow.version.major, nevow.version.minor, nevow.version.micro))


    def test_versionString(self):
        """
        L{nevow.__version__} is a L{str} giving at least as much information as
        is given by L{nevow.__version_info__}.
        """
        self.assertIn("%d.%d.%d" % nevow.__version_info__, nevow.__version__)
