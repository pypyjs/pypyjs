// -*- test-case-name: nevow.test.test_javascript -*-

// import Divmod

Divmod.Defer.AlreadyCalledError = Divmod.Class.subclass("Divmod.Defer.AlreadyCalledError");

Divmod.Defer.Failure = Divmod.Class.subclass("Divmod.Defer.Failure");
Divmod.Defer.Failure.methods(
    function __init__(self, error) {
        self.error = error;
    },

    /**
     * Return the underlying Error instance if it is an instance of the given
     * error class, otherwise return null;
     */
    function check(self, errorType) {
        if (self.error instanceof errorType) {
            return self.error;
        }
        return null;
    },

    function toString(self) {
        return 'Failure: ' + self.error;
    },

    function parseStack(self) {
        var stackString = self.error.stack;
        var frames = [];

        var line;
        var parts;
        var func;
        var rest;
        var divide;
        var fname;
        var lineNumber;
        var lines = stackString.split('\n');
        for (var i = 0, line = lines[i]; i < lines.length; ++i, line = lines[i]) {
            if (line.indexOf('@') == -1) {
                continue;
            }

            parts = line.split('@', 2);
            func = parts.shift();
            rest = parts.shift();

            divide = rest.lastIndexOf(':');
            if (divide == -1) {
                fname = rest;
                lineNumber = 0;
            } else {
                fname = rest.substr(0, divide);
                lineNumber = parseInt(rest.substr(divide + 1, rest.length));
            }
            frames.unshift({func: func, fname: fname, lineNumber: lineNumber});
        }
        return frames;
    },


    /**
     * Return a list of 'frames' from the stack, with many of the frames
     * filtered out. The removed frames are those which are added for every
     * single method call.
     *
     * @return: [{fname: <filename as string>,
     *            lineNumber: <line number as int>,
     *            func: <function that the frame is inside as string>}]
     */
    function filteredParseStack(self) {
        var frames = self.parseStack();
        var ret = [];
        for (var i = 0; i < frames.length; ++i) {
            var f = frames[i];
            if (f.fname == "" && f.lineNumber == 0) {
                ret.pop();
                continue;
            }
            ret.push(f);
        };
        return ret;
    },


    /**
     * Format a single frame from L{Failure.filteredParseStack} as a pretty
     * string.
     *
     * @return: string
     */
    function frameToPrettyText(self, frame) {
        return '  Function "' + frame.func + '":\n    ' + frame.fname + ':'
            + frame.lineNumber;
    },


    /**
     * Return a nicely formatted stack trace using L{Failure.frameToPrettyText}.
     */
    function toPrettyText(self, /* optional */ frames) {
        if (frames == undefined) {
            frames = self.parseStack();
        }
        var ret = 'Traceback (most recent call last):\n';
        for (var i = 0; i < frames.length; ++i) {
            ret += self.frameToPrettyText(frames[i]) + '\n';
        }
        return ret + self.error;
    },


    function toPrettyNode(self) {
        var stack = self.error.stack;
        if (!stack) {
            return document.createTextNode(self.toString());
        }

        var frames = self.parseStack();
        var resultNode = document.createElement('div');
        resultNode.style.overflow = 'scroll';
        resultNode.style.height = 640;
        resultNode.style.width = 480;
        var frameNode;
        for (var i = 0, f = frames[i]; i < frames.length; ++i, f = frames[i]) {
            if (f.lineNumber == 0) {
                continue;
            }
            frameNode = document.createElement('div');
            frameNode.appendChild(document.createTextNode(f.fname + '|' + f.lineNumber));
            resultNode.appendChild(frameNode);
            frameNode = document.createElement('div');
            frameNode.appendChild(document.createTextNode(f.func));
            resultNode.appendChild(frameNode);
        }
        return resultNode;
    });

Divmod.Defer.Deferred = Divmod.Class.subclass("Divmod.Defer.Deferred");

Divmod.Defer.Deferred.methods(
    function __init__(self) {
        self._callbacks = [];
        self._called = false;
        self._pauseLevel = 0;
    },
    function addCallbacks(self, callback, errback,
                          callbackArgs, errbackArgs) {
        if (!callbackArgs) {
            callbackArgs = [];
        }
        if (!errbackArgs) {
            errbackArgs = [];
        }
        self._callbacks.push([callback, errback, callbackArgs, errbackArgs]);
        if (self._called) {
            self._runCallbacks();
        }
        return self;
    },
    function addCallback(self, callback) {
        var callbackArgs = [];
        for (var i = 2; i < arguments.length; ++i) {
            callbackArgs.push(arguments[i]);
        }
        self.addCallbacks(callback, null, callbackArgs, null);
        return self;
    },
    function addErrback(self, errback) {
        var errbackArgs = [];
        for (var i = 2; i < arguments.length; ++i) {
            errbackArgs.push(arguments[i]);
        }
        self.addCallbacks(null, errback, null, errbackArgs);
        return self;
    },
    function addBoth(self, callback) {
        var callbackArgs = [];
        for (var i = 2; i < arguments.length; ++i) {
            callbackArgs.push(arguments[i]);
        }
        self.addCallbacks(callback, callback, callbackArgs, callbackArgs);
        return self;
    },
    function _pause(self) {
        self._pauseLevel++;
    },
    function _unpause(self) {
        self._pauseLevel--;
        if (self._pauseLevel) {
            return;
        }
        if (!self._called) {
            return;
        }
        self._runCallbacks();
    },
    function _isFailure(self, obj) {
        return (obj instanceof Divmod.Defer.Failure);
    },
    function _isDeferred(self, obj) {
        return (obj instanceof Divmod.Defer.Deferred);
    },
    function _continue(self, result) {
        self._result = result;
        self._unpause();
    },
    function _runCallbacks(self) {
        if (!self._pauseLevel) {
            var cb = self._callbacks;
            self._callbacks = [];
            while (cb.length) {
                var item = cb.shift();
                if (self._isFailure(self._result)) {
                    var callback = item[1];
                    var args = item[3];
                } else {
                    var callback = item[0];
                    var args = item[2];
                }

                if (callback == null) {
                    continue;
                }

                args.unshift(self._result);
                try {
                    self._result = callback.apply(null, args);
                    if (self._isDeferred(self._result)) {
                        self._callbacks = cb;
                        self._pause();
                        self._result.addBoth(function (r) {
                                self._continue(r);
                            });
                        break;
                    }
                } catch (e) {
                    self._result = Divmod.Defer.Failure(e);
                }
            }
        }

        if (self._isFailure(self._result)) {
            // This might be spurious
            Divmod.err(self._result.error);
        }
    },
    function _startRunCallbacks(self, result) {
        if (self._called) {
            throw new Divmod.Defer.AlreadyCalledError();
        }
        self._called = true;
        self._result = result;
        self._runCallbacks();
    },
    function callback(self, result) {
        self._startRunCallbacks(result);
    },
    function errback(self, err) {
        if (!self._isFailure(err)) {
            err = new Divmod.Defer.Failure(err);
        }
        self._startRunCallbacks(err);
    });

Divmod.Defer.succeed = function succeed(result) {
    var d = new Divmod.Defer.Deferred();
    d.callback(result);
    return d;
};

Divmod.Defer.fail = function fail(err) {
    var d = new Divmod.Defer.Deferred();
    d.errback(err);
    return d;
};


/**
 * First error to occur in a DeferredList if fireOnOneErrback is set.
 *
 * @ivar err: the L{Divmod.Defer.Failure} that occurred.
 *
 * @ivar index: the index of the Deferred in the DeferredList where it
 * happened.
 */
Divmod.Defer.FirstError = Divmod.Error.subclass('Divmod.Defer.FirstError');
Divmod.Defer.FirstError.methods(
    function __init__(self, err, index) {
        Divmod.Defer.FirstError.upcall(self, '__init__');
        self.err = err;
        self.index = index;
    },

    function toString(self) {
        return '<FirstError @ ' + self.index + ': ' + self.err.toString() + '>';
    });

/*
 * I combine a group of deferreds into one callback.
 *
 * I track a list of L{Deferred}s for their callbacks, and make a single
 * callback when they have all completed, a list of (success, result) tuples,
 * 'success' being a boolean.
 *
 * Note that you can still use a L{Deferred} after putting it in a
 * DeferredList.  For example, you can suppress 'Unhandled error in Deferred'
 * messages by adding errbacks to the Deferreds *after* putting them in the
 * DeferredList, as a DeferredList won't swallow the errors.  (Although a more
 * convenient way to do this is simply to set the consumeErrors flag)
 */
Divmod.Defer.DeferredList = Divmod.Defer.Deferred.subclass('Divmod.Defer.DeferredList');
Divmod.Defer.DeferredList.methods(
    /* Initialize a DeferredList.
     *
     * @type deferredList: C{Array} of L{Divmod.Defer.Deferred}s
     *
     * @param deferredList: The list of deferreds to track.
     *
     * @param fireOnOneCallback: A flag indicating that only one callback needs
     * to be fired for me to call my callback.
     *
     * @param fireOnOneErrback: A flag indicating that only one errback needs to
     * be fired for me to call my errback.
     *
     * @param consumeErrors: A flag indicating that any errors raised in the
     * original deferreds should be consumed by this DeferredList.  This is
     * useful to prevent spurious warnings being logged.
     */
    function __init__(self,
                      deferredList,
                      /* optional */
                      fireOnOneCallback /* = false */,
                      fireOnOneErrback /* = false */,
                      consumeErrors /* = false */) {
        self.resultList = new Array(deferredList.length);
        Divmod.Defer.DeferredList.upcall(self, '__init__');
        // don't callback in the fireOnOneCallback case because the result
        // type is different.
        if (deferredList.length == 0 && !fireOnOneCallback) {
            self.callback(self.resultList);
        }

        if (fireOnOneCallback == undefined) {
            fireOnOneCallback = false;
        }

        if (fireOnOneErrback == undefined) {
            fireOnOneErrback = false;
        }

        if (consumeErrors == undefined) {
            consumeErrors = false;
        }

        /* These flags need to be set *before* attaching callbacks to the
         * deferreds, because the callbacks use these flags, and will run
         * synchronously if any of the deferreds are already fired.
         */
        self.fireOnOneCallback = fireOnOneCallback;
        self.fireOnOneErrback = fireOnOneErrback;
        self.consumeErrors = consumeErrors;
        self.finishedCount = 0;

        for (var index = 0; index < deferredList.length; ++index) {
            deferredList[index].addCallbacks(function(result, index) {
                self._cbDeferred(result, true, index);
            }, function(err, index) {
                self._cbDeferred(err, false, index);
            }, [index], [index]);
        }
    },

    function _cbDeferred(self, result, success, index) {
        self.resultList[index] = [success, result];

        self.finishedCount += 1;
        if (!self._called) {
            if (success && self.fireOnOneCallback) {
                self.callback([result, index]);
            } else if (!success && self.fireOnOneErrback) {
                self.errback(new Divmod.Defer.FirstError(result, index));
            } else if (self.finishedCount == self.resultList.length) {
                self.callback(self.resultList);
            }
        }

        if (!success && self.consumeErrors) {
            return null;
        } else {
            return result;
        }
    });


/* Returns list with result of given Deferreds.
 *
 * This builds on C{DeferredList} but is useful since you don't need to parse
 * the result for success/failure.
 *
 * @type deferredList: C{Array} of L{Divmod.Defer.Deferred}s
 */
Divmod.Defer.gatherResults = function gatherResults(deferredList) {
    var d = new Divmod.Defer.DeferredList(deferredList, false, true, false);
    d.addCallback(function(results) {
        var undecorated = [];
        for (var i = 0; i < results.length; ++i) {
            undecorated.push(results[i][1]);
        }
        return undecorated;
    });
    return d;
};
