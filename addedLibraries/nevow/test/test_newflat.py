# Copyright (c) 2008 Divmod.
# See LICENSE for details.

"""
Tests for L{nevow._flat}.
"""

import sys, traceback

from zope.interface import implements

from twisted.trial.unittest import TestCase
from twisted.internet.defer import Deferred, succeed

from nevow.inevow import IRequest, IQ, IRenderable, IData
from nevow._flat import FlattenerError, UnsupportedType, UnfilledSlot
from nevow._flat import flatten, deferflatten
from nevow.tags import Proto, Tag, slot, raw, xml
from nevow.tags import invisible, br, div, directive
from nevow.entities import nbsp
from nevow.url import URL
from nevow.rend import Fragment
from nevow.loaders import stan
from nevow.flat import flatten as oldFlatten, precompile as oldPrecompile
from nevow.flat.ten import registerFlattener
from nevow.testutil import FakeRequest
from nevow.context import WovenContext

# Use the co_filename mechanism (instead of the __file__ mechanism) because
# it is the mechanism traceback formatting uses.  The two do not necessarily
# agree with each other.  This requires a code object compiled in this file.
# The easiest way to get a code object is with a new function.  I'll use a
# lambda to avoid adding anything else to this namespace.  The result will
# be a string which agrees with the one the traceback module will put into a
# traceback for frames associated with functions defined in this file.
HERE = (lambda: None).func_code.co_filename


class TrivialRenderable(object):
    """
    An object which renders to a parameterized value.

    @ivar result: The object which will be returned by the render method.
    @ivar requests: A list of all the objects passed to the render method.
    """
    implements(IRenderable)

    def __init__(self, result):
        self.result = result
        self.requests = []


    def render(self, request):
        """
        Give back the canned response and record the given request.
        """
        self.requests.append(request)
        return self.result



class RenderRenderable(object):
    """
    An object which renders to a parameterized value and has a render method
    which records how it is invoked.

    @ivar renders: A list of two-tuples giving the arguments the render method
        has been invoked with.
    @ivar name: A string giving the name of the render method.
    @ivar tag: The value which will be returned from C{render}.
    @ivar result: The value which will be returned from the render method.
    """
    implements(IRenderable)

    def __init__(self, renders, name, tag, result):
        self.renders = renders
        self.name = name
        self.tag = tag
        self.result = result


    def renderer(self, name):
        if name == self.name:
            return self.renderMethod
        raise ValueError("Invalid renderer name")


    def renderMethod(self, request, tag):
        self.renders.append((self, request))
        return self.result


    def render(self, request):
        return self.tag



class FlattenMixin:
    """
    Helper defining an assertion method useful for flattener tests.
    """
    def assertStringEqual(self, value, expected):
        """
        Assert that the given value is a C{str} instance and that it equals the
        expected value.
        """
        self.assertTrue(isinstance(value, str))
        self.assertEqual(value, expected)



class FlattenTests(TestCase, FlattenMixin):
    """
    Tests for L{nevow._flat.flatten}.
    """
    def flatten(self, root, request=None):
        """
        Helper to get a string from L{flatten}.
        """
        result = []
        # This isn't something shorter because this way is nicer to look at in
        # a debugger.
        for part in flatten(request, root, False, False):
            result.append(part)
        return "".join(result)


    def test_unflattenable(self):
        """
        Flattening an object which references an unflattenable object fails
        with L{FlattenerError} which gives the flattener's stack at the
        point of failure and which has an L{UnsupportedType} exception in
        its arguments.
        """
        unflattenable = object()
        deepest = [unflattenable]
        middlest = (deepest,)
        outermost = [middlest]
        err = self.assertRaises(FlattenerError, self.flatten, outermost)
        self.assertEqual(
            err._roots, [outermost, middlest, deepest, unflattenable])
        self.assertTrue(isinstance(err.args[0], UnsupportedType))


    def test_str(self):
        """
        An instance of L{str} is flattened to itself.
        """
        self.assertStringEqual(self.flatten('bytes<>&"\0'), 'bytes<>&"\0')


    def test_raw(self):
        """
        An instance of L{raw} is flattened to itself.
        """
        self.assertStringEqual(
            self.flatten(raw('bytes<>^&"\0')), 'bytes<>^&"\0')


    def test_attributeRaw(self):
        """
        An instance of L{raw} is flattened with " quoting if C{True} is passed
        for C{inAttribute}.  L{raw} instances are expected to have already had
        &, <, and > quoted.  L{raw} support is primarily for backwards
        compatibility.
        """
        self.assertStringEqual(
            "".join(flatten(None, raw('"&<>'), True, True)), '&quot;&<>')


    def test_attributeString(self):
        """
        An instance of L{str} is flattened with attribute quoting rules if
        C{True} is passed for C{inAttribute}.
        """
        self.assertStringEqual(
            "".join(flatten(None, '"&<>', True, False)),
            "&quot;&amp;&lt;&gt;")


    def test_textNodeString(self):
        """
        An instance of L{str} is flattened with XML quoting rules if C{True} is
        passed for C{inXML}.
        """
        self.assertStringEqual(
            "".join(flatten(None, '"&<>', False, True)),
            '"&amp;&lt;&gt;')


    def test_unicode(self):
        """
        An instance of L{unicode} is flattened to the UTF-8 representation of
        itself.
        """
        self.assertStringEqual(self.flatten(u'bytes<>&"\0'), 'bytes<>&"\0')
        unich = u"\N{LATIN CAPITAL LETTER E WITH GRAVE}"
        self.assertStringEqual(self.flatten(unich), unich.encode('utf-8'))


    def test_xml(self):
        """
        An L{xml} instance is flattened to the UTF-8 representation of itself.
        """
        self.assertStringEqual(self.flatten(xml("foo")), "foo")
        unich = u"\N{LATIN CAPITAL LETTER E WITH GRAVE}"
        self.assertStringEqual(self.flatten(xml(unich)), unich.encode('utf-8'))


    def test_entity(self):
        """
        An instance of L{Entity} is flattened to the XML representation of an
        arbitrary codepoint.
        """
        self.assertStringEqual(self.flatten(nbsp), "&#160;")


    def test_entityChild(self):
        """
        An instance of L{Entity} which is a child of a L{Tag} is flattened to
        the XML representation of an arbitrary codepoint.
        """
        self.assertStringEqual(
            self.flatten(div[nbsp]), "<div>&#160;</div>")


    def test_entityAttribute(self):
        """
        An instance of L{Entity} which is the value of an attribute of a L{Tag}
        is flattened to the XML representation of an arbitrary codepoint.
        """
        self.assertStringEqual(
            self.flatten(div(foo=nbsp)), '<div foo="&#160;"></div>')


    def test_iterable(self):
        """
        A C{list}, C{tuple} or C{generator} is flattened to the concatenation
        of whatever its elements flatten to, in order.
        """
        sequence = ("bytes", "<", ">", "&")
        result = "bytes<>&"
        self.assertStringEqual(self.flatten(tuple(sequence)), result)
        self.assertStringEqual(self.flatten(list(sequence)), result)
        def gen():
            for e in sequence:
                yield e
        self.assertStringEqual(self.flatten(gen()), result)


    def test_singletonProto(self):
        """
        L{Proto} instances corresponding to tags which are allowed to be
        self-closing are flattened that way.
        """
        self.assertStringEqual(self.flatten(br), "<br />")


    def test_nonSingletonProto(self):
        """
        L{Proto} instances corresponding to tags which are not allowed to be
        self-closing are not flattened that way.
        """
        self.assertStringEqual(self.flatten(div), "<div></div>")


    def test_invisibleProto(self):
        """
        L{Proto} instances with an empty C{name} attribute don't have markup
        generated for them.
        """
        self.assertStringEqual(self.flatten(invisible), "")
        self.assertStringEqual(self.flatten(Proto("")), "")


    def test_emptySingletonTag(self):
        """
        L{Tag} instances which are allowed to be self-closing are flattened
        that way.
        """
        self.assertStringEqual(self.flatten(br()), "<br />")


    def test_emptyNonSingletonTag(self):
        """
        L{Tag} instances which are not allowed to be self-closing are not
        flattened that way.
        """
        self.assertStringEqual(self.flatten(div()), "<div></div>")


    def test_invisibleTag(self):
        """
        L{Tag} instances with an empty C{tagName} attribute don't have markup
        generated for them, only for their children.
        """
        self.assertStringEqual(self.flatten(invisible["foo"]), "foo")
        self.assertStringEqual(self.flatten(Tag("")["foo"]), "foo")


    def test_unicodeTagName(self):
        """
        A L{Tag} with a C{tagName} attribute which is C{unicode} instead of
        C{str} is flattened to an XML representation.
        """
        self.assertStringEqual(self.flatten(Tag(u'div')), "<div></div>")
        self.assertStringEqual(self.flatten(Tag(u'div')['']), "<div></div>")


    def test_unicodeAttributeName(self):
        """
        A L{Tag} with an attribute name which is C{unicode} instead of C{str}
        is flattened to an XML representation.
        """
        self.assertStringEqual(
            self.flatten(Tag(u'div', {u'foo': 'bar'})), '<div foo="bar"></div>')


    def test_stringTagAttributes(self):
        """
        C{str} L{Tag} attribute values are flattened by applying XML attribute
        value quoting rules.
        """
        self.assertStringEqual(
            self.flatten(div(foo="bar")), '<div foo="bar"></div>')
        self.assertStringEqual(
            self.flatten(div(foo='"><&')),
            '<div foo="&quot;&gt;&lt;&amp;"></div>')


    def test_tupleTagAttributes(self):
        """
        C{tuple} L{Tag} attribute values are flattened by flattening the tuple
        and applying XML attribute value quoting rules to the result.
        """
        self.assertStringEqual(
            self.flatten(div(foo=('"', ">", "<", "&"))),
            '<div foo="&quot;&gt;&lt;&amp;"></div>')


    def test_tagChildren(self):
        """
        The children of a L{Tag} are flattened to strings included inside the
        XML markup delimiting the tag.
        """
        self.assertStringEqual(
            self.flatten(div["baz"]), '<div>baz</div>')
        self.assertStringEqual(
            self.flatten(div[["b", "a", "z"]]), '<div>baz</div>')


    def test_nestedTags(self):
        """
        The contents of a L{Tag} which is a child of another L{Tag} should be
        quoted just once.
        """
        self.assertStringEqual(
            self.flatten(div[div['&']]),
            "<div><div>&amp;</div></div>")


    def test_patternTag(self):
        """
        A L{Tag} with a I{pattern} special is omitted from the flattened
        output.
        """
        self.assertStringEqual(self.flatten(div(pattern="foo")), "")


    def test_onePatternTag(self):
        """
        A L{Tag} returned from L{IQ.onePattern} is represented in the flattened
        output.
        """
        self.assertStringEqual(
            self.flatten(IQ(div(pattern="foo")).onePattern("foo")),
            "<div></div>")


    def test_renderAttribute(self):
        """
        A L{Tag} with a I{render} special is replaced with the return value of
        the corresponding render method on the L{IRenderable} above the tag.
        """
        result = ("foo", " ", "bar")
        renders = []
        class RendererRenderable(TrivialRenderable):
            def render_foo(self, request, tag):
                renders.append((request, tag))
                return result

            def renderer(self, name):
                return getattr(self, 'render_' + name)

        request = object()
        tag = div(render="foo", bar="baz")["quux"]
        renderer = RendererRenderable(tag)
        self.assertStringEqual(self.flatten(renderer, request), "".join(result))
        self.assertEqual(len(renders), 1)
        self.assertIdentical(renders[0][0], request)
        self.assertEqual(renders[0][1].tagName, tag.tagName)
        self.assertEqual(renders[0][1].attributes, {"bar": "baz"})
        self.assertEqual(renders[0][1].children, ["quux"])


    def test_renderDirectiveAttribute(self):
        """
        A L{Tag} with a I{render} special which is a L{directive} is treated
        the same way as if the special value were just a string.
        """
        result = ("foo", " ", "bar")
        renders = []
        class RendererRenderable(TrivialRenderable):
            def render_foo(self, request, tag):
                renders.append((request, tag))
                return result

            def renderer(self, name):
                return getattr(self, 'render_' + name)

        request = object()
        tag = div(render=directive("foo"), bar="baz")["quux"]
        renderer = RendererRenderable(tag)
        self.assertStringEqual(self.flatten(renderer, request), "".join(result))
        self.assertEqual(len(renders), 1)
        self.assertIdentical(renders[0][0], request)
        self.assertEqual(renders[0][1].tagName, tag.tagName)
        self.assertEqual(renders[0][1].attributes, {"bar": "baz"})
        self.assertEqual(renders[0][1].children, ["quux"])


    def test_renderAttributeOnRenderableNestedInRenderable(self):
        """
        A L{Tag} with a renderer which returns an L{IRenderable} which renders
        to a L{Tag} with a I{render} special is replaced with the return value
        of the corresponding render method on the nested L{IRenderable}.
        """
        result = ("foo", " ", "bar")
        request = object()
        renders = []
        inner = RenderRenderable(renders, "bar", div(render="bar"), result)
        outer = RenderRenderable(renders, "foo", div(render="foo"), inner)
        self.assertStringEqual(self.flatten(outer, request), "".join(result))
        self.assertEqual(renders, [(outer, request), (inner, request)])


    def test_renderAttributeNestedInList(self):
        """
        A L{Tag} with a renderer which is in a list which is returned by
        L{IRenderable.render} is replaced with the result of the named renderer
        on the L{IRenderable} which returned the list.
        """
        result = ("foo", " ", "bar")
        renders = []
        renderable = RenderRenderable(
            renders, "foo", [div(render="foo")], result)
        self.assertStringEqual(
            self.flatten(renderable, None), "".join(result))


    def test_renderAttributeNestedInTag(self):
        """
        A L{Tag} with a renderer which is a child of a L{Tag} which was
        returned by L{IRenderable.render} is replaced with the result of the
        named renderer on the L{IRenderable} which returned the L{Tag}.
        """
        result = "quux"
        renders = []
        tag = div[div(render="foo")]
        renderable = RenderRenderable(renders, "foo", tag, result)
        self.assertStringEqual(
            self.flatten(renderable, None), "<div>quux</div>")


    def test_renderAttributeNestedInAttributeValue(self):
        """
        A L{Tag} with a renderer which is the value of an attribute of a L{Tag}
        which was returned by L{IRenderable.render} is replaced with the result
        of the named renderer on the L{IRenderable} which returned the L{Tag}.
        """
        result = "quux"
        renders = []
        request = object()
        tag = div(foo=invisible(render="bar"))
        renderable = RenderRenderable(renders, "bar", tag, result)
        self.assertStringEqual(
            self.flatten(renderable, request), '<div foo="quux"></div>')
        self.assertEqual(renders, [(renderable, request)])


    def test_renderAttributeNestedInSlot(self):
        """
        A L{Tag} with a renderer which is used as the value of a L{slot} which
        was returned by L{IRenderable.render} is replaced with the result of
        the named renderer on the L{IRenderable} which returned the L{slot}.
        """
        result = "quux"
        renders = []
        outer = div[slot("bar")]
        inner = div(render="foo")
        outer.fillSlots("bar", inner)
        renderable = RenderRenderable(renders, "foo", outer, result)
        self.assertStringEqual(
            self.flatten(renderable, None), "<div>quux</div>")


    def test_renderAttributeNestedInPrecompiledSlot(self):
        """
        A L{Tag} with a renderer which is used as the value of a
        L{_PrecompiledSlot} which was returned by L{IRenderable.render} is
        replaced with the result of the named renderer on the L{IRenderable}
        which returned the L{_PrecompiledSlot}.
        """
        result = "quux"
        renders = []
        request = object()
        outer = invisible[stan(div[slot("bar")]).load()]
        inner = div(render="foo")
        outer.fillSlots("bar", inner)
        renderable = RenderRenderable(renders, "foo", outer, result)
        self.assertStringEqual(
            self.flatten(renderable, request), "<div>quux</div>")
        self.assertEqual(renders, [(renderable, request)])


    def test_renderAttributedNestedInRenderResult(self):
        """
        A L{Tag} with a renderer which is returned by a render method is
        replaced with the return value of the named renderer on the
        L{IRenderable} which had the render method which returned the L{Tag}.
        """
        class TwoRenderers(object):
            implements(IRenderable)

            def renderer(self, name):
                return getattr(self, name)

            def foo(self, request, tag):
                return div(render="bar")

            def bar(self, request, tag):
                return "baz"

            def render(self, request):
                return div(render="foo")

        renderable = TwoRenderers()
        self.assertStringEqual(self.flatten(renderable), "baz")


    def test_slotsNestedInRenderResult(self):
        """
        A L{slot} in the return value of a render function is replaced by the
        value of that slot as found on the tag which had the render directive.
        """
        tag = div(render="foo")
        tag.fillSlots("bar", '"&<>')
        renderable = RenderRenderable([], "foo", tag, slot("bar"))
        self.assertStringEqual(self.flatten(renderable), '"&<>')


    def test_renderTextDataQuoted(self):
        """
        Strings returned by a render method on an L{IRenderable} provider which
        is a child of a L{Tag} are XML quoted.
        """
        tag = div[RenderRenderable([], "foo", div(render="foo"), '"&<>')]
        self.assertStringEqual(self.flatten(tag), '<div>"&amp;&lt;&gt;</div>')


    def test_renderMethodReturnsInputTag(self):
        """
        If a render method returns the tag it was passed, the tag is flattened
        as though it did not have a render directive.
        """
        class IdempotentRenderable(object):
            implements(IRenderable)

            def renderer(self, name):
                return getattr(self, name)

            def foo(self, request, tag):
                return tag

            def render(self, request):
                return div(render="foo", bar="baz")["hello, world"]

        renderable = IdempotentRenderable()
        self.assertStringEqual(
            self.flatten(renderable), '<div bar="baz">hello, world</div>')


    def test_url(self):
        """
        An L{URL} object is flattened to the appropriate representation of
        itself, whether it is the child of a tag or the value of a tag
        attribute.
        """
        link = URL.fromString("http://foo/fu?bar=baz&bar=baz#quux%2f")
        self.assertStringEqual(
            self.flatten(link),
            "http://foo/fu?bar=baz&bar=baz#quux%2F")
        self.assertStringEqual(
            self.flatten(div[link]),
            '<div>http://foo/fu?bar=baz&amp;bar=baz#quux%2F</div>')
        self.assertStringEqual(
            self.flatten(div(foo=link)),
            '<div foo="http://foo/fu?bar=baz&amp;bar=baz#quux%2F"></div>')
        self.assertStringEqual(
            self.flatten(div[div(foo=link)]),
            '<div><div foo="http://foo/fu?bar=baz&amp;bar=baz#quux%2F"></div>'
            '</div>')

        link = URL.fromString("http://foo/fu?%2f=%7f")
        self.assertStringEqual(
            self.flatten(link),
            "http://foo/fu?%2F=%7F")
        self.assertStringEqual(
            self.flatten(div[link]),
            '<div>http://foo/fu?%2F=%7F</div>')
        self.assertStringEqual(
            self.flatten(div(foo=link)),
            '<div foo="http://foo/fu?%2F=%7F"></div>')


    def test_unfilledSlot(self):
        """
        Flattening a slot which has no known value results in an
        L{FlattenerError} exception which has an L{UnfilledSlot} exception
        in its arguments.
        """
        exc = self.assertRaises(FlattenerError, self.flatten, slot("foo"))
        self.assertTrue(isinstance(exc.args[0], UnfilledSlot))


    def test_filledSlotTagChild(self):
        """
        Flattening a slot as a child of a L{Tag} which has been given a value
        for that slot results in the slot being replaced with the value in the
        output.
        """
        tag = div[slot("foo")]
        tag.fillSlots("foo", "bar")
        self.assertStringEqual(self.flatten(tag), "<div>bar</div>")


    def test_filledSlotTagChildEscaping(self):
        """
        Flattening a slot as a child of a L{Tag} which has been given a string
        value results in that string value being XML escaped in the output.
        """
        tag = div[slot("foo")]
        tag.fillSlots("foo", '"&<>')
        self.assertStringEqual(self.flatten(tag), '<div>"&amp;&lt;&gt;</div>')


    def test_filledSlotNestedTagChild(self):
        """
        Flattening a slot as a child of a L{Tag} which is itself a child of a
        L{Tag} which has been given a value for that slot results in the slot
        being replaced with the value in the output.
        """
        tag = div[div[slot("foo")]]
        tag.fillSlots("foo", "bar")
        self.assertStringEqual(self.flatten(tag), "<div><div>bar</div></div>")


    def test_filledSlotTagAttribute(self):
        """
        Flattening a slot which is the value of an attribute of a L{Tag}
        results in the value of the slot appearing as the attribute value in
        the output.
        """
        tag = div(foo=slot("bar"))
        tag.fillSlots("bar", "baz")
        self.assertStringEqual(self.flatten(tag), '<div foo="baz"></div>')


    def test_slotFilledWithProto(self):
        """
        Filling a slot with a L{Proto} results in the slot being replaced with
        the serialized form of the tag in the output.
        """
        tag = div[slot("foo")]
        tag.fillSlots("foo", br)
        self.assertStringEqual(self.flatten(tag), "<div><br /></div>")


    def test_unfilledPrecompiledSlot(self):
        """
        Flattening a L{_PrecompiledSlot} for which no value has been supplied
        results in an L{FlattenerError} exception.
        """
        tag = oldPrecompile(div[slot("foo")])
        self.assertRaises(FlattenerError, self.flatten, tag)


    def test_precompiledSlot(self):
        """
        A L{_PrecompiledSlot} is replaced with the value of that slot when
        flattened.
        """
        tag = invisible[oldPrecompile(div[slot("foo")])]
        tag.fillSlots("foo", '"&<>')
        self.assertStringEqual(self.flatten(tag), '<div>"&amp;&lt;&gt;</div>')


    def test_precompiledSlotTagAttribute(self):
        """
        A L{_PrecompiledSlot} which is the value of an attribute is replaced
        with the value of the slot with XML attribute quoting applied.
        """
        tag = invisible[oldPrecompile(div(foo=slot("foo")))]
        tag.fillSlots("foo", '"&<>')
        self.assertStringEqual(self.flatten(tag), '<div foo="&quot;&amp;&lt;&gt;"></div>')


    def test_precompiledSlotFilledWithSlot(self):
        """
        A L{_PrecompiledSlot} slot which is filled with another slot is
        replaced with the value the other slot is filled with.
        """
        tag = invisible[oldPrecompile(div[slot("foo")])]
        tag.fillSlots("foo", slot("bar"))
        tag.fillSlots("bar", '"&<>')
        self.assertStringEqual(self.flatten(tag), '<div>"&amp;&lt;&gt;</div>')


    def test_renderable(self):
        """
        Flattening an object which provides L{IRenderable} results in
        something based on the result of the object's C{render} method.
        """
        request = object()
        renderable = TrivialRenderable("bytes")
        self.assertStringEqual(
            self.flatten(renderable, request), "bytes")
        self.assertEqual(renderable.requests, [request])


    def test_renderableNestingRenderable(self):
        """
        Flattening an L{IRenderable} provider which returns another
        L{IRenderable} from its C{render} method results in the result of
        flattening the result of the inner L{IRenderable}'s C{render} method
        which is called with the request object.
        """
        request = object()
        inner = TrivialRenderable("bytes")
        outer = TrivialRenderable(inner)
        self.assertStringEqual(self.flatten(outer, request), "bytes")
        self.assertEqual(inner.requests, [request])


    def test_listNestingRenderable(self):
        """
        Flattening a C{list} which has an object providing L{IRenderable} as a
        child results in the result of the L{IRenderable}'s C{render} method
        which is called with the request object.
        """
        request = object()
        renderable = TrivialRenderable("bytes")
        self.assertStringEqual(self.flatten([renderable], request), "bytes")
        self.assertEqual(renderable.requests, [request])


    def test_tagNestingRenderable(self):
        """
        Flattening a L{Tag} which has an object providing L{IRenderable} as a
        child results in markup for the tag with child data from the
        L{IRenderable}'s C{render} which is called with the request object.
        """
        request = object()
        inner = TrivialRenderable("bytes")
        outer = div[inner]
        self.assertStringEqual(
            self.flatten(outer, request), "<div>bytes</div>")
        self.assertEqual(inner.requests, [request])


    def test_slotNestingRenderable(self):
        """
        Flattening a L{slot} which is filled with an object providing
        L{IRenderable} results in the result of the L{IRenderable}'s C{render}
        method which is called with the request object.
        """
        request = object()
        inner = TrivialRenderable("bytes")
        outer = slot("foo")
        tag = div[outer]
        tag.fillSlots("foo", inner)
        self.assertStringEqual(self.flatten(tag, request), "<div>bytes</div>")
        self.assertEqual(inner.requests, [request])


    def test_slotFromRenderable(self):
        """
        An L{IRenderable} provider which returns a C{Tag} inside a C{slot}
        from its C{render} method has that slot filled with the slot data
        available on the tag.
        """
        tag = div[slot("foo")]
        tag.fillSlots("foo", "bar")
        renderable = TrivialRenderable(tag)
        self.assertStringEqual(self.flatten(renderable), "<div>bar</div>")


    def _nestingTest(self, nestedObject, expected):
        limit = sys.getrecursionlimit()
        sys.setrecursionlimit(100)
        try:
            self.assertStringEqual(self.flatten(nestedObject), expected)
        finally:
            sys.setrecursionlimit(limit)


    def test_deeplyNestedList(self):
        """
        Flattening succeeds for an object with a level of list nesting
        significantly greater than the Python maximum recursion limit.
        """
        obj = ["foo"]
        for i in xrange(1000):
            obj = [obj]
        self._nestingTest(obj, "foo")


    def test_deeplyNestedSlot(self):
        """
        Flattening succeeds for an object with a level of slot nesting
        significantly greater than the Python maximum recursion limit.
        """
        tag = div()[slot("foo-0")]
        for i in xrange(1000):
            tag.fillSlots("foo-" + str(i), slot("foo-" + str(i + 1)))
        tag.fillSlots("foo-1000", "bar")
        self._nestingTest(tag, "<div>bar</div>")


    def test_deeplyNestedTag(self):
        """
        Flattening succeeds for a tag with a level of nesting significantly
        greater than the Python maximum recursion limit.
        """
        n = 1000
        tag = div["foo"]
        for i in xrange(n - 1):
            tag = div[tag]
        self._nestingTest(tag, "<div>" * n + "foo" + "</div>" * n)


    def test_deeplyNestedRenderables(self):
        """
        Flattening succeeds for an object with a level of L{IRenderable}
        nesting significantly greater than the Python maximum recursion limit.
        """
        obj = TrivialRenderable("foo")
        for i in xrange(1000):
            obj = TrivialRenderable(obj)
        self._nestingTest(obj, "foo")


    def test_legacyRenderer(self):
        """
        Flattening an L{IRenderer} succeeds with the same result as using the
        old flattener.
        """
        class Legacy(Fragment):
            docFactory = stan(invisible(render=directive('foo')))
            def render_foo(self, ctx, data):
                return '"&<>'
        fragment = Legacy()
        self.assertEqual(
            self.flatten(fragment), oldFlatten(fragment))
        self.assertEqual(
            self.flatten(div(foo=fragment)),
            oldFlatten(div(foo=fragment)))


    def test_legacySerializable(self):
        """
        Flattening an object for which a flattener was registered with
        L{registerFlattener} succeeds with the result of the registered
        flattener function.
        """
        request = FakeRequest()
        result = 'bytes&quot;'
        serializable = LegacySerializable(result)
        self.assertEqual(
            self.flatten(div(foo=serializable), request),
            '<div foo="' + result + '"></div>')
        [context] = serializable.flattenedWith
        self.assertTrue(isinstance(context, WovenContext))
        self.assertFalse(context.precompile)
        self.assertTrue(context.isAttrib)
        self.assertIdentical(context.locate(IRequest), request)
        self.assertIdentical(context.locate(IData), None)


    def test_legacySerializableReturnsSlot(self):
        """
        A slot returned by a flattener registered with L{registerFlattener} is
        filled with the value of a slot from "outside" the L{ISerializable}.
        """
        request = FakeRequest()
        result = slot('foo')
        serializable = LegacySerializable(result)
        tag = div(foo=serializable)
        tag.fillSlots("foo", "bar")
        self.assertEqual(self.flatten(tag, request), '<div foo="bar"></div>')


    def test_flattenExceptionStack(self):
        """
        If an exception is raised by a render method, L{FlattenerError} is
        raised with information about the stack between the flattener and the
        frame which raised the exception.
        """
        def broken():
            raise RuntimeError("foo")

        class BrokenRenderable(object):
            implements(IRenderable)

            def render(self, request):
                # insert another stack frame before the exception
                broken()


        request = object()
        renderable = BrokenRenderable()
        exc = self.assertRaises(
            FlattenerError, self.flatten, renderable, request)
        self.assertEqual(
            # There are probably some frames above this, but I don't care what
            # they are.
            exc._traceback[-2:],
            [(HERE, 927, 'render', 'broken()'),
             (HERE, 920, 'broken', 'raise RuntimeError("foo")')])



class FlattenerErrorTests(TestCase):
    """
    Tests for L{FlattenerError}.
    """
    def test_string(self):
        """
        If a L{FlattenerError} is created with a string root, up to around 40
        bytes from that string are included in the string representation of the
        exception.
        """
        self.assertEqual(
            str(FlattenerError(RuntimeError("reason"), ['abc123xyz'], [])),
            "Exception while flattening:\n"
            "  'abc123xyz'\n"
            "RuntimeError: reason\n")
        self.assertEqual(
            str(FlattenerError(
                    RuntimeError("reason"), ['0123456789' * 10], [])),
            "Exception while flattening:\n"
            "  '01234567890123456789<...>01234567890123456789'\n"
            "RuntimeError: reason\n")


    def test_unicode(self):
        """
        If a L{FlattenerError} is created with a unicode root, up to around 40
        characters from that string are included in the string representation
        of the exception.
        """
        self.assertEqual(
            str(FlattenerError(
                    RuntimeError("reason"), [u'abc\N{SNOWMAN}xyz'], [])),
            "Exception while flattening:\n"
            "  u'abc\\u2603xyz'\n" # Codepoint for SNOWMAN
            "RuntimeError: reason\n")
        self.assertEqual(
            str(FlattenerError(
                    RuntimeError("reason"), [u'01234567\N{SNOWMAN}9' * 10],
                    [])),
            "Exception while flattening:\n"
            "  u'01234567\\u2603901234567\\u26039<...>01234567\\u2603901234567"
            "\\u26039'\n"
            "RuntimeError: reason\n")


    def test_renderable(self):
        """
        If a L{FlattenerError} is created with an L{IRenderable} provider root,
        the repr of that object is included in the string representation of the
        exception.
        """
        class Renderable(object):
            implements(IRenderable)

            def __repr__(self):
                return "renderable repr"

        self.assertEqual(
            str(FlattenerError(
                    RuntimeError("reason"), [Renderable()], [])),
            "Exception while flattening:\n"
            "  renderable repr\n"
            "RuntimeError: reason\n")


    def test_tag(self):
        """
        If a L{FlattenerError} is created with a L{Tag} instance with source
        location information, the source location is included in the string
        representation of the exception.
        """
        tag = Tag(
            'div', filename='/foo/filename.xhtml', lineNumber=17, columnNumber=12)

        self.assertEqual(
            str(FlattenerError(RuntimeError("reason"), [tag], [])),
            "Exception while flattening:\n"
            "  File \"/foo/filename.xhtml\", line 17, column 12, in \"div\"\n"
            "RuntimeError: reason\n")


    def test_tagWithoutLocation(self):
        """
        If a L{FlattenerError} is created with a L{Tag} instance without source
        location information, only the tagName is included in the string
        representation of the exception.
        """
        self.assertEqual(
            str(FlattenerError(RuntimeError("reason"), [Tag('span')], [])),
            "Exception while flattening:\n"
            "  Tag <span>\n"
            "RuntimeError: reason\n")


    def test_traceback(self):
        """
        If a L{FlattenerError} is created with traceback frames, they are
        included in the string representation of the exception.
        """
        # Try to be realistic in creating the data passed in for the traceback
        # frames.
        def f():
            g()
        def g():
            raise RuntimeError("reason")

        try:
            f()
        except RuntimeError, exc:
            # Get the traceback, minus the info for *this* frame
            tbinfo = traceback.extract_tb(sys.exc_info()[2])[1:]
        else:
            self.fail("f() must raise RuntimeError")

        self.assertEqual(
            str(FlattenerError(exc, [], tbinfo)),
            "Exception while flattening:\n"
            "  File \"%s\", line %d, in f\n"
            "    g()\n"
            "  File \"%s\", line %d, in g\n"
            "    raise RuntimeError(\"reason\")\n"
            "RuntimeError: reason\n" % (
                HERE, f.func_code.co_firstlineno + 1,
                HERE, g.func_code.co_firstlineno + 1))



class LegacySerializable(object):
    """
    An object for which a legacy flattener is registered and which can only be
    flattened using that flattener.
    """
    def __init__(self, value):
        self.value = value
        self.flattenedWith = []



def flattenLegacySerializable(legacy, context):
    """
    Old-style flattener for L{LegacySerializable}.
    """
    legacy.flattenedWith.append(context)
    return [legacy.value]



registerFlattener(flattenLegacySerializable, LegacySerializable)



class DeferflattenTests(TestCase, FlattenMixin):
    """
    Tests for L{nevow._flat.deferflatten}.
    """
    def deferflatten(self, root, request=None):
        """
        Helper to get a string from L{deferflatten}.
        """
        result = []
        d = deferflatten(request, root, False, False, result.append)
        def cbFlattened(ignored):
            return "".join(result)
        d.addCallback(cbFlattened)
        return d


    def test_unflattenable(self):
        """
        L{deferflatten} returns a L{Deferred} which fails with
        L{FlattenerError} if it is passed an object which cannot be flattened.
        """
        return self.assertFailure(
            self.deferflatten(object()), FlattenerError)


    def test_unfilledSlotDeferredResult(self):
        """
        Flattening a L{Deferred} which results in an unfilled L{slot} results
        in a L{FlattenerError} failure.
        """
        return self.assertFailure(
            self.deferflatten(succeed(slot("foo"))),
            FlattenerError)


    def test_renderable(self):
        """
        Flattening an object which provides L{IRenderable} results in the
        result of the object's C{render} method which is called with the
        request.
        """
        request = object()
        renderable = TrivialRenderable("bytes")
        def cbFlattened(result):
            self.assertStringEqual(result, "bytes")
            self.assertEqual(renderable.requests, [request])
        flattened = self.deferflatten(renderable, request)
        flattened.addCallback(cbFlattened)
        return flattened


    def test_renderableException(self):
        """
        Flattening an object which provides L{IRenderable} with a C{render}
        method which synchronously raises an exception results in a L{Deferred}
        which fails with L{FlattenerError}.
        """
        class TestException(Exception):
            pass
        class BrokenRenderable(object):
            implements(IRenderable)

            def render(self, request):
                raise TestException()
        flattened = self.deferflatten(BrokenRenderable())
        return self.assertFailure(flattened, FlattenerError)


    def test_deferredRenderAttribute(self):
        """
        Flattening an object which provides L{IRenderable} with a C{render}
        method which returns a L{Deferred} which is called back with a L{Tag}
        with a render attribute results in the return value of the named
        renderer from the L{IRenderer} which returned the L{Deferred}.
        """
        flattened = self.deferflatten(
            RenderRenderable([], "foo", succeed(div(render="foo")), "bar"))
        flattened.addCallback(self.assertStringEqual, "bar")
        return flattened


    def test_synchronousDeferredSlot(self):
        """
        Flattening a L{slot} which is filled with a L{Deferred} which has a
        result already results in the result of the L{Deferred}.
        """
        tag = div[slot("foo")]
        tag.fillSlots("foo", succeed("bar"))
        flattened = self.deferflatten(tag)
        flattened.addCallback(self.assertStringEqual, "<div>bar</div>")
        return flattened


    def test_asynchronousDeferredSlot(self):
        """
        Flattening a L{slot} which is filled with a L{Deferred} which does not
        have a result already results in the result of the L{Deferred} when it
        becomes available.
        """
        tag = div[slot("foo")]
        deferred = Deferred()
        tag.fillSlots("foo", deferred)
        flattened = self.deferflatten(tag)
        flattened.addCallback(self.assertStringEqual, "<div>bar</div>")
        deferred.callback("bar")
        return flattened


    def test_deferredNestingRenderable(self):
        """
        Flattening a L{Deferred} which has an object providing L{IRenderable}
        as the result results in the result of the L{IRenderable}'s C{render}
        method.
        """
        request = object()
        renderable = TrivialRenderable("bytes")
        deferred = succeed(renderable)
        def cbFlattened(result):
            self.assertStringEqual(result, "bytes")
            self.assertEqual(renderable.requests, [request])
        flattened = self.deferflatten(deferred, request)
        flattened.addCallback(cbFlattened)
        return deferred


    def test_reusedDeferred(self):
        """
        Flattening a C{list} which contains the same L{Deferred} twice results
        in the result of the L{Deferred} twice.
        """
        deferred = succeed("bytes")
        root = [deferred, deferred]
        flattened = self.deferflatten(root)
        flattened.addCallback(self.assertStringEqual, "bytesbytes")
        return flattened


    def test_manySynchronousDeferreds(self):
        """
        Flattening a structure with many more L{Deferreds} than there are
        frames allowed by the Python recursion limit succeeds if all the
        L{Deferred}s have results already.
        """
        results = [str(i) for i in xrange(1000)]
        deferreds = map(succeed, results)
        limit = sys.getrecursionlimit()
        sys.setrecursionlimit(100)
        try:
            flattened = self.deferflatten(deferreds)
        except:
            sys.setrecursionlimit(limit)
            raise
        else:
            def cb(passthrough):
                sys.setrecursionlimit(limit)
                return passthrough
            flattened.addBoth(cb)
            flattened.addCallback(self.assertStringEqual, "".join(results))
            return flattened


    def test_deferredQuoting(self):
        """
        Flattening a L{Deferred} results in the result of the L{Deferred}
        without any quoting.
        """
        flattened = self.deferflatten(succeed('"&<>'))
        flattened.addCallback(self.assertStringEqual, '"&<>')
        return flattened


    def test_deferredAttributeValueQuoting(self):
        """
        Flattening a L{Tag} which has an attribute value which is a L{Deferred}
        results in the result of the L{Deferred} being XML attribute quoted and
        included as the value for that attribute of the tag.
        """
        tag = div(foo=succeed('"&<>'))
        flattened = self.deferflatten(tag)
        flattened.addCallback(
            self.assertStringEqual, '<div foo="&quot;&amp;&lt;&gt;"></div>')
        return flattened


    def test_deferredTagChildQuoting(self):
        """
        Flattening a L{Tag} which has a child which is a L{Deferred} results in
        the result of the L{Deferred} being XML quoted and included as a child
        value for the tag.
        """
        tag = div[succeed('"&<>')]
        flattened = self.deferflatten(tag)
        flattened.addCallback(
            self.assertStringEqual, '<div>"&amp;&lt;&gt;</div>')
        return flattened


    def test_slotDeferredResultQuoting(self):
        """
        Flattening a L{Tag} with a L{Deferred} as a child which results in a
        L{slot} results in the value of the slot being XML quoted and included
        as a child value for the tag.
        """
        deferred = succeed(slot("foo"))
        tag = div[deferred]
        tag.fillSlots("foo", '"&<>')
        flattened = self.deferflatten(tag)
        flattened.addCallback(
            self.assertStringEqual, '<div>"&amp;&lt;&gt;</div>')
        return flattened


    def test_legacyAsynchronousRenderer(self):
        """
        Flattening an L{IRenderer} which returns a L{Deferred} from one of its
        render methods succeeds with therthe same result as using the old
        flattener.
        """
        deferredResult = Deferred()
        rendererCalled = []
        class Legacy(Fragment):
            docFactory = stan(invisible(render=directive('foo')))
            def render_foo(self, ctx, data):
                rendererCalled.append(None)
                return deferredResult
        fragment = Legacy()
        finished = self.deferflatten(fragment)
        finished.addCallback(
            self.assertStringEqual, "foobarbaz")
        # Sanity check - we do not want the Deferred to have been called back
        # before it is returned from the render method.
        self.assertTrue(rendererCalled)
        deferredResult.callback("foobarbaz")
        return finished


    def test_attributeString(self):
        """
        An instance of L{str} is flattened with attribute quoting rules if
        C{True} is passed for C{inAttribute}.
        """
        result = []
        finished = deferflatten(None, '"&<>', True, False, result.append)
        finished.addCallback(lambda ignored: "".join(result))
        finished.addCallback(self.assertStringEqual, "&quot;&amp;&lt;&gt;")
        return finished


    def test_textNodeString(self):
        """
        An instance of L{str} is flattened with XML quoting rules if C{True} is
        passed for C{inXML}.
        """
        result = []
        finished = deferflatten(None, '"&<>', False, True, result.append)
        finished.addCallback(lambda ignored: "".join(result))
        finished.addCallback(self.assertStringEqual, '"&amp;&lt;&gt;')
        return finished
