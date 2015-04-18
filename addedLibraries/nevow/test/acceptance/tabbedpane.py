"""
Acceptance tests for L{nevow.taglibrary.tabbedPane}.

Run as::

    twistd -n athena-widget --element nevow.test.acceptance.tabbedpane.{tabbedPaneFragment,fetchedTabbedPaneFragment}
"""

from nevow.taglibrary.tabbedPane import TabbedPaneFragment
from nevow import tags, athena, loaders


def tabbedPaneFragment():
    """
    Return a L{TabbedPaneFragment}.  The tabbed pane should have 4 tabs: "Tab
    0", "Tab 1", "Tab 2" and "Tab 3".  The content of each tab should be a
    C{<h1>} node containing the tab's number.
    """
    return TabbedPaneFragment(
        [('Page ' + str(i), tags.h1[str(i)]) for i in xrange(4)])



class TabbedPaneFetcher(athena.LiveElement):
    jsClass = u'Nevow.Test.TestTabbedPane.TabbedPaneFetcher'
    docFactory = loaders.xmlstr("""
<div xmlns:athena="http://divmod.org/ns/athena/0.7"
  xmlns:nevow="http://nevow.com/ns/nevow/0.1"
  nevow:render="liveElement">
  <a href="#">
    <athena:handler event="onclick" handler="dom_getTabbedPane" />
    Get a tabbed pane from the server
  </a>
</div>""")

    def getTabbedPane(self):
        """
        Return a L{TabbedPaneFragment}.
        """
        f = tabbedPaneFragment()
        f.setFragmentParent(self)
        return f
    athena.expose(getTabbedPane)



def fetchedTabbedPaneFragment():
    """
    Return a widget will fetch a L{TabbedPaneFragment} from the server when
    asked to.  Renders as a "Get a tabbed pane from the server" link, which,
    when clicked, will return the result of L{tabbedPaneFragment}.
    """
    return TabbedPaneFetcher()
