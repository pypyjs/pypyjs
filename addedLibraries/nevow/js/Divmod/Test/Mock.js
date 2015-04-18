/**
 * L{Divmod.UnitTest.TestCase}s that are used by L{Divmod.Test.TestUnitTest}
 * in order to test the unit testing framework.
 */

// import Divmod.UnitTest

/**
 * L{TestCase} subclass that we use as the primary subject of our tests in
 * L{TestCaseTest}.
 *
 * L{_WasRun} mostly just keeps track of which methods were called on it.
 */
Divmod.Test.Mock._WasRun = Divmod.UnitTest.TestCase.subclass('Divmod.Test.Mock._WasRun');
Divmod.Test.Mock._WasRun.methods(
    function __init__(self, methodName) {
        self.log = "";
        Divmod.Test.Mock._WasRun.upcall(self, '__init__', methodName);
    },

    function setUp(self) {
        self.log += 'setUp ';
    },

    function test_good(self) {
        self.log += 'test ';
    },

    function test_bad(self) {
        self.fail("fail this test deliberately");
    },

    function test_error(self) {
        throw Divmod.Error("error");
    },

    function tearDown(self) {
        self.log += 'tearDown';
    });



Divmod.Test.Mock._BadSetUp = Divmod.UnitTest.TestCase.subclass('Divmod.Test.Mock._BadSetUp');
Divmod.Test.Mock._BadSetUp.methods(
    function __init__(self, methodName) {
        self.log = "";
        Divmod.Test.Mock._BadSetUp.upcall(self, '__init__', methodName);
    },

    function setUp(self) {
        self.fail("failed setup");
    },

    function test_method(self) {
        self.log += 'test_method ';
    },

    function tearDown(self) {
        self.log += 'tearDown';
    });



Divmod.Test.Mock._BadTearDown = Divmod.UnitTest.TestCase.subclass('Divmod.Test.Mock._BadTearDown');
Divmod.Test.Mock._BadTearDown.methods(
    function __init__(self, methodName) {
        self.log = "";
        Divmod.Test.Mock._BadTearDown.upcall(self, '__init__', methodName);
    },

    function setUp(self) {
        self.log += "setUp ";
    },

    function test_method(self) {
        self.log += 'test_method ';
    },

    function tearDown(self) {
        self.fail('deliberate fail in tearDown');
    });
