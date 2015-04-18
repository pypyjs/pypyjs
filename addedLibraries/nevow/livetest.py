
from twisted.internet import defer
from nevow import livepage, loaders, tags, rend, static, entities, util
from nevow.livepage import js


testFrameNode = js.testFrameNode
contentDocument = testFrameNode.contentDocument
gid = contentDocument.getElementById
XPathResult = js.XPathResult
null = js.null


class xpath(object):
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return 'nevow.livetest.xpath(%r)' % (self.path, )

    def _asjs(self, localName):
        yield livepage.var(
            js.targetXPathResult,
            contentDocument.evaluate(self.path,
                                     contentDocument,
                                     null,
                                     XPathResult.ANY_TYPE,
                                     null)), livepage.eol
        yield livepage.var(
            localName,
            js.targetXPathResult.iterateNext()), livepage.eol


class Driver(object):
    def __init__(self, handle, suite):
        self.handle = handle
        self.suite = list(suite)
        self.results = {}
        self.state = 0
        self.iterator = self.drive()
        self.nextTest()

    passes = 0
    failures = 0

    def drive(self):
        for i, test in enumerate(self.suite):
            self.state = i
            action, target, parameter = test
            actionCallable = getattr(self, 'action_%s' % (action, ), None)
            if actionCallable is not None:
                test = actionCallable(target, parameter)
                if test is not None:
                    yield  test

        self.handle.send(livepage.set('test-status', 'Complete'))

    def nextTest(self):
        try:
            test = self.iterator.next()
        except StopIteration:
            return
        self.handle.send(test)

    def passed(self):
        self.results[self.state] = True
        self.passes += 1
        self.handle.send(js.passed(self.state))
        self.nextTest()

    def failed(self, text=''):
        self.results[self.state] = False
        self.failures += 1
        self.handle.send(js.failed(self.state, text))
        self.nextTest()

    def checkException(self):
        def continueTests(ctx, status):
            if status == 'passed':
                self.passed()
            else:
                self.failed()

        continuer = self.handle.transient(continueTests)
        return livepage.anonymous(
            [livepage.js("if (testFrameNode.contentDocument.title != 'Exception') {\n\t"),
            continuer('passed'),
            livepage.js("\n} else {\n\t"),
            continuer('failed'),
            livepage.js("\n}")])

    def action_visit(self, target, param):
        yield js.addLoadObserver(self.checkException()), livepage.eol
        yield js.setContentLocation(target), livepage.eol

    def action_assert(self, target, param):
        def doAssert(ctx, actual):
            if param == actual:
                self.passed()
            else:
                self.failed("%r != %r" % (param, actual))

        if isinstance(target, xpath):
            yield target._asjs(js.targetNode)
        else:
            yield livepage.var(js.targetNode, gid(target)), livepage.eol

        yield self.handle.transient(
            doAssert, js.targetNode.innerHTML)

    def action_value(self, target, param):
        def doAssert(ctx, actual):
            if param == actual:
                self.passed()
            else:
                self.failed()
        if isinstance(target, xpath):
            yield target._asjs(js.targetNode)
        else:
            yield livepage.var(js.targetNode, gid(target)), livepage.eol
        yield self.handle.transient(
            doAssert, js.targetNode.value)

    def action_follow(self, target, param):
        if isinstance(target, xpath):
            yield target._asjs(js.targetNode)
        else:
            yield livepage.var(js.targetNode, gid(target)), livepage.eol

        yield [
            js.addLoadObserver(self.checkException()),
            livepage.eol,
            js.setContentLocation(js.targetNode.href)]

    def action_post(self, target, param):
        def passed(ctx):
            self.passed()

        if isinstance(target, xpath):
            yield target._asjs(js.targetForm)
        else:
            yield livepage.var(js.targetForm, contentDocument[target]), livepage.eol

        yield livepage.var(js.postTarget, js.targetForm.action), livepage.eol
        for key, value in param.items():
            yield livepage.assign(js.targetForm[key].value, value), livepage.eol
        yield js.addLoadObserver(
            livepage.anonymous(
                self.handle.transient(passed))), livepage.eol
        yield js.sendSubmitEvent(js.targetForm, livepage.anonymous(js))

    def action_submit(self, target, param):
        """This should only be used with livepage, to simulate an onsubmit.

        It could be possible to make this work when not testing a livepage
        app, using a monstrosity similar to that used by action_click, below.
        """
        def passed(ctx):
            self.passed()

        if isinstance(target, xpath):
            yield target._asjs(js.targetForm)
        else:
            yield livepage.var(js.targetForm, contentDocument[target]), livepage.eol

        yield livepage.var(js.postTarget, js.targetForm.action), livepage.eol
        for key, value in param.items():
            yield livepage.assign(js.targetForm[key].value, value), livepage.eol
        yield livepage.var(
            js.inputListener,
            contentDocument.defaultView.listenForInputEvents(
                livepage.anonymous(
                    self.handle.transient(passed)))), livepage.eol

        yield js.sendSubmitEvent(
            js.targetForm,
            livepage.anonymous(
                contentDocument.defaultView.stopListening(js.inputListener)))

    def action_click(self, target, param):
        """TODO: Either decide that this should only be used in the presence
        of a real, honest-to-god livepage app, or figure out some way to simplify
        this monstrosity.
        """
        def passed(ctx):
            self.passed()

        if isinstance(target, xpath):
            yield target._asjs(js.targetNode)
        else:
            yield livepage.var(js.targetNode, gid(target)), livepage.eol

        ## If the testee is using livepage, we don't want the test to pass
        ## until all input events (and the response javascript from these
        ## input events) have passed. To do this we use listenForInputEvents,
        ## passing a continuation function which will be called when all input
        ## event responses have been evaluated. We call stopListening
        ## immediately after sending the click event. This means we
        ## start listening for input events, simulate the click, then stop listening.
        ## If any input events were initiated during the click, our test only passes
        ## when all event responses have been processed.

        ## If we are not using livepage, listenForInputEvents will not be defined.
        ## Because it is hard to do javascript tests (if statement) from python,
        ## ifTesteeUsingLivePage has been defined in livetest-postscripts.
        testDidPass = self.handle.transient(passed)
        yield [
            js.ifTesteeUsingLivePage(
                ## Using livepage
                livepage.anonymous(
                    livepage.assign(
                        ## Save the listener in a variable so we can stop listening later
                        js.inputListener,
                        contentDocument.defaultView.listenForInputEvents(
                            ## When all observed events complete, continue running tests
                            livepage.anonymous(
                                testDidPass)))),
                ## Not using livepage; do nothing here.
                livepage.anonymous('')), livepage.eol,
            js.sendClickEvent(
                ## Click our node.
                js.targetNode,
                ## Immediately after clicking the node, run this stuff.
                livepage.anonymous(
                    js.ifTesteeUsingLivePage(
                        ## We're done clicking the node, and we're using livepage.
                        ## Stop listening for input events. This will fire the continuation
                        ## immediately if no input events were observed; otherwise it
                        ## will wait for all responses to be evaluated before firing the
                        ## continuation.
                        livepage.anonymous(contentDocument.defaultView.stopListening(js.inputListener)),
                        ## We're done clicking the node, and we are not using livepage.
                        ## Call testDidPass.
                        livepage.anonymous(testDidPass))))]

    def action_call(self, target, param):
        # Import reactor here to avoid installing default at startup
        from twisted.internet import reactor
        def doit():
            target(self.handle, *param).addCallback(
                lambda result: self.passed()
            ).addErrback(
                lambda result: self.failed())
        reactor.callLater(0, doit)
        return ''

    def action_fail(self, target, param):
        # Import reactor here to avoid installing default at startup
        from twisted.internet import reactor
        def doit():
            target(self.handle, *param).addCallback(
                lambda result: self.failed()
            ).addErrback(
                lambda result: self.passed())
        reactor.callLater(0, doit)
        


class Tester(livepage.LivePage):
    addSlash = True
    child_css = static.File(util.resource_filename('nevow', 'livetest.css'))
    child_scripts = static.File(util.resource_filename('nevow', 'livetest.js'))
    child_postscripts = static.File(util.resource_filename('nevow', 'livetest-postscripts.js'))
    docFactory = loaders.stan(tags.html[
        tags.head[
            tags.script(src="scripts"),
            tags.link(rel="stylesheet", type="text/css", href="css")],
        tags.body[
            tags.table(id="testprogress")[
                tags.tr[
                    tags.th["Tests"], tags.th["Pass"], tags.th["Fail"]],
                tags.tr[
                    tags.td(id="test-status")["Running"],
                    tags.td(id="test-passes", _class="test-passes")[entities.nbsp],
                    tags.td(id="test-failures", _class="test-failures")[entities.nbsp]]],
            tags.table(id="testresults", render=tags.directive('sequence'))[
                tags.tr(pattern="item", render=tags.directive('test'))[
                    tags.td(title=tags.slot('action'))[tags.slot('action')],
                    tags.td(title=tags.slot('target'))[tags.slot('target')],
                    tags.td(title=tags.slot('parameter'))[tags.slot('parameter')]]],
            tags.iframe(id="testframe", src="asdf"),
            tags.script(src="postscripts"),
            livepage.glue]])

    def beforeRender(self, ctx):
        self.testId = 0

    def render_test(self, ctx, test):
        ctx.tag(id=("test-", self.testId))
        action, target, parameter = test
        ctx.fillSlots('action', action)
        ctx.fillSlots('target', str(target))
        ctx.fillSlots('parameter', str(parameter))
        self.testId += 1
        return ctx.tag

    def goingLive(self, ctx, handle):
        Driver(handle, self.original)


class ChildXPath(rend.Page):
    docFactory = loaders.stan(
        tags.html[
            tags.body[
                tags.div[
                    tags.span[
                        tags.div(id='target-node-identifier')[
                            'expected content']]]]])


def thingThatPasses(_):
    return defer.succeed(None)


def thingThatFails(_):
    return defer.fail(None)


class TestTests(rend.Page):
    addSlash = True
    docFactory = loaders.stan(tags.html[tags.a(href="/testtests/tests/")["Run tests"]])
    child_foo = '<html><body><div id="body">foo</div><form method="POST", name="theForm" action="postTarget"><input name="blah" /></form></body></html>'
    child_bar = "bar"
    child_baz = '<html><body onclick="alert(event.clientX);alert( event.clientY);"><div id="body">toot</div><a id="nextPage" href="foo" onclick="alert(\'clicked\')">Foo</a></body></html>'

    child_clickHandler = """<html>
    <body>
        <a id="theClicker" onclick="this.innerHTML='Clicked'">Click me!</a>
    </body>
</html>"""

    def child_postTarget(self, ctx):
        return rend.Page(
            docFactory=loaders.stan(
                tags.html[tags.body(id="body")[str(ctx.arg('blah'))]]))

    def child_testtests(self, ctx):
        return self

    def child_xpath(self, ctx):
        ## print 'lkfjasldkjasd!!!!!!!!'
        return ChildXPath()

    child_tests = Tester([
    ('visit', '/testtests/xpath', ''),
    ('assert', xpath('/html/body/div/span/div[@id="target-node-identifier"]'), 'expected content'),
    ('visit', '/testtests/foo', ''),
    ('visit', '/testtests/bar', ''),
    ('visit', '/testtests/baz', ''),
    ('assert', 'body', 'toot'),
    ('follow', 'nextPage', ''),
    ('assert', 'body', 'foo'),
    ('post', 'theForm', dict(blah="blah")),
    ('assert', 'body', 'blah'),
    ('visit', '/testtests/clickHandler', ''),
    ('click', 'theClicker', ''),
    ('assert', 'theClicker', 'Clicked'),
    ('call', thingThatPasses, ()),
    ('fail', thingThatFails, ())
])


def createResource():
    return TestTests()

