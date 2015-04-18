# -*- test-case-name: nevow.test.test_flatstan,nevow.test.test_later -*-
# Copyright (c) 2004,2008 Divmod.
# See LICENSE for details.

from twisted.internet import defer

from nevow import flat


def _isDeferred(d):
    """
    Flattener predicate for trampolining out when handling a Deferred.
    """
    return isinstance(d, defer.Deferred)


def _drive(iterable, finished):
    """
    Spin an iterable returned by L{nevow.flat.iterflatten}, setting up
    callbacks and errbacks on Deferreds it spits out so as to continue spinning
    it after those Deferreds fire.
    """
    try:
        next = iterable.next()
    except StopIteration:
        finished.callback('')
    except:
        finished.errback()
    else:
        deferred, returner = next
        def cb(result):
            """
            Pass the result of a Deferred on to the callable which is
            waiting for it and then resume driving the iterable.

            No one has any business whatsoever being on the callback chain
            after this callback, so we can swallow the Deferred's result to
            ease the garbage collector's job and for consistency with C{eb}
            below.
            """
            returner(result)
            _drive(iterable, finished)

        def eb(failure):
            """
            Handle asynchronous failures in the iterable by passing them on
            to the outer Deferred.  The iterable will not be resumed by this
            driver any further.

            Like C{cb} above, we swallow this result intentionally.  The
            only thing that could reasonably happen to it were we to return
            it here is for it to be logged as an unhandled Deferred, since
            we are supposed to be the last errback on the chain.
            """
            finished.errback(failure)

        deferred.addCallback(cb).addErrback(eb)


def deferflatten(stan, ctx, writer):
    finished = defer.Deferred()
    iterable = flat.iterflatten(stan, ctx, writer, _isDeferred)
    _drive(iterable, finished)
    return finished


def DeferredSerializer(original, context):
    """
    Serialize the result of the given Deferred without affecting its result.

    @type original: L{defer.Deferred}
    @param original: The Deferred being serialized.

    @rtype: L{defer.Deferred}
    @return: A Deferred which will be called back with the result of
        serializing the result of C{original} or which will errback if
        either C{original} errbacks or there is an error serializing the
        result of C{original}.
    """
    d = defer.Deferred()
    def cb(result):
        d2 = defer.maybeDeferred(flat.serialize, result, context)
        d2.chainDeferred(d)
        return result
    def eb(error):
        d.errback(error)
        return error
    original.addCallbacks(cb, eb)
    return d
