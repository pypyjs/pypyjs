/**
 * Tests for Divmod.Inspect
 */

// import Divmod.UnitTest
// import Divmod.Inspect


Divmod.Test.TestInspect.TestInspect = Divmod.UnitTest.TestCase.subclass('TestInspect');
Divmod.Test.TestInspect.TestInspect.methods(
    /**
     * Test that L{Divmod.Inspect.methods} returns all the methods of a class
     * object.
     */
    function test_methods(self) {

        /* Divmod.Class has no visible toString method for some reason.  If this
         * ever changes, feel free to change this test.
         */
        self.assertArraysEqual(Divmod.Inspect.methods(Divmod.Class),
                               ["__init__"]);

        var TestClass = Divmod.Class.subclass("test_inspect.test_methods.TestClass");
        TestClass.methods(function method() {});

        /* Subclasses get two methods automagically, __init__ and toString.  If
         * this ever changes, feel free to change this test.
         */
        self.assertArraysEqual(Divmod.Inspect.methods(TestClass),
                               ["__init__", "method", "toString"]);


        var TestSubclass = TestClass.subclass("test_inspect.test_methods.TestSubclass");
        TestSubclass.methods(function anotherMethod() {});

        self.assertArraysEqual(Divmod.Inspect.methods(TestSubclass),
                               ["__init__", "anotherMethod", "method",
                                "toString"]);
    },


    /**
     * Test that an appropriate exception is raised if the methods of an instance
     * are requested.
     */
    function test_methodsAgainstInstance(self) {
        var msg = "Only classes have methods.";
        var error;

        error = self.assertThrows(
            Error,
            function() {
                return Divmod.Inspect.methods([]);
            });
        self.assertIdentical(error.message, msg);

        error = self.assertThrows(
            Error,
            function() {
                return Divmod.Inspect.methods({});
            });
        self.assertIdentical(error.message, msg);

        error = self.assertThrows(
            Error,
            function() {
                return Divmod.Inspect.methods(0);
            });
        self.assertIdentical(error.message, msg);

        error = self.assertThrows(
            Error,
            function() {
                return Divmod.Inspect.methods("");
            });
        self.assertIdentical(error.message, msg);

        error = self.assertThrows(
            Error,
            function() {
                return Divmod.Inspect.methods(Divmod.Class());
            });
        self.assertIdentical(error.message, msg);
    });
