/**
 * Tests for LiveTrial
 */

// import Divmod.UnitTest
// import Nevow.Athena.Test


Divmod.Test.TestLivetrial.TestLivetrial = Divmod.UnitTest.TestCase.subclass('TestLivetrial');
Divmod.Test.TestLivetrial.TestLivetrial.methods(
    function makeTestCase(self) {
        var testCase = {};
        testCase.__class__ = {};
        testCase.__class__.__name__ = 'testcasename';
        return testCase;
    },


    /**
     * Test running a test with L{Nevow.Athena.Test._TestMethod}.  This only tests
     * that the method is invoked and that startTest and stopTest are called on the
     * reporter.
     */
    function test_testMethod(self) {
        var runArgs = null;
        var runThis = null;
        var testCase = self.makeTestCase();

        testCase.method = function() {
            self.assertIdentical(runArgs, null, "Test case test method called more than once.");
            runArgs = arguments;
            runThis = this;
        };

        var method = Nevow.Athena.Test._TestMethod(testCase, 'method');
        self.assertIdentical(method.fullyQualifiedName, 'testcasename.method');

        var reporter = {};
        var started = false;
        reporter.startTest = function(testMethod) {
            self.assertIdentical(testMethod, method, "Test method passed to startTest was wrong.");
            started = true;
        };

        var stopped = false;
        reporter.stopTest = function(testMethod) {
            self.assertIdentical(testMethod, method, "Test method passed to stopTest was wrong.");
            stopped = true;
        };

        reporter.addSuccess = function() {};
        reporter.addFailure = function() {};

        method.run(reporter);

        self.assert(runArgs != null, "Test method not actually run.");
        self.assert(started, "Reporter was never told the test started.");
        self.assert(stopped, "Reporter was never told the test stopped.");

        self.assertIdentical(runArgs.length, 0, "Wrong number of arguments passed to run().");
        self.assertIdentical(runThis, testCase, "Wrong execution context when calling run().");
    },


    /**
     * Test that a synchronously succeeding test results in addSuccess being invoked.
     */
    function test_testMethodSynchronousSuccessReporting(self) {
        var testCase = self.makeTestCase();
        var success = null;

        testCase.method = function() {
            /*
             * We don't have to do anything in order to succeed.
             */
        };

        var method = Nevow.Athena.Test._TestMethod(testCase, 'method');
        var reporter = {};
        reporter.startTest = function() {};
        reporter.stopTest = function() {};
        reporter.addSuccess = function(testCase) {
            success = testCase;
        };

        method.run(reporter);

        self.assertIdentical(success, method,
                             "Test method not passed to addSuccess().");
    },


    /**
     * Test that an asynchronously succeeding test results in addSuccess being
     * invoked.
     */
    function test_testMethodAsynchronousSuccessReporting(self) {
        var testCase = self.makeTestCase();
        var success = null;
        var resultDeferred = Divmod.Defer.Deferred();

        testCase.method = function() {
            return resultDeferred;
        };

        var method = Nevow.Athena.Test._TestMethod(testCase, 'method');
        var reporter = {};
        reporter.startTest = function() {};
        reporter.stopTest = function() {};
        reporter.addSuccess = function(testCase) {
            success = testCase;
        };

        method.run(reporter);

        self.assertIdentical(success, null, "addSuccess() called too early.");

        resultDeferred.callback(null);

        self.assertIdentical(success, method,
                             "Test method not passed to addSuccess().");
    },


    /**
     * Test that a synchronously failing test results in addFailure being invoked.
     */
    function test_testMethodSynchronousFailureReporting(self) {
        var testCase = self.makeTestCase();
        var failure = null;

        testCase.method = function() {
            throw new Error("Test failure");
        };

        var method = Nevow.Athena.Test._TestMethod(testCase, 'method');
        var reporter = {};
        reporter.startTest = function() {};
        reporter.stopTest = function() {};
        reporter.addFailure = function(testCase) {
            failure = testCase;
        };

        method.run(reporter);

        self.assertIdentical(failure, method, "Test method not passed to addFailure().");
    },


    /**
     * Test that an asynchronously failing test results in addFailure being
     * invoked.
     */
    function test_testMethodAsynchronousFailureReporting(self) {
        var testCase = self.makeTestCase();
        var failure = null;
        var resultDeferred = Divmod.Defer.Deferred();

        testCase.method = function() {
            return resultDeferred;
        };

        var method = Nevow.Athena.Test._TestMethod(testCase, 'method');
        var reporter = {};
        reporter.startTest = function() {};
        reporter.stopTest = function() {};
        reporter.addFailure = function(testCase, error) {
            failure = testCase;
        };

        method.run(reporter);

        self.assertIdentical(failure, null, "addFailure() called too early.");

        resultDeferred.errback(new Error("Test failure"));

        self.assertIdentical(failure, method, "Test method not passed to addFailure().");
    },


    function test_testCaseMethods(self) {
        var TestCase = Nevow.Athena.Test.TestCase.subclass('test_livetrial.test_testCaseMethods');
        TestCase.methods(

            /* Override this to avoid doing anything with nodes, which we cannot do
             * in this test harness.
             */
            function __init__() {},

            /* Define a few methods, some of which should be picked up by
             * getTestMethods().
             */
            function test_foo() {},
            function test_bar() {},
            function mumble() {});

        var testCaseInstance = TestCase({});

        var expected = ['test_bar', 'test_foo'];
        var methods = testCaseInstance.getTestMethods();
        methods.sort();
        for(var i=0; i<methods.length; ++i) {
            self.assert(methods[i] instanceof Nevow.Athena.Test._TestMethod);
            self.assertIdentical(methods[i].testMethodName, expected[i]);
        }
        self.assertIdentical(methods.length, expected.length);
    });
