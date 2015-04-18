// -*- test-case-name: nevow.test.test_javascript.JSUnitTests.test_rdm -*-

// import Divmod
// import Divmod.UnitTest
// import Divmod.Defer
// import Divmod.Test.TestRuntime
// import Nevow.Athena
// import Nevow.Test.Util

Nevow.Test.TestMessageDelivery.ReliableMessageDeliveryTests = Divmod.UnitTest.TestCase.subclass(
    "Nevow.Test.TestMessageDelivery.ReliableMessageDeliveryTests");

Nevow.Test.TestMessageDelivery.ReliableMessageDeliveryTests.methods(
    /**
     * Create a ReliableMessageDelivery with a mock output factory and
     * connection lost notification that record the associated information
     * with the calls on this test case.
     */
    function setUp(self) {
        self.requests = [];
        self.lostConnection = false;
        self.fakePage = {
          connectionLost: function () {
                self.lostConnection = true;
            }
        };
        self.channel = Nevow.Athena.ReliableMessageDelivery(
            function (synchronous) {
                if (synchronous === undefined) {
                    synchronous = false;
                }
                var d = Divmod.Defer.Deferred();
                var output = {
                  send: function (ack, messages) {
                        var theReq = {
                          // things expected by interface
                          abort: function () {
                                this.aborted = true;
                            },
                          deferred: d,
                          aborted: false,
                          // things we want to check on
                          synchronous: synchronous,
                          ack: ack,
                          messages: messages.slice()
                        };
                        self.requests.push(theReq);
                        return theReq;
                    }
                };
                return output;
            },
            self.fakePage);
    },

    /**
     * Verify that starting the channel sets the 'running' attribute to true,
     * and will make an outgoing request with no payload.  This request is
     * provided so that the server can send notifications.
     */
    function test_startChannel(self) {
        // Sanity check.
        self.assertIdentical(self.requests.length, 0);
        self.assertIdentical(self.channel.running, false);
        self.channel.start();
        self.assertIdentical(self.channel.running, true);
        self.assertIdentical(self.requests.length, 1);
        var r = self.requests[0];
        self.assertArraysEqual(r.messages, []);
    },

    /**
     * Verify that adding a message to a ReliableMessageDelivery will make an
     * outgoing request that will be queued until that request completes
     * successfully.
     */
    function test_addMessage(self) {
        self.channel.start();
        var MESSAGE = "A message that the test is sending";
        self.channel.addMessage(MESSAGE);

        self.assertIdentical(self.requests.length, 2);
        var r = self.requests[1];
        self.assertIdentical(r.messages.length, 1);
        self.assertArraysEqual(r.messages[0], [0, MESSAGE]);
        self.assertIdentical(self.channel.messages.length,
                             1);
        self.assertArraysEqual(self.channel.messages[0], [0, MESSAGE]);
        // Now, have the server acknowledge the message in a noop.
        r.deferred.callback([0, [[0, ["noop", []]]]]);
        self.assertArraysEqual(self.channel.messages, []);
        // Only the "live" connection should remain.
        self.assertArraysEqual(self.channel.requests, [self.requests[0]]);
    },

    /**
     * When the server answers the last outstanding request, the reliable
     * message delivery should create a new one.
     */
    function test_answeringLastRequest(self) {
        self.channel.start();
        self.requests[0].deferred.callback([-1, [[0, ["noop", []]]]]);
        self.assertIdentical(self.requests.length, 2);
        self.assertIdentical(self.channel.requests.length, 1);
    },

    /**
     * Verify that messages from the server are sent to an action_ method on
     * the page object associated with the delivery channel.
     */
    function test_messageDispatch(self) {
        self.channel.start();
        var checkA = 3;
        var checkB = "stuff";
        var checkC = {other: "stuff"};
        var called = true;
        var gotA = null;
        var gotB = null;
        var gotC = null;
        var checkThis = null;
        self.fakePage.action_testaction = function (a, b, c) {
            checkThis = this;
            gotA = a;
            gotB = b;
            gotC = c;
        }
        self.requests[0].deferred.callback(
            [-1, [[0, ["testaction", [checkA, checkB, checkC]]]]]);
        self.assertIdentical(gotA, checkA);
        self.assertIdentical(gotB, checkB);
        self.assertIdentical(gotC, checkC);
        self.assertIdentical(checkThis, self.fakePage);
    },

    /**
     * Messages with the same sequence number should only be processed once.
     */
    function test_sequenceChecking(self) {
        var dupcount = 0;
        self.fakePage.action_duplicate = function () {
            dupcount++;
        };
        self.channel.messageReceived([[0, ["duplicate", []]]]);
        self.assertIdentical(dupcount, 1);
        self.channel.messageReceived([[0, ["duplicate", []]]]);
        self.assertIdentical(dupcount, 1);
        self.channel.messageReceived([[1, ["duplicate", []]]]);
        self.assertIdentical(dupcount, 2);
    },

    /**
     * When the reliable message delivery channel is closed, it must be done
     * in a few steps:
     *
     *  - terminate all current asynchronous reqeusts
     *    (The page would shut them down in a moment anyway, and forcing them
     *    to tear down while the environment is still under our control will
     *    allow everything to shut down gracefully, and will, for example,
     *    avoid tickling bugs in firebug.)
     *
     * - make one synchronous request containing a single message telling the
     *   server that the connection has been terminated.
     *
     * This technique is documented here:
     *
     * http://www.hunlock.com/blogs/Mastering_The_Back_Button_With_Javascript#quickIDX6
     *
     * This is really sub-optimal, and we shouldn't *need* any page tear-down
     * at all; the message queue should be structured such that the server can
     * notice connections have gone away.
     */
    function test_sendCloseMessage(self) {
        self.channel.start();
        self.channel.addMessage("message1");
        self.channel.sendCloseMessage();
        self.assertIdentical(self.lostConnection, true);
        self.assertIdentical(self.requests.length, 3);
        // created by 'start'
        self.assertIdentical(self.requests[0].synchronous, false);
        self.assertIdentical(self.requests[0].aborted, true);
        // created by 'message1'
        self.assertIdentical(self.requests[1].synchronous, false);
        self.assertIdentical(self.requests[1].aborted, true);
        // created by 'sendCloseMessage'
        self.assertIdentical(self.requests[2].synchronous, true);
        self.assertIdentical(self.requests[2].aborted, false);
        self.assertIdentical(self.requests[2].ack, -1);
        // Check for the special sequence number
        self.assertIdentical(self.requests[2].messages[0][0], "unload");
        // the command
        self.assertIdentical(self.requests[2].messages[0][1][0], "close");
        // the command's arguments
        self.assertArraysEqual(self.requests[2].messages[0][1][1], []);
    });

/**
 * Tests to ensure that global state is set up properly.
 */
Nevow.Test.TestMessageDelivery.GlobalSetupTests = Divmod.UnitTest.TestCase.subclass(
    "Nevow.Test.TestMessageDelivery.GlobalSetupTests");

Nevow.Test.TestMessageDelivery.GlobalSetupTests.methods(

    function setUp(self) {
        self.faker = Nevow.Test.Util.Faker();
    },

    function tearDown(self) {
        self.faker.stop();
    },

    /**
     * Verify that the _createMessageDelivery function takes a PageWidget and
     * creates a MessageDelivery object that creates HTTPRequestOutput objects
     * for its outputFactory, and will invoke Nevow.Athena._connectionLost
     * when its connection is lost.
     */
    function test_defaultMessageDelivery(self) {
        self.faker.fake("window", {location: "http://unittest.example.com/"});
        var fakePage = Nevow.Athena.PageWidget("fake-widget-id",
                                               Nevow.Athena._createMessageDelivery);
        var testRDM = fakePage.deliveryChannel;
        var asyncfactory = testRDM.outputFactory();
        self.assert(asyncfactory instanceof Nevow.Athena.HTTPRequestOutput);
        self.assertIdentical(asyncfactory.synchronous, false);
        var syncfactory = testRDM.outputFactory(true);
        self.assertIdentical(syncfactory.synchronous, true);
        self.assertIdentical(testRDM.page, fakePage);
    },

    /**
     * Verify that the HTTPRequestOutput sends the appropriate request via the
     * runtime.
     */
    function test_outputSend(self) {
        var reqs = [];
        self.faker.fake("makeHTTPRequest",
                         function () {
                             var fr = Divmod.Test.TestRuntime.FakeRequest();
                             reqs.push(fr);
                             return fr;
                         },
                         Divmod.Runtime.theRuntime);
        var reqOut = Nevow.Athena.HTTPRequestOutput(
            "http://unittest.example.com/",
            [["test", "arg"]],
            [['header', 'value']],
            true);
        reqOut.send(5, ["hello"]);
        self.assertIdentical(reqs.length, 1);
        self.assertArraysEqual(reqs[0].opened, ["POST", "http://unittest.example.com/?test=arg", false]);
        self.assertArraysEqual(reqs[0].sent, ['[5, ["hello"]]']);
    });
