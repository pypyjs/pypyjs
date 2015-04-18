# -*- test-case-name: nevow.test.test_livepage -*-
# Copyright (c) 2004 Divmod.
# See LICENSE for details.

"""
Previous generation Nevow Comet support.  Do not use this module.

@see: L{nevow.athena}
"""

import itertools, types
import warnings

from zope.interface import implements, Interface

from twisted.internet import defer, error
from twisted.internet.task import LoopingCall
from twisted.python import log

from nevow import tags, inevow, context, static, flat, rend, url, util, stan

# If you need to debug livepage itself or your livepage app, set this to true
DEBUG = False

_jslog = None

def _openjslog():
    global _jslog
    if _jslog is None:
        _jslog = file("js.log", "w")
        _jslog.write("**********\n")
        _jslog.flush()
    return _jslog

def jslog(*x):
    if DEBUG:
        mylog = _openjslog()
        for y in x:
            mylog.write(str(y))
        mylog.flush()

class JavascriptContext(context.WovenContext):
    def __init__(self, parent=None, tag=None, isAttrib=None,
                inJSSingleQuoteString=None, remembrances=None):
        super(JavascriptContext, self).__init__(
            parent, tag, inJS=True, isAttrib=isAttrib,
            inJSSingleQuoteString=inJSSingleQuoteString,
            remembrances=None)


class TimeoutException(Exception):
    pass


class ClientSideException(Exception):
    pass


class SingleQuote(object):
    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.children)


def flattenSingleQuote(singleQuote, ctx):
    new = JavascriptContext(ctx, tags.invisible[singleQuote], inJSSingleQuoteString=True)
    return flat.serialize(singleQuote.children, new)
flat.registerFlattener(flattenSingleQuote, SingleQuote)


class _js(object):
    """
    Stan for Javascript. There is a convenience instance of this
    class named "js" in the livepage module which you should use
    instead of the _js class directly.

    Marker indicating literal Javascript should be rendered.
    No escaping will be performed.

    When inside a JavascriptContext, Nevow will automatically put
    apostrophe quote marks around any Python strings it renders.
    This makes turning a Python string into a JavaScript string very
    easy. However, there are often situations where you wish to
    generate some literal Javascript code and do not wish quote
    marks to be placed around it. In this situation, the js object
    should be used.

    The simplest usage is to simply pass a python string to js.
    When the js object is rendered, the python string will be
    rendered as if it were literal javascript. For example::

        client.send(js(\"alert('hello')\"))

    However, to make the generation of Javascript more
    convenient, the js object also provides safe implementations
    of __getattr__, __call__, and __getitem__. See the following
    examples to get an idea of how to use it. The Python code
    is to the left of the -> and the Javascript which results is
    to the right::

        js(\"alert('any javascript you like')\") -> alert('any javascript you like')

        js.window.title -> window.title

        js.document.getElementById('foo') -> document.getElementById('foo')

        js.myFunction('my argument') -> myFunction('my argument')

        js.myFunction(True, 5, \"it's a beautiful day\") -> myFunction(true, 5, 'it\\'s a beautiful day')

        js.document.all[\"something\"] -> document.all['something']

        js[1, 2] -> [1, 2]

    XXX TODO support javascript object literals somehow? (They look like dicts)
    perhaps like this::

        js[\"one\": 1, \"two\": 2] -> {\"one\": 1, \"two\": 2}

    The livepage module includes many convenient instances of the js object.
    It includes the literals::

        document
        window
        this
        self

    It includes shorthand for commonly called javascript functions::

        alert -> alert
        get -> document.getElementById
        set -> nevow_setNode
        append -> nevow_appendNode
        prepend -> nevow.prependNode
        insert -> nevow.insertNode

    It includes convenience calls against the client-side server object::

        server.handle('callMe') -> server.handle('callMe')

    It includes commonly-used fragments of javascript::

        stop -> ; return false;
        eol -> \\n

    Stop is used to prevent the browser from executing it's default
    event handler. For example::

        button(onclick=[server.handle('click'), stop]) -> <button onclick=\"server.handle('click'); return false;\" />

    EOL is currently required to separate statements (this requirement
    may go away in the future). For example::

        client.send([
            alert('hello'), eol,
            alert('goodbye')])

    XXX TODO: investigate whether rendering a \\n between list elements
    in a JavascriptContext has any ill effects.
    """

    def __init__(self, name=None):
        if name is None:
            name = []
        if isinstance(name, str):
            name = [stan.raw(name)]
        self._children = name

    def __getattr__(self, name):
        if name == 'clone':
            raise RuntimeError("Can't clone")
        if self._children:
            newchildren = self._children[:]
            newchildren.append(stan.raw('.'+name))
            return self.__class__(newchildren)
        return self.__class__(name)

    def __call__(self, *args):
        if not self._children:
            return self.__class__(args[0])
        newchildren = self._children[:]
        stuff = []
        for x in args:
            if isinstance(x, (
                basestring, stan.Tag, types.FunctionType,
                types.MethodType, types.UnboundMethodType)):
                x = stan.raw("'"), SingleQuote(x), stan.raw("'")
            stuff.append((x, stan.raw(',')))
        if stuff:
            stuff[-1] = stuff[-1][0]
        newchildren.extend([stan.raw('('), stuff, stan.raw(')')])
        return self.__class__(newchildren)

    def __getitem__(self, args):
        if not isinstance(args, (tuple, list)):
            args = (args,)
        newchildren = self._children[:]
        stuff = [(x, stan.raw(',')) for x in args]
        if stuff:
            stuff[-1] = stuff[-1][0]
        newchildren.extend([stan.raw("["), stuff, stan.raw("]")])
        return self.__class__(newchildren)

    def __iter__(self):
        """Prevent an infinite loop if someone tries to do
        for x in jsinstance:
        """
        raise NotImplementedError, "js instances are not iterable. (%r)" % (self, )

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self._children)
def flattenJS(theJS, ctx):
    new = JavascriptContext(ctx, tags.invisible[theJS])
    return flat.serialize(theJS._children, new)
flat.registerFlattener(flattenJS, _js)


js = _js()
document = _js('document')
get = document.getElementById
window = _js('window')
this = _js('this')
self = _js('self')
server = _js('server')
alert = _js('alert')
stop = _js('; return false;')
eol = tags.raw('\n')

set = js.nevow_setNode
append = js.nevow_appendNode
prepend = js.nevow_prependNode
insert = js.nevow_insertNode


def assign(where, what):
    """Assign what to where. Equivalent to
    where = what;
    """
    return _js([where, stan.raw(" = "), what])


setq = assign # hee


def var(where, what):
    """Define local variable 'where' and assign 'what' to it.
    Equivalent to var where = what;
    """
    return _js([stan.raw("var "), where, stan.raw(" = "), what, stan.raw(";")])


def anonymous(block):
    """
    Turn block (any stan) into an anonymous JavaScript function
    which takes no arguments. Equivalent to::

        function () {
            block
        }
    """
    return _js([stan.raw("function() {\n"), block, stan.raw("\n}")])


class IClientHandle(Interface):
    def hookupOutput(output, finisher=None):
        """hook up an output conduit to this live evil instance.
        """

    def send(script):
        """send a script through the output conduit to the browser.
        If no output conduit is yet hooked up, buffer the script
        until one is.
        """

    def handleInput(identifier, *args):
        """route some input from the browser to the appropriate
        destination.
        """


class IHandlerFactory(Interface):
    def locateHandler(ctx, name):
        """Locate a handler callable with the given name.
        """


class _transient(object):
    def __init__(self, transientId, arguments=None):
        self.transientId = transientId
        if arguments is None:
            arguments = []
        elif isinstance(arguments, tuple):
            arguments = list(arguments)
        else:
            raise TypeError, "Arguments must be None or tuple"
        self.arguments = arguments

    def __call__(self, *arguments):
        return type(self)(self.transientId, arguments)


def flattenTransient(transient, ctx):
    thing = js.server.handle("--transient.%s" % (transient.transientId, ), *transient.arguments)
    return flat.serialize(thing, ctx)
flat.registerFlattener(flattenTransient, _transient)


class ClientHandle(object):
    """An object which represents the client-side webbrowser.
    """
    implements(IClientHandle)

    outputConduit = None

    def __init__(self, livePage, handleId, refreshInterval, targetTimeoutCount):
        self.refreshInterval = refreshInterval
        self.targetTimeoutCount = targetTimeoutCount
        self.timeoutCount = 0
        self.livePage = livePage
        self.handleId = handleId
        self.outputBuffer = []
        self.bufferDeferreds = []
        self.closed = False
        self.closeNotifications = []
        self.firstTime = True
        self.timeoutLoop = LoopingCall(self.checkTimeout)
        if refreshInterval:
            self.timeoutLoop.start(self.refreshInterval)
        self._transients = {}
        self.transientCounter = itertools.count().next
        self.nextId = itertools.count().next ## For backwards compatibility with handler

    def transient(self, what, *args):
        """Register a transient event handler, 'what'.
        The callable 'what' can only be invoked by the
        client once before being garbage collected.
        Additional attempts to invoke the handler
        will fail.
        """
        transientId = str(self.transientCounter())
        self._transients[transientId] = what
        return _transient(transientId, args)

    def popTransient(self, transientId):
        """Remove a transient previously registered
        by a call to transient. Normally, this will be done
        automatically when the transient is invoked.
        However, you can invoke it yourself if you wish
        to revoke the client's capability to call the
        transient handler.
        """
        if DEBUG: print "TRANSIENTS", self._transients
        return self._transients.pop(transientId)

    def _actuallySend(self, scripts):
        output = self.outputConduit
        written = []
        def writer(write):
            #print "WRITER", write
            written.append(write)
        def finisher(finish):
            towrite = '\n'.join(written)
            jslog("<<<<<<\n%s\n" % towrite)
            output.callback(towrite)
        flat.flattenFactory(scripts, self.outputContext, writer, finisher)
        self.outputConduit = None
        self.outputContext = None

    def send(self, *script):
        """Send the stan "script", which can be flattened to javascript,
        to the browser which is connected to this handle, and evaluate
        it in the context of the browser window.
        """
        if self.outputConduit:
            self._actuallySend(script)
        else:
            self.outputBuffer.append(script)
            self.outputBuffer.append(eol)

    def setOutput(self, ctx, output):
        self.timeoutCount = 0
        self.outputContext = ctx
        self.outputConduit = output
        if self.outputBuffer:
            if DEBUG: print "SENDING BUFFERED", self.outputBuffer
            self._actuallySend(self.outputBuffer)
            self.outputBuffer = []

    def _actuallyPassed(self, result, deferreds):
        for d in deferreds:
            d.callback(result)

    def _actuallyFailed(self, failure, deferreds):
        for d in deferreds:
            d.errback(failure)

    def checkTimeout(self):
        if self.outputConduit is not None:
            ## The browser is waiting for us, send a noop.
            self.send(_js('null;'))
            return
        self.timeoutCount += 1
        if self.timeoutCount >= self.targetTimeoutCount:
            ## This connection timed out.
            self._closeComplete(
                TimeoutException(
                    "This connection did not ACK in at least %s seconds." % (
                        self.targetTimeoutCount * self.refreshInterval, )))

    def outputGone(self, failure, output):
#        assert output == self.outputConduit
        # Twisted errbacks with a ConnectionDone when the client closes the
        # connection cleanly. Pretend it didn't happen and carry on.
        self.outputConduit = None
        if failure.check(error.ConnectionDone):
            self._closeComplete()
        else:
            self._closeComplete(failure)
        return None

    def _closeComplete(self, failure=None):
        if self.closed:
            return
        self.closed = True
        self.timeoutLoop.stop()
        self.timeoutLoop = None
        for notify in self.closeNotifications[:]:
            if failure is not None:
                notify.errback(failure)
            else:
                notify.callback(None)
        self.closeNotifications = []

    def notifyOnClose(self):
        """This will return a Deferred that will be fired when the
        connection is closed 'normally', i.e. in response to handle.close()
        . If the connection is lost in any other way (because the browser
        navigated to another page, the browser was shut down, the network
        connection was lost, or the timeout was reached), this will errback
        instead."""
        d = defer.Deferred()
        self.closeNotifications.append(d)
        return d

    def close(self, executeScriptBeforeClose=""):
        if DEBUG: print "CLOSE WAS CALLED"
        d = self.notifyOnClose()
        self.send(js.nevow_closeLive(executeScriptBeforeClose))
        return d

    def set(self, where, what):
        self.send(js.nevow_setNode(where, what))

    def prepend(self, where, what):
        self.send(js.nevow_prependNode(where, what))

    def append(self, where, what):
        self.send(js.nevow_appendNode(where, what))

    def alert(self, what):
        self.send(js.alert(what))

    def call(self, what, *args):
        self.send(js(what)(*args))

    def sendScript(self, string):
        warnings.warn(
            "[0.5] nevow.livepage.ClientHandle.sendScript is deprecated, use send instead.",
            DeprecationWarning,
            2)
        self.send(string)


class DefaultClientHandleFactory(object):
    clientHandleClass = ClientHandle

    def __init__(self):
        self.clientHandles = {}
        self.handleCounter = itertools.count().next

    def newClientHandle(self, livePage, refreshInterval, targetTimeoutCount):
        handleid = str(self.handleCounter())
        handle = self.clientHandleClass(
            livePage, handleid, refreshInterval, targetTimeoutCount)
        self.clientHandles[handleid] = handle
        handle.notifyOnClose().addBoth(lambda ign: self.deleteHandle(handleid))
        return handle

    def deleteHandle(self, handleid):
        del self.clientHandles[handleid]

    def getHandleForId(self, handleId):
        """Override this to restore old handles on demand.
        """
        return self.clientHandles[handleId]

theDefaultClientHandleFactory = DefaultClientHandleFactory()


class OutputHandlerResource:
    implements(inevow.IResource)

    def __init__(self, clientHandle):
        self.clientHandle = clientHandle

    def locateChild(self, ctx, segments):
        raise NotImplementedError()

    def renderHTTP(self, ctx):
        request = inevow.IRequest(ctx)
        neverEverCache(request)
        activeChannel(request)
        ctx.remember(jsExceptionHandler, inevow.ICanHandleException)
        request.channel._savedTimeOut = None # XXX TODO
        d = defer.Deferred()
        request.notifyFinish().addErrback(self.clientHandle.outputGone, d)
        jsContext = JavascriptContext(ctx, tags.invisible())
        self.clientHandle.livePage.rememberStuff(jsContext)
        jsContext.remember(self.clientHandle, IClientHandle)
        if self.clientHandle.firstTime:
            self.clientHandle.livePage.goingLive(jsContext, self.clientHandle)
            self.clientHandle.firstTime = False
        self.clientHandle.setOutput(jsContext, d)
        return d


class InputHandlerResource:
    implements(inevow.IResource)

    def __init__(self, clientHandle):
        self.clientHandle = clientHandle

    def locateChild(self, ctx, segments):
        raise NotImplementedError()

    def renderHTTP(self, ctx):
        self.clientHandle.timeoutCount = 0

        request = inevow.IRequest(ctx)
        neverEverCache(request)
        activeChannel(request)
        ctx.remember(self.clientHandle, IClientHandle)
        ctx.remember(jsExceptionHandler, inevow.ICanHandleException)
        self.clientHandle.livePage.rememberStuff(ctx)

        handlerName = request.args['handler-name'][0]
        arguments = request.args.get('arguments', ())
        jslog(">>>>>>\n%s %s\n" % (handlerName, arguments))
        if handlerName.startswith('--transient.'):
            handler = self.clientHandle.popTransient(handlerName.split('.')[-1])
        else:
            handler = self.clientHandle.livePage.locateHandler(
                ctx, request.args['handler-path'],
                handlerName)

        jsContext = JavascriptContext(ctx, tags.invisible[handler])
        towrite = []

        def writer(r):
            jslog("WRITE ", r)
            towrite.append(r)

        def finisher(r):
            jslog("FINISHED", r)
            writestr = ''.join(towrite)
            jslog("<><><>\n%s\n" % (writestr, ))
            request.write(writestr)
            request.finish()
            return r

        result = handler(jsContext, *arguments)
        jslog("RESULT ", result)

        if result is None:
            return defer.succeed('')
        return self.clientHandle.livePage.flattenFactory(result, jsContext,
                                            writer, finisher)



class DefaultClientHandlesResource(object):
    implements(inevow.IResource)

    clientResources = {
        'input': InputHandlerResource,
        'output': OutputHandlerResource,
        }

    clientFactory = theDefaultClientHandleFactory

    def locateChild(self, ctx, segments):
        handleId = segments[0]
        handlerType = segments[1]
        client = self.clientFactory.clientHandles[handleId]

        return self.clientResources[handlerType](client), segments[2:]

theDefaultClientHandlesResource = DefaultClientHandlesResource()

class attempt(defer.Deferred):
    """
    Attempt to do 'stuff' in the browser. callback on the server
    if 'stuff' executes without raising an exception. errback on the
    server if 'stuff' raises a JavaScript exception in the client.

    Used like this::

        def printIt(what):
            print "Woo!", what

        C = IClientHandle(ctx)
        C.send(
            attempt(js("1+1")).addCallback(printIt))

        C.send(
            attempt(js("thisWillFail")).addErrback(printIt))
    """
    def __init__(self, stuff):
        self.stuff = stuff
        defer.Deferred.__init__(self)


def flattenAttemptDeferred(d, ctx):
    def attemptComplete(ctx, result, reason=None):
        if result == 'success':
            d.callback(None)
        else:
            d.errback(ClientSideException(reason))
    transient = IClientHandle(ctx).transient(attemptComplete)
    return flat.serialize([
_js("""try {
    """),
    d.stuff,
_js("""
    """),
    transient('success'),
_js("""
} catch (e) {
    """),
    transient('failure', js.e),
_js("}")
        ], ctx)
flat.registerFlattener(flattenAttemptDeferred, attempt)


class IOutputEvent(Interface):
    pass

class IInputEvent(Interface):
    pass


class ExceptionHandler(object):
    def renderHTTP_exception(self, ctx, failure):
        log.msg("Exception during input event:")
        log.err(failure)
        request = inevow.IRequest(ctx)
        request.write("throw new Error('Server side error: %s')" % (failure.getErrorMessage().replace("'", "\\'").replace("\n", "\\\n"), ))
        request.finish()

    def renderInlineException(self, ctx, reason):
        """TODO: I don't even think renderInlineException is ever called by anybody
        """
        pass


jsExceptionHandler = ExceptionHandler()


def neverEverCache(request):
    """ Set headers to indicate that the response to this request should never,
    ever be cached.
    """
    request.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate')
    request.setHeader('Pragma', 'no-cache')

def activeChannel(request):
    """Mark this connection as a 'live' channel by setting the Connection: close
    header and flushing all headers immediately.
    """
    request.setHeader("Connection", "close")
    request.write('')

class LivePage(rend.Page):
    """
    A Page which is Live provides asynchronous, bidirectional RPC between
    Python on the server and JavaScript in the client browser. A LivePage must
    include the "liveglue" JavaScript which includes a unique identifier which
    is assigned to every page render of a LivePage and the JavaScript required
    for the client to communicate asynchronously with the server.

    A LivePage grants the client browser the capability of calling server-side
    Python methods using a small amount of JavaScript code. There are two
    types of Python handler methods, persistent handlers and transient handlers.

      - To grant the client the capability to call a persistent handler over and over
        as many times as it wishes, subclass LivePage and provide handle_foo
        methods. The client can then call handle_foo by executing the following
        JavaScript::

          server.handle('foo')

        handle_foo will be invoked because the default implementation of
        locateHandler looks for a method prefixed handle_*. To change this,
        override locateHandler to do what you wish.

      - To grant the client the capability of calling a handler once and
        exactly once, use ClientHandle.transient to register a callable and
        embed the return result in a page to render JavaScript which will
        invoke the transient handler when executed. For example::

            def render_clickable(self, ctx, data):
                def hello(ctx):
                    return livepage.alert(\"Hello, world. You can only click me once.\")

                return ctx.tag(onclick=IClientHandle(ctx).transient(hello))

        The return result of transient can also be called to pass additional
        arguments to the transient handler. For example::

            def render_choice(self, ctx, data):
                def chosen(ctx, choseWhat):
                    return livepage.set(
                        \"choosable\",
                        [\"Thanks for choosing \", choseWhat])

                chooser = IClientHandle(ctx).transient(chosen)

                return span(id=\"choosable\")[
                    \"Choose one:\",
                    p(onclick=chooser(\"one\"))[\"One\"],
                    p(onclick=chooser(\"two\"))[\"Two\"]]

        Note that the above situation displays temporary UI to the
        user. When the user invokes the chosen handler, the UI which
        allowed the user to invoke the chosen handler is removed from
        the client. Thus, it is important that the transient registration
        is deleted once it is invoked, otherwise uncollectable garbage
        would accumulate in the handler dictionary. It is also important
        that either the one or the two button consume the same handler,
        since it is an either/or choice. If two handlers were registered,
        the untaken choice would be uncollectable garbage.
    """
    refreshInterval = 30
    targetTimeoutCount = 3

    clientFactory = theDefaultClientHandleFactory

    def renderHTTP(self, ctx):
        if not self.cacheable:
            neverEverCache(inevow.IRequest(ctx))
        return rend.Page.renderHTTP(self, ctx)

    def locateHandler(self, ctx, path, name):
        ### XXX TODO: Handle path
        return getattr(self, 'handle_%s' % (name, ))

    def goingLive(self, ctx, handle):
        """This particular LivePage instance is 'going live' from the
        perspective of the ClientHandle 'handle'. Override this to
        get notified when a new browser window observes this page.

        This means that a new user is now looking at the page, an old
        user has refreshed the page, or an old user has opened a new
        window or tab onto the page.

        This is the first time the ClientHandle instance is available
        for general use by the server. This Page may wish to keep
        track of the ClientHandle instances depending on how your
        application is set up.
        """
        pass

    def child_livepage_client(self, ctx):
        return theDefaultClientHandlesResource

    # child_nevow_glue.js = static.File # see below

    def render_liveid(self, ctx, data):
        warnings.warn("You don't need a liveid renderer any more; just liveglue is fine.",
                      DeprecationWarning)
        return ''

    cacheable = False           # Set this to true to use ***HIGHLY***
                                # EXPERIMENTAL lazy ID allocation feature,
                                # which will allow your LivePage instances to
                                # be cached by clients.

    def render_liveglue(self, ctx, data):
        if not self.cacheable:
            handleId = "'", self.clientFactory.newClientHandle(
                self,
                self.refreshInterval,
                self.targetTimeoutCount).handleId, "'"
        else:
            handleId = 'null'

        return [
            tags.script(type="text/javascript")[
                "var nevow_clientHandleId = ", handleId ,";"],
            tags.script(type="text/javascript",
                        src=url.here.child('nevow_glue.js'))
            ]


setattr(
    LivePage,
    'child_nevow_glue.js',
    static.File(
        util.resource_filename('nevow', 'liveglue.js'),
        'text/javascript'))


glue = tags.directive('liveglue')




##### BACKWARDS COMPATIBILITY CODE


ctsTemplate = "nevow_clientToServerEvent('%s',this,''%s)%s"
handledEventPostlude = '; return false;'


class handler(object):
    callme = None
    args = ()
    identifier = None
    def __init__(self, *args, **kw):
        """**DEPRECATED** [0.5]

        Handler is now deprecated. To expose server-side code to the client
        to be called by JavaScript, read the LivePage docstring.
        """
        warnings.warn(
            "[0.5] livepage.handler is deprecated; Provide handle_foo methods (or override locateHandler) on your LivePage and use (in javascript) server.handle('foo'), or use ClientHandle.transient to register a one-shot handler capability.",
            DeprecationWarning,
            2)
        ## Handle working like a 2.4 decorator where calling handler returns a decorator
        if not callable(args[0]) or isinstance(args[0], _js):
            self.args = args
            return
        self.callme = args[0]
        self(*args[1:], **kw)

    def __call__(self, *args, **kw):
        if self.callme is None:
            self.callme = args[0]
            args = args[1:]

        self.args += args
        self.outsideAttribute = kw.get('outsideAttribute')
        bubble = kw.get('bubble')
        if bubble:
            self.postlude = ';'
        else:
            self.postlude = handledEventPostlude

        if 'identifier' in kw:
            self.identifier = kw['identifier']

        return self

    content = property(lambda self: flt(self))


def flattenHandler(handler, ctx):
    client = IClientHandle(ctx)
    iden = handler.identifier
    if iden is None:
        iden = client.nextId()
    iden = '--handler-%s' % (iden, )
    ## TODO this should be the IHandlerFactory instead of IResource
    setattr(IHandlerFactory(ctx), 'handle_%s' % (iden, ), handler.callme)
    isAttrib = not handler.outsideAttribute
    new = JavascriptContext(ctx, tags.invisible[handler.args], isAttrib=isAttrib)

    rv = flat.flatten(
        js.nevow_clientToServerEvent(*(iden, this, '') + handler.args),
        new)
    rv += handler.postlude
    return tags.xml(rv)
flat.registerFlattener(flattenHandler, handler)


def flt(stan, quote=True, client=None, handlerFactory=None):
    """Flatten some stan to a string suitable for embedding in a javascript
    string.

    If quote is True, apostrophe, quote, and newline will be quoted
    """
    warnings.warn("[0.5] livepage.flt is deprecated. Don't use it.", DeprecationWarning, 2)
    from nevow import testutil
    fr = testutil.FakeRequest()
    ctx = context.RequestContext(tag=fr)
    ctx.remember(client, IClientHandle)
    ctx.remember(handlerFactory, IHandlerFactory)
    ctx.remember(None, inevow.IData)

    fl = flat.flatten(stan, ctx=ctx)
    if quote:
        fl = fl.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
    return fl
