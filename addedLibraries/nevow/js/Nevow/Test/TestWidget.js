// -*- test-case-name: nevow.test.test_javascript.JSUnitTests.test_widget -*-

// import Divmod.UnitTest
// import Nevow.Athena
// import Nevow.Test.Util
// import Nevow.Test.WidgetUtil

Nevow.Test.TestWidget.DummyWidget = Nevow.Athena.Widget.subclass(
    'Nevow.Test.TestWidget.DummyWidget');
Nevow.Test.TestWidget.DummyWidget.methods(
    function onclick(self, event) {
        self.clicked = 'implicitly';
    },

    function explicitClick(self, event) {
        self.clicked = 'explicitly';
    });

Nevow.Test.TestWidget.WidgetTests = Divmod.UnitTest.TestCase.subclass(
    'Nevow.Test.TestWidget.WidgetTests');
Nevow.Test.TestWidget.WidgetTests.methods(
    /**
     * Create a widget for use in each test.
     */
    function setUp(self) {
        self.node = Nevow.Test.WidgetUtil.makeWidgetNode(1);
        self.otherNode = document.createElement("span");
        self.node.appendChild(self.otherNode);
        self.widget = Nevow.Test.TestWidget.DummyWidget(self.node);
        Nevow.Test.WidgetUtil.registerWidget(self.widget);
        self._unmockRDM = Nevow.Test.WidgetUtil.mockTheRDM();
    },

    function tearDown(self) {
        self._unmockRDM();
    },

    /**
     * L{Nevow.Athena.Widget.addChildWidgetFromWidgetInfo}'s deferred should
     * errback if one of the import deferreds does.
     */
    function test_addChildWidgetFromWidgetInfoError(self) {
        var requiredModules = [
            ['test_addChildWidgetFromWidgetInfoError1',
             '/test_addChildWidgetFromWidgetInfoError1']];
        var widgetInfo = {
            requiredModules: requiredModules,
            requiredCSSModules: [],
            id: 'test_addChildWidgetFromWidgetInfoError',
            'class': 'test_addChildWidgetFromWidgetInfoError',
            children: [],
            initArguments: [],
            markup: ''};
        var loadScriptError = new Error(
            'test_addChildWidgetFromWidgetInfoloadScriptError');
        var origLoadScript = Divmod.Runtime.theRuntime.loadScript;
        var loadScript = function loadScript(location) {
            self.assertIdentical(location, requiredModules[0][1]);
            return Divmod.Defer.fail(loadScriptError);
        }
        Divmod.Runtime.theRuntime.loadScript = loadScript;
        try {
            var result = self.widget.addChildWidgetFromWidgetInfo(widgetInfo);
        } finally {
            Divmod.Runtime.theRuntime.loadScript = origLoadScript;
        }
        var theFailure;
        result.addErrback(
            function(err) {
                theFailure = err;
            });
        var firstError = theFailure.check(Divmod.Defer.FirstError);
        self.assertIdentical(firstError.err.error, loadScriptError);
    },

    /**
     * L{Nevow.Athena.Widget.addChildWidgetFromWidgetInfo} should call
     * L{Divmod.Runtime.Platform.loadStylesheet} with each required
     * stylesheet.
     */
    function test_addChildWidgetStylesheets(self) {
        var requiredCSSModules = [
            '/test_addChildWidgetStylesheets1',
            '/test_addChildWidgetStylesheets2'];
        var widgetInfo = {
            requiredModules: [],
            requiredCSSModules: requiredCSSModules,
            id: 'test_addChildWidgetStylesheets',
            'class': 'test_addChildWidgetStylesheets',
            children: [],
            initArguments: [],
            markup: ''};
        var loadedStylesheets = [];
        var origLoadStylesheet = Divmod.Runtime.theRuntime.loadStylesheet;
        var loadStylesheet = function loadStylesheet(location) {
            loadedStylesheets.push(location);
        }
        Divmod.Runtime.theRuntime.loadStylesheet = loadStylesheet;
        try {
            var result = self.widget.addChildWidgetFromWidgetInfo(widgetInfo);
        } finally {
            Divmod.Runtime.theRuntime.loadStylesheet = loadStylesheet;
        }
        self.assertArraysEqual(loadedStylesheets, requiredCSSModules);
    },

    /**
     * Verify that translateNodeId returns a correctly translated id.
     */
    function test_translateNodeId(self) {
        var translatedId = self.widget.translateNodeId('foo');
        self.assert(translatedId == 'athenaid:1-foo');
    },

    /**
     * Verify that connectDOMEvent will connect the appropriate DOM event to
     * the browser, and the default handler method name and node will be the
     * name of the event and the widget's node.
     */
    function test_connectDOMEventDefaults(self) {
        self.widget.connectDOMEvent("onclick");
        self.node.onclick();
        self.assertIdentical(self.widget.clicked, "implicitly");
    },

    /**
     * Verify that connectDOMEvent will connect the appropriate DOM event to
     * the browser, and the explicitly selected handler will be invoked.
     */
    function test_connectDOMEventCustomMethod(self) {
        self.widget.connectDOMEvent("onclick", "explicitClick");
        self.node.onclick();
        self.assertIdentical(self.widget.clicked, "explicitly");
    },

    /**
     * Verify that connectDOMEvent will connect the appropriate DOM event to
     * the browser, and the explicitly selected node will be used.
     */
    function test_connectDOMEventCustomNode(self) {
        self.widget.connectDOMEvent("onclick", "explicitClick", self.otherNode);
        self.otherNode.onclick();
        self.assertIdentical(self.widget.clicked, "explicitly");
    });


Nevow.Test.TestWidget.PageWidgetTests = Divmod.UnitTest.TestCase.subclass(
    'Nevow.Test.TestWidget.PageWidgetTests');

/**
 * Nevow.Athena.PageWidget is the client half of nevow.athena.LivePage.  It
 * handles global, page-level responsibilities in the client, such as serving
 * as the root widget, implementing callRemote for all its widgets by handling
 * and sending messages to a ReliableMessageDelivery, and dealing with
 * connection lost notifications.
 */
Nevow.Test.TestWidget.PageWidgetTests.methods(

    /**
     * Verify that two objects have the same set of attributes, that they are
     * equivalent as dictionaries.
     */
    function assertObjectsEqual(self, obj1, obj2) {
        self.compare(function (a, b) {
            var aattrs = Divmod.dir(a).sort();
            var battrs = Divmod.dir(b).sort();
            self.assertArraysEqual(aattrs, battrs);
            for (var attrname in aattrs) {
                if (a[attrname] !== b[attrname]) {
                    return false;
                }
            }
            return true;
        }, "!~==", obj1, obj2);
    },

    /**
     * Create a PageWidget attached to a fake delivery channel.
     */
    function setUp(self) {
        self.messages = [];
        self.channelClosed = false;
        var fakeRDMFactory = function () {
            var rdm = {
              addMessage: function (msg) {
                    self.messages.push(msg);
                },
              stop: function () {
                    self.channelClosed = true;
                }
            };
            return rdm;
        }
        self.page = Nevow.Athena.PageWidget("fake-livepage-id", fakeRDMFactory);
        Nevow.Test.TestWidget.TEMPORARY_GLOBAL = self;
    },

    function tearDown(self) {
        delete Nevow.Test.TestWidget.TEMPORARY_GLOBAL;
    },

    /**
     * The 'respond' action should look up a Deferred in the remoteCalls
     * object and delete it.
     */
    function test_respondAction(self) {
        var OPAQUE_ID = "opaque test remote call id";
        var RESULT = "opaque test result";
        var d = Divmod.Defer.Deferred();
        var innerResult = null;
        d.addCallback(function (result) {
            innerResult = result;
        });
        self.page.remoteCalls[OPAQUE_ID] = d;
        self.page.action_respond(OPAQUE_ID, true, RESULT);
        self.assert(!(OPAQUE_ID in self.page.remoteCalls));
        self.assertIdentical(innerResult, RESULT);
    },

    /**
     * Test that the 'noop' action does nothing, so the server can ping us.
     */
    function test_noopAction(self) {
        self.page.action_noop();
    },

    /**
     * A test for a call action.
     *
     * @param toReturn: a 2-arg function which takes the expected return value
     * and may return it, raise an exception, or return a Deferred that wraps
     * it (or fails).  The second argument to is is a 1-arg function which
     * changes the return value to expect.
     *
     * @param: expectSuccess: a boolean, whether the test should expect the
     * method to succeed.
     */
    function callActionTest(self, toReturn, expectSuccess) {
        var innerThis = null;
        var innerArg = null;
        var TEST_ARG = "test argument";
        var OPAQUE_ID = 'opaque-identifier';
        var RESULT = 'resulting value';
        var expected = RESULT;
        self.tempMethod = function (arg) {
            innerThis = this;
            innerArg = arg;
            return toReturn(RESULT, function (arg) {
                expected = arg;
            });
        };
        self.page.action_call(
            'Nevow.Test.TestWidget.TEMPORARY_GLOBAL.tempMethod',
            OPAQUE_ID, [TEST_ARG]);
        self.assertIdentical(innerArg, TEST_ARG);
        self.assertIdentical(innerThis, self);
        var msg = self.messages[0];
        var args = msg[1];
        self.assertIdentical(msg[0], "respond");
        self.assertArraysEqual(args, [OPAQUE_ID, expectSuccess, expected]);
    },

    /**
     * The 'call' action should invoke a given global function and return its
     * value to the server along with a flag indicating it succeed by adding a
     * new message.
     */
    function test_callAction(self) {
        self.callActionTest(function (value) {
            return value;
        }, true);
    },

    /**
     * The 'call' action should invoke a given global function and, if that
     * function raises an exception, serialize that exception along with a
     * flag indicating it failed by adding a new message.
     */
    function test_callActionFail(self) {
        self.callActionTest(function (value, expect) {
            var e = new Error();
            expect(e);
            throw e;
        }, false);
    },

    /**
     * The 'call' action should invoke a given global function and return the
     * result of its deferred to the server along with a flag indicating it
     * succeed by adding a new message.
     */
    function test_callActionDeferred(self) {
        self.callActionTest(function (value, expect) {
            var d = Divmod.Defer.succeed(value);
            expect(value);
            return d;
        }, true);
    },

    /**
     * The 'call' action should invoke a given global function and return the
     * failure from its deferred to the server along with a flag indicating it
     * failed by adding a new message.
     */
    function test_callActionDeferredFail(self) {
        self.callActionTest(function (value, expect) {
            var e = new Error();
            expect(e);
            return Divmod.Defer.fail(e);
        }, false);
    },

    /**
     * The 'close' action should stop the reliable message delivery channel.
     */
    function test_closeAction(self) {
        self.page.action_close();
        self.assertIdentical(self.channelClosed, true);
    },

    /**
     * PageWidget ought to send a message to the PageWidget's reliable message
     * delivery channel when a remote reference that addresses it sends a
     * message.
     */
    function test_pageCallRemote(self) {
        var ref = Nevow.Athena.RemoteReference(1234, self.page);
        var d = ref.callRemote("testMethod", 5, 7, 9);
        // Format of the message is ['call', [requestId, method, objectID, args, kwargs]]
        // See Python's action_call
        self.assertIdentical(self.messages.length, 1);
        self.assertIdentical(self.messages[0].length, 2);
        self.assertIdentical(self.messages[0][0], "call");
        self.assertIdentical(self.messages[0][1].length, 5);
        self.assertIdentical(self.messages[0][1][0], "c2s0"); // requestId starts at 0.
        self.assertIdentical(self.messages[0][1][1], "testMethod");
        self.assertIdentical(self.messages[0][1][2], 1234);
        self.assertArraysEqual(self.messages[0][1][3], [5, 7, 9]);
        self.assertObjectsEqual(self.messages[0][1][4], {});

        // Verify that the Deferred is waiting.
        self.assertIdentical(self.page.remoteCalls["c2s0"], d);
    });

Nevow.Test.TestWidget.SetupTests = Divmod.UnitTest.TestCase.subclass(
    'Nevow.Test.TestWidget.SetupTests');

/**
 * Test things about the page state that Athena needs to set up in order to
 * function properly.
 */
Nevow.Test.TestWidget.SetupTests.methods(

    /**
     * Replace the 'window' object so the tests can inspect it easily.
     */
    function setUp(self) {
        self.faker = Nevow.Test.Util.Faker();
        self.closeMessageSent = false;
        self.page = Nevow.Athena.PageWidget(
            "asdf", function (page) {
                return self;
            });
    },

    /**
     * Mock the ReliableMessageDelivery.sendCloseMessage method by setting a
     * flag to verify that it was called.
     */
    function sendCloseMessage(self) {
        self.closeMessageSent = true;
        self.page.connectionLost();
    },

    /**
     * Put back all the fakes.
     */
    function tearDown(self) {
        self.faker.stop();
    },

    /**
     * Verify that the page's onbeforeunload event handler will set the
     * pageUnloaded attribute and invoke the delivery channel's fast-path
     * instant teardown.
     */
    function test_onbeforeunload(self) {
        self.assertIdentical(self.page.pageUnloaded, false);
        var disconnectDialogShown = false;
        self.page.showDisconnectDialog = function () {
            disconnectDialogShown = true;
        };
        self.page.onbeforeunload();
        self.assertIdentical(self.page.pageUnloaded, true);
        self.assertIdentical(self.closeMessageSent, true);
        // This should not show the disconnect dialog; onbeforeunload is a
        // "clean" disconnect.
        self.assertIdentical(disconnectDialogShown, false);

    },

    /**
     * The 'Escape' key's default behavior in Firefox is to kill the outgoing
     * connection immediately.  If the user does this 3 times, it will cancel
     * 3 output channels, which will cause the Athena connection to die.
     *
     * When we receive such an event on the top-level window, cancel it so
     * that the connections will not be affected, but do not otherwise alter
     * the event, so that users can handle keys as they see fit.
     */
    function test_escapeCancelsDefault(self) {
        var fakeEvt = self._fakeEvent(Nevow.Athena.KEYCODE_ESCAPE);
        var result = self.page.onkeypress(fakeEvt);
        self.assertIdentical(fakeEvt.cancelBubble, false);
        self.assertIdentical(result, true);
        self.assert(fakeEvt.prevented, "Did not prevent default behavior.");
    },

    /**
     * Create a fake event object.
     */
    function _fakeEvent(self, keyCode) {
        var evt = {
          prevented: false,
          keyCode: keyCode,
          cancelBubble: false,
          stopPropagation: function () {
                self.fail("Should not stop propagation.")
            },
          preventDefault: function () {
                evt.prevented = true;
            }
        };
        return evt;
    },

    /**
     * Functions registered with 'notifyOnDisconnect' should be invoked when
     * the page is disconnected.
     */
    function test_notifyOnDisconnect(self) {
        var called = 0;
        var arg = 0;
        var thunk = {};
        self.faker.fake('page', self.page, Nevow.Athena);
        Nevow.Athena.notifyOnDisconnect(function (inarg) {
            called++;
            arg = inarg;
        });
        self.assertIdentical(called, 0);
        self.page.connectionLost(thunk);
        self.assertIdentical(called, 1);
        self.assertIdentical(arg, thunk);
        self.page.connectionLost();
        self.assertIdentical(called, 1);
    },

    /**
     * The 'escape' key handler should not modify the event in any way, it
     * should simply return true.
     */
    function test_nonEscapeKeyDoesNothing(self) {
        var NOT_ESCAPE = 1234;
        var fakeEvt = self._fakeEvent(NOT_ESCAPE);
        var result = self.page.onkeypress(fakeEvt);
        self.assertIdentical(fakeEvt.cancelBubble, false);
        self.assertIdentical(result, true);
        self.assert(!fakeEvt.prevented, "Prevented default behavior.");
    },

    /**
     * Verify that the window's top-level key-press handler is installed.  See
     * test_escapeCancelsDefault for an explanation of why we need to do this.
     */
    function test_registeredKeyPress(self) {
        var NOT_ESCAPE = 1234;
        var fakeEvt = self._fakeEvent(NOT_ESCAPE);
        self.window = {};
        self.called = false;
        self.page.onkeypress = function () {
            self.called = true;
        };
        Divmod.Base.addToCallStack(
            self.window, 'onkeypress', self.page.makeHandler('onkeypress'));
        self.window.onkeypress(fakeEvt);
        self.assert(self.called, "Key not bound.")
    });
