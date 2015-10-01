//
// run_unittest_tests.js
//
// Run the PyPy.js "unittest" module's unit tests in Node.
//

// NOTE: there are two halfexpected failures (see below)


require("./lib/pypyjs.js");


var test_files = [
    "modules/unittest/test/test_assertions.py",
    // "modules/unittest/test/test_break.py",  // NOTE: see below about os.kill
    "modules/unittest/test/test_case.py",
    "modules/unittest/test/test_discovery.py",
    "modules/unittest/test/test_functiontestcase.py",
    "modules/unittest/test/test_loader.py",  // NOTE: see below about "loader failures"
    "modules/unittest/test/test_program.py",
    "modules/unittest/test/test_result.py",
    "modules/unittest/test/test_runner.py",
    "modules/unittest/test/test_setups.py",
    "modules/unittest/test/test_skipping.py",
    "modules/unittest/test/test_suite.py"
];


pypyjs.ready().then(function() {
    for (var file of test_files) {
        pypyjs.execfile(file).catch(console.error);
    }
});


/* NOTE about os.kill:
 * The "test_break.py" file tests that the "unittest" module responds correctly to Unix signals.
 * We don't have those on PyPy.js, so the tests aren't relevant. Yet the "os" module does have a
 * "kill" attribute at the moment, so the tests' auto-skip mechanism doesn't work.
 */

/* NOTE about loader failures:
 * The "test_loader.py" module is for the TestLoader class. For a reason I don't know, two tests
 * fail for me under PyPy.js... but they also seem to fail under CPython 2, CPython 3, and native
 * PyPy 2.4 and 2.6. Not sure what's going on here, but it doesn't seem to inhibit anything.
 */
