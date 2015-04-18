# Copyright (c) 2008 Divmod.
# See LICENSE for details.

"""
Tests for L{nevow.livepage}.
"""

from twisted.trial import unittest

from nevow import livepage, tags, util, flat, inevow, loaders, context


def makeCtx(inString=None, inAttribute=None):
    return livepage.JavascriptContext(
        isAttrib=inAttribute,
        inJSSingleQuoteString=inString)


class TestQuoting(unittest.TestCase):
    def test_normal(self):
        """No quoting at all happens when we are in a JavascriptContext
        which is not in a single quoted string or a double quoted string.
        """
        ctx = makeCtx()
        self.assertEquals(flat.flatten("foo", ctx), "'foo'")
        self.assertEquals(flat.flatten(livepage.js("1 < 2 & 3"), ctx), "1 < 2 & 3")

    def test_inAttribute(self):
        """When inside an attribute, we must make sure to quote
        double quotes.
        """
        ctx = makeCtx(inAttribute=True)
        self.assertEquals(flat.flatten('foo', ctx), "'foo'")
        self.assertEquals(
            flat.flatten(livepage.js.foo('hello"world'), ctx),
            "foo('hello&quot;world')")
        self.assertEquals(
            flat.flatten(livepage.js.foo("1 < 2 & 3"), ctx),
            "foo('1 &lt; 2 &amp; 3')")

    def test_inSingleQuoteString(self):
        """When inside a single-quote string, we must quote single-
        quoted strings.
        """
        ctx = makeCtx()
        self.assertEquals(
            flat.flatten(livepage.js.foo(tags.div["single'quote"]), ctx),
            "foo('<div>single\\'quote</div>')")

    def test_rawSingleQuote(self):
        """When putting something returned from IQ or otherwise extracted
        from a docFactory inside a single-quote string, the FlattenRaw must
        be responsible for quoting single-quotes.
        """
        l = loaders.stan(
            tags.div(pattern="foo")[
                tags.a(onclick=livepage.js.foo('bar'))["click\n me"]])
        self.assertEquals(
            flat.flatten(livepage.js.foo(inevow.IQ(l).onePattern('foo')), makeCtx()),
            """foo('<div><a onclick="foo(\\\'bar\\\')">click\\n me</a></div>')""")

    def test_dontQuoteJS(self):
        """We must not put js objects in single quotes, even if they
        are inside another js.__call__
        """
        self.assertEquals(
            flat.flatten(livepage.js.foo(livepage.js.bar()), makeCtx()),
            "foo(bar())")

    def sendThrough(self, what):
        page = livepage.LivePage()
        handle = livepage.ClientHandle(page, 'asdf', 0, 0)
        ctx = makeCtx()
        page.rememberStuff(ctx)
        d = util.Deferred()
        handle.setOutput(ctx, d)
        handle.send(what)
        return d.result

    def test_sendThroughClientHandle(self):
        self.assertEquals(self.sendThrough('hello'), "'hello'")
        self.assertEquals(self.sendThrough(livepage.js.foo('bar',1)), "foo('bar',1)")

    def test_sendThroughWithFunction(self):
        self.assertEquals(self.sendThrough(lambda c, d: livepage.js('hello')), 'hello')
        self.assertEquals(self.sendThrough(lambda c, d: [1,2, livepage.js('hi'), "it's a string"]), "12hi'it\\'s a string'")

        def rend_table(self,ctx,data):
            return tags.table[
                tags.tr[
                    tags.th["hea'der1"], tags.th["hea'der2"]],
                tags.tr(id="ro'w1")[
                    tags.td["va'l1"],tags.td["va'l2"]]]

        self.assertEquals(
            self.sendThrough(livepage.append('mynode', rend_table)),
            """nevow_appendNode('mynode','<table><tr><th>hea\\'der1</th><th>hea\\'der2</th></tr><tr id="ro\\'w1"><td>va\\'l1</td><td>va\\'l2</td></tr></table>')""")











fakeId = '--handler-fake-id'


class TestLive(livepage.ClientHandle):
    sent = None
    def __init__(self):
        self.refreshInterval = 30
        self.targetTimeoutCount = 3
        self.timeoutCount = 0
        self.handleId = 'fake-test'
        self.nextId = lambda: "fake-id"
        self.outputBuffer = []
        self.closed = False
        self.closeNotifications = []
        self.firstTime = True
        self.outputContext = None

    def callback(self, script):
        self.sent = str(script)

    def handleInput(self, name, *args):
        self.send = self.callback
        getattr(self, 'handle_%s' % (name, ))(self, *args)
        del self.send

    outputConduit = property(lambda s: s, lambda s, n: None)


class LiveGatherer(TestLive):
    def __init__(self):
        TestLive.__init__(self)
        self.heard = []

    def sendScript(self, script):
        self.heard.append(script)


class Quoting(unittest.TestCase):
    def setUp(self):
        self.livepage = TestLive()
        self.ctx = context.WovenContext()
        self.ctx.remember(self.livepage, livepage.IClientHandle)
        self.ctx.remember(livepage.LivePage(), inevow.IResource)

    def flt(self, what, quote=False):
        return livepage.flt(what, quote=quote, client=self.livepage, handlerFactory=self.livepage)

    def testCall(self):
        self.livepage.call("concat", "1", "2")
        self.assertEquals(self.livepage.sent, "concat('1','2')")
        self.livepage.call("bloop", r"a\b\c")
        self.assertEquals(self.livepage.sent, r"bloop('a\\b\\c')")
        self.livepage.call("zoop", "a'b'c")
        self.assertEquals(self.livepage.sent, r"zoop('a\'b\'c')")
        self.livepage.call("floop", "a\nb\nc")
        self.assertEquals(self.livepage.sent, "floop('a\\nb\\nc')")

    def test_callWithJS(self):
        self.livepage.call("add", 1, 2)
        self.assertEquals(self.livepage.sent, "add(1,2)")
        self.livepage.call("amIEvil", True)
        self.assertEquals(self.livepage.sent, "amIEvil(true)")
        self.livepage.call("add", 1.4, 2.4)
        self.assertEquals(self.livepage.sent, "add(1.4,2.4)")
        self.livepage.call('alert', livepage.js('document.title'))
        self.assertEquals(self.livepage.sent, 'alert(document.title)')
        self.livepage.call('alert', livepage.document.title)
        self.assertEquals(self.livepage.sent, 'alert(document.title)')

    def test_callWithStan(self):
        self.livepage.call("replace", tags.span)
        self.assertEquals(self.livepage.sent, "replace('<span />')")
        self.livepage.call('fun', tags.span["'"])
        self.assertEquals(self.livepage.sent, r"fun('<span>\'</span>')")
        self.livepage.call('fun', tags.span["\""])
        self.assertEquals(self.livepage.sent, "fun('<span>\"</span>')")
        self.livepage.call('fun', tags.span['\\'])
        self.assertEquals(self.livepage.sent, "fun('<span>\\\\</span>')")

    def test_js(self):
        foo = livepage.js('foo')
        self.livepage.call('alert', foo('1'))
        self.assertEquals(self.livepage.sent, "alert(foo('1'))")
        self.livepage.sendScript(foo(1))
        self.assertEquals(self.livepage.sent, "foo(1)")

        window = livepage.js('window')
        self.livepage.sendScript(window.open('http://google.com'))
        self.assertEquals(self.livepage.sent, "window.open('http://google.com')")
        array = livepage.js('array')
        self.livepage.sendScript(array[5])
        self.assertEquals(self.livepage.sent, "array[5]")
        self.livepage.sendScript(livepage.js[1,2,3])
        self.assertEquals(self.livepage.sent, "[1,2,3]")
        self.livepage.sendScript(livepage.js[()])
        self.assertEquals(self.livepage.sent, "[]")
        self.livepage.sendScript(livepage.js[[1,2,3]])
        self.assertEquals(self.livepage.sent, "[1,2,3]")

    def test_setAndAppend(self):
        for apiName in ['set', 'append']:
            api = getattr(self.livepage, apiName)
            funcName = "nevow_%sNode" % (apiName, )
            api('node', 'value')
            self.assertEquals(self.livepage.sent, funcName + "('node','value')")
            api('node', 1)
            self.assertEquals(self.livepage.sent, funcName + "('node',1)")
            api('node', tags.span["Hello"])
            self.assertEquals(self.livepage.sent, funcName + "('node','<span>Hello</span>')")
            api('node', livepage.document.title)
            self.assertEquals(self.livepage.sent, funcName + "('node',document.title)")
            api('node', '\\')
            self.assertEquals(self.livepage.sent, funcName + r"('node','\\')")
            api('node', "'")
            self.assertEquals(self.livepage.sent, funcName + r"('node','\'')")
            api('node', '"')
            self.assertEquals(self.livepage.sent, funcName + "('node','\"')")
            api('\\', '')
            self.assertEquals(self.livepage.sent, funcName + "('\\\\','')")

    def test_alert(self):
        self.livepage.alert('Hello')
        self.assertEquals(self.livepage.sent, "alert('Hello')")
        self.livepage.alert(5)
        self.assertEquals(self.livepage.sent, "alert(5)")
        self.livepage.alert(livepage.document.title)
        self.assertEquals(self.livepage.sent, "alert(document.title)")
        self.livepage.alert('\\')
        self.assertEquals(self.livepage.sent, "alert('\\\\')")
        self.livepage.alert("'")
        self.assertEquals(self.livepage.sent, r"alert('\'')")
        self.livepage.alert('"')
        self.assertEquals(self.livepage.sent, "alert('\"')")

    def test_handler(self):
        result = livepage.handler(onClick)
        self.assertEquals(self.flt(result),
            livepage.ctsTemplate % (fakeId, '', livepage.handledEventPostlude))
        self.livepage.handleInput(fakeId)
        self.assertEquals(self.livepage.sent, 'null;')

    def test_closedOverHandler(self):
        closedOver = 'hello'
        def closuredHandler(client):
            client.sendScript(closedOver)

        ## We have to "render" the result because the event handler has to be
        ## subscribed to at render time.
        result = self.flt(livepage.handler(closuredHandler))
        ## The closured handler will have been assigned a unique id.
        self.assertEquals(result,
            livepage.ctsTemplate % (fakeId, '', livepage.handledEventPostlude))

        self.livepage.handleInput(fakeId)
        self.assertEquals(self.livepage.sent, 'hello')

    def test_handlerWithArgs(self):
        options = [
            dict(bubble=True, outsideAttribute=True),
            dict(bubble=False, outsideAttribute=True),
            dict(bubble=False, outsideAttribute=False),
            dict(bubble=True, outsideAttribute=False)]

        for opts in options:
            if opts['bubble']:
                postlude = ';'
            else:
                postlude = livepage.handledEventPostlude

            self.assertEquals(
                self.flt(livepage.handler(argsHandler, 'hello', **opts)),
                livepage.ctsTemplate % (fakeId, ",'hello'", postlude))

            self.assertEquals(
                self.flt(livepage.handler(argsHandler, "'", **opts)),
                livepage.ctsTemplate % (fakeId, ",'\\''", postlude))

            self.assertEquals(
                self.flt(livepage.handler(argsHandler, "\\", **opts)),
                livepage.ctsTemplate % (fakeId, ",'\\\\'", postlude))

            self.assertEquals(
                self.flt(livepage.handler(argsHandler, "\n", **opts)),
                livepage.ctsTemplate % (fakeId, ",'\\n'", postlude))

    def test_handlerWithArgsQuoting(self):
        self.assertEquals(
            self.flt(livepage.handler(argsHandler, '"')),
            livepage.ctsTemplate % (fakeId, ",'&quot;'", livepage.handledEventPostlude))

        self.assertEquals(
            self.flt(livepage.handler(argsHandler, '&')),
            livepage.ctsTemplate % (fakeId, ",'&amp;'", livepage.handledEventPostlude))

    def test_outsideAttributeArgsQuoting(self):
        self.assertEquals(
           self.flt(livepage.handler(argsHandler, '"', outsideAttribute=True)),
            livepage.ctsTemplate % (fakeId, ",'\"'", livepage.handledEventPostlude))

        self.assertEquals(
            self.flt(livepage.handler(argsHandler, '&', outsideAttribute=True)),
            livepage.ctsTemplate % (fakeId, ",'&'", livepage.handledEventPostlude))

    def test_bubble(self):
        self.assertEquals(
            self.flt(livepage.handler(onClick, bubble=True)),
            livepage.ctsTemplate % (fakeId, '', ';'))

    def test_handlerWithIdentifier(self):
        lp = self.livepage
        gatherer = self.livepage = LiveGatherer()

        self.flt(livepage.handler(oneHandler, identifier='same'))
        gatherer.handleInput('--handler-same')
        self.assertEquals(gatherer.heard, ['one'])

        self.flt(livepage.handler(twoHandler, identifier='same'))
        gatherer.handleInput('--handler-same')
        self.assertEquals(gatherer.heard, ['one', 'two'])

        self.livepage = lp

    def test_decoratorLike(self):
        decorator = livepage.handler(livepage.document)
        self.assertEquals(
            self.flt(decorator(argsHandler)),
            livepage.ctsTemplate % (fakeId, ',document', livepage.handledEventPostlude))


def onClick(client):
    client.sendScript('null;')


def argsHandler(client, *args):
    client.sendScript(','.join(args))


def oneHandler(client):
    client.sendScript('one')


def twoHandler(client):
    client.sendScript('two')


