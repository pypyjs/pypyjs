// -*- test-case-name: nevow.test.test_howtolistings -*-

/**
 * This test case is for the EchoWidget module under part00 of the Nevow/Athena chat tutorial.
 */

// import Divmod.UnitTest
// import Divmod.Defer
// import Nevow.Test.WidgetUtil
// import EchoThing

Nevow.Test.TestHowtoListing00.TestableEchoWidget = EchoThing.EchoWidget.subclass(
    "Nevow.Test.TestHowtoListing00.TestableEchoWidget");

/**
 * Provide a testable version of the widget with less coupling with the
 * runtime and DOM.  (This should only override Athena methods, not methods
 * defined in EchoWidget itself, as that would be self-defeating.)
 */
Nevow.Test.TestHowtoListing00.TestableEchoWidget.methods(
    /**
     * Provide a mocked constructor which allows us to refer to a test case
     * from mock methods.
     */

    function __init__(self, node, testCase) {
        self.testCase = testCase;
        return Nevow.Test.TestHowtoListing00.TestableEchoWidget.upcall(self, "__init__", node);
    },
    /**
     * Provide a mocked version of nodeByAttribute which doesn't require
     * runtime features (such as XPath).
     */
    function nodeByAttribute(self, attribute, value) {
        return self.testCase.mockNodes[value];
    });

Nevow.Test.TestHowtoListing00.TestHowtoListing00 = Divmod.UnitTest.TestCase.subclass(
    'Nevow.Test.TestHowtoListing00.TestHowtoListing00');

Nevow.Test.TestHowtoListing00.TestHowtoListing00.methods(

    /**
     * Set up the tests to run.
     */
    function setUp(self) {
        self.node = Nevow.Test.WidgetUtil.makeWidgetNode();
        self.mockNodes = {};
        self.mockNodes["scrollArea"] = document.createElement("div");
        self.mockNodes['echoBox'] = document.createElement('div');
        self.mockNodes['message'] = document.createElement('input');

        self.echoWidget = Nevow.Test.TestHowtoListing00.TestableEchoWidget(self.node, self);
    },

    /**
     * Verify that the 'echo' function will manipulate the scrolling area in a
     * way which is visible to the user.
     */
    function test_echo(self) {
        var mockScroll = self.mockNodes['scrollArea'];
        self.echoWidget.addText("hello!");
        self.assertIdentical(mockScroll.childNodes.length, 1);
        self.assertIdentical(mockScroll.childNodes[0].nodeType, document.ELEMENT_NODE);
        self.assertIdentical(mockScroll.childNodes[0].childNodes.length, 1);
        self.assertIdentical(mockScroll.childNodes[0].childNodes[0].nodeValue, "hello!");
    },

    /**
     * Invoking the 'doSay' event handler ought to call a remote method to
     * tell the server that the given text has been said.
     */
    function test_saySomething(self) {
        self.mockNodes['message'].value = 'hello!';
        var d = Divmod.Defer.Deferred();
        var called = false;
        self.echoWidget.callRemote = function (method, argument) {
            called = true;
            self.assertIdentical(method, "say");
            self.assertIdentical(argument, "hello!");
            return d;
        }
        var eventResult = self.echoWidget.doSay();
        self.assertIdentical(eventResult, false);
        self.assert(called);
        self.assertIdentical(self.mockNodes['message'].value, '');
    });
