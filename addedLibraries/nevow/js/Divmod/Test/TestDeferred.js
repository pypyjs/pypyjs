/**
 * Tests for Divmod.Defer
 */


// import Divmod.Defer
// import Divmod.UnitTest


Divmod.Test.TestDeferred.TestFailure = Divmod.UnitTest.TestCase.subclass('TestFailure');
Divmod.Test.TestDeferred.TestFailure.methods(
    function setUp(self) {
        try {
            throw Divmod.Error("message");
        } catch (e) {
            self.failure = Divmod.Defer.Failure(e);
        }
    },


    /**
     * Check that we can format a 'frame', as returned from
     * L{Failure.parseStack}.
     */
    function test_frameToPrettyText(self) {
        var text = self.failure.frameToPrettyText({func: 'foo',
                                                   fname: 'Foo/foo.js',
                                                   lineNumber: 82});
        self.assertIdentical(text, '  Function "foo":\n    Foo/foo.js:82');
    },


    /**
     * Test that L{toPrettyText} returns a nicely formatted stack trace
     * that formats frames using L{Failure.frameToPrettyText}.
     */
    function test_toPrettyText(self) {
        var frames = self.failure.parseStack();
        var text = self.failure.toPrettyText();
        var lines = text.split('\n');
        self.assertIdentical(lines[0], 'Traceback (most recent call last):');
        self.assertIdentical(lines[lines.length - 1],
                             self.failure.error.toString());
        for (var i = 0; i < frames.length; ++i) {
            var expected = self.failure.frameToPrettyText(frames[i]);
            self.assertIdentical(lines[2*i+1] + '\n' + lines[2*i+2], expected);
        }
    },


    /**
     * Test that L{toPrettyText} uses its optional parameter as a source
     * of frames for the pretty stack trace.
     */
    function test_toPrettyTextOptional(self) {
        var frames = self.failure.filteredParseStack();
        var lines = self.failure.toPrettyText(frames).split('\n');
        for (var i = 0; i < frames.length; ++i) {
            var expected = self.failure.frameToPrettyText(frames[i]);
            self.assertIdentical(lines[2*i+1] + '\n' + lines[2*i+2], expected);
        };
    },


    /**
     * Test L{filteredParseStack}, which is designed to remove the superfluous
     * frames from the stacks.
     */
    function test_smartParse(self) {
        var allFrames = self.failure.parseStack();
        var relevantFrames = self.failure.filteredParseStack();
        var elidedFN, elidedLN;
        for (var i = 0; i < allFrames.length; ++i) {
            if (allFrames[i].fname == "" && allFrames[i].lineNumber == 0) {
                elidedFN = allFrames[i-1].fname;
                elidedLN = allFrames[i-1].lineNumber;
            }
        }
        for (var i = 0; i < relevantFrames.length; ++i) {
            var frame = relevantFrames[i];
            self.assert(frame.fname != "");
            self.assert(frame.lineNumber != 0);
            self.assert(frame.fname != elidedFN, "Found " + elidedFN);
            self.assert(frame.lineNumber != elidedLN, "Found " + elidedLN);
        }
    });



Divmod.Test.TestDeferred.TestDeferred = Divmod.UnitTest.TestCase.subclass('TestDeferred');
Divmod.Test.TestDeferred.TestDeferred.methods(
    function test_succeedDeferred(self) {
        var result = null;
        var error = null;
        var d = Divmod.Defer.succeed("success");
        d.addCallback(function(res) {
                result = res;
            });
        d.addErrback(function(err) {
                error = err;
            });
        self.assertIdentical(result, 'success');
        self.assertIdentical(error, null);
    },


    function test_failDeferred(self) {
        var result = null;
        var error = null;
        var d = Divmod.Defer.fail(Error("failure"));
        d.addCallback(function(res) {
                result = res;
            });
        d.addErrback(function(err) {
                error = err;
            });
        self.assertIdentical(result, null);
        self.assertIdentical(error.error.message, 'failure');
    },


    function test_callThisDontCallThat(self) {
        var thisCalled = false;
        var thatCalled = false;
        var thisCaller = function (rlst) { thisCalled = true; }
        var thatCaller = function (err) { thatCalled = true; }

        var d = new Divmod.Defer.Deferred();

        d.addCallbacks(thisCaller, thatCaller);
        d.callback(true);

        self.assert(thisCalled);
        self.assert(!thatCalled);

        thisCalled = thatCalled = false;

        d = new Divmod.Defer.Deferred();
        d.addCallbacks(thisCaller, thatCaller);
        d.errback(new Divmod.Defer.Failure(Error("Test error for errback testing")));

        self.assert(!thisCalled);
        self.assert(thatCalled);
    },


    function test_callbackResultPassedToNextCallback(self) {
        var interimResult = null;
        var finalResult = null;

        var d = new Divmod.Defer.Deferred();
        d.addCallback(function(result) {
                interimResult = result;
                return "final result";
            });
        d.addCallback(function(result) {
                finalResult = result;
            });
        d.callback("interim result");

        self.assertIdentical(interimResult, "interim result");
        self.assertIdentical(finalResult, "final result");
    },


    function test_addCallbacksAfterResult(self) {
        var callbackResult = null;
        var d = new Divmod.Defer.Deferred();
        d.callback("callback");
        d.addCallbacks(
            function(result) {
                callbackResult = result;
            });
        self.assertIdentical(callbackResult, "callback");
    },


    function test_deferredReturnedFromCallback(self) {
        var theResult = null;
        var interimDeferred = new Divmod.Defer.Deferred();
        var outerDeferred = new Divmod.Defer.Deferred();

        outerDeferred.addCallback(
            function(ignored) {
                return interimDeferred;
            });
        outerDeferred.addCallback(
            function(result) {
                theResult = result;
            });

        outerDeferred.callback("callback");
        self.assertIdentical(theResult, null,
                             "theResult got value too soon: " + theResult);

        interimDeferred.callback("final result");
        self.assertIdentical(theResult, "final result",
                             "theResult did not get final result: "
                             + theResult);
    },


    function test_deferredList(self) {
        var defr1 = new Divmod.Defer.Deferred();
        var defr2 = new Divmod.Defer.Deferred();
        var defr3 = new Divmod.Defer.Deferred();
        var dl = new Divmod.Defer.DeferredList([defr1, defr2, defr3]);

        var result;
        function cb(resultList) {
            result = resultList;
        };

        dl.addCallback(cb);
        defr1.callback("1");
        defr2.errback(new Error("2"));
        defr3.callback("3");

        assert(result.length == 3);
        assert(result[0].length == 2);
        assert(result[0][0]);
        assert(result[0][1] == "1");
        assert(result[1].length == 2);
        assert(!result[1][0]);
        assert(result[1][1] instanceof Divmod.Defer.Failure);
        assert(result[1][1].error.message == "2");
        assert(result[2].length == 2);
        assert(result[2][0]);
        assert(result[2][1] == "3");
    },


    /**
     * L{Divmod.Defer.DeferredList} should fire immediately if the list of
     * deferreds is empty.
     */
    function test_emptyDeferredList(self) {
        var result = null;
        var dl = new Divmod.Defer.DeferredList([]).addCallback(function(res) {
                result = res;
            });
        self.assert(result instanceof Array);
        self.assertIdentical(result.length, 0);
    },


    /**
     * L{Divmod.Defer.DeferredList} should fire immediately if the list of
     * deferreds is empty, even when C{fireOnOneErrback} is passed.
     */
    function test_emptyDeferredListErrback(self) {
        var result;
        Divmod.Defer.DeferredList([], false, true).addCallback(
            function(theResult) {
                result = theResult;
            });
        self.assert(result instanceof Array);
        self.assertIdentical(result.length, 0);
    },


    function test_fireOnOneCallback(self) {
        var result = null;
        var dl = new Divmod.Defer.DeferredList(
            [new Divmod.Defer.Deferred(), Divmod.Defer.succeed("success")],
            true, false, false);
        dl.addCallback(function(res) {
                result = res;
            });
        self.assert(result instanceof Array);
        self.assertArraysEqual(result, ['success', 1]);
    },


    function test_fireOnOneErrback(self) {
        var result = null;
        var dl = new Divmod.Defer.DeferredList(
            [new Divmod.Defer.Deferred(),
             Divmod.Defer.fail(new Error("failure"))],
            false, true, false);
        dl.addErrback(function(err) {
                result = err;
            });
        self.assert(result instanceof Divmod.Defer.Failure);
        self.assert(result.error instanceof Divmod.Defer.FirstError);
    },


    function test_gatherResults(self) {
        var result = null;
        var dl = Divmod.Defer.gatherResults([Divmod.Defer.succeed("1"),
                                             Divmod.Defer.succeed("2")]);
        dl.addCallback(function(res) {
                result = res;
            });
        self.assert(result instanceof Array);
        self.assertArraysEqual(result, ['1', '2']);
    });
