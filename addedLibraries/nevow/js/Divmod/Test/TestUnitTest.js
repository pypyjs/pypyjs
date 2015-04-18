// -*- test-case-name: nevow.test.test_javascript -*-

/**
 * Tests for Divmod.UnitTest, the Javascript unit-testing framework.
 * Uses mock test cases provided by Divmod.Test.Mock.
 */

// import Divmod.UnitTest
// import Divmod.Test.Mock
/* DON'T load Divmod.MockBrowser; it should be imported implicitly. */


/**
 * A mock L{TestResult} object that we use to test that L{startTest} and L{stopTest}
 * are called appropriately.
 */
Divmod.Test.TestUnitTest.MockResult = Divmod.Class.subclass('Divmod.Test.TestUnitTest.MockResult');
Divmod.Test.TestUnitTest.MockResult.methods(
    function __init__(self) {
        self.log = '';
    },

    function startTest(self, test) {
        self.log += 'startTest ' + test.id();
    },

    function addSuccess(self, test) {
        self.log += ' addSuccess ' + test.id();
    },

    function stopTest(self, test) {
        self.log += ' stopTest ' + test.id();
    });



/**
 * Tests for assertions in L{Divmod.UnitTest.TestCase}.
 */
Divmod.Test.TestUnitTest.AssertionTests = Divmod.UnitTest.TestCase.subclass('Divmod.Test.TestUnitTest.AssertionTests');
Divmod.Test.TestUnitTest.AssertionTests.methods(
    /**
     * Test that L{assert} raises an exception if its expression is false.
     */
    function test_assert(self) {
        self.assertThrows(Divmod.UnitTest.AssertionError,
                          function () { self.assert(false, "message"); })
    },

    /**
     * Verify that isTestCaseClass returns a positive result for TestCase
     * subclasses and a negative result for other types of object.
     */

    function test_isTestCaseClass(self) {
        self.assertIdentical(
            true, Divmod.UnitTest.isTestCaseClass(
                Divmod.Test.TestUnitTest.AssertionTests));
        self.assertIdentical(
            false, Divmod.UnitTest.isTestCaseClass(
                Divmod.Test.TestUnitTest.AssertionTests()));
        self.assertIdentical(
            false, Divmod.UnitTest.isTestCaseClass(1));
    },


    /**
     * Test that L{assertThrows} doesn't raise an exception if its callable
     * raises the excepted error.
     */
    function test_assertThrowsPositive(self) {
        try {
            self.assertThrows(Divmod.UnitTest.AssertionError,
                              function () {
                                  throw Divmod.UnitTest.AssertionError();
                              });
        } catch (e) {
            self.fail("assertThrows should have passed: " + e.message);
        }
    },


    /**
     * Test that L{assertThrows} raises an exception if its callable does
     * I{not} raise an exception.
     */
    function test_assertThrowsNoException(self) {
        var raised = true;
        try {
            self.assertThrows(Divmod.UnitTest.AssertionError,
                              function () { });
            raised = false;
        } catch (e) {
            if (!(e instanceof Divmod.UnitTest.AssertionError)) {
                self.fail("assertThrows should have thrown AssertionError");
            }
        }
        if (!raised) {
            self.fail("assertThrows did not raise an error");
        }
    },


    /**
     * Test that L{assertThrows} raises an exception if its callable raises
     * the wrong kind of exception.
     */
    function test_assertThrowsWrongException(self) {
        var raised = true;
        try {
            self.assertThrows(Divmod.UnitTest.AssertionError,
                              function () { throw Divmod.IndexError(); });
            raised = false;
        } catch (e) {
            if (!(e instanceof Divmod.UnitTest.AssertionError)) {
                self.fail("assertThrows should have thrown AssertionError");
            }
        }
        if (!raised) {
            self.fail("assertThrows did not raise an error");
        }
    },


    /**
     * L{assertThrows} passes additional varargs to C{callable}.
     */
    function test_assertThrowsVarargs(self) {
        var args = [];
        function foo(a, b, c) {
            args.push(a);
            args.push(b);
            args.push(c);
            throw Divmod.UnitTest.AssertionError();
        }

        var expectedArgs = [1, 'two', [3, 3, 3]];
        try {
            self.assertThrows(
                Divmod.UnitTest.AssertionError,
                foo,
                expectedArgs[0],
                expectedArgs[1],
                expectedArgs[2]);
        } catch (e) {
            self.fail("assertThrows should have passed: " + e.message);
        }
        self.assertArraysEqual(args, expectedArgs);
    },


    /**
     * Test that L{compare} does not raise an exception if its callable
     * returns C{true}.
     */
    function test_comparePositive(self) {
        self.compare(function () { return true; });
    },


    /**
     * Test that L{compare} raises an error if its callable returns C{false}.
     */
    function test_compareNegative(self) {
        self.assertThrows(Divmod.UnitTest.AssertionError,
                          function () {
                              self.compare(
                                  function (a, b) { return a === b; },
                                  "!==", "a", "b");
                          });
    },


    /**
     * Test that the message of L{compare}'s AssertionError describes the
     * failed the comparison based on its parameters.
     */
    function test_compareDefaultMessage(self) {
        try {
            self.compare(function () {return false;}, "<->", "a", "b");
        } catch (e) {
            self.assertIdentical(e.message, '"a" <-> "b"');
        }
    },


    /**
     * Test that the L{compare}'s AssertionError includes the optional
     * message if it is provided.
     */
    function test_compareWithMessage(self) {
        try {
            self.compare(function () {return false;}, "<->", "a", "b",
                         "Hello");
        } catch (e) {
            self.assertIdentical(e.message, '"a" <-> "b": Hello');
        }
    },


    /**
     * Test that L{assertIdentical} raises an exception if its arguments are
     * unequal, and that the message of the raised exception contains the
     * arguments.
     */
    function test_assertIdenticalNegative(self) {
        var e = self.assertThrows(Divmod.UnitTest.AssertionError,
                                  function () {
                                      self.assertIdentical('apple', 'orange');
                                  });
        self.assert(e.message === '"apple" !== "orange"', e.message);
    },


    /**
     * If L{assertIdentical} is given a message as an optional third argument,
     * that message should appear in the raised exception's message. Test this.
     */
    function test_assertIdenticalNegativeWithMessage(self) {
        try {
            self.assertIdentical('apple', 'orange', 'some message');
        } catch (e) {
            self.assert(e.message === '"apple" !== "orange": some message');
        }
    },


    /**
     * Test that L{assertIdentical} doesn't raise an exception if its
     * arguments are equal.
     */
    function test_assertIdenticalPositive(self) {
        self.assertIdentical('apple', 'apple');
    },


    /**
     * Test that L{assertIdentical} thinks that 1 and '1' are unequal.
     */
    function test_assertIdenticalDifferentTypes(self) {
        var raised = true;
        var e = self.assertThrows(Divmod.UnitTest.AssertionError,
                                  function () {
                                      self.assertIdentical(1, '1');
                                  });
        self.assert(e.message === '1 !== "1"');
    },


    /**
     * Test that L{assertArraysEqual} doesn't raise an exception if it is
     * passed that two 'equal' arrays.
     */
    function test_assertArraysEqualPositive(self) {
        self.assertArraysEqual([], []);
        self.assertArraysEqual([1, 2], [1, 2]);
    },


    /**
     * Test that L{assertArraysEqual} raises exceptions if it is passed two unequal
     * arrays.
     */
    function test_assertArraysEqualNegative(self) {
        self.assertThrows(Divmod.UnitTest.AssertionError,
                          function () {
                              self.assertArraysEqual([1, 2], [1, 2, 3]);
                          });
        self.assertThrows(Divmod.UnitTest.AssertionError,
                          function () {
                              self.assertArraysEqual({'foo': 2}, [2]);
                          });
        self.assertThrows(Divmod.UnitTest.AssertionError,
                          function () {
                              self.assertArraysEqual(1, [1]);
                          });
        self.assertThrows(Divmod.UnitTest.AssertionError,
                          function () {
                              self.assertArraysEqual(function () { return 1; },
                                                     function () { return 2; });
                          });
        self.assertThrows(Divmod.UnitTest.AssertionError,
                          function () {
                              self.assertArraysEqual(function () { },
                                                     function () { });
                          });
    },


    /**
     * Test that two equal arrays are not identical, and that an object is
     * identical to itself.
     */
    function test_assertIdentical(self) {
        var foo = [1, 2];
        self.assertIdentical(foo, foo);
        self.assertThrows(Divmod.UnitTest.AssertionError,
                          function () { self.assertIdentical(foo, [1, 2]); });
    });



/**
 * Tests for L{TestCase}.
 */
Divmod.Test.TestUnitTest.TestCaseTest = Divmod.UnitTest.TestCase.subclass('Divmod.Test.TestUnitTest.TestCaseTest');
Divmod.Test.TestUnitTest.TestCaseTest.methods(
    function setUp(self) {
        self.result = Divmod.UnitTest.TestResult();
    },

    /**
     * Test that when a test is run, C{setUp} is called first, then the test
     * method, then L{tearDown}.
     */
    function test_wasRun(self) {
        var test = Divmod.Test.Mock._WasRun("test_good");
        self.assertIdentical(test.log, '');
        test.run(self.result);
        self.assertIdentical(test.log, 'setUp test tearDown');
    },

    /**
     * Test that C{tearDown} still gets called, even when the test fails.
     */
    function test_tearDownCalled(self) {
        var test = Divmod.Test.Mock._WasRun("test_bad");
        test.run(self.result);
        self.assertIdentical(test.log, 'setUp tearDown');
    },

    /**
     * Test that C{run} takes a L{TestResult} that we can use to see whether
     * the test passed.
     */
    function test_goodResult(self) {
        var test = Divmod.Test.Mock._WasRun('test_good');
        test.run(self.result);
        self.assertArraysEqual(self.result.getSummary(), [1, 0, 0]);
        self.assert(self.result.wasSuccessful());
    },


    /**
     * Test that C{run} takes a L{TestResult} that we can use to see whether
     * test test failed.
     */
    function test_badResult(self) {
        var test = Divmod.Test.Mock._WasRun('test_bad');
        test.run(self.result);
        self.assertArraysEqual(self.result.getSummary(), [1, 1, 0]);
        self.assert(!self.result.wasSuccessful());
    },


    /**
     * Test that the L{TestResult} distinguishes between failed assertions
     * and general errors.
     */
    function test_errorResult(self) {
        var test = Divmod.Test.Mock._WasRun('test_error');
        test.run(self.result);
        self.assertArraysEqual(self.result.getSummary(), [1, 0, 1]);
        self.assert(!self.result.wasSuccessful());
    },


    /**
     * Test that we can find out which tests had which errors and which tests
     * succeeded.
     */
    function test_resultAccumulation(self) {
        var suite = Divmod.UnitTest.TestSuite();
        var bad = Divmod.Test.Mock._WasRun('test_bad');
        var good = Divmod.Test.Mock._WasRun('test_good');
        var error = Divmod.Test.Mock._WasRun('test_error');
        suite.addTests([bad, good, error]);
        suite.run(self.result);
        self.assertArraysEqual(self.result.getSummary(), [3, 1, 1]);
        // check the failure
        self.assertIdentical(self.result.failures[0].length, 2);
        self.assertIdentical(self.result.failures[0][0], bad);
        self.assert(self.result.failures[0][1]
                    instanceof Divmod.UnitTest.AssertionError);
        self.assertIdentical(self.result.failures[0][1].message,
                             "fail this test deliberately");
        // check the error
        self.assertIdentical(self.result.errors[0].length, 2);
        self.assertIdentical(self.result.errors[0][0], error);
        self.assert(self.result.errors[0][1] instanceof Divmod.Error);
        self.assertIdentical(self.result.errors[0][1].message, "error");
        self.assertArraysEqual(self.result.successes, [good]);
    },


    /**
     * Test that neither L{tearDown} nor the test method is called when
     * L{setUp} fails.
     */
    function test_failureInSetUp(self) {
        var test = Divmod.Test.Mock._BadSetUp('test_method');
        self.assertIdentical(test.log, '');
        test.run(self.result);
        self.assertIdentical(test.log, '');
    },


    /**
     * Test that failures in L{setUp} are reported to the L{TestResult}
     * object.
     */
    function test_failureInSetUpReported(self) {
        var test = Divmod.Test.Mock._BadSetUp('test_method');
        test.run(self.result);
        self.assertArraysEqual(self.result.getSummary(), [1, 0, 1]);
    },


    /**
     * Test that failures in L{tearDown} are reported to the L{TestResult}
     * object.
     */
    function test_failureInTearDownReported(self) {
        var test = Divmod.Test.Mock._BadTearDown('test_method');
        test.run(self.result);
        self.assertArraysEqual(self.result.getSummary(), [1, 0, 1]);
    },


    /**
     * Test that a test which fails in L{tearDown} does *not* get added as
     * a success.
     */
    function test_badTearDownNotSuccess(self) {
        var test = Divmod.Test.Mock._BadTearDown('test_method');
        test.run(self.result);
        self.assertIdentical(self.result.successes.length, 0);
    },


    /**
     * Test that L{TestCase.run} calls L{TestResult.startTest} and
     * L{TestResult.stopTest}.
     */
    function test_startAndStopTest(self) {
        var test = Divmod.Test.Mock._WasRun('test_good');
        var id = test.id();
        var result = Divmod.Test.TestUnitTest.MockResult();
        test.run(result);
        self.assertIdentical(
            result.log,
            'startTest ' + id + ' addSuccess ' + id + ' stopTest ' + id);
    },


    /**
     * Test that we can create a L{TestSuite}, add tests to it, run it and
     * get the results of all of the tests.
     */
    function test_testSuite(self) {
        var suite = Divmod.UnitTest.TestSuite();
        suite.addTest(Divmod.Test.Mock._WasRun('test_good'));
        suite.addTest(Divmod.Test.Mock._WasRun('test_bad'));
        suite.run(self.result);
        self.assertArraysEqual(self.result.getSummary(), [2, 1, 0]);
        self.assert(!self.result.wasSuccessful());
    },


    /**
     * Check that C{countTestCases} returns 0 for an empty suite, 1 for a test,
     * and n for a suite with n tests.
     */
    function test_countTestCases(self) {
        self.assertIdentical(self.countTestCases(), 1);
        var suite = Divmod.UnitTest.TestSuite();
        self.assertIdentical(suite.countTestCases(), 0);
        suite.addTest(self);
        self.assertIdentical(suite.countTestCases(), 1);
        suite.addTest(Divmod.Test.Mock._WasRun('good'));
        self.assertIdentical(suite.countTestCases(), 2);
    },


    /**
     * Test that C{id} returns the fully-qualified name of the test.
     */
    function test_id(self) {
        var test = Divmod.Test.Mock._WasRun('test_good');
        self.assertIdentical(test.id(), 'Divmod.Test.Mock._WasRun.test_good');
    },


    /**
     * Test that C{visit} calls the visitor with the test case.
     */
    function test_visitCase(self) {
        var log = [];
        function visitor(test) {
            log.push(test);
        }
        self.visit(visitor);
        self.assertArraysEqual(log, [self]);
    },


    /**
     * Test that C{visit} calls the visitor for each test case in a suite.
     */
    function test_visitSuite(self) {
        var log = [];
        function visitor(test) {
            log.push(test);
        }
        Divmod.UnitTest.TestSuite().visit(visitor);
        self.assertArraysEqual(log, []);
        var tests = [self, Divmod.Test.Mock._WasRun('test_good')];
        var suite = Divmod.UnitTest.TestSuite(tests);
        suite.visit(visitor);
        self.assertArraysEqual(log, tests);
    },


    /**
     * Check that issubclass returns true when the first parameter is a subclass
     * of the second, and false otherwise.
     */
    function test_issubclass(self) {
        self.assert(self.__class__.subclassOf(self.__class__),
                    "Thing should subclass itself");
        self.assert(self.__class__.subclassOf(Divmod.UnitTest.TestCase));
        self.assert(!Divmod.UnitTest.TestCase.subclassOf(self.__class__));
    });



Divmod.Test.TestUnitTest.LoaderTests = Divmod.UnitTest.TestCase.subclass("Divmod.Test.TestUnitTest.LoaderTests");
Divmod.Test.TestUnitTest.LoaderTests.methods(
    /**
     * Return a list containing the id() of each test in a suite.
     */
    function getTestIDs(self, suite) {
        var ids = [];
        suite.visit(function (test) { ids.push(test.id()); });
        return ids;
    },


    /**
     * Test that C{loadFromClass} returns an empty suite when given a
     * C{TestCase} subclass that contains no tests.
     */
    function test_loadFromClassEmpty(self) {
        var suite = Divmod.UnitTest.loadFromClass(Divmod.UnitTest.TestCase);
        self.assertArraysEqual(self.getTestIDs(suite), []);
    },


    /**
     * Test that C{loadFromClass} returns a suite which contains all the
     * test methods in a given C{TestCase} subclass.
     */
    function test_loadFromClass(self) {
        var suite = Divmod.UnitTest.loadFromClass(Divmod.Test.Mock._WasRun);
        self.assertArraysEqual(self.getTestIDs(suite),
                               ['Divmod.Test.Mock._WasRun.test_bad',
                                'Divmod.Test.Mock._WasRun.test_error',
                                'Divmod.Test.Mock._WasRun.test_good']);
    },


    /**
     * Test that C{loadFromModule} returns an empty suite when given a module
     * with no unit tests.
     */
    function test_loadFromModuleEmpty(self) {
        var module = {};
        var suite = Divmod.UnitTest.loadFromModule(module);
        self.assertIdentical(suite.countTestCases(), 0);
    },


    /**
     * Test that C{loadFromModule} returns a suite which contains all the
     * test methods in a given module.
     */
    function test_loadFromModule(self) {
        var Mock = {};
        Mock.SomeTestCase = Divmod.UnitTest.TestCase.subclass('Mock.SomeTestCase');
        Mock.SomeTestCase.methods(function test_method(self) {});
        suite = Divmod.UnitTest.loadFromModule(Mock);
        self.assertArraysEqual(self.getTestIDs(suite),
                               ['Mock.SomeTestCase.test_method']);
    });


Divmod.Test.TestUnitTest.RunnerTest = Divmod.UnitTest.TestCase.subclass('Divmod.Test.TestUnitTest.RunnerTest');
Divmod.Test.TestUnitTest.RunnerTest.methods(
    function setUp(self) {
        self.result = Divmod.UnitTest.TestResult();
    },


    /**
     * Test that the summary of an empty result object indicates the 'test run'
     * passed, and that no tests were run.
     */
    function test_formatSummaryEmpty(self) {
        self.assertIdentical(Divmod.UnitTest.formatSummary(self.result),
                             "PASSED (tests=0)");
    },


    /**
     * Test that the summary of a result object from a successful test run
     * indicates that the run was successful along with the number of tests in
     * the run.
     */
    function test_formatSummaryOK(self) {
        var test = Divmod.Test.Mock._WasRun('test_good');
        test.run(self.result);
        self.assertIdentical(Divmod.UnitTest.formatSummary(self.result),
                             "PASSED (tests=1)");
    },


    /**
     * Test that the summary of a result object from a test run with failures
     * indicates an overall failure as well as the number of test failures.
     */
    function test_formatSummaryFailed(self) {
        var test = Divmod.Test.Mock._WasRun('test_bad');
        test.run(self.result);
        self.assertIdentical(Divmod.UnitTest.formatSummary(self.result),
                             "FAILED (tests=1, failures=1)");
    },


    /**
     * As L{test_formatSummaryFailed}, but for errors instead of failures.
     */
    function test_formatSummaryError(self) {
        var test = Divmod.Test.Mock._WasRun('test_error');
        test.run(self.result);
        self.assertIdentical(Divmod.UnitTest.formatSummary(self.result),
                             "FAILED (tests=1, errors=1)");
    },


    /**
     * Sanity test added to make sure the summary makes sense when a suite
     * has both failed and errored tests.
     */
    function test_formatSummaryMultiple(self) {
        var test = Divmod.UnitTest.loadFromClass(Divmod.Test.Mock._WasRun);
        test.run(self.result);
        self.assertIdentical(Divmod.UnitTest.formatSummary(self.result),
                             "FAILED (tests=3, errors=1, failures=1)");
    },


    /**
     * Check that L{formatErrors} returns an empty string for an empty result.
     */
    function test_formatErrorsEmpty(self) {
        self.assertIdentical(Divmod.UnitTest.formatErrors(self.result), '');
    },


    /**
     * Check that L{formatErrors} returns an empty string for a successful result.
     */
    function test_formatErrorsOK(self) {
        var test = Divmod.Test.Mock._WasRun('test_good');
        test.run(self.result);
        self.assertIdentical(Divmod.UnitTest.formatErrors(self.result), '');
    },


    /**
     * Check that the L{formatError} returns a nicely formatted representation
     * of a failed/errored test.
     */
    function test_formatError(self) {
        var test = Divmod.Test.Mock._WasRun('test_bad');
        var error, failure;
        try {
            throw Divmod.Error("error-message");
        } catch (e) {
            error = e;
            failure = Divmod.Defer.Failure(error);
        }
        self.assertIdentical(
            Divmod.UnitTest.formatError('FAILURE', test, error),
            '[FAILURE] Divmod.Test.Mock._WasRun.test_bad: error-message\n'
            + failure.toPrettyText(failure.filteredParseStack()) + '\n');
    },


    /**
     * Check that L{formatErrors} returns a string that contains all of the
     * errors and failures from the result, formatted using L{formatError}.
     */
    function test_formatErrors(self) {
        var test = Divmod.UnitTest.loadFromClass(Divmod.Test.Mock._WasRun);
        test.run(self.result);
        var expected = '';
        for (var i = 0; i < self.result.errors.length; ++i) {
            expected += Divmod.UnitTest.formatError('ERROR',
                                                self.result.errors[i][0],
                                                self.result.errors[i][1]);
        }
        for (var i = 0; i < self.result.failures.length; ++i) {
            expected += Divmod.UnitTest.formatError('FAILURE',
                                                self.result.failures[i][0],
                                                self.result.failures[i][1]);
        }
        var observed = Divmod.UnitTest.formatErrors(self.result);
        self.assertIdentical(observed, expected);
    });

Divmod.Test.TestUnitTest.MockDocumentTest = Divmod.UnitTest.TestCase.subclass(
    'Divmod.Test.TestUnitTest.MockDocumentTest');

Divmod.Test.TestUnitTest.MockDocumentTest.methods(
    /**
     * Verify that the document is implicitly imported by the test set up.
     * NB: If we ever have a way to run these tests in a real browser, there
     * should be a way to skip this one.
     */
    function test_documentExists(self) {
        self.assert(document instanceof Divmod.MockBrowser.Document);
    },

    /**
     * Verify that the document has a "body" attribute which is an element.
     */
    function test_documentHasBody(self) {
        self.assert(document.body instanceof Divmod.MockBrowser.Element);
    },

    /**
     * Verify that the elements created by the document have their tag name
     * set based on input.
     */
    function test_createElement(self) {
        var aDocument = Divmod.MockBrowser.Document();
        self.assertIdentical(aDocument.createElement('something').tagName,
                             'SOMETHING');
    },

    /**
     * Elements created with L{Document.createElement} should have a
     * C{ownerDocument} property which refers to the document which created
     * them.
     */
    function test_createdElementHasDocument(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement('a');
        self.assertIdentical(anElement.ownerDocument, aDocument);
    },

    /**
     * Verify that text nodes are created with appropriate 'length',
     * 'nodeValue', and (empty) 'childNodes' attributes.
     */

    function test_createTextNode(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var aNode = aDocument.createTextNode("hello, world!");
        self.assertIdentical(aNode.length, 13);
        self.assertIdentical(aNode.nodeValue, "hello, world!");
        self.assertIdentical(aNode.childNodes.length, 0);
    },

    /**
     * Text Nodes created with L{Document.createElement} should have a
     * C{ownerDocument} property which refers to the document which created
     * them.
     */
    function test_createdTextNodeHasDocument(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var aNode = aDocument.createTextNode("hello, world!");
        self.assertIdentical(aNode.ownerDocument, aDocument);
    },

    /**
     * Verify that setting an attribute on an element results in that
     * attribute being returned from getAttribute.
     */
    function test_setGetAttribute(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement('test');
        anElement.setAttribute("abc", "123");
        self.assertIdentical(anElement.getAttribute("abc"), "123");
    },

    /**
     * Verify that setting an attribute and then removing it results in
     * getAttribute subsequently returning C{undefined}.
     */
    function test_getRemoveAttribute(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement('test');
        anElement.setAttribute("abc", "123");
        anElement.removeAttribute("abc");
        self.assertIdentical(anElement.getAttribute("abc"), undefined);
    },

    /**
     * Verify that an Element will have a "style" attribute that can be
     * manipulated.
     */
    function test_elementHasStyle(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement('test');
        anElement.style.border = 'thin solid blue';
        self.assertIdentical(anElement.style.border, 'thin solid blue');
    },

    /**
     * Verify that an Element given a certain class via setAttribute will be
     * given a 'className' attribute that matches the class.
     */
    function test_firefoxStyleClassAttribute(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement('test');
        anElement.setAttribute("class", "something");
        self.assertIdentical(anElement.className, "something");
    },

    /**
     * Verify that a mock element's appendChild() puts that element into the
     * childNodes array.
     */
    function test_appendChild(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement("test");
        var anotherElement = aDocument.createElement('test2');
        anElement.appendChild(anotherElement);
        self.assertIdentical(anElement.childNodes[0], anotherElement);
        self.assertIdentical(anotherElement.parentNode, anElement);
    },

    /**
     * Verify that a mock element's removeChild() removes that element (and
     * only that element) from the childNodes array.
     */
    function test_removeChild(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement("test");
        var anotherElement = aDocument.createElement("test2");
        var ignoreMe = aDocument.createElement("testX");
        var ignoreMe2 = aDocument.createElement("testY");
        anElement.appendChild(ignoreMe);
        anElement.appendChild(anotherElement);
        anElement.appendChild(ignoreMe2);
        anElement.removeChild(anotherElement);

        self.assertIdentical(anElement.childNodes.length, 2);
        for (var i = 0; i < anElement.childNodes.length; i++) {
            self.assert(anElement.childNodes[i] !== anotherElement);
        }
    },

    /**
     * Verify that an exception will be raised if a mock element is asked to
     * remove a child which it does not contain.
     */
    function test_removeChildInvalid(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement("test");
        var anotherElement = aDocument.createElement("test2");
        self.assertThrows(
            Divmod.MockBrowser.DOMError,
            function () {
                anElement.removeChild(anotherElement);
            });
    },

    /**
     * Verify that elements can be retrieved by their ID.
     */
    function test_getElementById(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement("a");
        var anotherElement = aDocument.createElement("b");
        aDocument.body.appendChild(anElement);
        aDocument.body.appendChild(anotherElement);

        anotherElement.id = 'test1';
        self.assertIdentical(aDocument.getElementById('test1'), anotherElement);
        var thirdElement = aDocument.createElement('c');
        aDocument.body.appendChild(thirdElement);
        thirdElement.id = 'test2';
        self.assertIdentical(aDocument.getElementById('test2'), thirdElement);
    },

    /**
     * Verify that orphaned elements (those not in any document) will not be
     * returned by getElementById even if they have an ID that matches.
     */
    function test_getElementByIdNoOrphans(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement("a");
        anElement.id = 'test1';
        self.assertIdentical(aDocument.getElementById('test1'), null);
        aDocument.body.appendChild(anElement);
        self.assertIdentical(aDocument.getElementById('test1'), anElement);
    },

    /**
     * Verify that conflicting IDs are resolved in the reverse order they are
     * created; i.e. that the most recently added created node in the document
     * with a given ID is found.
     *
     * This behavior is inconsistent with actual browser DOM, but providing
     * proper DOM semantics is difficult due to the fact that tests are
     * sharing lots of global state but should not be.
     *
     * Although these tests here each create their own document object for
     * better isolation, third-party code designed to run in an actual browser
     * (c.f. MochiKit.DOM) will generally assume that there is only one global
     * document and may hold their own references to it.
     *
     * Browsers appear to treat the first element to be added to the document
     * with a given ID as the definitive one, whereas we always want to take
     * the most recent, because a previous test may have stomped on that ID.
     *
     * Eventually it might be a better idea to have the test framework
     * interact with the global document a bit, re-setting it to a pristine
     * state between tests to that they do not interact with each other, and
     * correcting this implementation to be completely consistent with the
     * browser's getElementById.
     *
     * However, for the time being, this point is mostly moot; I can't find a
     * description of the behavior of ID conflicts in either the DOM
     * specifications or browser documentation (except by the vague
     * implication that they should never, ever happen) so this behavior is
     * correct inasmuch as it prevents tests from having inter-test
     * interactions which they should not have. -glyph
     */

    function test_conflictResolutionOrder(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var c = aDocument.createElement("c");
        var b = aDocument.createElement("b");
        var a = aDocument.createElement("a");

        c.id = 'test1';

        aDocument.body.appendChild(a);
        aDocument.body.appendChild(b);
        aDocument.body.appendChild(c);

        self.assertIdentical(aDocument.getElementById('test1'), c);
        b.id = 'test1';
        a.id = 'test1';

        // a was created later.
        self.assertIdentical(aDocument.getElementById("test1"), a);
    },

    /**
     * Verify that getElementById with an id that does not exist will mimic
     * Firefox's behavior and return 'null'.
     */
    function test_getNoElementById(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement("div");
        anElement.id = "some-id";
        self.assertIdentical(aDocument.getElementById("some-other-id"), null);
    },

    /**
     * Make a L{Document} containing some C{<span>} and C{<div>} nodes at
     * various depths.
     */
    function _makeNestedDocument(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var outerNode = aDocument.createElement("div");
        var innerNode = aDocument.createElement("div");
        var spanOne = aDocument.createElement("span");
        spanOne.appendChild(aDocument.createTextNode("LULZ"));
        innerNode.appendChild(spanOne);
        outerNode.appendChild(innerNode);
        var spanTwo = aDocument.createElement("span");
        spanTwo.appendChild(aDocument.createTextNode("OK"));
        outerNode.appendChild(spanTwo);
        aDocument.body.appendChild(outerNode);
        return aDocument;
    },

    /**
     * getElementsByTagName, when called on L{Document}, should return all
     * nodes with the specified tag name, at any depth inside the document's
     * body.
     */
    function test_getElementsByTagNameDocument(self) {
        var aDocument = self._makeNestedDocument();
        var outerNode = aDocument.body.childNodes[0];
        var deepSpan = outerNode.childNodes[0].childNodes[0];
        var shallowSpan = outerNode.childNodes[1];
        var result = aDocument.getElementsByTagName('span');
        self.assertIdentical(result.length, 2);
        self.assertIdentical(result[0], deepSpan);
        self.assertIdentical(result[1], shallowSpan);
    },

    /**
     * getElementsByTagName, when called on L{Document.body}, should exclude
     * its body node from the result.
     */
    function test_getElementsByTagNameBodyNoBody(self) {
        var aDocument = Divmod.MockBrowser.Document();
        self.assertIdentical(
            aDocument.body.getElementsByTagName('body').length, 0);
    },

    /**
     * getElementsByTagName, when called on L{Document}, should include its
     * body node from the result.
     */
    function test_getElementsByTagNameDocumentIncludesBody(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var nodes = aDocument.getElementsByTagName('body');
        self.assertIdentical(nodes.length, 1);
        self.assertIdentical(nodes[0], aDocument.body);
    },

    /**
     * getElementsByTagName should also work on L{Element}.
     */
    function test_getElementsByTagNameElement(self) {
        var aDocument = self._makeNestedDocument();
        var outerNode = aDocument.body.childNodes[0];
        var deepSpan = outerNode.childNodes[0].childNodes[0];
        var shallowSpan = outerNode.childNodes[1];
        var result = outerNode.getElementsByTagName('span');
        self.assertIdentical(result.length, 2);
        self.assertIdentical(result[0], deepSpan);
        self.assertIdentical(result[1], shallowSpan);
    },

    /**
     * getElementsByTagName, when called on L{Element}, should exclude the
     * node it's called on from the result.
     */
    function test_getElementsByTagNameElementNoTop(self) {
        var aDocument = self._makeNestedDocument();
        var shallowDiv = aDocument.body.childNodes[0];
        var deepDiv = shallowDiv.childNodes[0];
        var result = shallowDiv.getElementsByTagName('div');
        self.assertIdentical(result.length, 1);
        self.assertIdentical(result[0], deepDiv);
    },

    /**
     * getElementsByTagName should return all elements (no text nodes) when
     * passed C{*}.
     */
    function test_getElementsByTagNameWildcard(self) {
        var aDocument = self._makeNestedDocument();
        var result = aDocument.getElementsByTagName('*');
        self.assertIdentical(result.length, 5);
        self.assertIdentical(result[0], aDocument.body);
        var outerNode = aDocument.body.childNodes[0];
        self.assertIdentical(result[1], outerNode);
        var innerNode = outerNode.childNodes[0];
        self.assertIdentical(result[2], innerNode);
        var spanOne = innerNode.childNodes[0];
        self.assertIdentical(result[3], spanOne);
        var spanTwo = outerNode.childNodes[1];
        self.assertIdentical(result[4], spanTwo);

        result = outerNode.getElementsByTagName('*');
        self.assertIdentical(result.length, 3);
        self.assertIdentical(result[0], innerNode);
        self.assertIdentical(result[1], spanOne);
        self.assertIdentical(result[2], spanTwo);
    },

    /**
     * Verify that the string representation of a mock element captures all of
     * its interesting features to provide something to introspect while
     * debugging.
     */
    function test_elementToString(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement("stuff");
        // Tag name.
        self.assertIdentical(
            anElement.toString(), "<{MOCK}STUFF />");
        anElement.setAttribute("hello", "world");
        // Attributes.
        self.assertIdentical(
            anElement.toString(), '<{MOCK}STUFF hello="world" />');
        anElement.style.border = "thick solid blue";
        // Special "style" attribute.
        self.assertIdentical(
            anElement.toString(),
            '<{MOCK}STUFF hello="world" {style}="border: thick solid blue; " />');
        anotherElement = aDocument.createElement("other");
        anElement.appendChild(anotherElement);
        // Child nodes.
        self.assertIdentical(
            anElement.toString(),
            '<{MOCK}STUFF hello="world" {style}="border: thick solid blue; ">...</STUFF>');
    },

    /**
     * Verify that the default size of an Element will initially be (0, 0)
     * until that element is added to the document.
     */
    function test_defaultElementSize(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement("stuff");

        self.assertIdentical(0, anElement.clientHeight);
        self.assertIdentical(0, anElement.clientWidth);

        aDocument.body.appendChild(anElement);

        self.assertIdentical(aDocument.DEFAULT_HEIGHT,
                             anElement.clientHeight);
        self.assertIdentical(aDocument.DEFAULT_WIDTH,
                             anElement.clientWidth);
    },

    /**
     * Verify that the platform will respect the sizes set for mock elements
     * in tests.
     */
    function test_getMockElementSize(self) {
        var aDocument = Divmod.MockBrowser.Document();
        var anElement = aDocument.createElement("stuff");
        anElement.setMockElementSize(1234, 5678);

        var size = Divmod.Runtime.theRuntime.getElementSize(anElement);

        self.assertIdentical(size.w, 1234);
        self.assertIdentical(size.h, 5678);
    });


/**
 * Tests for L{Divmod.Runtime.Platform.repr}.
 */
Divmod.Test.TestUnitTest.ReprTests =
    Divmod.UnitTest.TestCase.subclass('Divmod.Test.TestUnitTest.ReprTests');
Divmod.Test.TestUnitTest.ReprTests.methods(
    /**
     * Test that repr(undefined) and repr(null) work.
     */
    function test_undefinedAndNull(self) {
        var repr = Divmod.UnitTest.repr;
        self.assertIdentical(repr(null), 'null');
        self.assertIdentical(repr(undefined), 'undefined');
    },

    /**
     * Test that some simple values have a reasonable repr().
     */
    function test_simpleValues(self) {
        var repr = Divmod.UnitTest.repr;
        self.assertIdentical(repr(5), '5');
        self.assertIdentical(repr('foo'), '"foo"');
        self.assert(repr(['foo']).search('foo') >= 0);
    });
