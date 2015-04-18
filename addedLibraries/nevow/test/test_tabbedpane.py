# Copyright (c) 2009 Divmod.  See LICENSE for details.

"""
Tests for L{nevow.taglibrary.tabbedPane}.
"""

from twisted.trial.unittest import TestCase


class TabbedPaneTests(TestCase):
    def test_import(self):
        """
        L{nevow.taglibrary.tabbedPane} can be imported.

        This is a very meager test, and it should certainly be augmented
        with friends later, but for the time being, it is sufficient to
        cover the fix I am making, which actually makes the module
        importable. -exarkun
        """
        import nevow.taglibrary.tabbedPane
