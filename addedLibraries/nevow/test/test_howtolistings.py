
"""
This module tests the code listings used in the documentation.
"""

import sys

from twisted.python.filepath import FilePath
from twisted.trial.unittest import SkipTest, TestCase

from nevow._widget_plugin import ElementRenderingLivePage
from nevow.testutil import renderLivePage, JavaScriptTestCase
from nevow.athena import jsDeps, expose

from nevow import plugins


class ExampleTestBase(object):
    """
    This is a mixin which adds an example to the path, tests it, and then
    removes it from the path and unimports the modules which the test loaded.
    Test cases which test example code and documentation listings should use
    this.

    This is done this way so that examples can live in isolated path entries,
    next to the documentation, replete with their own plugin packages and
    whatever other metadata they need.  Also, example code is a rare instance
    of it being valid to have multiple versions of the same code in the
    repository at once, rather than relying on version control, because
    documentation will often show the progression of a single piece of code as
    features are added to it, and we want to test each one.
    """

    examplePath = None

    def setUp(self):
        """
        Add our example directory to the path and record which modules are
        currently loaded.
        """
        self.originalPath = sys.path[:]
        self.originalModules = sys.modules.copy()
        here = FilePath(__file__).parent().parent().parent()
        for childName in self.examplePath:
            here = here.child(childName)
        if not here.exists():
            raise SkipTest("Examples (%s) not found - cannot test" % (here.path,))
        sys.path.append(here.path)
        # This stuff is pretty horrible; we need to turn off JS caching for the
        # duration of this test (this flag will be set back to True by the
        # plugin-loading itself, so no need to clean it up) because the
        # previously-loaded list of plugins is going to be invalid.
        jsDeps._loadPlugins = True
        # Even more horrible!  nevow.plugins.__path__ needs to be recomputed
        # each time for the new value of sys.path.
        reload(plugins)


    def tearDown(self):
        """
        Remove the example directory from the path and remove all modules loaded by
        the test from sys.modules.
        """
        sys.modules.clear()
        sys.modules.update(self.originalModules)
        sys.path[:] = self.originalPath
        reload(plugins)



class ExampleJavaScriptTestCase(JavaScriptTestCase):
    """
    Since JavaScriptTestCase does not use setUp and tearDown, we can't use
    simple inheritance to invoke the functionality in ExampleTestBase; so,
    instead, this class composes JavaScriptTestCase with a ExampleTestBase.
    """
    def run(self, result):
        """
        Wrap L{JavaScriptTestCase.run} to change and restore the plugin environment
        on each test run.
        """
        base = ExampleTestBase()
        base.examplePath = self.examplePath
        try:
            base.setUp()
        except SkipTest, e:
            result.startTest(self)
            result.addSkip(self, str(e))
            result.stopTest(self)
        else:
            try:
                return JavaScriptTestCase.run(self, result)
            finally:
                base.tearDown()


def chatListing(partname):
    """
    Return a list of strings that represents a path from the root of the Nevow
    source package which contains a potential PYTHONPATH entry with some
    listing code in it, based on which part of the chat tutorial it came from.
    """
    return ['doc', 'howto', 'chattutorial', 'part'+partname, 'listings']



class Part00Tests(ExampleJavaScriptTestCase):
    """
    Refer to JavaScript unit tests for section 01 of the tutorial.
    """

    examplePath = chatListing('00')

    def test_part00(self):
        """
        Test method pointing to part 00 of the tutorial.
        """
        return 'Nevow.Test.TestHowtoListing00'



class Echo00(ExampleTestBase, TestCase):
    """
    These tests will make sure that the very basic 'echobox' portion of the
    tutorial works.
    """
    examplePath = chatListing('00')

    def test_renderEcho(self):
        """
        Rendering the echo example element should produce a very simple text area.
        """
        from echothing.echobox import EchoElement
        TEXT = 'Echo Element'
        eb = EchoElement()
        erlp = ElementRenderingLivePage(eb)
        def checkContent(result):
            # The "liveElement" renderer inserts this, let's look for it to
            # make sure it rendered live:
            self.assertIn('id="athena:'+str(eb._athenaID)+'"', result)
            self.assertIn('athena:class="EchoThing.EchoWidget"', result)
            self.assertIn(TEXT, result)
        return renderLivePage(erlp).addCallback(checkContent)


    def test_echoTellsClient(self):
        """
        When 'hear' is called on a ChatterElement, it should inform its client of what
        was said and by whom.
        """
        from echothing.echobox import EchoElement
        eb = EchoElement()
        echoed = []
        eb.callRemote = lambda method, message: echoed.append((method, message))
        eb.say(u'HELLO... Hello... hello...')
        self.assertEquals(echoed, [('addText', u'HELLO... Hello... hello...')])



class Part01Tests(ExampleJavaScriptTestCase):
    """
    Refer to JavaScript unit tests for section 01 of the tutorial.
    """

    examplePath = chatListing('01')

    def test_part01(self):
        """
        Test method pointing to part 01 of the tutorial.
        """
        return 'Nevow.Test.TestHowtoListing01'



class RenderAndChat01(ExampleTestBase, TestCase):
    """
    These tests make sure that the listing for part 01 of the chatterbox
    tutorial will import, render, and allow users to chat with each other.
    """

    examplePath = chatListing('01')

    def test_basicRendering(self):
        """
        Rendering the example element should produce a chat area.
        """
        from chatthing.chatterbox import ChatterElement, ChatRoom
        PROMPT = 'Choose your username: '
        cb = ChatterElement(ChatRoom())
        erlp = ElementRenderingLivePage(cb)
        def checkContent(result):
            # The "liveElement" renderer inserts this, let's look for it to
            # make sure it rendered live:
            self.assertIn('id="athena:'+str(cb._athenaID)+'"', result)
            self.assertIn('athena:class="ChatThing.ChatterWidget"', result)
            self.assertIn(PROMPT, result)
        return renderLivePage(erlp).addCallback(checkContent)


    def test_username(self):
        """
        When a user sets their username in the chat room, it should set an
        attribute on their ChatterElement instance.
        """
        from chatthing.chatterbox import ChatterElement, ChatRoom
        cb = ChatterElement(ChatRoom())
        setUsername = expose.get(cb, 'setUsername')
        setUsername(u'jethro')
        self.assertIdentical(u'jethro', cb.username)


    def test_loginThenWall(self):
        """
        When a user logs in the 'wall' method on their ChatterElement gets called,
        notifiying everyone in the room that they have entered.
        """
        from chatthing.chatterbox import ChatRoom
        jethroHeard = []
        cletusHeard = []
        cr = ChatRoom()
        user1 = cr.makeChatter()
        user1.wall = lambda msg: jethroHeard.append(msg)
        user1.setUsername(u'jethro')
        user2 = cr.makeChatter()
        user2.wall = lambda msg: cletusHeard.append(msg)
        user2.setUsername(u'cletus')
        self.assertEquals(jethroHeard,
                          [u' * user jethro has joined the room',
                           u' * user cletus has joined the room'])
        self.assertEquals(cletusHeard, [u' * user cletus has joined the room'])


    def test_sayThenHear(self):
        """
        When a user calls the 'say' method on their ChatterElement, everyone (including
        them) should 'hear' it.
        """
        from chatthing.chatterbox import ChatRoom
        cr = ChatRoom()
        user1 = cr.makeChatter()
        user1.wall = lambda msg: msg
        user1.setUsername(u'jethro')
        user2 = cr.makeChatter()
        user2.wall = lambda msg: msg
        user2.setUsername(u'cletus')
        jethroHeard = []
        cletusHeard = []
        user1.hear = lambda who, what: jethroHeard.append((who,what))
        user2.hear = lambda who, what: cletusHeard.append((who,what))
        say = expose.get(user1, 'say')
        say(u'Hey, Cletus!')
        self.assertEquals(jethroHeard, cletusHeard)
        self.assertEquals(cletusHeard, [(u'jethro', u'Hey, Cletus!')])


    def test_wallTellsClient(self):
        """
        When 'wall' is called on a ChatterElement, it should inform its client of
        the message.
        """
        from chatthing.chatterbox import ChatRoom
        cb = ChatRoom().makeChatter()
        heard = []
        cb.callRemote = lambda method, msg: heard.append((method, msg))
        cb.wall(u'Message for everyone...')
        self.assertEquals(heard, [('displayMessage', u'Message for everyone...')])

    def test_hearTellsClient(self):
        """
        When 'hear' is called on a ChatterElement, it should inform its client of what
        was said and by whom.
        """
        from chatthing.chatterbox import ChatRoom
        cb = ChatRoom().makeChatter()
        heard = []
        cb.callRemote = lambda method, who, what: heard.append((method, who, what))
        cb.hear(u'Hello', u'Chat')
        self.assertEquals(heard, [('displayUserMessage', u'Hello', u'Chat')])

