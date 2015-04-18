# -*- test-case-name: nevow.test.test_athena -*-

import itertools, os, re, warnings

from zope.interface import implements

from twisted.internet import defer, error, reactor
from twisted.python import log, failure, context
from twisted.python.util import sibpath
from twisted import plugin

from nevow import inevow, plugins, flat, _flat
from nevow import rend, loaders, static
from nevow import json, util, tags, guard, stan
from nevow.util import CachedFile
from nevow.useragent import UserAgent, browsers
from nevow.url import here, URL

from nevow.page import Element, renderer

ATHENA_XMLNS_URI = "http://divmod.org/ns/athena/0.7"
ATHENA_RECONNECT = "__athena_reconnect__"

expose = util.Expose(
    """
    Allow one or more methods to be invoked by the client::

    | class Foo(LiveElement):
    |     def twiddle(self, x, y):
    |         ...
    |     def frob(self, a, b):
    |         ...
    |     expose(twiddle, frob)

    The Widget for Foo will be allowed to invoke C{twiddle} and C{frob}.
    """)



class OrphanedFragment(Exception):
    """
    Raised when an operation requiring a parent is attempted on an unattached
    child.
    """



class LivePageError(Exception):
    """
    Base exception for LivePage errors.
    """
    jsClass = u'Divmod.Error'



class NoSuchMethod(LivePageError):
    """
    Raised when an attempt is made to invoke a method which is not defined or
    exposed.
    """
    jsClass = u'Nevow.Athena.NoSuchMethod'

    def __init__(self, objectID, methodName):
        self.objectID = objectID
        self.methodName = methodName
        LivePageError.__init__(self, objectID, methodName)



def neverEverCache(request):
    """
    Set headers to indicate that the response to this request should never,
    ever be cached.
    """
    request.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate')
    request.setHeader('Pragma', 'no-cache')


def activeChannel(request):
    """
    Mark this connection as a 'live' channel by setting the Connection: close
    header and flushing all headers immediately.
    """
    request.setHeader("Connection", "close")
    request.write('')



class MappingResource(object):
    """
    L{inevow.IResource} which looks up segments in a mapping between symbolic
    names and the files they correspond to. 

    @type mapping: C{dict}
    @ivar mapping: A map between symbolic, requestable names (eg,
    'Nevow.Athena') and C{str} instances which name files containing data
    which should be served in response.
    """
    implements(inevow.IResource)

    def __init__(self, mapping):
        self.mapping = mapping


    def renderHTTP(self, ctx):
        return rend.FourOhFour()


    def resourceFactory(self, fileName):
        """
        Retrieve an L{inevow.IResource} which will render the contents of
        C{fileName}.
        """
        return static.File(fileName)


    def locateChild(self, ctx, segments):
        try:
            impl = self.mapping[segments[0]]
        except KeyError:
            return rend.NotFound
        else:
            return self.resourceFactory(impl), []



def _dependencyOrdered(coll, memo):
    """
    @type coll: iterable of modules
    @param coll: The initial sequence of modules.

    @type memo: C{dict}
    @param memo: A dictionary mapping module names to their dependencies that
                 will be used as a mutable cache.
    """



class AthenaModule(object):
    """
    A representation of a chunk of stuff in a file which can depend on other
    chunks of stuff in other files.
    """
    _modules = {}

    lastModified = 0
    deps = None
    packageDeps = []

    def getOrCreate(cls, name, mapping):
        # XXX This implementation of getOrCreate precludes the
        # simultaneous co-existence of several different package
        # namespaces.
        if name in cls._modules:
            return cls._modules[name]
        mod = cls._modules[name] = cls(name, mapping)
        return mod
    getOrCreate = classmethod(getOrCreate)


    def __init__(self, name, mapping):
        self.name = name
        self.mapping = mapping

        if '.' in name:
            parent = '.'.join(name.split('.')[:-1])
            self.packageDeps = [self.getOrCreate(parent, mapping)]

        self._cache = CachedFile(self.mapping[self.name], self._getDeps)


    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name,)


    _importExpression = re.compile('^// import (.+)$', re.MULTILINE)
    def _extractImports(self, fileObj):
        s = fileObj.read()
        for m in self._importExpression.finditer(s):
            yield self.getOrCreate(m.group(1).decode('ascii'), self.mapping)



    def _getDeps(self, jsFile):
        """
        Calculate our dependencies given the path to our source.
        """
        depgen = self._extractImports(file(jsFile, 'rU'))
        return self.packageDeps + dict.fromkeys(depgen).keys()


    def dependencies(self):
        """
        Return a list of names of other JavaScript modules we depend on.
        """
        return self._cache.load()


    def allDependencies(self, memo=None):
        """
        Return the transitive closure of dependencies, including this module.

        The transitive dependencies for this module will be ordered such that
        any particular module is located after all of its dependencies, with no
        module occurring more than once.

        The dictionary passed in for C{memo} will be modified in-place; if it
        is reused across multiple calls, dependencies calculated during a
        previous invocation will not be recalculated again.

        @type memo: C{dict} of C{str: list of AthenaModule}
        @param memo: A dictionary mapping module names to the modules they
                     depend on that will be used as a mutable cache.

        @rtype: C{list} of C{AthenaModule}
        """
        if memo is None:
            memo = {}
        ordered = []

        def _getDeps(dependent):
            if dependent.name in memo:
                deps = memo[dependent.name]
            else:
                memo[dependent.name] = deps = dependent.dependencies()
            return deps

        def _insertDep(dependent):
            if dependent not in ordered:
                for dependency in _getDeps(dependent):
                    _insertDep(dependency)
                ordered.append(dependent)

        _insertDep(self)
        return ordered



class JSModule(AthenaModule):
    """
    L{AthenaModule} subclass for dealing with Javascript modules.
    """
    _modules= {}



class CSSModule(AthenaModule):
    """
    L{AthenaModule} subclass for dealing with CSS modules.
    """
    _modules = {}



class JSPackage(object):
    """
    A Javascript package.

    @type mapping: C{dict}
    @ivar mapping: Mapping between JS module names and C{str} representing
    filesystem paths containing their implementations.
    """
    implements(plugin.IPlugin, inevow.IJavascriptPackage)

    def __init__(self, mapping):
        self.mapping = mapping



def _collectPackageBelow(baseDir, extension):
    """
    Assume a filesystem package hierarchy starting at C{baseDir}.  Collect all
    files within it ending with C{extension} into a mapping between
    dot-separated symbolic module names and their corresponding filesystem
    paths.

    Note that module/package names beginning with . are ignored.

    @type baseDir: C{str}
    @param baseDir: A path to the root of a package hierarchy on a filesystem.

    @type extension: C{str}
    @param extension: The filename extension we're interested in (e.g. 'css'
    or 'js').

    @rtype: C{dict}
    @return: Mapping between C{unicode} module names and their corresponding
    C{str} filesystem paths.
    """
    mapping = {}
    EMPTY = sibpath(__file__, 'empty-module.' + extension)

    _revMap = {baseDir: ''}
    for (root, dirs, filenames) in os.walk(baseDir):
        stem = _revMap[root]
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for dir in dirs:
            name = stem + dir
            path = os.path.join(root, dir, '__init__.' + extension)
            if not os.path.exists(path):
                path = EMPTY
            mapping[unicode(name, 'ascii')] = path
            _revMap[os.path.join(root, dir)] = name + '.'

        for fn in filenames:
            if fn.startswith('.'):
                continue

            if fn == '__init__.' + extension:
                continue

            if not fn.endswith('.' + extension):
                continue

            name = stem + fn[:-(len(extension) + 1)]
            path = os.path.join(root, fn)
            mapping[unicode(name, 'ascii')] = path
    return mapping



class AutoJSPackage(object):
    """
    A L{inevow.IJavascriptPackage} implementation that scans an on-disk
    hierarchy locating modules and packages.

    @type baseDir: C{str}
    @ivar baseDir: A path to the root of a JavaScript packages/modules
    filesystem hierarchy.
    """
    implements(plugin.IPlugin, inevow.IJavascriptPackage)

    def __init__(self, baseDir):
        self.mapping = _collectPackageBelow(baseDir, 'js')



class AutoCSSPackage(object):
    """
    Like L{AutoJSPackage}, but for CSS packages.  Modules within this package
    can be referenced by L{LivePage.cssModule} or L{LiveElement.cssModule}.
    """
    implements(plugin.IPlugin, inevow.ICSSPackage)

    def __init__(self, baseDir):
        self.mapping = _collectPackageBelow(baseDir, 'css')



def allJavascriptPackages():
    """
    Return a dictionary mapping JavaScript module names to local filenames
    which implement those modules.  This mapping is constructed from all the
    C{IJavascriptPackage} plugins available on the system.  It also includes
    C{Nevow.Athena} as a special case.
    """
    d = {}
    for p in plugin.getPlugIns(inevow.IJavascriptPackage, plugins):
        d.update(p.mapping)
    return d



def allCSSPackages():
    """
    Like L{allJavascriptPackages}, but for CSS packages.
    """
    d = {}
    for p in plugin.getPlugIns(inevow.ICSSPackage, plugins):
        d.update(p.mapping)
    return d



class JSDependencies(object):
    """
    Keeps track of which JavaScript files depend on which other
    JavaScript files (because JavaScript is a very poor language and
    cannot do this itself).
    """
    _loadPlugins = False

    def __init__(self, mapping=None):
        if mapping is None:
            self.mapping = {}
            self._loadPlugins = True
        else:
            self.mapping = mapping


    def getModuleForName(self, className):
        """
        Return the L{JSModule} most likely to define the given name.
        """
        if self._loadPlugins:
            self.mapping.update(allJavascriptPackages())
            self._loadPlugins = False

        jsMod = className
        while jsMod:
            try:
                self.mapping[jsMod]
            except KeyError:
                if '.' not in jsMod:
                    break
                jsMod = '.'.join(jsMod.split('.')[:-1])
            else:
                return JSModule.getOrCreate(jsMod, self.mapping)
        raise RuntimeError("Unknown class: %r" % (className,))
    getModuleForClass = getModuleForName


jsDeps = JSDependencies()



class CSSRegistry(object):
    """
    Keeps track of a set of CSS modules.
    """
    def __init__(self, mapping=None):
        if mapping is None:
            mapping = {}
            loadPlugins = True
        else:
            loadPlugins = False
        self.mapping = mapping
        self._loadPlugins = loadPlugins


    def getModuleForName(self, moduleName):
        """
        Turn a CSS module name into an L{AthenaModule}.

        @type moduleName: C{unicode}

        @rtype: L{CSSModule}
        """
        if self._loadPlugins:
            self.mapping.update(allCSSPackages())
            self._loadPlugins = False
        try:
            self.mapping[moduleName]
        except KeyError:
            raise RuntimeError('Unknown CSS module: %r' % (moduleName,))
        return CSSModule.getOrCreate(moduleName, self.mapping)

_theCSSRegistry = CSSRegistry()



class JSException(Exception):
    """
    Exception class to wrap remote exceptions from JavaScript.
    """



class JSCode(object):
    """
    Class for mock code objects in mock JS frames.
    """
    def __init__(self, name, filename):
        self.co_name = name
        self.co_filename = filename



class JSFrame(object):
    """
    Class for mock frame objects in JS client-side traceback wrappers.
    """
    def __init__(self, func, fname, ln):
        self.f_back = None
        self.f_locals = {}
        self.f_globals = {}
        self.f_code = JSCode(func, fname)
        self.f_lineno = ln



class JSTraceback(object):
    """
    Class for mock traceback objects representing client-side JavaScript
    tracebacks.
    """
    def __init__(self, frame, ln):
        self.tb_frame = frame
        self.tb_lineno = ln
        self.tb_next = None



def parseStack(stack):
    """
    Extract function name, file name, and line number information from the
    string representation of a JavaScript trace-back.
    """
    frames = []
    for line in stack.split('\n'):
        if '@' not in line:
            continue
        func, rest = line.split('@', 1)
        if ':' not in rest:
            continue

        divide = rest.rfind(':')
        if divide == -1:
            fname, ln = rest, ''
        else:
            fname, ln = rest[:divide], rest[divide + 1:]
        ln = int(ln)
        frames.insert(0, (func, fname, ln))
    return frames



def buildTraceback(frames, modules):
    """
    Build a chain of mock traceback objects from a serialized Error (or other
    exception) object, and return the head of the chain.
    """
    last = None
    first = None
    for func, fname, ln in frames:
        fname = modules.get(fname.split('/')[-1], fname)
        frame = JSFrame(func, fname, ln)
        tb = JSTraceback(frame, ln)
        if last:
            last.tb_next = tb
        else:
            first = tb
        last = tb
    return first



def getJSFailure(exc, modules):
    """
    Convert a serialized client-side exception to a Failure.
    """
    text = '%s: %s' % (exc[u'name'], exc[u'message'])

    frames = []
    if u'stack' in exc:
        frames = parseStack(exc[u'stack'])

    return failure.Failure(JSException(text), exc_tb=buildTraceback(frames, modules))



class LivePageTransport(object):
    implements(inevow.IResource)

    def __init__(self, messageDeliverer, useActiveChannels=True):
        self.messageDeliverer = messageDeliverer
        self.useActiveChannels = useActiveChannels


    def locateChild(self, ctx, segments):
        return rend.NotFound


    def renderHTTP(self, ctx):
        req = inevow.IRequest(ctx)
        neverEverCache(req)
        if self.useActiveChannels:
            activeChannel(req)

        requestContent = req.content.read()
        messageData = json.parse(requestContent)

        response = self.messageDeliverer.basketCaseReceived(ctx, messageData)
        response.addCallback(json.serialize)
        req.notifyFinish().addErrback(lambda err: self.messageDeliverer._unregisterDeferredAsOutputChannel(response))
        return response



class LivePageFactory:
    noisy = True

    def __init__(self):
        self.clients = {}

    def addClient(self, client):
        clientID = self._newClientID()
        self.clients[clientID] = client
        if self.noisy:
            log.msg("Rendered new LivePage %r: %r" % (client, clientID))
        return clientID

    def getClient(self, clientID):
        return self.clients[clientID]

    def removeClient(self, clientID):
        # State-tracking bugs may make it tempting to make the next line a
        # 'pop', but it really shouldn't be; if the Page instance with this
        # client ID is already gone, then it should be gone, which means that
        # this method can't be called with that argument.
        del self.clients[clientID]
        if self.noisy:
            log.msg("Disconnected old LivePage %r" % (clientID,))

    def _newClientID(self):
        return guard._sessionCookie()


_thePrivateAthenaResource = static.File(util.resource_filename('nevow', 'athena_private'))


class ConnectFailed(Exception):
    pass


class ConnectionLost(Exception):
    pass


CLOSE = u'close'
UNLOAD = u'unload'

class ReliableMessageDelivery(object):
    """
    A reliable message delivery abstraction over a possibly unreliable transport.

    @type livePage: L{LivePage}
    @ivar livePage: The page this delivery is associated with.

    @type connectTimeout: C{int}
    @ivar connectTimeout: The amount of time (in seconds) to wait for the
        initial connection, before timing out.

    @type transportlessTimeout: C{int}
    @ivar transportlessTimeout: The amount of time (in seconds) to wait for
        another transport to connect if none are currently connected, before
        timing out.

    @type idleTimeout: C{int}
    @ivar idleTimeout: The maximum amount of time (in seconds) to leave a
        connected transport, before sending a noop response.

    @type connectionLost: callable or C{None}
    @ivar connectionLost: A callback invoked with a L{failure.Failure} if the
        connection with the client is lost (due to a timeout, for example).

    @type scheduler: callable or C{None}
    @ivar scheduler: If passed, this is used in place of C{reactor.callLater}.

    @type connectionMade: callable or C{None}
    @ivar connectionMade: A callback invoked with no arguments when it first
        becomes possible to to send a message to the client.
    """
    _paused = 0
    _stopped = False
    _connected = False

    outgoingAck = -1            # sequence number which has been acknowledged
                                # by this end of the connection.

    outgoingSeq = -1            # sequence number of the next message to be
                                # added to the outgoing queue.

    def __init__(self,
                 livePage,
                 connectTimeout=60, transportlessTimeout=30, idleTimeout=300,
                 connectionLost=None,
                 scheduler=None,
                 connectionMade=None):
        self.livePage = livePage
        self.messages = []
        self.outputs = []
        self.connectTimeout = connectTimeout
        self.transportlessTimeout = transportlessTimeout
        self.idleTimeout = idleTimeout
        if scheduler is None:
            scheduler = reactor.callLater
        self.scheduler = scheduler
        self._transportlessTimeoutCall = self.scheduler(self.connectTimeout, self._connectTimedOut)
        self.connectionMade = connectionMade
        self.connectionLost = connectionLost


    def _connectTimedOut(self):
        self._transportlessTimeoutCall = None
        self.connectionLost(failure.Failure(ConnectFailed("Timeout")))


    def _transportlessTimedOut(self):
        self._transportlessTimeoutCall = None
        self.connectionLost(failure.Failure(ConnectionLost("Timeout")))


    def _idleTimedOut(self):
        output, timeout = self.outputs.pop(0)
        if not self.outputs:
            self._transportlessTimeoutCall = self.scheduler(self.transportlessTimeout, self._transportlessTimedOut)
        output([self.outgoingAck, []])


    def _sendMessagesToOutput(self, output):
        log.msg(athena_send_messages=True, count=len(self.messages))
        output([self.outgoingAck, self.messages])


    def pause(self):
        self._paused += 1


    def _trySendMessages(self):
        """
        If we have pending messages and there is an available transport, then
        consume it to send the messages.
        """
        if self.messages and self.outputs:
            output, timeout = self.outputs.pop(0)
            timeout.cancel()
            if not self.outputs:
                self._transportlessTimeoutCall = self.scheduler(self.transportlessTimeout, self._transportlessTimedOut)
            self._sendMessagesToOutput(output)


    def unpause(self):
        """
        Decrement the pause counter and if the resulting state is not still
        paused try to flush any pending messages and expend excess outputs.
        """
        self._paused -= 1
        if self._paused == 0:
            self._trySendMessages()
            self._flushOutputs()


    def addMessage(self, msg):
        if self._stopped:
            return

        self.outgoingSeq += 1
        self.messages.append((self.outgoingSeq, msg))
        if not self._paused and self.outputs:
            output, timeout = self.outputs.pop(0)
            timeout.cancel()
            if not self.outputs:
                self._transportlessTimeoutCall = self.scheduler(self.transportlessTimeout, self._transportlessTimedOut)
            self._sendMessagesToOutput(output)


    def addOutput(self, output):
        if not self._connected:
            self._connected = True
            self.connectionMade()
        if self._transportlessTimeoutCall is not None:
            self._transportlessTimeoutCall.cancel()
            self._transportlessTimeoutCall = None
        if not self._paused and self.messages:
            self._transportlessTimeoutCall = self.scheduler(self.transportlessTimeout, self._transportlessTimedOut)
            self._sendMessagesToOutput(output)
        else:
            if self._stopped:
                self._sendMessagesToOutput(output)
            else:
                self.outputs.append((output, self.scheduler(self.idleTimeout, self._idleTimedOut)))


    def close(self):
        assert not self._stopped, "Cannot multiply stop ReliableMessageDelivery"
        self.addMessage((CLOSE, []))
        self._stopped = True
        while self.outputs:
            output, timeout = self.outputs.pop(0)
            timeout.cancel()
            self._sendMessagesToOutput(output)
        self.outputs = None
        if self._transportlessTimeoutCall is not None:
            self._transportlessTimeoutCall.cancel()
            self._transportlessTimeoutCall = None


    def _unregisterDeferredAsOutputChannel(self, deferred):
        for i in xrange(len(self.outputs)):
            if self.outputs[i][0].im_self is deferred:
                output, timeout = self.outputs.pop(i)
                timeout.cancel()
                break
        else:
            return
        if not self.outputs:
            self._transportlessTimeoutCall = self.scheduler(self.transportlessTimeout, self._transportlessTimedOut)


    def _createOutputDeferred(self):
        """
        Create a new deferred, attaching it as an output.  If the current
        state is not paused, try to flush any pending messages and expend
        any excess outputs.
        """
        d = defer.Deferred()
        self.addOutput(d.callback)
        if not self._paused and self.outputs:
            self._trySendMessages()
            self._flushOutputs()
        return d


    def _flushOutputs(self):
        """
        Use up all except for one output.

        This provides ideal behavior for the default HTTP client
        configuration, since only a maximum of two simultaneous connections
        are allowed.  The remaining one output will let us signal the client
        at will without preventing the client from establishing new
        connections.
        """
        if self.outputs is None:
            return
        while len(self.outputs) > 1:
            output, timeout = self.outputs.pop(0)
            timeout.cancel()
            output([self.outgoingAck, []])


    def basketCaseReceived(self, ctx, basketCase):
        """
        This is called when some random JSON data is received from an HTTP
        request.

        A 'basket case' is currently a data structure of the form [ackNum, [[1,
        message], [2, message], [3, message]]]

        Its name is highly informal because unless you are maintaining this
        exact code path, you should not encounter it.  If you do, something has
        gone *badly* wrong.
        """
        ack, incomingMessages = basketCase

        outgoingMessages = self.messages

        # dequeue messages that our client certainly knows about.
        while outgoingMessages and outgoingMessages[0][0] <= ack:
            outgoingMessages.pop(0)

        if incomingMessages:
            log.msg(athena_received_messages=True, count=len(incomingMessages))
            if incomingMessages[0][0] == UNLOAD:
                # Page-unload messages are special, because they are not part
                # of the normal message stream: they are a notification that
                # the message stream can't continue.  Browser bugs force us to
                # handle this as quickly as possible, since the browser can
                # lock up hard while waiting for a response to this message
                # (and the user has already navigated away from the page, so
                # there's no useful communication that can take place any more)
                # so only one message is allowed.  In the actual Athena JS,
                # only one is ever sent, so there is no need to handle more.
                # The structure of the packet is preserved for symmetry,
                # however, if we ever need to expand on it.  Realistically, the
                # only message that can be usefully processed here is CLOSE.
                msg = incomingMessages[0][1]
                self.livePage.liveTransportMessageReceived(ctx, msg)
                return self._createOutputDeferred()
            elif self.outgoingAck + 1 >= incomingMessages[0][0]:
                lastSentAck = self.outgoingAck
                self.outgoingAck = max(incomingMessages[-1][0], self.outgoingAck)
                self.pause()
                try:
                    for (seq, msg) in incomingMessages:
                        if seq > lastSentAck:
                            self.livePage.liveTransportMessageReceived(ctx, msg)
                        else:
                            log.msg("Athena transport duplicate message, discarding: %r %r" %
                                    (self.livePage.clientID,
                                     seq))
                    d = self._createOutputDeferred()
                finally:
                    self.unpause()
            else:
                d = defer.succeed([self.outgoingAck, []])
                log.msg(
                    "Sequence gap! %r went from %s to %s" %
                    (self.livePage.clientID,
                     self.outgoingAck,
                     incomingMessages[0][0]))
        else:
            d = self._createOutputDeferred()

        return d


BOOTSTRAP_NODE_ID = 'athena:bootstrap'
BOOTSTRAP_STATEMENT = ("eval(document.getElementById('" + BOOTSTRAP_NODE_ID +
                       "').getAttribute('payload'));")

class _HasJSClass(object):
    """
    A utility to share some code between the L{LivePage}, L{LiveElement}, and
    L{LiveFragment} classes which all have a jsClass attribute that represents
    a JavaScript class.

    @ivar jsClass: a JavaScript class.
    @type jsClass: L{unicode}
    """

    def _getModuleForClass(self):
        """
        Get a L{JSModule} object for the class specified by this object's
        jsClass string.
        """
        return jsDeps.getModuleForClass(self.jsClass)


    def _getRequiredModules(self, memo):
        """
        Return a list of two-tuples containing module names and URLs at which
        those modules are accessible.  All of these modules must be loaded into
        the page before this Fragment's widget can be instantiated.  modules
        are accessible.
        """
        return [
            (dep.name, self.page.getJSModuleURL(dep.name))
            for dep
            in self._getModuleForClass().allDependencies(memo)
            if self.page._shouldInclude(dep.name)]



def jsModuleDeclaration(name):
    """
    Generate Javascript for a module declaration.
    """
    var = ''
    if '.' not in name:
        var = 'var '
    return '%s%s = {"__name__": "%s"};' % (var, name, name)



class _HasCSSModule(object):
    """
    C{cssModule}-handling code common to L{LivePage}, L{LiveElement} and
    L{LiveFragment}.

    @ivar cssModule: A CSS module name.
    @type cssModule: C{unicode} or C{NoneType}
    """
    def _getRequiredCSSModules(self, memo):
        """
        Return a list of CSS module URLs.

        @rtype: C{list} of L{url.URL}
        """
        if self.cssModule is None:
            return []
        module = self.page.cssModules.getModuleForName(self.cssModule)
        return [
            self.page.getCSSModuleURL(dep.name)
            for dep in module.allDependencies(memo)
            if self.page._shouldIncludeCSSModule(dep.name)]


    def getStylesheetStan(self, modules):
        """
        Get some stan which will include the given modules.

        @type modules: C{list} or L{url.URL}

        @rtype: Stan
        """
        return [
            tags.link(
                rel='stylesheet', type='text/css', href=url)
            for url in modules]



class LivePage(rend.Page, _HasJSClass, _HasCSSModule):
    """
    A resource which can receive messages from and send messages to the client
    after the initial page load has completed and which can send messages.

    @ivar requiredBrowserVersions: A dictionary mapping User-Agent browser
        names to the minimum supported version of those browsers.  Clients
        using these browsers which are below the minimum version will be shown
        an alternate page explaining this rather than the normal page content.

    @ivar unsupportedBrowserLoader: A document loader which will be used to
        generate the content shown to unsupported browsers.

    @type _cssDepsMemo: C{dict}
    @ivar _cssDepsMemo: A cache for CSS module dependencies; by default, this
                        will only be shared within a single page instance.

    @type _jsDepsMemo: C{dict}
    @ivar _jsDepsMemo: A cache for JS module dependencies; by default, this
                       will only be shared within a single page instance.

    @type _didConnect: C{bool}
    @ivar _didConnect: Initially C{False}, set to C{True} if connectionMade has
        been invoked.

    @type _didDisconnect: C{bool}
    @ivar _didDisconnect: Initially C{False}, set to C{True} if _disconnected
        has been invoked.

    @type _localObjects: C{dict} of C{int} : widget
    @ivar _localObjects: Mapping from an object ID to a Python object that will
        accept messages from the client.

    @type _localObjectIDCounter: C{callable} returning C{int}
    @ivar _localObjectIDCounter: A callable that will return a new
        locally-unique object ID each time it is called.
    """
    jsClass = u'Nevow.Athena.PageWidget'
    cssModule = None

    factory = LivePageFactory()
    _rendered = False
    _didConnect = False
    _didDisconnect = False

    useActiveChannels = True

    # This is the number of seconds that is acceptable for a LivePage to be
    # considered 'connected' without any transports still active.  In other
    # words, if the browser cannot make requests for more than this timeout
    # (due to network problems, blocking javascript functions, or broken
    # proxies) then deferreds returned from notifyOnDisconnect() will be
    # errbacked with ConnectionLost, and the LivePage will be removed from the
    # factory's cache, and then likely garbage collected.
    TRANSPORTLESS_DISCONNECT_TIMEOUT = 30

    # This is the amount of time that each 'transport' request will remain open
    # to the server.  Although the underlying transport, i.e. the conceptual
    # connection established by the sequence of requests, remains alive, it is
    # necessary to periodically cancel requests to avoid browser and proxy
    # bugs.
    TRANSPORT_IDLE_TIMEOUT = 300

    page = property(lambda self: self)

    # Modules needed to bootstrap
    BOOTSTRAP_MODULES = ['Divmod', 'Divmod.Base', 'Divmod.Defer',
                         'Divmod.Runtime', 'Nevow', 'Nevow.Athena']

    # Known minimum working versions of certain browsers.
    requiredBrowserVersions = {
        browsers.GECKO: (20051111,),
        browsers.INTERNET_EXPLORER: (6, 0),
        browsers.WEBKIT: (523,),
        browsers.OPERA: (9,)}

    unsupportedBrowserLoader = loaders.stan(
        tags.html[
            tags.body[
                'Your browser is not supported by the Athena toolkit.']])


    def __init__(self, iface=None, rootObject=None, jsModules=None,
                 jsModuleRoot=None, transportRoot=None, cssModules=None,
                 cssModuleRoot=None, *a, **kw):
        super(LivePage, self).__init__(*a, **kw)

        self.iface = iface
        self.rootObject = rootObject
        if jsModules is None:
            jsModules = JSPackage(jsDeps.mapping)
        self.jsModules = jsModules
        self.jsModuleRoot = jsModuleRoot
        if transportRoot is None:
            transportRoot = here
        self.transportRoot = transportRoot
        self.cssModuleRoot = cssModuleRoot
        if cssModules is None:
            cssModules = _theCSSRegistry
        self.cssModules = cssModules
        self.liveFragmentChildren = []
        self._includedModules = []
        self._includedCSSModules = []
        self._disconnectNotifications = []
        self._jsDepsMemo = {}
        self._cssDepsMemo = {}


    def _shouldInclude(self, moduleName):
        if moduleName not in self._includedModules:
            self._includedModules.append(moduleName)
            return True
        return False


    def _shouldIncludeCSSModule(self, moduleName):
        """
        Figure out whether the named CSS module has already been included.

        @type moduleName: C{unicode}

        @rtype: C{bool}
        """
        if moduleName not in self._includedCSSModules:
            self._includedCSSModules.append(moduleName)
            return True
        return False


    # Child lookup may be dependent on the application state
    # represented by a LivePage.  In this case, it is preferable to
    # dispatch child lookup on the same LivePage instance as performed
    # the initial rendering of the page.  Override the default
    # implementation of locateChild to do this where appropriate.
    def locateChild(self, ctx, segments):
        try:
            client = self.factory.getClient(segments[0])
        except KeyError:
            return super(LivePage, self).locateChild(ctx, segments)
        else:
            return client, segments[1:]


    def child___athena_private__(self, ctx):
        return _thePrivateAthenaResource


    # A note on timeout/disconnect logic: whenever a live client goes from some
    # transports to no transports, a timer starts; whenever it goes from no
    # transports to some transports, the timer is stopped; if the timer ever
    # expires the connection is considered lost; every time a transport is
    # added a timer is started; when the transport is used up, the timer is
    # stopped; if the timer ever expires, the transport has a no-op sent down
    # it; if an idle transport is ever disconnected, the connection is
    # considered lost; this lets the server notice clients who actively leave
    # (closed window, browser navigates away) and network congestion/errors
    # (unplugged ethernet cable, etc)
    def _becomeLive(self, location):
        """
        Assign this LivePage a clientID, associate it with a factory, and begin
        tracking its state.  This only occurs when a LivePage is *rendered*,
        not when it is instantiated.
        """
        self.clientID = self.factory.addClient(self)

        if self.jsModuleRoot is None:
            self.jsModuleRoot = location.child(self.clientID).child('jsmodule')
        if self.cssModuleRoot is None:
            self.cssModuleRoot = location.child(self.clientID).child('cssmodule')

        self._requestIDCounter = itertools.count().next

        self._messageDeliverer = ReliableMessageDelivery(
            self,
            self.TRANSPORTLESS_DISCONNECT_TIMEOUT * 2,
            self.TRANSPORTLESS_DISCONNECT_TIMEOUT,
            self.TRANSPORT_IDLE_TIMEOUT,
            self._disconnected,
            connectionMade=self._connectionMade)
        self._remoteCalls = {}
        self._localObjects = {}
        self._localObjectIDCounter = itertools.count().next

        self.addLocalObject(self)


    def _supportedBrowser(self, request):
        """
        Determine whether a known-unsupported browser is making a request.

        @param request: The L{IRequest} being made.

        @rtype: C{bool}
        @return: False if the user agent is known to be unsupported by Athena,
            True otherwise.
        """
        agentString = request.getHeader("user-agent")
        if agentString is None:
            return True
        agent = UserAgent.fromHeaderValue(agentString)
        if agent is None:
            return True

        requiredVersion = self.requiredBrowserVersions.get(agent.browser, None)
        if requiredVersion is not None:
            return agent.version >= requiredVersion
        return True


    def renderUnsupported(self, ctx):
        """
        Render a notification to the user that his user agent is
        unsupported by this LivePage.

        @param ctx: The current rendering context.

        @return: Something renderable (same behavior as L{renderHTTP})
        """
        return flat.flatten(self.unsupportedBrowserLoader.load())


    def renderHTTP(self, ctx):
        """
        Attach this livepage to its transport, and render it and all of its
        attached widgets to the browser.  During rendering, the page is
        attached to its factory, acquires a clientID, and has headers set
        appropriately to prevent a browser from ever caching the page, since
        the clientID it gives to the browser is transient and changes every
        time.

        These state changes associated with rendering mean that L{LivePage}s
        can only be rendered once, because they are attached to a particular
        user's browser, and it must be unambiguous what browser
        L{LivePage.callRemote} will invoke the method in.

        The page's contents are rendered according to its docFactory, as with a
        L{Page}, unless the user-agent requesting this LivePage is determined
        to be unsupported by the JavaScript runtime required by Athena.  In
        that case, a static page is rendered by this page's
        C{renderUnsupported} method.

        If a special query argument is set in the URL, "__athena_reconnect__",
        the page will instead render the JSON-encoded clientID by itself as the
        page's content.  This allows an existing live page in a browser to
        programmatically reconnect without re-rendering and re-loading the
        entire page.

        @see: L{LivePage.renderUnsupported}

        @see: L{Page.renderHTTP}

        @param ctx: a L{WovenContext} with L{IRequest} remembered.

        @return: a string (the content of the page) or a Deferred which will
        fire with the same.

        @raise RuntimeError: if the page has already been rendered, or this
        page has not been given a factory.
        """
        if self._rendered:
            raise RuntimeError("Cannot render a LivePage more than once")
        if self.factory is None:
            raise RuntimeError("Cannot render a LivePage without a factory")

        self._rendered = True
        request = inevow.IRequest(ctx)
        if not self._supportedBrowser(request):
            request.write(self.renderUnsupported(ctx))
            return ''

        self._becomeLive(URL.fromString(flat.flatten(here, ctx)))

        neverEverCache(request)
        if request.args.get(ATHENA_RECONNECT):
            return json.serialize(self.clientID.decode("ascii"))
        return rend.Page.renderHTTP(self, ctx)


    def _connectionMade(self):
        """
        Invoke connectionMade on all attached widgets.
        """
        for widget in self._localObjects.values():
            widget.connectionMade()
        self._didConnect = True


    def _disconnected(self, reason):
        """
        Callback invoked when the L{ReliableMessageDelivery} is disconnected.

        If the page has not already disconnected, fire any deferreds created
        with L{notifyOnDisconnect}; if the page was already connected, fire
        C{connectionLost} methods on attached widgets.
        """
        if not self._didDisconnect:
            self._didDisconnect = True

            notifications = self._disconnectNotifications
            self._disconnectNotifications = None
            for d in notifications:
                d.errback(reason)
            calls = self._remoteCalls
            self._remoteCalls = {}
            for (reqID, resD) in calls.iteritems():
                resD.errback(reason)
            if self._didConnect:
                for widget in self._localObjects.values():
                    widget.connectionLost(reason)
            self.factory.removeClient(self.clientID)


    def connectionMade(self):
        """
        Callback invoked when the transport is first connected.
        """


    def connectionLost(self, reason):
        """
        Callback invoked when the transport is disconnected.

        This method will only be called if connectionMade was called.

        Override this.
        """


    def addLocalObject(self, obj):
        objID = self._localObjectIDCounter()
        self._localObjects[objID] = obj
        return objID


    def removeLocalObject(self, objID):
        """
        Remove an object from the page's mapping of IDs that can receive
        messages.

        @type  objID: C{int}
        @param objID: The ID returned by L{LivePage.addLocalObject}.
        """
        del self._localObjects[objID]


    def callRemote(self, methodName, *args):
        requestID = u's2c%i' % (self._requestIDCounter(),)
        message = (u'call', (unicode(methodName, 'ascii'), requestID, args))
        resultD = defer.Deferred()
        self._remoteCalls[requestID] = resultD
        self.addMessage(message)
        return resultD


    def addMessage(self, message):
        self._messageDeliverer.addMessage(message)


    def notifyOnDisconnect(self):
        """
        Return a Deferred which will fire or errback when this LivePage is
        no longer connected.

        Note that if a LivePage never establishes a connection in the first
        place, the Deferreds this returns will never fire.

        @rtype: L{defer.Deferred}
        """
        d = defer.Deferred()
        self._disconnectNotifications.append(d)
        return d


    def getJSModuleURL(self, moduleName):
        return self.jsModuleRoot.child(moduleName)


    def getCSSModuleURL(self, moduleName):
        """
        Return a URL rooted a L{cssModuleRoot} from which the CSS module named
        C{moduleName} can be fetched.

        @type moduleName: C{unicode}

        @rtype: C{str}
        """
        return self.cssModuleRoot.child(moduleName)


    def getImportStan(self, moduleName):
        moduleDef = jsModuleDeclaration(moduleName);
        return [tags.script(type='text/javascript')[tags.raw(moduleDef)],
                tags.script(type='text/javascript', src=self.getJSModuleURL(moduleName))]


    def render_liveglue(self, ctx, data):
        bootstrapString = '\n'.join(
            [self._bootstrapCall(method, args) for
             method, args in self._bootstraps(ctx)])
        return ctx.tag[
            self.getStylesheetStan(self._getRequiredCSSModules(self._cssDepsMemo)),

            # Hit jsDeps.getModuleForName to force it to load some plugins :/
            # This really needs to be redesigned.
            [self.getImportStan(jsDeps.getModuleForName(name).name)
             for (name, url)
             in self._getRequiredModules(self._jsDepsMemo)],
            tags.script(type='text/javascript',
                        id=BOOTSTRAP_NODE_ID,
                        payload=bootstrapString)[
                BOOTSTRAP_STATEMENT]
        ]


    def _bootstraps(self, ctx):
        """
        Generate a list of 2-tuples of (methodName, arguments) representing the
        methods which need to be invoked as soon as all the bootstrap modules
        are loaded.

        @param: a L{WovenContext} that can render an URL.
        """
        return [
            ("Divmod.bootstrap",
             [flat.flatten(self.transportRoot, ctx).decode("ascii")]),
            ("Nevow.Athena.bootstrap",
             [self.jsClass, self.clientID.decode('ascii')])]


    def _bootstrapCall(self, methodName, args):
        """
        Generate a string to call a 'bootstrap' function in an Athena JavaScript
        module client-side.

        @param methodName: the name of the method.

        @param args: a list of objects that will be JSON-serialized as
        arguments to the named method.
        """
        return '%s(%s);' % (
            methodName, ', '.join([json.serialize(arg) for arg in args]))


    def child_jsmodule(self, ctx):
        return MappingResource(self.jsModules.mapping)


    def child_cssmodule(self, ctx):
        """
        Return a L{MappingResource} wrapped around L{cssModules}.
        """
        return MappingResource(self.cssModules.mapping)


    _transportResource = None
    def child_transport(self, ctx):
        if self._transportResource is None:
            self._transportResource = LivePageTransport(
                self._messageDeliverer,
                self.useActiveChannels)
        return self._transportResource


    def locateMethod(self, ctx, methodName):
        if methodName in self.iface:
            return getattr(self.rootObject, methodName)
        raise AttributeError(methodName)


    def liveTransportMessageReceived(self, ctx, (action, args)):
        """
        A message was received from the reliable transport layer.  Process it by
        dispatching it first to myself, then later to application code if
        applicable.
        """
        method = getattr(self, 'action_' + action)
        method(ctx, *args)


    def action_call(self, ctx, requestId, method, objectID, args, kwargs):
        """
        Handle a remote call initiated by the client.
        """
        localObj = self._localObjects[objectID]
        try:
            func = localObj.locateMethod(ctx, method)
        except AttributeError:
            result = defer.fail(NoSuchMethod(objectID, method))
        else:
            result = defer.maybeDeferred(func, *args, **kwargs)
        def _cbCall(result):
            success = True
            if isinstance(result, failure.Failure):
                log.msg("Sending error to browser:")
                log.err(result)
                success = False
                if result.check(LivePageError):
                    result = (
                        result.value.jsClass,
                        result.value.args)
                else:
                    result = (
                        u'Divmod.Error',
                        [u'%s: %s' % (
                                result.type.__name__.decode('ascii'),
                                result.getErrorMessage().decode('ascii'))])
            message = (u'respond', (unicode(requestId), success, result))
            self.addMessage(message)
        result.addBoth(_cbCall)


    def action_respond(self, ctx, responseId, success, result):
        """
        Handle the response from the client to a call initiated by the server.
        """
        callDeferred = self._remoteCalls.pop(responseId)
        if success:
            callDeferred.callback(result)
        else:
            callDeferred.errback(getJSFailure(result, self.jsModules.mapping))


    def action_noop(self, ctx):
        """
        Handle noop, used to initialise and ping the live transport.
        """


    def action_close(self, ctx):
        """
        The client is going away.  Clean up after them.
        """
        self._messageDeliverer.close()
        self._disconnected(error.ConnectionDone("Connection closed"))



handler = stan.Proto('athena:handler')
_handlerFormat = "return Nevow.Athena.Widget.handleEvent(this, %(event)s, %(handler)s);"

def _rewriteEventHandlerToAttribute(tag):
    """
    Replace athena:handler children of the given tag with attributes on the tag
    which correspond to those event handlers.
    """
    if isinstance(tag, stan.Tag):
        extraAttributes = {}
        for i in xrange(len(tag.children) - 1, -1, -1):
            if isinstance(tag.children[i], stan.Tag) and tag.children[i].tagName == 'athena:handler':
                info = tag.children.pop(i)
                name = info.attributes['event'].encode('ascii')
                handler = info.attributes['handler']
                extraAttributes[name] = _handlerFormat % {
                    'handler': json.serialize(handler.decode('ascii')),
                    'event': json.serialize(name.decode('ascii'))}
                tag(**extraAttributes)
    return tag


def rewriteEventHandlerNodes(root):
    """
    Replace all the athena:handler nodes in a given document with onfoo
    attributes.
    """
    stan.visit(root, _rewriteEventHandlerToAttribute)
    return root


def _mangleId(oldId):
    """
    Return a consistently mangled form of an id that is unique to the widget
    within which it occurs.
    """
    return ['athenaid:', tags.slot('athena:id'), '-', oldId]


def _rewriteAthenaId(tag):
    """
    Rewrite id attributes to be prefixed with the ID of the widget the node is
    contained by. Also rewrite label "for" attributes which must match the id of
    their form element.
    """
    if isinstance(tag, stan.Tag):
        elementId = tag.attributes.pop('id', None)
        if elementId is not None:
            tag.attributes['id'] = _mangleId(elementId)
        if tag.tagName == "label":
            elementFor = tag.attributes.pop('for', None)
            if elementFor is not None:
                tag.attributes['for'] = _mangleId(elementFor)
        if tag.tagName in ('td', 'th'):
            headers = tag.attributes.pop('headers', None)
            if headers is not None:
                ids = headers.split()
                headers = [_mangleId(headerId) for headerId in ids]
                for n in xrange(len(headers) - 1, 0, -1):
                    headers.insert(n, ' ')
                tag.attributes['headers'] = headers
    return tag


def rewriteAthenaIds(root):
    """
    Rewrite id attributes to be unique to the widget they're in.
    """
    stan.visit(root, _rewriteAthenaId)
    return root


class _LiveMixin(_HasJSClass, _HasCSSModule):
    jsClass = u'Nevow.Athena.Widget'
    cssModule = None

    preprocessors = [rewriteEventHandlerNodes, rewriteAthenaIds]

    fragmentParent = None

    _page = None

    # Reference to the result of a call to _structured, if one has been made,
    # otherwise None.  This is used to make _structured() idempotent.
    _structuredCache = None

    def __init__(self, *a, **k):
        super(_LiveMixin, self).__init__(*a, **k)
        self.liveFragmentChildren = []

    def page():
        def get(self):
            if self._page is None:
                if self.fragmentParent is not None:
                    self._page = self.fragmentParent.page
            return self._page
        def set(self, value):
            self._page = value
        doc = """
        The L{LivePage} instance which is the topmost container of this
        fragment.
        """
        return get, set, None, doc
    page = property(*page())


    def getInitialArguments(self):
        """
        Return a C{tuple} or C{list} of arguments to be passed to this
        C{LiveFragment}'s client-side Widget.

        This will be called during the rendering process.  Whatever it
        returns will be serialized into the page and passed to the
        C{__init__} method of the widget specified by C{jsClass}.

        @rtype: C{list} or C{tuple}
        """
        return ()


    def _prepare(self, tag):
        """
        Check for clearly incorrect settings of C{self.jsClass} and
        C{self.page}, add this object to the page and fill the I{athena:id}
        slot with this object's Athena identifier.
        """
        assert isinstance(self.jsClass, unicode), "jsClass must be a unicode string"

        if self.page is None:
            raise OrphanedFragment(self)
        self._athenaID = self.page.addLocalObject(self)
        if self.page._didConnect:
            self.connectionMade()
        tag.fillSlots('athena:id', str(self._athenaID))


    def setFragmentParent(self, fragmentParent):
        """
        Sets the L{LiveFragment} (or L{LivePage}) which is the logical parent
        of this fragment.  This should parallel the client-side hierarchy.

        All LiveFragments must have setFragmentParent called on them before
        they are rendered for the client; otherwise, they will be unable to
        properly hook up to the page.

        LiveFragments should have their own setFragmentParent called before
        calling setFragmentParent on any of their own children.  The normal way
        to accomplish this is to instantiate your fragment children during the
        render pass.

        If that isn't feasible, instead override setFragmentParent and
        instantiate your children there.

        This architecture might seem contorted, but what it allows that is
        interesting is adaptation of foreign objects to LiveFragment.  Anywhere
        you adapt to LiveFragment, setFragmentParent is the next thing that
        should be called.
        """
        self.fragmentParent = fragmentParent
        self.page = fragmentParent.page
        fragmentParent.liveFragmentChildren.append(self)


    def _flatten(self, what):
        """
        Synchronously flatten C{what} and return the result as a C{str}.
        """
        # Nested import because in a significant stroke of misfortune,
        # nevow.testutil already depends on nevow.athena.  It makes more sense
        # for the dependency to go from nevow.athena to nevow.testutil.
        # Perhaps a sane way to fix this would be to move FakeRequest to a
        # different module from whence nevow.athena and nevow.testutil could
        # import it. -exarkun
        from nevow.testutil import FakeRequest
        return "".join(_flat.flatten(FakeRequest(), what, False, False))


    def _structured(self):
        """
        Retrieve an opaque object which may be usable to construct the
        client-side Widgets which correspond to this fragment and all of its
        children.
        """
        if self._structuredCache is not None:
            return self._structuredCache

        children = []
        requiredModules = []
        requiredCSSModules = []

        # Using the context here is terrible but basically necessary given the
        # /current/ architecture of Athena and flattening.  A better
        # implementation which was not tied to the rendering system could avoid
        # this.
        markup = context.call(
            {'children': children,
             'requiredModules': requiredModules,
             'requiredCSSModules': requiredCSSModules},
            self._flatten, tags.div(xmlns="http://www.w3.org/1999/xhtml")[self]).decode('utf-8')

        del children[0]

        self._structuredCache = {
            u'requiredModules': [(name, flat.flatten(url).decode('utf-8'))
                                 for (name, url) in requiredModules],
            u'requiredCSSModules': [flat.flatten(url).decode('utf-8')
                                    for url in requiredCSSModules],
            u'class': self.jsClass,
            u'id': self._athenaID,
            u'initArguments': tuple(self.getInitialArguments()),
            u'markup': markup,
            u'children': children}
        return self._structuredCache


    def liveElement(self, request, tag):
        """
        Render framework-level boilerplate for making sure the Widget for this
        Element is created and added to the page properly.
        """
        requiredModules = self._getRequiredModules(self.page._jsDepsMemo)
        requiredCSSModules = self._getRequiredCSSModules(self.page._cssDepsMemo)

        # Add required attributes to the top widget node
        tag(**{'xmlns:athena': ATHENA_XMLNS_URI,
               'id': 'athena:%d' % self._athenaID,
               'athena:class': self.jsClass})

        # This will only be set if _structured() is being run.
        if context.get('children') is not None:
            context.get('children').append({
                    u'class': self.jsClass,
                    u'id': self._athenaID,
                    u'initArguments': self.getInitialArguments()})
            context.get('requiredModules').extend(requiredModules)
            context.get('requiredCSSModules').extend(requiredCSSModules)
            return tag

        return (
            self.getStylesheetStan(requiredCSSModules),

            # Import stuff
            [self.getImportStan(name) for (name, url) in requiredModules],

            # Dump some data for our client-side __init__ into a text area
            # where it can easily be found.
            tags.textarea(id='athena-init-args-' + str(self._athenaID),
                          style="display: none")[
                json.serialize(self.getInitialArguments())],

            # Arrange to be instantiated
            tags.script(type='text/javascript')[
                """
                Nevow.Athena.Widget._widgetNodeAdded(%(athenaID)d);
                """ % {'athenaID': self._athenaID,
                       'pythonClass': self.__class__.__name__}],

            # Okay, application stuff, plus metadata
            tag,
            )
    renderer(liveElement)


    def render_liveFragment(self, ctx, data):
        return self.liveElement(inevow.IRequest(ctx), ctx.tag)


    def getImportStan(self, moduleName):
        return self.page.getImportStan(moduleName)


    def locateMethod(self, ctx, methodName):
        remoteMethod = expose.get(self, methodName, None)
        if remoteMethod is None:
            raise AttributeError(self, methodName)
        return remoteMethod


    def callRemote(self, methodName, *varargs):
        return self.page.callRemote(
            "Nevow.Athena.callByAthenaID",
            self._athenaID,
            unicode(methodName, 'ascii'),
            varargs)


    def _athenaDetachServer(self):
        """
        Locally remove this from its parent.

        @raise OrphanedFragment: if not attached to a parent.
        """
        if self.fragmentParent is None:
            raise OrphanedFragment(self)
        for ch in self.liveFragmentChildren:
            ch._athenaDetachServer()
        self.fragmentParent.liveFragmentChildren.remove(self)
        self.fragmentParent = None
        page = self.page
        self.page = None
        page.removeLocalObject(self._athenaID)
        if page._didConnect:
            self.connectionLost(ConnectionLost('Detached'))
        self.detached()
    expose(_athenaDetachServer)


    def detach(self):
        """
        Remove this from its parent after notifying the client that this is
        happening.

        This function will *not* work correctly if the parent/child
        relationships of this widget do not exactly match the parent/child
        relationships of the corresponding fragments or elements on the server.

        @return: A L{Deferred} which will fire when the detach completes.
        """
        d = self.callRemote('_athenaDetachClient')
        d.addCallback(lambda ign: self._athenaDetachServer())
        return d


    def detached(self):
        """
        Application-level callback invoked when L{detach} succeeds or when the
        client invokes the detach logic from its side.

        This is invoked after this fragment has been disassociated from its
        parent and from the page.

        Override this.
        """


    def connectionMade(self):
        """
        Callback invoked when the transport is first available to this widget.

        Override this.
        """


    def connectionLost(self, reason):
        """
        Callback invoked once the transport is no longer available to this
        widget.

        This method will only be called if connectionMade was called.

        Override this.
        """



class LiveFragment(_LiveMixin, rend.Fragment):
    """
    This class is deprecated because it relies on context objects
    U{which are being removed from Nevow<http://divmod.org/trac/wiki/WitherContext>}.

    @see: L{LiveElement}
    """
    def __init__(self, *a, **kw):
        super(LiveFragment, self).__init__(*a, **kw)
        warnings.warn("[v0.10] LiveFragment has been superceded by LiveElement.",
                      category=DeprecationWarning,
                      stacklevel=2)


    def rend(self, context, data):
        """
        Hook into the rendering process in order to check preconditions and
        make sure the document will actually be renderable by satisfying
        certain Athena requirements.
        """
        context = rend.Fragment.rend(self, context, data)
        self._prepare(context.tag)
        return context




class LiveElement(_LiveMixin, Element):
    """
    Base-class for a portion of a LivePage.  When being rendered, a LiveElement
    has a special ID attribute added to its top-level tag.  This attribute is
    used to dispatch calls from the client onto the correct object (this one).

    A LiveElement must use the `liveElement' renderer somewhere in its document
    template.  The node given this renderer will be the node used to construct
    a Widget instance in the browser (where it will be saved as the `node'
    property on the widget object).

    JavaScript handlers for elements inside this node can use
    C{Nevow.Athena.Widget.get} to retrieve the widget associated with this
    LiveElement.  For example::

        <form onsubmit="Nevow.Athena.Widget.get(this).callRemote('foo', bar); return false;">

    Methods of the JavaScript widget class can also be bound as event handlers
    using the handler tag type in the Athena namespace::

        <form xmlns:athena="http://divmod.org/ns/athena/0.7">
            <athena:handler event="onsubmit" handler="doFoo" />
        </form>

    This will invoke the C{doFoo} method of the widget which contains the form
    node.

    Because this mechanism sets up error handling and otherwise reduces the
    required boilerplate for handling events, it is preferred and recommended
    over directly including JavaScript in the event handler attribute of a
    node.

    The C{jsClass} attribute of a LiveElement instance determines the
    JavaScript class used to construct its corresponding Widget.  This appears
    as the 'athena:class' attribute.

    JavaScript modules may import other JavaScript modules by using a special
    comment which Athena recognizes::

        // import Module.Name

    Different imports must be placed on different lines.  No other comment
    style is supported for these directives.  Only one space character must
    appear between the string 'import' and the name of the module to be
    imported.  No trailing whitespace or non-whitespace is allowed.  There must
    be exactly one space between '//' and 'import'.  There must be no
    preceeding whitespace on the line.

    C{Nevow.Athena.Widget.callRemote} can be given permission to invoke methods
    on L{LiveElement} instances by passing the functions which implement those
    methods to L{nevow.athena.expose} in this way::

        class SomeElement(LiveElement):
            def someMethod(self, ...):
                ...
            expose(someMethod)

    Only methods exposed in this way will be accessible.

    L{LiveElement.callRemote} can be used to invoke any method of the widget on
    the client.

    XML elements with id attributes will be rewritten so that the id is unique
    to that particular instance. The client-side
    C{Nevow.Athena.Widget.nodeById} API is provided to locate these later
    on. For example::

        <div id="foo" />

    and then::

        var node = self.nodyById('foo');

    On most platforms, this API will be much faster than similar techniques
    using C{Nevow.Athena.Widget.nodeByAttribute} etc.

    Similarly to how Javascript classes are specified, L{LiveElement}
    instances may also identify a CSS module which provides appropriate styles
    with the C{cssModule} attribute (a unicode string naming a module within a
    L{inevow.ICSSPackage}).

    The referenced CSS modules are treated as regular CSS, with the exception
    of support for the same::

        // import CSSModule.Name

    syntax as is provided for Javascript modules.
    """
    def render(self, request):
        """
        Hook into the rendering process in order to check preconditions and
        make sure the document will actually be renderable by satisfying
        certain Athena requirements.
        """
        document = tags.invisible[Element.render(self, request)]
        self._prepare(document)
        return document



class IntrospectionFragment(LiveFragment):
    """
    Utility for developers which provides detailed information about
    the state of a live page.
    """

    jsClass = u'Nevow.Athena.IntrospectionWidget'

    docFactory = loaders.stan(
        tags.span(render=tags.directive('liveFragment'))[
        tags.a(
        href="#DEBUG_ME",
        class_='toggle-debug')["Debug"]])



__all__ = [
    # Constants
    'ATHENA_XMLNS_URI',

    # Errors
    'LivePageError', 'OrphanedFragment', 'ConnectFailed', 'ConnectionLost',

    # JS support
    'MappingResource', 'JSModule', 'JSPackage', 'AutoJSPackage',
    'allJavascriptPackages', 'JSDependencies', 'JSException', 'JSCode',
    'JSFrame', 'JSTraceback',

    # CSS support
    'CSSRegistry', 'CSSModule',

    # Core objects
    'LivePage', 'LiveFragment', 'LiveElement', 'IntrospectionFragment',

    # Decorators
    'expose', 'handler',
    ]
