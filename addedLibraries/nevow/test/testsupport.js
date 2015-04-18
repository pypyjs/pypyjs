

/**
 * Run an Array of test methods.  Report success or failure for each.
 *
 * @type testFunctions: C{Array}
 * @param testFunctions: The zero-argument callables to invoke.
 *
 * @throw Error: If any element of C{testFunctions} throws an error, this
 * function will throw an error after running all of the other test functions.
 *
 * @return: C{undefined}
 */
function runTests(testFunctions) {
    var testFailures = 0;
    print("(JS)...");
    for (var i = 0; i < testFunctions.length; ++i) {
        try {
            testFunctions[i]();
            print("  " + testFunctions[i].name + "... \x1b[1;32m[OK]\x1b[0m");
        } catch (e) {
            print("  " + testFunctions[i].name + "... \x1b[1;31m[FAIL]\x1b[0m");
            print(e.message);
            print(e.stack);
            testFailures++;
        }
    }
    if (testFailures > 0) {
        throw new Error("***** FAILED *****");
    }
}

/**
 * Throw an error if the given object is true.
 *
 * @param a: The object of which to test the truth value.
 *
 * @param msg: An optional string which will used to create the thrown
 * Error if specified.
 *
 * @throw Error: If the given object is true, an error is thrown.
 *
 * @return: C{undefined}
 */
function failIf(a, msg) {
    if (a) {
        if (msg == undefined) {
            msg = a;
        }
        throw new Error(msg);
    }
}

/**
 * Throw an error if the given object is false.
 *
 * @param a: The object of which to test the truth value.
 *
 * @param msg: An optional string which will used to create the thrown
 * Error if specified.
 *
 * @throw Error: If the given object is false, an error is thrown.
 *
 * @return: C{undefined}
 */
function failUnless(a, msg) {
    if (!a) {
        if (msg == undefined) {
            msg = a;
        }
        throw new Error(msg);
    }
}

/**
 * Throw an error unless the given condition is true.
 *
 * @type cond: boolean
 * @param cond: The condition to test.
 *
 * @param err: A string describing the purpose of this assertion.
 *
 * @throw Error: If the given condition is false, an error is thrown.
 *
 * @return: C{undefined}
 */
function assert (cond, err) {
    if (!cond) {
        throw new Error("Test Failure: " + err);
    }
};


/**
 * Throw an error unless two objects compare equal.
 *
 * @param a: An object to compare to C{b}.
 *
 * @param b: An object to compare to C{a}.
 *
 * @throw Error: If the two objects do not compare equal, an error is thrown.
 *
 * @return: C{undefined}
 */
function assertEqual(a, b, msg) {
    if (a != b) {
        throw new Error(a + " != " + b + ": " + msg);
    }
};


/**
 * Throw an error unless a given function throws a particular error.
 *
 * @param expectedError: The error type (class or prototype) which is
 * expected to be thrown.
 *
 * @param callable: A no-argument callable which is expected to throw
 * C{expectedError}.
 *
 * @throw Error: If no error is thrown or the wrong error is thrown, an error
 * is thrown.
 *
 * @return: The error instance which was thrown.
 */
function assertThrows(expectedError, callable) {
    var threw;
    try {
        callable();
    } catch (error) {
        threw = error;
        assert(error instanceof expectedError, "Wrong error type thrown: " + error);
    }
    assert(threw !== undefined, "Callable threw no error.");
    return threw;
};


/**
 * Throw an error unless two arrays are equal to each other.
 *
 * @type a: C{Array}
 * @param a: An array to compare to C{b}.
 *
 * @type b: C{Array}
 * @param b: An array to compare to C{a}.
 *
 * @param elementComparison: A three-argument callable which, if specified,
 * will be used to compare the elements of the array to each other.  If not
 * specified, the == operator will be used.  The arguments should be like those
 * of C{assertEqual}.
 *
 * @throw Error: Thrown if either C{a} or C{b} is not an Array or if
 * C{a.length} is not equal to C{b.length} or if any of C{a[i]} is not equal to
 * C{b[i]} for C{0 <= i < a.length}.
 *
 * @return C{undefined}
 */
function assertArraysEqual(a, b, /* optional */ elementComparison) {
    assert(a instanceof Array, "First argument not an Array (" + a + ")");
    assert(b instanceof Array, "Second argument not an Array (" + b + ")");
    assertEqual(a.length, b.length, a.toSource() + " != " + b.toSource());

    if (elementComparison == undefined) {
        elementComparison = assertEqual;
    }

    for (var i = 0; i < a.length; ++i) {
        elementComparison(a[i], b[i], "Element " + i + " not equal");
    }
}


_testsupportDummyScheduler = [];
function setTimeout(f, n) {
    _testsupportDummyScheduler.push([n, f]);
}
