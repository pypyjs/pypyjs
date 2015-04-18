
"""
Tests for L{nevow.page.Element}
"""

from zope.interface.verify import verifyObject

from twisted.internet.defer import Deferred
from twisted.trial.unittest import TestCase

from nevow.rend import Page
from nevow.inevow import IRequest, IRenderable
from nevow.testutil import FakeRequest
from nevow.context import WovenContext
from nevow.loaders import stan, xmlstr
from nevow.tags import directive, invisible, p
from nevow.errors import MissingRenderMethod, MissingDocumentFactory
from nevow.page import FlattenerError, Element, renderer
from nevow.page import deferflatten as newFlatten
from nevow.flat import flatten as synchronousFlatten
from nevow.flat import flattenFactory as oldFlatten


class ElementTests(TestCase):
    """
    Tests for the awesome new L{Element} class.
    """
    def test_renderable(self):
        """
        L{Element} implements L{IRenderable}.
        """
        self.assertTrue(verifyObject(IRenderable, Element()))


    def test_missingDocumentFactory(self):
        """
        L{Element.render} raises L{MissingDocumentFactory} if the C{docFactory}
        attribute is C{None}.
        """
        element = Element()
        err = self.assertRaises(MissingDocumentFactory, element.render, None)
        self.assertIdentical(err.element, element)


    def test_missingDocumentFactoryRepr(self):
        """
        Test that a L{MissingDocumentFactory} instance can be repr()'d without
        error.
        """
        class PrettyReprElement(Element):
            def __repr__(self):
                return 'Pretty Repr Element'
        self.assertIn('Pretty Repr Element',
                      repr(MissingDocumentFactory(PrettyReprElement())))


    def test_missingRendererMethod(self):
        """
        When called with the name which is not associated with a render method,
        L{Element.renderer} raises L{MissingRenderMethod}.
        """
        element = Element()
        err = self.assertRaises(
            MissingRenderMethod, element.renderer, "foo")
        self.assertIdentical(err.element, element)
        self.assertEqual(err.renderName, "foo")


    def test_missingRenderMethodRepr(self):
        """
        Test that a L{MissingRenderMethod} instance can be repr()'d without
        error.
        """
        class PrettyReprElement(Element):
            def __repr__(self):
                return 'Pretty Repr Element'
        s = repr(MissingRenderMethod(PrettyReprElement(),
                                     'expectedMethod'))
        self.assertIn('Pretty Repr Element', s)
        self.assertIn('expectedMethod', s)


    def test_definedRenderer(self):
        """
        When called with the name of a defined render method, L{Element.renderer}
        returns that render method.
        """
        class ElementWithRenderMethod(Element):
            def foo(self, request, tag):
                return "bar"
            renderer(foo)
        foo = ElementWithRenderMethod().renderer("foo")
        self.assertEqual(foo(None, None), "bar")


    def test_render(self):
        """
        L{Element.render} loads a document from the C{docFactory} attribute and
        returns it.
        """
        args = []
        preproc = object()
        class DocFactory(object):
            def load(self, ctx, preprocessors, precompile=None):
                args.append(preprocessors)
                return "result"

        element = Element()
        element.preprocessors = (preproc,)
        element.docFactory = DocFactory()
        self.assertEqual(element.render(None), "result")
        self.assertEqual(args, [(preproc,)])


    def test_overriddenRend(self):
        """
        If an L{Element} subclass overrides C{rend}, L{Element.render} calls
        the overridden method and returns its result.
        """
        contexts = []
        class OldStyleElement(Element):
            docFactory = stan("Hello, world!")
            def rend(self, ctx, data):
                contexts.append(ctx)
                return Element.rend(self, ctx, data)
        request = FakeRequest()
        element = OldStyleElement()
        self.assertEqual(element.render(request), ["Hello, world!"])
        [ctx] = contexts
        self.assertTrue(isinstance(ctx, WovenContext))
        self.assertIdentical(IRequest(ctx), request)



class FlattenIntegrationTests(TestCase):
    """
    Tests for integration between L{Element} and L{nevow._flat.deferflatten}.
    """
    def _render(self, fragment, request=None):
        """
        Test helper which tries to render the given fragment.
        """
        ctx = WovenContext()
        if request is None:
            request = FakeRequest()
        ctx.remember(request, IRequest)
        return Page(docFactory=stan(fragment)).renderString(ctx)


    def test_missingDocumentFactory(self):
        """
        Test that rendering a Element without a docFactory attribute raises
        the appropriate exception.
        """
        def cb(ignored):
            # The old flattener unconditionally logs errors.
            self.flushLoggedErrors(MissingDocumentFactory)
        d = self.assertFailure(self._render(Element()), FlattenerError)
        d.addCallback(cb)
        return d


    def test_missingRenderMethod(self):
        """
        Test that flattening an L{Element} with a C{docFactory} which has a tag
        with a render directive fails with L{FlattenerError} if there is no
        available render method to satisfy that directive.
        """
        element = Element(docFactory=stan(p(render=directive('renderMethod'))))
        def cb(ignored):
            # The old flattener unconditionally logs errors.
            self.flushLoggedErrors(MissingRenderMethod)
        d = self.assertFailure(self._render(element), FlattenerError)
        d.addCallback(cb)
        return d


    def test_simpleStanRendering(self):
        """
        Test that a Element with a simple, static stan document factory
        renders correctly.
        """
        f = Element(docFactory=stan(p["Hello, world."]))
        return self._render(f).addCallback(
            self.assertEquals, "<p>Hello, world.</p>")


    def test_docFactoryClassAttribute(self):
        """
        Test that if there is a non-None docFactory attribute on the class
        of an Element instance but none on the instance itself, the class
        attribute is used.
        """
        class SubElement(Element):
            docFactory = stan(p["Hello, world."])
        return self._render(SubElement()).addCallback(
            self.assertEquals, "<p>Hello, world.</p>")


    def test_simpleXHTMLRendering(self):
        """
        Test that a Element with a simple, static xhtml document factory
        renders correctly.
        """
        f = Element(docFactory=xmlstr("<p>Hello, world.</p>"))
        return self._render(f).addCallback(
            self.assertEquals, "<p>Hello, world.</p>")


    def test_stanDirectiveRendering(self):
        """
        Test that a Element with a valid render directive has that directive
        invoked and the result added to the output.
        """
        renders = []
        class RenderfulElement(Element):
            def renderMethod(self, request, tag):
                renders.append((self, request))
                return tag["Hello, world."]
            renderer(renderMethod)
        request = object()
        element = RenderfulElement(
            docFactory=stan(p(render=directive('renderMethod'))))
        finished = self._render(element, request)
        def cbFinished(result):
            self.assertEqual(result, "<p>Hello, world.</p>")
            self.assertEqual(renders, [(element, request)])
        finished.addCallback(cbFinished)
        return finished


    def test_stanDirectiveRenderingOmittingTag(self):
        """
        Test that a Element with a render method which omits the containing
        tag successfully removes that tag from the output.
        """
        class RenderfulElement(Element):
            def renderMethod(self, request, tag):
                return "Hello, world."
            renderer(renderMethod)
        f = RenderfulElement(
            docFactory=stan(p(render=directive('renderMethod'))[
                    "Goodbye, world."]))
        return self._render(f).addCallback(
            self.assertEquals, "Hello, world.")


    def test_elementContainingStaticElement(self):
        """
        Test that a Element which is returned by the render method of another
        Element is rendered properly.
        """
        class RenderfulElement(Element):
            def renderMethod(self, request, tag):
                return tag[Element(docFactory=stan("Hello, world."))]
            renderer(renderMethod)
        f = RenderfulElement(
            docFactory=stan(p(render=directive('renderMethod'))))
        return self._render(f).addCallback(
            self.assertEquals, "<p>Hello, world.</p>")


    def test_elementContainingDynamicElement(self):
        """
        Test that directives in the document factory of a Element returned from a
        render method of another Element are satisfied from the correct object:
        the "inner" Element.
        """
        class OuterElement(Element):
            def outerMethod(self, request, tag):
                return tag[InnerElement(docFactory=stan(directive("innerMethod")))]
            renderer(outerMethod)
        class InnerElement(Element):
            def innerMethod(self, request, tag):
                return "Hello, world."
            renderer(innerMethod)
        f = OuterElement(
            docFactory=stan(p(render=directive('outerMethod'))))
        return self._render(f).addCallback(
            self.assertEquals, "<p>Hello, world.</p>")


    def test_synchronousFlatten(self):
        """
        Flattening a L{Element} with no Deferreds using the old synchronous
        flattener API returns a value synchronously.
        """
        element = Element()
        element.docFactory = stan(["hello, world"])
        self.assertEqual(synchronousFlatten(element), "hello, world")


    def test_synchronousFlattenError(self):
        """
        If the old flattener encounters an exception while flattening an
        L{IRenderable}, the exception is raised to the caller of the flattener
        API.
        """
        element = Element()
        element.docFactory = stan(invisible(render=directive('foo')))
        self.assertRaises(FlattenerError, synchronousFlatten, element)


    def test_flattenable(self):
        """
        Flattening L{Element} instances with the new flatten function results in
        the flattened version of whatever their C{render} method returns.
        """
        element = Element()
        element.docFactory = stan(["Hello, world"])
        result = []
        finished = newFlatten(FakeRequest(), element, False, False, result.append)
        finished.addCallback(lambda ignored: "".join(result))
        finished.addCallback(self.assertEqual, "Hello, world")
        return finished


    def test_oldFlattenable(self):
        """
        Flattening L{Element} instances with the old flatten function results in
        the flattened version of whatever their C{render} method returns.
        """
        result = []
        element = Element()
        element.docFactory = stan(['"&<>'])
        request = FakeRequest()
        context = WovenContext()
        context.remember(request)
        finished = oldFlatten(element, context, result.append, lambda ign: ign)
        finished.addCallback(lambda ign: "".join(result))
        finished.addCallback(self.assertEqual, '"&amp;&lt;&gt;')
        return finished


    def test_oldFlattenableInAttribute(self):
        """
        Flattening a L{Element} as the value of an attribute of a L{Tag} XML
        attribute escapes the element's flattened document.
        """
        result = []
        element = Element()
        element.docFactory = stan(['"&<>'])
        request = FakeRequest()
        context = WovenContext()
        context.remember(request)
        finished = oldFlatten(p(foo=element), context, result.append, lambda ign: ign)
        finished.addCallback(lambda ign: "".join(result))
        finished.addCallback(self.assertEqual, '<p foo="&quot;&amp;&lt;&gt;"></p>')
        return finished


    def test_oldFlattenableOverriddenRend(self):
        """
        Flattening L{Element} instances with an overridden C{rend} method
        flattened with the old flatten function results in the flattened
        version of whatever their C{rend} method returns.
        """
        renders = []
        class OldStyleElement(Element):
            docFactory = stan("Hello, world")
            def rend(self, ctx, data):
                return invisible(render=directive("foo"))[Element.rend(self, ctx, data)]

            def foo(self, request, tag):
                renders.append((self, request))
                return p[tag]
            renderer(foo)

        result = []
        element = OldStyleElement()
        request = FakeRequest()
        context = WovenContext()
        context.remember(request)
        finished = oldFlatten(element, context, result.append, lambda ign: ign)
        def cbFinished(ignored):
            self.assertEqual("".join(result), "<p>Hello, world</p>")
            self.assertEqual(renders, [(element, request)])
        finished.addCallback(cbFinished)
        return finished


    def test_oldFlattenableError(self):
        """
        If the old flattener encounters an asynchronous Failure while
        flattening an L{IRenderable}, the returned L{Deferred} fires with the
        failure.
        """
        result = Deferred()
        element = Element()
        element.docFactory = stan(result)

        request = FakeRequest()
        context = WovenContext()
        context.remember(request)

        accumulator = []
        finished = oldFlatten(element, context, accumulator.append, lambda ign: ign)
        result.addErrback(lambda err: err.trap(RuntimeError))
        finished = self.assertFailure(finished, RuntimeError)
        result.errback(RuntimeError("test error"))
        return finished
