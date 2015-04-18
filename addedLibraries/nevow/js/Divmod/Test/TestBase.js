// -*- test-case-name: nevow.test.test_javascript -*-

/**
 * Tests for Divmod.__init__
 */

// import Divmod.UnitTest

Divmod.Test.TestBase.TestBase = Divmod.UnitTest.TestCase.subclass('TestBase');
Divmod.Test.TestBase.TestBase.methods(

    /**
     * Verify that the Divmod module's bootstrap function sets its '_location'
     * attribute.
     */
    function test_divmodBootstrap(self) {
        var notDivmod = {};
        notDivmod.bootstrap = Divmod.bootstrap;
        var STUFF = "hello there";
        notDivmod.bootstrap(STUFF);
        self.assertIdentical(notDivmod._location, STUFF);
    },

    /**
     * Test L{Divmod.Base.reprString} correctly escapes various whitespace
     * characters.
     */
    function test_reprString(self) {
        var s = '\r\n\f\b\t';
        var repr = Divmod.Base.reprString(s);
        var expected = "\"\\r\\n\\f\\b\\t\"";
        self.assertIdentical(repr, expected);
    },


    /**
     * Trivial JSON serialization test.  Not nearly comprehensive.  This code
     * is going away soon anyway.
     */
    function test_serializeJSON(self) {
        var expr = [{a: 1, b: "2"}];
        var json = Divmod.Base.serializeJSON(expr);
        var expected = "[{\"a\":1, \"b\":\"2\"}]";
        self.assertIdentical(json, expected);
    },


    /**
     * Check that arrays which contain identical elements are considered
     * equal.
     */
    function test_arraysEqualPositive(self) {
        self.assert(Divmod.arraysEqual([], []));
        self.assert(Divmod.arraysEqual([1, 2], [1, 2]));
        var x = {a: 1, b: 2};
        self.assert(Divmod.arraysEqual([x, 3], [x, 3]));
    },


    /**
     * Check that arrays with contain different elements are not
     * considered equal.
     */
    function test_arraysEqualNegative(self) {
        self.assert(!Divmod.arraysEqual([], [null]));
        self.assert(!Divmod.arraysEqual([1], [2]));
        self.assert(!Divmod.arraysEqual({'a': undefined}, {'b': 2}));
        self.assert(!Divmod.arraysEqual(
                        function () { return 1; },
                        function () { return 2; }));
    },


    /**
     * Check that different arrays with missing elements are not considered
     * equal.
     */
    function test_missingElements(self) {
        var a = [];
        var b = [];
        a[3] = '3';
        b[3] = '3';
        b[2] = '2';
        self.assert(!Divmod.arraysEqual(a, b));
    });
