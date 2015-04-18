// -*- test-case-name: nevow.test.test_howtolistings -*-

/**
 * This test case is for the ChatterWidget module under part01 of the Nevow/Athena chat tutorial.
 */

// import Divmod.UnitTest
// import Divmod.Defer
// import Nevow.Test.WidgetUtil
// import ChatThing

Nevow.Test.TestHowtoListing01.TestableChatterWidget = ChatThing.ChatterWidget.subclass(
    "Nevow.Test.TestHowtoListing01.TestableChatterWidget");

/**
 * Provide a testable version of the widget with less coupling with the
 * runtime and DOM.  (This should only override Athena methods, not methods
 * defined in ChatterWidget itself, as that would be self-defeating.)
 */
Nevow.Test.TestHowtoListing01.TestableChatterWidget.methods(
    /**
     * Provide a mocked constructor which allows us to refer to a test case
     * from mock methods.
     */

    function __init__(self, node, testCase) {
        self.testCase = testCase;
        return Nevow.Test.TestHowtoListing01.TestableChatterWidget.upcall(self, "__init__", node);
    },
    /**
     * Provide a mocked version of nodeByAttribute which doesn't require
     * runtime features (such as XPath).
     */
    function nodeByAttribute(self, attribute, value) {
        return self.testCase.mockNodes[value];
    });

Nevow.Test.TestHowtoListing01.TestHowtoListing01 = Divmod.UnitTest.TestCase.subclass(
    'Nevow.Test.TestHowtoListing01.TestHowtoListing01');

Nevow.Test.TestHowtoListing01.TestHowtoListing01.methods(

    /**
     * Set up the tests to run.
     */
    function setUp(self) {
        self.node = Nevow.Test.WidgetUtil.makeWidgetNode();
        self.mockNodes = {};
        self.mockNodes["scrollArea"] = document.createElement("div");
        self.mockNodes['username'] = document.createElement('input');
        self.mockNodes['sendLine'] = document.createElement('div');
        self.mockNodes['chooseBox'] = document.createElement('div');
        self.mockNodes['userMessage'] = document.createElement('input');
        self.mockNodes['loggedInAs'] = document.createElement('div');

        self.chatterWidget = Nevow.Test.TestHowtoListing01.TestableChatterWidget(self.node, self);
    },

    /**
     * Verify that the 'displayMessage' function will manipulate the scrolling
     * area in a way which is visible to the user.
     */
    function test_displayMessage(self) {
        var mockScroll = self.mockNodes['scrollArea'];
        self.chatterWidget.displayMessage(" * bob has entered the room");
        self.assertIdentical(mockScroll.childNodes.length, 1);
        self.assertIdentical(mockScroll.childNodes[0].nodeType, document.ELEMENT_NODE);
        self.assertIdentical(mockScroll.childNodes[0].childNodes.length, 1);
        self.assertIdentical(mockScroll.childNodes[0].childNodes[0].nodeValue,
                             " * bob has entered the room");
    },

    /**
     * Verify that the 'displayUserMessage' function will manipulate the
     * scrolling area in a way which is visible to the user.
     */
    function test_displayUserMessage(self) {
        var mockScroll = self.mockNodes['scrollArea'];
        self.chatterWidget.displayUserMessage("bob", "hello!");
        self.assertIdentical(mockScroll.childNodes.length, 1);
        self.assertIdentical(mockScroll.childNodes[0].nodeType, document.ELEMENT_NODE);
        self.assertIdentical(mockScroll.childNodes[0].childNodes.length, 1);
        self.assertIdentical(mockScroll.childNodes[0].childNodes[0].nodeValue, "bob: hello!");
    },

    /**
     * Invoking the doSetUserName event handler ought to call a remote method
     * to choose the username for this widget on the server; when the remote
     * method completes, it should:
     *  1) hide the 'choose username' box,
     *  2) show the chat area,
     *  3) show the 'logged in as' area, and
     *  4) display the user name in the 'logged in as' node.
     */
    function test_chooseUserName(self) {
        self.mockNodes['username'].value = "jethro";
        var d = Divmod.Defer.Deferred();
        self.chatterWidget.callRemote = function (method, argument) {
            self.assertIdentical(method, "setUsername");
            self.assertIdentical(argument, "jethro");
            return d;
        };
        // Make sure the event won't propagate, or the form will submit.

        var eventResult = self.chatterWidget.doSetUsername();
        self.assertIdentical(eventResult, false);
        d.callback(null);
        self.assertIdentical(
            self.mockNodes['sendLine'].style.display, "block");
        self.assertIdentical(
            self.mockNodes['chooseBox'].style.display, "none");
        self.assertIdentical(
            self.mockNodes['loggedInAs'].style.display, "block");
        self.assertIdentical(
            self.mockNodes['loggedInAs'].childNodes[0].nodeValue, 'jethro');
    },

    /**
     * Invoking the 'doSay' event handler ought to call a remote method to
     * tell the server that the given text has been said.
     */
    function test_saySomething(self) {
        self.mockNodes['userMessage'].value = 'hello!';
        var d = Divmod.Defer.Deferred();
        var called = false;
        self.chatterWidget.callRemote = function (method, argument) {
            called = true;
            self.assertIdentical(method, "say");
            self.assertIdentical(argument, "hello!");
            return d;
        }
        var eventResult = self.chatterWidget.doSay();
        self.assertIdentical(eventResult, false);
        self.assert(called);
        self.assertIdentical(self.mockNodes['userMessage'].value, '');
    });

