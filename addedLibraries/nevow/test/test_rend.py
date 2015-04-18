# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from zope.interface import implements, Interface

from twisted.internet import defer
from twisted.trial import unittest
from twisted.trial.util import suppress as SUPPRESS
from twisted.python.reflect import qual

from nevow import appserver
from nevow import inevow
from nevow import context
from nevow import flat
from nevow import rend
from nevow import loaders
from nevow.stan import slot
from nevow.tags import directive, p, html, ul, li, span, table, tr, th, td
from nevow.tags import div, invisible, head, title, strong, body, a
from nevow import testutil
from nevow import url
from nevow import util

import formless
from formless import webform as freeform
from formless import annotate
from formless import iformless


def deferredRender(res, request=None):
    if request is None:
        request = testutil.FakeRequest()
        request.d = defer.Deferred()

    d = util.maybeDeferred(res.renderHTTP,
        context.PageContext(
            tag=res, parent=context.RequestContext(
                tag=request)))

    def done(result):
        if isinstance(result, str):
            request.write(result)
        request.d.callback(request.accumulator)
        return result
    d.addCallback(done)
    return request.d


class TestPage(unittest.TestCase):

    def test_simple(self):
        xhtml = '<ul id="nav"><li>one</li><li>two</li><li>three</li></ul>'
        r = rend.Page(docFactory=loaders.htmlstr(xhtml))
        return deferredRender(r).addCallback(
            lambda result: self.assertEquals(result, xhtml))
    test_simple.suppress = [
        SUPPRESS(message=
                 r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                 "Please start using xmlfile and/or xmlstr.")]



    def test_extend(self):
        xhtml = '<ul id="nav"><li>one</li><li>two</li><li>three</li></ul>'
        class R(rend.Page):
            docFactory = loaders.htmlstr(xhtml)
        r = R()
        return deferredRender(r).addCallback(
            lambda result: self.assertEquals(result, xhtml))
    test_extend.suppress = [
        SUPPRESS(message=
                 r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                 "Please start using xmlfile and/or xmlstr.")]


    def test_data(self):
        xhtml = (
            '<ul id="nav" nevow:data="numbers" nevow:render="sequence">'
            '<li nevow:pattern="item" nevow:render="string">number</li>'
            '</ul>')

        class R(rend.Page):
            docFactory = loaders.htmlstr(xhtml)
            def data_numbers(self, context, data):
                return ['one', 'two', 'three']
        r = R()
        return deferredRender(r).addCallback(
            lambda result: self.assertEquals(
            result,
            '<ul id="nav"><li>one</li><li>two</li><li>three</li></ul>'))
    test_data.suppress = [
        SUPPRESS(message=
                 r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                 "Please start using xmlfile and/or xmlstr.")]


    def test_noData(self):
        """Test when data is missing, i.e. self.original is None and no data
        directives had been used"""
        class R(rend.Page):
            docFactory = loaders.htmlstr('<p nevow:render="foo"></p>')
            def render_foo(self, ctx, data):
                return ctx.tag.clear()[data]
        r = R()
        return deferredRender(r).addCallback(
            lambda result: self.assertIn('None', result))
    test_noData.suppress = [
        SUPPRESS(message=
                 r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                 "Please start using xmlfile and/or xmlstr.")]


    def test_render(self):
        xhtml = '<span nevow:render="replace">replace this</span>'

        class R(rend.Page):
            docFactory = loaders.htmlstr(xhtml)
            def render_replace(self, context, data):
                return context.tag.clear()['abc']

        r = R()
        return deferredRender(r).addCallback(
            lambda result: self.assertEquals(result, '<span>abc</span>'))
    test_render.suppress = [
        SUPPRESS(message=
                 r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                 "Please start using xmlfile and/or xmlstr.")]


    def test_dataAndRender(self):
        xhtml = '''
        <table nevow:data="numbers" nevow:render="sequence">
        <tr nevow:pattern="header"><th>English</th><th>French</th></tr>
        <tr nevow:pattern="item" nevow:render="row"><td><nevow:slot name="english"/></td><td><nevow:slot name="french"/></td></tr>
        </table>
        '''

        class R(rend.Page):
            docFactory = loaders.htmlstr(xhtml)
            def data_numbers(self, context, data):
                return [
                    ['one', 'un/une'],
                    ['two', 'deux'],
                    ['three', 'trois'],
                    ]
            def render_row(self, context, data):
                context.fillSlots('english', data[0])
                context.fillSlots('french', data[1])
                return context.tag

        r = R()
        d = deferredRender(r)
        d.addCallback(
            lambda result: self.assertEquals(
                result,
                '<table>'
                '<tr><th>English</th><th>French</th></tr>'
                '<tr><td>one</td><td>un/une</td></tr>'
                '<tr><td>two</td><td>deux</td></tr>'
                '<tr><td>three</td><td>trois</td></tr>'
                '</table>'))
    test_dataAndRender.suppress = [
        SUPPRESS(message=
                 r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                 "Please start using xmlfile and/or xmlstr.")]


    def test_stanData(self):
        class R(rend.Page):
            def data_numbers(context, data):
                return ['one', 'two', 'three']
            tags = ul(data=data_numbers, render=directive('sequence'))[
                li(pattern='item')[span(render=str)]
                ]
            docFactory = loaders.stan(tags)

        r = R()
        return deferredRender(r).addCallback(
            lambda result: self.assertEquals(result, '<ul><li>one</li><li>two</li><li>three</li></ul>'))

    def test_stanRender(self):


        class R(rend.Page):
            def render_replace(context, data):
                return context.tag.clear()['abc']
            tags = span(render=render_replace)['replace this']
            docFactory = loaders.stan(tags)

        r = R()
        return deferredRender(r).addCallback(
            lambda result: self.assertEquals(result, '<span>abc</span>'))

    def test_stanDataAndRender(self):

        class R(rend.Page):

            def data_numbers(context, data):
                return [
                    ['one', 'un/une'],
                    ['two', 'deux'],
                    ['three', 'trois'],
                    ]

            def render_row(context, data):
                context.fillSlots('english', data[0])
                context.fillSlots('french', data[1])
                return context.tag

            tags = table(data=data_numbers, render=directive('sequence'))[
                tr(pattern='header')[th['English'], th['French']],
                tr(pattern='item', render=render_row)[td[slot('english')], td[slot('french')]],
                ]

            docFactory = loaders.stan(tags)

        r = R()
        return deferredRender(r).addCallback(
            lambda result: self.assertEquals(result, '<table><tr><th>English</th><th>French</th></tr><tr><td>one</td><td>un/une</td></tr><tr><td>two</td><td>deux</td></tr><tr><td>three</td><td>trois</td></tr></table>'))

    def test_composite(self):

        class R(rend.Page):

            def render_inner(self, context, data):
                return rend.Page(docFactory=loaders.stan(div(id='inner')))

            docFactory = loaders.stan(
                div(id='outer')[
                    span(render=render_inner)
                    ]
                )
        r = R()
        return deferredRender(r).addCallback(
            lambda result: self.assertEquals(result, '<div id="outer"><div id="inner"></div></div>'))

    def _testDocFactoryInStanTree(self, docFactory, expected):
        class Page(rend.Page):
            docFactory = loaders.stan(div[invisible(render=directive('included'))])

            def __init__(self, included):
                self.included = included
                rend.Page.__init__(self)

            def render_included(self, context, data):
                return self.included

        return deferredRender(Page(docFactory)).addCallback(
            self.assertEqual, '<div>' + expected + '</div>')


    def test_stanInStanTree(self):
        """
        """
        return self._testDocFactoryInStanTree(
            loaders.stan(p['fee']),
            '<p>fee</p>')


    def test_htmlStringInStanTree(self):
        """
        Test that an htmlstr loader in a stan document is flattened by
        having its document loaded and flattened.
        """
        return self._testDocFactoryInStanTree(
            loaders.htmlstr('<p>fi</p>'),
            '<p>fi</p>')
    test_htmlStringInStanTree.suppress = [
        SUPPRESS(message=
                 r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                 "Please start using xmlfile and/or xmlstr.")]


    def test_xmlStringInStanTree(self):
        """
        Like L{test_htmlStringInStanTree}, but for an xmlstr loader.
        """
        return self._testDocFactoryInStanTree(
            loaders.xmlstr('<p>fo</p>'),
            '<p>fo</p>')


    def test_htmlFileInStanTree(self):
        """
        Like L{test_htmlStringInStanTree}, but for an htmlfile loader.
        """
        doc = '<p>fum</p>'
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(doc)
        f.close()

        return self._testDocFactoryInStanTree(
            loaders.htmlfile(temp),
            '<p>fum</p>')
    test_htmlFileInStanTree.suppress = [
        SUPPRESS(message=
                 r"\[v0.8\] htmlfile is deprecated because it's buggy. "
                 "Please start using xmlfile and/or xmlstr.")]


    def test_xmlFileInStanTree(self):
        """
        Like L{test_htmlStringInStanTree}, but for an xmlfile loader.
        """
        doc = '<p>I</p>'
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(doc)
        f.close()

        return self._testDocFactoryInStanTree(
            loaders.xmlfile(temp),
            '<p>I</p>')


    def test_reusedDocFactory(self):
        """
        Test that a docFactory which is used more than once behaves properly
        both times.
        """
        class Page(rend.Page):
            docFactory = loaders.stan(div[invisible(render=directive('included'))])

            def __init__(self, included):
                self.included = included
                rend.Page.__init__(self)

            def render_included(self, context, data):
                return self.included

        p1 = Page(loaders.stan('first'))
        p2 = Page(loaders.xmlstr('<p>second</p>'))

        d = deferredRender(p1)
        def rendered(result):
            self.assertEqual(result, '<div>first</div>')
            return deferredRender(p2)
        d.addCallback(rendered)

        def renderedAgain(result):
            self.assertEqual(result, '<div><p>second</p></div>')
        d.addCallback(renderedAgain)

        return d


    def test_buffered(self):
        class Page(rend.Page):
            buffered = True
            docFactory = loaders.stan(html[head[title['test']]])

        p = Page()
        return deferredRender(p).addCallback(
            lambda result:
            self.assertEquals(result, '<html><head><title>test</title></head></html>'))

    def test_component(self):
        """
        Test that the data is remembered correctly when a Page is embedded in
        a component-like manner.
        """

        class Data:
            foo = 'foo'
            bar = 'bar'

        class Component(rend.Fragment):

            def render_foo(self, context, data):
                return strong[data.foo]

            def render_bar(self, context, data):
                return data.bar

            docFactory = loaders.stan(p[render_foo, ' ', render_bar])

        class Page(rend.Page):
            docFactory = loaders.stan(div[Component(Data())])

        page = Page()
        return deferredRender(page).addCallback(
            lambda result:
            self.assertEquals(result, '<div><p><strong>foo</strong> bar</p></div>'))

    def test_fragmentContext(self):
        # A fragment is remembered as the IRendererFactory. It must create a new context
        # to avoid messing up the page's context.

        class Fragment(rend.Fragment):
            docFactory = loaders.stan(p(render=directive('foo')))
            def render_foo(self, ctx, data):
                return 'foo'

        class Page(rend.Page):
            docFactory = loaders.stan(
                    html(render=directive("template"))[
                        body[
                            p(render=directive("before")),
                            p[slot(name="maincontent")],
                            p(render=directive("after")),
                        ],
                    ]
                )

            def render_before(self,context,data):
                return context.tag["before"]

            def render_template(self,context,data):
                context.fillSlots('maincontent', Fragment())
                return context.tag

            def render_after(self,context,data):
                return context.tag["after"]

        result = Page().renderSynchronously()
        # print result
        self.failIf("'foo' was not found" in result)
        self.failIf("'after' was not found" in result)


    def test_rendererNotFound(self):
        """
        An unparameterized renderer which is not defined should render a
        message about the renderer not being defined.

        Wanted behaviour: missing renderers etc. raise an exception, with some
        helpful hints on where to locate the typo.

        Feel free to replace test_rendererNotFound{,Parametrized} with unit
        tests for the exception raising behaviour, if you do implement it.
        """
        class Page(rend.Page):
            docFactory = loaders.stan(html(render=directive("notfound")))
        page = Page()
        result = page.renderSynchronously()
        self.assertEquals(
            result,
            "<html>The renderer named 'notfound' was not found in %s.</html>"
            % util.escapeToXML(repr(page)))
    test_rendererNotFound.suppress = [
        SUPPRESS(category=DeprecationWarning,
            message=("Renderer 'notfound' missing on nevow.test.test_rend.Page"
                     " will result in an exception."))]


    def test_rendererNotFoundParameterized(self):
        """
        A parameterized renderer which is not defined should render a message
        about the renderer not being defined.
        """
        class Page(rend.Page):
            docFactory = loaders.stan(html(render=directive("notfound dummy")))
        page = Page()
        result = page.renderSynchronously()
        self.assertEquals(
            result,
            "<html>The renderer named 'notfound' was not found in %s.</html>"
            % util.escapeToXML(repr(page)))
    test_rendererNotFoundParameterized.suppress = [
        SUPPRESS(
            category=DeprecationWarning,
            message=("Renderer 'notfound' missing on nevow.test.test_rend.Page"
                     " will result in an exception."))]


    def test_missingRendererDeprecated(self):
        """
        Using a renderer which is not defined should emit a deprecation
        warning.
        """
        rendererName = "notfound"
        class MisdefinedPage(rend.Page):
            docFactory = loaders.stan(html(render=directive(rendererName)))
        page = MisdefinedPage()
        message = "Renderer %r missing on %s will result in an exception."
        message %= (rendererName, qual(MisdefinedPage))
        self.assertWarns(
            DeprecationWarning, message, rend.__file__,
            page.renderSynchronously)
    if getattr(unittest.TestCase, 'assertWarns', None) is None:
        test_missingRendererDeprecated.skip = "TestCase.assertWarns missing"



class TestFragment(unittest.TestCase):

    def test_deprecatedPatternAbuseNonsense(self):

        class Fragment(rend.Fragment):
            docFactory = loaders.stan(a(href=url.here)['Click!'])

        class Page(rend.Page):
            docFactory = loaders.stan(Fragment())

        # If this fails, fragment pattern abuse is probably broken again.
        return deferredRender(Page())


class TestRenderFactory(unittest.TestCase):

    def test_dataRenderer(self):
        ctx = context.WovenContext()
        ctx.remember(rend.RenderFactory(), inevow.IRendererFactory)
        self.assertEquals(flat.flatten(p(data='foo', render=directive('data')), ctx), '<p>foo</p>')

class TestConfigurableMixin(unittest.TestCase):
    def test_formRender(self):
        class FormPage(rend.Page):
            bind_test1 = [('foo', annotate.String()), ('bar', annotate.Integer())]
            bind_test2 = annotate.MethodBinding('test2', annotate.Method(
                arguments=[annotate.Argument('foo', annotate.String())]))

            bind_test3 = annotate.Property('test3', annotate.Integer())
            
            def bind_test4(self, ctx):
                return ([('foo', annotate.String()), ('bar', annotate.Integer())])
            
            def bind_test5(self, ctx):
                return annotate.MethodBinding('test5', annotate.Method(
                    arguments=[annotate.Argument('foo', annotate.String()),
                               annotate.Argument('bar', annotate.Integer())]))

            docFactory = loaders.stan(html[freeform.renderForms()])
        return deferredRender(FormPage())
    
    def test_formRenderDeferred(self):
        class FormPage(rend.Page):
            bind_test1 = defer.succeed([('foo', annotate.String()),
                                        ('bar', annotate.Integer())])
            bind_test2 = defer.succeed(annotate.MethodBinding('test2', annotate.Method(
                arguments=[annotate.Argument('foo', annotate.String())])))

            bind_test3 = defer.succeed(annotate.Property('test3', annotate.Integer()))
            
            def bind_test4(self, ctx):
                return defer.succeed([('foo', annotate.String()),
                                       ('bar', annotate.Integer())])
            
            def bind_test5(self, ctx):
                return defer.succeed(annotate.MethodBinding('test5', annotate.Method(
                    arguments=[annotate.Argument('foo', annotate.String()),
                               annotate.Argument('bar', annotate.Integer())])))

            docFactory = loaders.stan(html[freeform.renderForms()])
        return deferredRender(FormPage())


    def test_formPost(self):
        class FormPage(rend.Page):
            bind_test1 = ([('foo', annotate.Integer())])
            def test1(self, foo):
                return foo

        ctx = context.WovenContext()
        result = FormPage().postForm(ctx, 'test1', {'foo': ['42']})
        return result.addCallback(lambda result: self.assertEquals(result, 42))

    def test_formPostDeferred(self):
        class FormPage(rend.Page):
            bind_test1 = defer.succeed(([('foo', annotate.Integer())]))
            def test1(self, foo):
                return foo

        ctx = context.WovenContext()
        result = FormPage().postForm(ctx, 'test1', {'foo': ['42']})
        return result.addCallback(lambda result: self.assertEquals(result, 42))

    def test_formPostFailure(self):
        class FormPage(rend.Page):
            bind_test1 = ([('foo', annotate.Integer())])
            def test1(self, foo):
                return foo

        ctx = context.WovenContext()
        result = FormPage().postForm(ctx, 'test1', {'foo': ['hello, world!']})
        return self.assertFailure(result, annotate.ValidateError)

    def test_formPostFailureDeferred(self):
        class FormPage(rend.Page):
            bind_test1 = defer.succeed(([('foo', annotate.Integer())]))
            def test1(self, foo):
                return foo

        ctx = context.WovenContext()
        result = FormPage().postForm(ctx, 'test1', {'foo': ['hello, world!']})
        return self.assertFailure(result, annotate.ValidateError)

class IThing(formless.TypedInterface):
    foo = formless.String()

class Thing:
    implements(IThing)

class TestLocateConfigurable(unittest.TestCase):

    def test_onSelf(self):

        class Page(rend.Page):
            implements(IThing)
            docFactory = loaders.stan(html[freeform.renderForms()])

        page = Page()
        return deferredRender(page)

    def test_onSelfOriginal(self):

        class Page(rend.Page):
            docFactory = loaders.stan(html[freeform.renderForms('original')])

        page = Page(Thing())
        return deferredRender(page)

    def test_onKeyedConfigurable(self):

        class Page(rend.Page):

            def __init__(self):
                rend.Page.__init__(self)
                self.thing = Thing()

            def configurable_thing(self, context):
                return self.thing

            docFactory = loaders.stan(html[freeform.renderForms('thing')])

        page = Page()
        return deferredRender(page)


class TestDeferredDefaultValue(unittest.TestCase):
    def test_deferredProperty(self):
        class IDeferredProperty(formless.TypedInterface):
            d = formless.String()

        from nevow import util
        deferred = util.Deferred()
        deferred.callback('the default value')
        class Implementation(object):
            implements(IDeferredProperty)
            d = deferred

        return deferredRender(rend.Page(Implementation(), docFactory=loaders.stan(html[freeform.renderForms('original')]))).addCallback(
            lambda result: self.assertIn('value="the default value"', result))


class TestRenderString(unittest.TestCase):

    def test_simple(self):
        doc = div[p['foo'],p['bar']]
        return rend.Page(docFactory=loaders.stan(doc)).renderString().addCallback(
            lambda result: self.assertEquals(result, '<div><p>foo</p><p>bar</p></div>'))

    def test_parentCtx(self):
        class IFoo(Interface):
            pass
        ctx = context.WovenContext()
        ctx.remember('Hello!', IFoo)
        class Page(rend.Page):
            def render_foo(self, ctx, data):
                return IFoo(ctx)
            docFactory = loaders.stan(p[render_foo])
        return Page().renderString(ctx).addCallback(
            lambda result:
            self.assertEquals(
            result,
            '<p>Hello!</p>'
            ))

    def test_remembers(self):

        class Page(rend.Page):
            docFactory = loaders.stan(
                html[
                    body[
                        p(data=directive('foo'), render=directive('bar'))
                        ]
                    ]
                )
            def data_foo(self, ctx, data):
                return 'foo'
            def render_bar(self, ctx, data):
                return ctx.tag.clear()[data+'bar']

        return Page().renderString().addCallback(
            lambda result: self.assertEquals(result, '<html><body><p>foobar</p></body></html>'))


class TestRenderSynchronously(unittest.TestCase):

    def test_simple(self):

        doc = div[p['foo'],p['bar']]
        result = rend.Page(docFactory=loaders.stan(doc)).renderSynchronously()
        self.assertEquals(result, '<div><p>foo</p><p>bar</p></div>')

    def test_parentCtx(self):
        class IFoo(Interface):
            pass
        ctx = context.WovenContext()
        ctx.remember('Hello!', IFoo)
        class Page(rend.Page):
            def render_foo(self, ctx, data):
                return IFoo(ctx)
            docFactory = loaders.stan(p[render_foo])
        self.assertEquals(Page().renderSynchronously(ctx), '<p>Hello!</p>')


def getResource(root, path):
    return appserver.NevowSite(root).getPageContextForRequestContext(
            context.RequestContext(
                tag=testutil.FakeRequest(uri=path)))


class TestLocateChild(unittest.TestCase):

    def test_inDict(self):
        class Child(rend.Page):
            pass
        class Parent(rend.Page):
            pass
        p = Parent()
        p.putChild('child', Child())
        return getResource(p, '/child').addCallback(
            lambda r: self.failUnless(inevow.IResource.providedBy(r.tag)))

    def test_resourceAttr(self):
        class Child(rend.Page):
            pass
        class Parent(rend.Page):
            child_child = Child()
        p = Parent()
        return getResource(p, '/child').addCallback(
            lambda r: self.failUnless(inevow.IResource.providedBy(r.tag)))

    def test_methodAttr(self):
        class Child(rend.Page):
            pass
        class Parent(rend.Page):
            def child_now(self, request):
                return Child()
            def child_defer(self, request):
                return defer.succeed(None).addCallback(lambda x: Child())
        p = Parent()
        return self._dotestparent(p)

    def _dotestparent(self, p):

        return defer.DeferredList([
            getResource(p, '/now').addCallback(
            lambda r: self.failUnless(inevow.IResource.providedBy(r.tag))),

            getResource(p, '/defer').addCallback(

            lambda r: self.failUnless(inevow.IResource.providedBy(r.tag)))],
                                  fireOnOneErrback=True)

    def test_childFactory(self):
        class Child(rend.Page):
            pass
        class Parent(rend.Page):
            def childFactory(self, name, context):
                if name == 'now':
                    return Child()
                if name == 'defer':
                    return defer.succeed(None).addCallback(lambda x: Child())
        p = Parent()
        return self._dotestparent(p)

    def test_oldResource(self):
        from twisted.web import twcgi
        class Parent(rend.Page):
            child_child = twcgi.CGIScript('abc.cgi')
        p = Parent()
        return getResource(p, '/child').addCallback(
            lambda r: self.failUnless(inevow.IResource.providedBy(r.tag)))

    def test_noneChild(self):
        class Parent(rend.Page):
            def child_child(self, request):
                return None
            def geyDynamicChild(self, name, request):
                return None
        p = Parent()

        return defer.DeferredList([
            getResource(p, '/child').addCallback(
            lambda r: self.failUnless(isinstance(r.tag, rend.FourOhFour))),

            getResource(p, '/other').addCallback(
            lambda r: self.failUnless(isinstance(r.tag, rend.FourOhFour))
            )],
                                  fireOnOneErrback=True)

    def test_missingRemembrances(self):

        class IThing(Interface):
            pass

        class Page(rend.Page):

            def render_it(self, ctx, data):
                return ctx.locate(IThing)

            def child_child(self, ctx):
                ctx.remember("Thing", IThing)
                return defer.succeed(Page())

            docFactory = loaders.stan(html[render_it])

        page = Page()
        return getResource(page, '/child').addCallback(
            lambda r: self.failUnless(inevow.IResource.providedBy(r.tag)))

    def test_redirectToURL(self):
        redirectTarget = "http://example.com/bar"
        class RedirectingPage(rend.Page):
            def locateChild(self, ctx, segments):
                return url.URL.fromString(redirectTarget), ()

        page = RedirectingPage()
        def doAssert(r):
            ## Render the redirect.
            r.tag.renderHTTP(r)
            req = inevow.IRequest(r)
            self.assertEquals(req.redirected_to, redirectTarget)

        return getResource(page, '/url').addCallback(doAssert)

    def _testRedirecting(self,uchr):
        class RedirectingPage(rend.Page):
            def locateChild(self, ctx, segments):
                return url.URL.fromString(self.original), ()

        page = RedirectingPage(uchr)

        def dotest(r):
            r.tag.renderHTTP(r)
            self.assertEquals(uchr,
                              inevow.IRequest(r).redirected_to)

        return getResource(page, '/url').addCallback(dotest)


    def test_redirectQuoting(self):
        return self._testRedirecting('http://example.com/foo!!bar').addCallback(
            lambda ign: self._testRedirecting('http://example.com/foo!%40%24bar?b!%40z=123'))

    def test_stringChild(self):
        theString = "<html>Hello, world</html>"
        class StringChildPage(rend.Page):
            def child_foo(self, ctx):
                return theString
        page = StringChildPage()

        return getResource(page, '/foo').addCallback(
            lambda c: deferredRender(c.tag).addCallback(
            lambda result: self.assertEquals(result, theString)))

    def test_freeformChildMixin_nonTrue(self):
        """Configurables that have c.__nonzero__()==False are accepted."""
        class SimpleConf(object):
            implements(iformless.IConfigurable)
            # mock mock
            def postForm(self, ctx, bindingName, args):
                return 'SimpleConf OK'
        class FormPage(rend.Page):
            addSlash = True
            def configurable_(self, ctx):
                return SimpleConf()
        page = FormPage()

        D = getResource(page, '/foo')
        def x1(r):
            self.failUnless(isinstance(r.tag, rend.FourOhFour))
        D.addCallback(x1)

        def x2(ign):
            D2 = getResource(page, '/freeform_post!!foo')
            def x3(r):
                self.failIf(isinstance(r.tag, rend.FourOhFour))
                return deferredRender(r.tag).addCallback(
                    lambda result: self.assertEquals(result, 'You posted a form to foo'))
            D2.addCallback(x3)
            return D2
        D.addCallback(x2)

        def x4(ign):
            SimpleConf.__nonzero__ = lambda x: False

            D3 = getResource(page, '/freeform_post!!foo')
            def x5(r):
                self.failIf(isinstance(r.tag, rend.FourOhFour))
                return deferredRender(r.tag).addCallback(
                    lambda result:
                    self.assertEquals(result, 'You posted a form to foo'))
            return D3.addCallback(x5)
        D.addCallback(x4)
        return D


class TestStandardRenderers(unittest.TestCase):

    def test_data(self):
        ctx = context.WovenContext()

        ctx.remember('foo', inevow.IData)
        tag = p(render=rend.data)
        self.assertEquals(flat.flatten(tag, ctx), '<p>foo</p>')

        ctx.remember('\xc2\xa3'.decode('utf-8'), inevow.IData)
        tag = p(render=rend.data)
        self.assertEquals(flat.flatten(tag, ctx), '<p>\xc2\xa3</p>')

        ctx.remember([1,2,3,4,5], inevow.IData)
        tag = p(render=rend.data)
        self.assertEquals(flat.flatten(tag, ctx), '<p>12345</p>')

        ctx.remember({'foo':'bar'}, inevow.IData)
        tag = p(data=directive('foo'), render=rend.data)
        self.assertEquals(flat.flatten(tag, ctx), '<p>bar</p>')

class TestMacro(unittest.TestCase):

    def test_macro(self):
        doc = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xmlns:n="http://nevow.com/ns/nevow/0.1">
  <body>
    <n:invisible n:macro="content" />
  </body>
</html>
        """
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(doc)
        f.close()

        class Base(rend.Page):
            docFactory = loaders.xmlfile(temp)

        class Page1(Base):
            def macro_content(self, ctx):
                return p["Page1"]

        class Page2(Base):
            def macro_content(self, ctx):
                return p["Page2"]

        p1 = Page1()
        p2 = Page2()

        ctx1 = context.WovenContext()
        ctx2 = context.WovenContext()

        ctx1.remember(p1, inevow.IRendererFactory)
        ctx2.remember(p2, inevow.IRendererFactory)

        p1_str = p1.renderSynchronously(ctx1)
        p2_str = p2.renderSynchronously(ctx2)

        self.assertNotEquals(p1_str, p2_str)

    def test_macroInsideSpecialScope(self):
        """http://divmod.org/trac/ticket/490
        """
        class Base(rend.Page):
            def macro_content(self, ctx):
                return p["content"]
        
        class Page1(Base):
            docFactory = loaders.stan(
                html[
                    body(render=directive('foo'))[
                        p(macro=directive('content'))
                    ]
                ])
                
            def render_foo(self, ctx, data):
                return ctx.tag

        class Page2(Base):
            docFactory = loaders.stan(
                html[
                    body[
                        p(macro=directive('content'))
                    ]
                ])
            
        p1 = Page1()
        p2 = Page2()

        ctx1 = context.WovenContext()
        ctx2 = context.WovenContext()

        ctx1.remember(p1, inevow.IRendererFactory)
        ctx2.remember(p2, inevow.IRendererFactory)

        p1_str = p1.renderSynchronously(ctx1)
        p2_str = p2.renderSynchronously(ctx2)

        self.assertEquals(p1_str, p2_str)

