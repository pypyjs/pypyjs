// -*- test-case-name: nevow.test.test_javascript -*-

/**
 * JavaScript unit testing framework, modeled on xUnit.
 */


// import Divmod
// import Divmod.Inspect
// import Divmod.Runtime


/**
 * Return a suite which contains every test defined in C{testClass}. Assumes
 * that if a method name starts with C{test_}, then it is a test.
 */
Divmod.UnitTest.loadFromClass = function loadFromClass(testClass) {
    var prefix = 'test_';
    var suite = Divmod.UnitTest.TestSuite();
    var methods = Divmod.Inspect.methods(testClass);
    for (var i = 0; i < methods.length; ++i) {
        var name = methods[i];
        // XXX - abstract startsWith
        if (name.substr(0, prefix.length) == prefix) {
            suite.addTest(testClass(name));
        }
    }
    return suite;
};


/**
 * Return C{true} is given value is a subclass of L{Divmod.UnitTest.TestCase},
 * C{false} otherwise.
 */
Divmod.UnitTest.isTestCaseClass = function isTestCaseClass(klass) {
    if (klass.subclassOf === undefined) {
        return false;
    }
    return klass.subclassOf(Divmod.UnitTest.TestCase);
};


/**
 * Return a suite which contains every test defined in C{testModule}.
 */
Divmod.UnitTest.loadFromModule = function loadFromModule(testModule) {
    var suite = Divmod.UnitTest.TestSuite();
    for (var name in testModule) {
        if (Divmod.UnitTest.isTestCaseClass(testModule[name])) {
            suite.addTest(Divmod.UnitTest.loadFromClass(testModule[name]));
        }
    }
    return suite;
};



/**
 * Raised to indicate that a test has failed.
 */
Divmod.UnitTest.AssertionError = Divmod.Error.subclass('Divmod.UnitTest.AssertionError');
Divmod.UnitTest.AssertionError.methods(
    function toString(self) {
        return 'AssertionError: ' + self.message;
    });


/**
 * Represents the results of a run of unit tests.
 *
 * @type testsRun: integer
 * @ivar testsRun: The number of tests that have been run using this as the
 *                 result.
 *
 * @type failures: Array of [L{TestCase}, L{Divmod.Error}] pairs
 * @ivar failures: The assertion failures that have occurred in this test run,
 *                 paired with the tests that generated them.
 *
 * @type successes: Array of L{TestCase}
 * @ivar successes: A list of tests that succeeded.
 *
 * @type errors: Array of [L{TestCase}, L{Divmod.Error}] pairs
 * @ivar errors: The errors that were raised by tests in this test run, paired
 *               with the tests that generated them.
 */
Divmod.UnitTest.TestResult = Divmod.Class.subclass('Divmod.UnitTest.TestResult');
Divmod.UnitTest.TestResult.methods(
    function __init__(self) {
        self.testsRun = 0;
        self.failures = [];
        self.successes = [];
        self.errors = [];
    },


    /**
     * Called by C{TestCase.run} at the start of the test.
     *
     * @param test: The test that just started.
     * @type test: L{Divmod.UnitTest.TestCase}
     */
    function startTest(self, test) {
        self.testsRun++;
    },


    /**
     * Called by C{TestCase.run} at the end of the test run.
     *
     * @param test: The test that just finished.
     * @type test: L{Divmod.UnitTest.TestCase}
     */
    function stopTest(self, test) {
    },


    /**
     * Report an error that occurred while running the given test.
     *
     * @param test: The test that had an error.
     * @type test: L{Divmod.UnitTest.TestCase}
     *
     * @param error: The error that occurred.
     * @type error: Generally a L{Divmod.Error} instance.
     */
    function addError(self, test, error) {
        self.errors.push([test, error]);
    },


    /**
     * Report a failed assertion that occurred while running the given test.
     *
     * @param test: The test with the failed assertion.
     * @type test: L{Divmod.UnitTest.TestCase}
     *
     * @param failure: The failure that occurred.
     * @type failure: A L{Divmod.UnitTest.AssertionError} instance.
     */
    function addFailure(self, test, failure) {
        self.failures.push([test, failure]);
    },


    /**
     * Report that the given test succeeded.
     *
     * @param test: The test that succeeded.
     * @type test: L{Divmod.UnitTest.TestCase}
     */
    function addSuccess(self, test) {
        self.successes.push(test);
    },


    /**
     * Return a triple of (tests run, number of failures, number of errors)
     */
    function getSummary(self) {
        return [self.testsRun, self.failures.length, self.errors.length];
    },


    /**
     * Return C{true} if there have been no failures or errors. Return C{false}
     * if there have been.
     */
    function wasSuccessful(self) {
        return self.failures.length == 0 && self.errors.length == 0;
    });



Divmod.UnitTest.SubunitTestClient = Divmod.UnitTest.TestResult.subclass('Divmod.UnitTest.SubunitTestClient');
Divmod.UnitTest.SubunitTestClient.methods(
    function _write(self, string) {
        print(string);
    },

    function _sendException(self, error) {
        var f = Divmod.Defer.Failure(error);
        self._write(f.toPrettyText(f.filteredParseStack()));
    },

    function addError(self, test, error) {
        self._write("error: " + test.id() + " [");
        self._sendException(error);
        self._write(']');
    },

    function addFailure(self, test, error) {
        self._write("failure: " + test.id() + " [");
        self._sendException(error);
        self._write(']');
    },

    function addSuccess(self, test) {
        self._write('successful: ' + test.id());
    },

    function startTest(self, test) {
        self._write('test: ' + test.id());
    });



/**
 * Represents a collection of tests. Implements the Composite pattern.
 */
Divmod.UnitTest.TestSuite = Divmod.Class.subclass('Divmod.UnitTest.TestSuite');
Divmod.UnitTest.TestSuite.methods(
    function __init__(self, /* optional */ tests) {
        self.tests = [];
        if (tests != undefined) {
            self.addTests(tests);
        }
    },


    /**
     * Add the given test to the suite.
     *
     * @param test: The test to add.
     * @type test: L{Divmod.UnitTest.TestCase} or L{Divmod.UnitTest.TestSuite}
     */
    function addTest(self, test) {
        self.tests.push(test);
    },


    /**
     * Add the given tests to the suite.
     *
     * @param tests: An array of tests to add.
     * @type tests: [L{Divmod.UnitTest.TestCase} or L{Divmod.UnitTest.TestSuite}]
     */
    function addTests(self, tests) {
        for (var i = 0; i < tests.length; ++i) {
            self.addTest(tests[i]);
        }
    },


    /**
     * Return the number of actual tests contained in this suite.
     */
    function countTestCases(self) {
        var total = 0;
        self.visit(function (test) { total += test.countTestCases(); });
        return total;
    },


    /**
     * Visit each test case in this suite with the given visitor function.
     */
    function visit(self, visitor) {
        for (var i = 0; i < self.tests.length; ++i) {
            self.tests[i].visit(visitor);
        }
    },


    /**
     * Run all of the tests in the suite.
     */
    function run(self, result) {
        self.visit(function (test) { test.run(result); });
    });



/**
 * I represent a single unit test.
 */
Divmod.UnitTest.TestCase = Divmod.Class.subclass('Divmod.UnitTest.TestCase');
Divmod.UnitTest.TestCase.methods(
    /**
     * Construct a test.
     *
     * @type methodName: string
     * @param methodName: The name of a method on this object that contains
     * the unit test.
     */
    function __init__(self, methodName) {
        self._methodName = methodName;
    },


    /**
     * Return a string which identifies this test.
     */
    function id(self) {
        return self.__class__.__name__ + '.' + self._methodName;
    },


    /**
     * Count the number of test cases in this test. Always 1, because an
     * instance represents a single test.
     */
    function countTestCases(self) {
        return 1;
    },


    /**
     * Visit this test case.
     *
     * @param visitor: A callable which takes one argument (a test case).
     */
    function visit(self, visitor) {
        visitor(self);
    },


    /**
     * Fail the test. Equivalent to an invalid assertion.
     *
     * @type reason: text
     * @param reason: Why the test is being failed.
     * @throw: Divmod.UnitTest.AssertionError
     */
    function fail(self, reason) {
        throw Divmod.UnitTest.AssertionError(reason);
    },


    /**
     * Assert that the given expression evalutates to true.
     *
     * @type expression: boolean
     * @param expression: The thing we are asserting.
     *
     * @type message: text
     * @param message: An optional parameter, explaining what the assertion
     * means.
     */
    function assert(self, expression, /* optional */ message) {
        if (!expression) {
            self.fail(message);
        }
    },


    /**
     * Compare C{a} and C{b} using the provided predicate.
     *
     * @type predicate: A callable that accepts two parameters.
     * @param predicate: Returns either C{true} or C{false}.
     *
     * @type description: text
     * @param description: Describes the inverse of the comparison. This is
     *                     used in the L{AssertionError} if the comparison
     *                     fails.
     *
     * @type a: any
     * @param a: The thing to be compared with C{b}. Passed as the first
     *           parameter to C{predicate}.
     *
     * @type b: any
     * @param b: The thing to be compared with C{a}. Passed as the second
     *           parameter to C{predicate}.
     *
     * @type message: text
     * @param message: An optional message to be included in the raised
     *                 L{AssertionError}.
     *
     * @raises L{Divmod.UnitTest.AssertionError} if C{predicate} returns
     * C{false}.
     */
    function compare(self, predicate, description, a, b,
                     /* optional */ message) {
        var repr = Divmod.UnitTest.repr;
        if (!predicate(a, b)) {
            msg = repr(a) + " " + description + " " + repr(b);
            if (message != null) {
                msg += ': ' + message;
            }
            self.fail(msg);
        }
    },


    /**
     * Assert that C{a} and C{b} are equal. Recurses into arrays and dicts.
     */
    function assertArraysEqual(self, a, b, /* optional */ message) {
        self.compare(Divmod.arraysEqual, '!=', a, b, message);
    },


    /**
     * Assert that C{a} and C{b} are identical.
     */
    function assertIdentical(self, a, b, /* optional */ message) {
        self.compare(function (x, y) { return x === y; },
                     '!==', a, b, message);
    },


    /**
     * Assert that C{callable} throws C{expectedError}
     *
     * @param expectedError: The error type (class or prototype) which is
     * expected to be thrown.
     *
     * @param callable: A callable which is expected to throw C{expectedError}.
     *
     * @param ...: Optional positional arguments passed to C{callable}.
     *
     * @throw AssertionError: Thrown if the callable doesn't throw
     * C{expectedError}. This could be because it threw a different error or
     * because it didn't throw any errors.
     *
     * @return: The exception that was raised by callable.
     */
    function assertThrows(self, expectedError, callable /*... */) {
        var threw = null;
        var args = Array.prototype.slice.call(arguments, 3);
        try {
            callable.apply(null, args);
        } catch (e) {
            threw = e;
            self.assert(e instanceof expectedError,
                        "Wrong error type thrown: " + e);
        }
        self.assert(threw != null, "Callable threw no error");
        return threw;
    },


    /**
     * Override me to provide code to set up a unit test. This method is called
     * before the test method.
     *
     * L{setUp} is most useful when a subclass contains many test methods which
     * require a common base configuration. L{tearDown} is the complement of
     * L{setUp}.
     */
    function setUp(self) {
    },


    /**
     * Override me to provide code to clean up a unit test. This method is called
     * after the test method.
     *
     * L{tearDown} is at its most useful when used to clean up resources that are
     * initialized/modified by L{setUp} or by the test method.
     */
    function tearDown(self) {
    },


    /**
     * Actually run this test.
     */
    function run(self, result) {
        var success = true;
        result.startTest(self);

        // XXX: This probably isn't the best place to put this, but it's the
        // only place for the time being; see #2806 for the proper way to deal
        // with this.
        Divmod.Runtime.initRuntime();

        try {
            self.setUp();
        } catch (e) {
            result.addError(self, e);
            return result;
        }
        try {
            self[self._methodName]();
        } catch (e) {
            if (e instanceof Divmod.UnitTest.AssertionError) {
                result.addFailure(self, e);
            } else {
                result.addError(self, e);
            }
            success = false;
        }
        try {
            self.tearDown();
        } catch (e) {
            result.addError(self, e);
            success = false;
        }
        if (success) {
            result.addSuccess(self);
        }
        result.stopTest(self);
    });



/**
 * Return a nicely formatted summary from the given L{TestResult}.
 */
Divmod.UnitTest.formatSummary = function formatSummary(result) {
    var summary;
    if (result.wasSuccessful()) {
        summary = "PASSED "
    } else {
        summary = "FAILED "
    }
    summary += "(tests=" + result.testsRun;
    if (result.errors.length > 0) {
        summary += ", errors=" + result.errors.length
    }
    if (result.failures.length > 0) {
        summary += ", failures=" + result.failures.length;
    }
    summary += ')';
    return summary;
};



/**
 * Return a formatted string containing all the errors and failures in a result
 *
 * @param result: A test result.
 * @type result: L{Divmod.UnitTest.TestResult}
 */
Divmod.UnitTest.formatErrors = function formatErrors(result) {
    var format = '';
    for (var i = 0; i < result.errors.length; ++i) {
        format += Divmod.UnitTest.formatError('ERROR',
                                              result.errors[i][0],
                                              result.errors[i][1]);
    }
    for (var i = 0; i < result.failures.length; ++i) {
        format += Divmod.UnitTest.formatError('FAILURE',
                                              result.failures[i][0],
                                              result.failures[i][1]);
    }
    return format;
};



/**
 * Return a formatting string showing the failure/error that occurred in a test.
 *
 * @param test: A test which had a failure or error.
 * @type test: L{Divmod.UnitTest.TestCase}
 *
 * @param error: An error or failure which occurred in the test.
 * @type error: L{Divmod.Error}
 */
Divmod.UnitTest.formatError = function formatError(kind, test, error) {
    var f = Divmod.Defer.Failure(error);
    var ret = '[' + kind + '] ' + test.id() + ': ' + error.message + '\n';
    ret += f.toPrettyText(f.filteredParseStack()) + '\n';
    return ret;
};



/**
 * Run the given test, printing the summary of results and any errors. If run
 * inside a web browser, it will try to print these things to the printer, so
 * don't use this in a web browser.
 *
 * @param test: The test to run.
 * @type test: L{Divmod.UnitTest.TestCase} or L{Divmod.UnitTest.TestSuite}
 */
Divmod.UnitTest.run = function run(test) {
    var result = Divmod.UnitTest.TestResult()
    test.run(result);
    print(Divmod.UnitTest.formatErrors(result));
    print(Divmod.UnitTest.formatSummary(result));
};


Divmod.UnitTest.runRemote = function runRemote(test) {
    var result = Divmod.UnitTest.SubunitTestClient();
    test.run(result);
};


/**
 * Return a string representation of an arbitrary value, similar to
 * Python's builtin repr() function.
 */
Divmod.UnitTest.repr = function repr(value) {
    // We can't call methods on undefined or null.
    if (value === undefined) {
        return 'undefined';
    } else if (value === null) {
        return 'null';
    } else if (typeof value === 'string') {
        return '"' + value + '"';
    } else if (typeof value === 'number') {
        return '' + value;
    } else if (value.toSource !== undefined) {
        return value.toSource();
    } else if (value.toString !== undefined) {
        return value.toString();
    } else {
        return '' + value;
    }
};
