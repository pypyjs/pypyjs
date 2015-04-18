
"""
An (unfortunately somewhat contrived, and involved) acceptance test which
demonstrates that it is possible to combine a few features of Athena to
re-connect a widget to a newly-created server-side counterpart.  In order to
see the demonstration, click 'show ID', 'disconnect', then 'show ID' again.
You will see that you have received a new ReconnectableElement.

Run as::

    twistd -n athena-widget --element nevow.test.acceptance.reconnect.reconnect

"""

from nevow.athena import LiveElement, expose
from nevow import loaders, tags
from nevow._widget_plugin import ElementRenderingLivePage as OriginalPage

class ReconnectableElementRenderingLivePage(OriginalPage):
    """
    A version of the ElementRenderingLivePage from the plugin which also has
    methods suitable for reconnection.

    XXX: this class unfortunately uncovers some nasty corners of the LivePage
    API.  Don't be too surprised if this ends up broken by some future fixes to
    that API.  We should not attempt to keep this working as-is; if you do find
    it in a broken state, just update it to use newer, better documented APIs.
    """
    jsClass = u'Nevow.Test.ReconnectAcceptanceTest.ReconnectingPage'
    def __init__(self, *a, **k):
        """
        Make sure our interface allows the particular method we want to expose.
        """
        super(ReconnectableElementRenderingLivePage, self).__init__(*a, **k)
        self.iface = ['giveElementID']
        self.rootObject = self


    def giveElementID(self, newID):
        """
        Assign an ID to the widget.
        """
        self.element.setFragmentParent(self)
        self._localObjects[newID] = self.element

    expose(giveElementID)


# Monkey patch to cheat a little bit in the context of the widget plugin.
from nevow import _widget_plugin
_widget_plugin.ElementRenderingLivePage = ReconnectableElementRenderingLivePage

import itertools

counter = itertools.count().next

class ReconnectableElement(LiveElement):
    """
    I am a live element that can disconnect and be reconnected.
    """
    docFactory = loaders.stan(
        tags.div(render=tags.directive("liveElement"))[
            tags.button(onclick="Nevow.Athena.page.deliveryChannel.sendCloseMessage(); return true;")["Disconnect"],
            tags.button(onclick="""
            Nevow.Athena.Widget.get(this).callRemote('getID').addCallback(function (result) {
                var e = document.createElement('div');
                e.appendChild(document.createTextNode('ID: '+result));
                document.body.appendChild(e);
            })
            """)["Show ID"]])


    def __init__(self):
        """
        Create a ReconnectableElement with a unique ID
        """
        LiveElement.__init__(self)
        self.currentID = counter()


    def getID(self):
        """
        Retrieve my current ID.
        """
        return self.currentID
    expose(getID)



def reconnect():
    return ReconnectableElement()
