# Copyright (c) 2004,2008 Divmod.
# See LICENSE for details.

from twisted.internet import defer

from zope.interface import implements, Interface

from nevow import stan
from nevow import context
from nevow import tags
from nevow import entities
from nevow import inevow
from nevow import flat
from nevow import rend
from nevow.testutil import FakeRequest, TestCase

from nevow.flat import twist

proto = stan.Proto('hello')


class Base(TestCase):
    contextFactory = context.WovenContext
    def renderer(self, context, data):
        return lambda context, data: ""

    def setupContext(self, precompile=False, setupRequest=lambda r:r):
        fr = setupRequest(FakeRequest(uri='/', currentSegments=['']))
        ctx = context.RequestContext(tag=fr)
        ctx.remember(fr, inevow.IRequest)
        ctx.remember(None, inevow.IData)
        ctx = context.WovenContext(parent=ctx, precompile=precompile)
        return ctx

    def render(self, tag, precompile=False, data=None, setupRequest=lambda r: r, setupContext=lambda c:c, wantDeferred=False):
        ctx = self.setupContext(precompile, setupRequest)
        ctx = setupContext(ctx)
        if precompile:
            return flat.precompile(tag, ctx)
        else:
            if wantDeferred:
                L = []
                D = twist.deferflatten(tag, ctx, L.append)
                D.addCallback(lambda igresult: ''.join(L))
                return D
            else:
                return flat.flatten(tag, ctx)


class TestSimpleSerialization(Base):
    def test_serializeProto(self):
        self.assertEquals(self.render(proto), '<hello />')

    def test_serializeTag(self):
        tag = proto(someAttribute="someValue")
        self.assertEquals(self.render(tag), '<hello someAttribute="someValue"></hello>')

    def test_serializeChildren(self):
        tag = proto(someAttribute="someValue")[
            proto
        ]
        self.assertEquals(self.render(tag), '<hello someAttribute="someValue"><hello /></hello>')

    def test_serializeWithData(self):
        tag = proto(data=5)
        self.assertEquals(self.render(tag), '<hello></hello>')

    def test_adaptRenderer(self):
        ## This is an implementation of the "adapt" renderer
        def _(context, data):
            return context.tag[
                data
            ]
        tag = proto(data=5, render=_)
        self.assertEquals(self.render(tag), '<hello>5</hello>')

    def test_serializeDataWithRenderer(self):
        tag = proto(data=5, render=str)
        self.assertEquals(self.render(tag), '5')

    def test_noContextRenderer(self):
        def _(data):
            return data
        tag = proto(data=5, render=_)
        self.assertEquals(self.render(tag), '5')
        tag = proto(data=5, render=lambda data: data)
        self.assertEquals(self.render(tag), '5')

    def test_aBunchOfChildren(self):
        tag = proto[
            "A Child",
            5,
            "A friend in need is a friend indeed"
        ]
        self.assertEquals(self.render(tag), '<hello>A Child5A friend in need is a friend indeed</hello>')

    def test_basicPythonTypes(self):
        tag = proto(data=5)[
            "A string; ",
            u"A unicode string; ",
            5, " (An integer) ",
            1.0, " (A float) ",
            1L, " (A long) ",
            True, " (A bool) ",
            ["A ", "List; "],
            stan.xml("<xml /> Some xml; "),
            lambda data: "A function"
        ]
        if self.hasBools:
            self.assertEquals(self.render(tag), "<hello>A string; A unicode string; 5 (An integer) 1.0 (A float) 1 (A long) True (A bool) A List; <xml /> Some xml; A function</hello>")
        else:
            self.assertEquals(self.render(tag), "<hello>A string; A unicode string; 5 (An integer) 1.0 (A float) 1 (A long) 1 (A bool) A List; <xml /> Some xml; A function</hello>")

    def test_escaping(self):
        tag = proto(foo="<>&\"'")["<>&\"'"]
        self.assertEquals(self.render(tag), '<hello foo="&lt;&gt;&amp;&quot;\'">&lt;&gt;&amp;"\'</hello>')


class TestComplexSerialization(Base):
    def test_precompileWithRenderer(self):
        tag = tags.html[
            tags.body[
                tags.div[
                    tags.p["Here's a string"],
                    tags.p(data=5, render=str)
                ]
            ]
        ]
        prelude, context, postlude = self.render(tag, precompile=True)
        self.assertEquals(prelude, "<html><body><div><p>Here's a string</p>")
        self.assertEquals(context.tag.tagName, "p")
        self.assertEquals(context.tag.data, 5)
        self.assertEquals(context.tag.render, str)
        self.assertEquals(postlude, '</div></body></html>')

    def test_precompileSlotData(self):
        """Test that tags with slotData are not precompiled out of the
        stan tree.
        """
        tag = tags.p[tags.slot('foo')]
        tag.fillSlots('foo', 'bar')
        precompiled = self.render(tag, precompile=True)
        self.assertEquals(self.render(precompiled), '<p>bar</p>')


    def test_precompiledSlotLocation(self):
        """
        The result of precompiling a slot preserves the location information
        associated with the slot.
        """
        filename = 'foo/bar'
        line = 123
        column = 432
        [slot] = self.render(
            tags.slot('foo', None, filename, line, column), precompile=True)
        self.assertEqual(slot.filename, filename)
        self.assertEqual(slot.lineNumber, line)
        self.assertEqual(slot.columnNumber, column)


    def makeComplex(self):
        return tags.html[
            tags.body[
                tags.table(data=5)[
                    tags.tr[
                        tags.td[
                            tags.span(render=str)
                        ],
                    ]
                ]
            ]
        ]

    def test_precompileTwice(self):
        def render_same(context, data):
            return context.tag

        doc = tags.html[
            tags.body(render=render_same, data={'foo':5})[
                tags.p["Hello"],
                tags.p(data=tags.directive('foo'))[
                    str
                ]
            ]
        ]
        result1 = self.render(doc, precompile=True)
        result2 = self.render(doc, precompile=True)
        rendered = self.render(result2)
        self.assertEquals(rendered, "<html><body><p>Hello</p><p>5</p></body></html>")

    def test_precompilePrecompiled(self):
        def render_same(context, data):
            return context.tag

        doc = tags.html[
            tags.body(render=render_same, data={'foo':5})[
                tags.p["Hello"],
                tags.p(data=tags.directive('foo'))[
                    str
                ]
            ]
        ]
        result1 = self.render(doc, precompile=True)
        result2 = self.render(result1, precompile=True)
        rendered = self.render(result2)
        self.assertEquals(rendered, "<html><body><p>Hello</p><p>5</p></body></html>")

    def test_precompileDoesntChangeOriginal(self):
        doc = tags.html(data="foo")[tags.p['foo'], tags.p['foo']]

        result = self.render(doc, precompile=True)
        rendered = self.render(result)

        self.assertEquals(len(doc.children), 2)
        self.assertEquals(rendered, "<html><p>foo</p><p>foo</p></html>")

    def test_precompileNestedDynamics(self):
        tag = self.makeComplex()
        prelude, dynamic, postlude = self.render(tag, precompile=True)
        self.assertEquals(prelude, '<html><body>')

        self.assertEquals(dynamic.tag.tagName, 'table')
        self.failUnless(dynamic.tag.children)
        self.assertEquals(dynamic.tag.data, 5)

        childPrelude, childDynamic, childPostlude = dynamic.tag.children

        self.assertEquals(childPrelude, '<tr><td>')
        self.assertEquals(childDynamic.tag.tagName, 'span')
        self.assertEquals(childDynamic.tag.render, str)
        self.assertEquals(childPostlude, '</td></tr>')

        self.assertEquals(postlude, '</body></html>')

    def test_precompileThenRender(self):
        tag = self.makeComplex()
        prerendered = self.render(tag, precompile=True)
        self.assertEquals(self.render(prerendered), '<html><body><table><tr><td>5</td></tr></table></body></html>')

    def test_precompileThenMultipleRenders(self):
        tag = self.makeComplex()
        prerendered = self.render(tag, precompile=True)
        self.assertEquals(self.render(prerendered), '<html><body><table><tr><td>5</td></tr></table></body></html>')
        self.assertEquals(self.render(prerendered), '<html><body><table><tr><td>5</td></tr></table></body></html>')

    def test_patterns(self):
        tag = tags.html[
            tags.body[
                tags.ol(data=["one", "two", "three"], render=rend.sequence)[
                    tags.li(pattern="item")[
                        str
                    ]
                ]
            ]
        ]
        self.assertEquals(self.render(tag), "<html><body><ol><li>one</li><li>two</li><li>three</li></ol></body></html>")

    def test_precompilePatternWithNoChildren(self):
        tag = tags.img(pattern='item')
        pc = flat.precompile(tag)
        self.assertEquals(pc[0].tag.children, [])

    def test_slots(self):
        tag = tags.html[
            tags.body[
                tags.table(data={'one': 1, 'two': 2}, render=rend.mapping)[
                    tags.tr[tags.td["Header one."], tags.td["Header two."]],
                    tags.tr[
                        tags.td["One: ", tags.slot("one")],
                        tags.td["Two: ", tags.slot("two")]
                    ]
                ]
            ]
        ]
        self.assertEquals(self.render(tag), "<html><body><table><tr><td>Header one.</td><td>Header two.</td></tr><tr><td>One: 1</td><td>Two: 2</td></tr></table></body></html>")


    def test_slotAttributeEscapingWhenPrecompiled(self):
        """
        Test that slots which represent attribute values properly quote those
        values for that context.
        """
        def render_searchResults(ctx, remoteCursor):
            ctx.fillSlots('old-query', '"meow"')
            return ctx.tag

        tag = tags.invisible(render=render_searchResults)[
            tags.input(value=tags.slot('old-query')),
        ]

        # this test passes if the precompile test is skipped.
        precompiled = self.render(tag, precompile=True)

        self.assertEquals(self.render(precompiled), '<input value="&quot;meow&quot;" />')


    def test_nestedpatterns(self):
        def data_table(context, data):  return [[1,2,3],[4,5,6]]
        def data_header(context, data):  return ['col1', 'col2', 'col3']
        tag = tags.html[
            tags.body[
                tags.table(data=data_table, render=rend.sequence)[
                    tags.tr(pattern='header', data=data_header, render=rend.sequence)[
                        tags.td(pattern='item')[str]
                    ],
                    tags.tr(pattern='item', render=rend.sequence)[
                        tags.td(pattern='item')[str]
                    ]
                ]
            ]
        ]
        self.assertEquals(self.render(tag), "<html><body><table><tr><td>col1</td><td>col2</td><td>col3</td></tr><tr><td>1</td><td>2</td><td>3</td></tr><tr><td>4</td><td>5</td><td>6</td></tr></table></body></html>")

    def test_cloning(self):
        def data_foo(context, data):  return [{'foo':'one'}, {'foo':'two'}]

      # tests nested lists without precompilation (precompilation flattens the lists)
        def render_test(context, data):
            return tags.ul(render=rend.sequence)[
                    tags.li(pattern='item')[
                        'foo', (((tags.invisible(data=tags.directive('foo'), render=str),),),)
                    ]
                ]

        # tests tags inside attributes (weird but useful)
        document = tags.html(data=data_foo)[
            tags.body[
                tags.ul(render=rend.sequence)[
                  tags.li(pattern='item')[
                    tags.a(href=('test/', tags.invisible(data=tags.directive('foo'), render=str)))['link']
                  ]
                ],
                render_test
            ]
        ]
        document=self.render(document, precompile=True)
        self.assertEquals(self.render(document), '<html><body><ul><li><a href="test/one">link</a></li><li><a href="test/two">link</a></li></ul><ul><li>fooone</li><li>footwo</li></ul></body></html>')

    def test_singletons(self):
        for x in ('img', 'br', 'hr', 'base', 'meta', 'link', 'param', 'area',
            'input', 'col', 'basefont', 'isindex', 'frame'):
            self.assertEquals(self.render(tags.Proto(x)()), '<%s />' % x)

    def test_nosingleton(self):
        for x in ('div', 'span', 'script', 'iframe'):
            self.assertEquals(self.render(tags.Proto(x)()), '<%(tag)s></%(tag)s>' % {'tag': x})

    def test_nested_data(self):
        def checkContext(ctx, data):
            self.assertEquals(data, "inner")
            self.assertEquals(ctx.locate(inevow.IData, depth=2), "outer")
            return 'Hi'
        tag = tags.html(data="outer")[tags.span(render=lambda ctx,data: ctx.tag, data="inner")[checkContext]]
        self.assertEquals(self.render(tag), "<html><span>Hi</span></html>")

    def test_nested_remember(self):
        class IFoo(Interface):
            pass
        class Foo(str):
            implements(IFoo)

        def checkContext(ctx, data):
            self.assertEquals(ctx.locate(IFoo), Foo("inner"))
            self.assertEquals(ctx.locate(IFoo, depth=2), Foo("outer"))
            return 'Hi'
        tag = tags.html(remember=Foo("outer"))[tags.span(render=lambda ctx,data: ctx.tag, remember=Foo("inner"))[checkContext]]
        self.assertEquals(self.render(tag), "<html><span>Hi</span></html>")

    def test_deferredRememberInRenderer(self):
        class IFoo(Interface):
            pass
        def rememberIt(ctx, data):
            ctx.remember("bar", IFoo)
            return defer.succeed(ctx.tag)
        def locateIt(ctx, data):
            return IFoo(ctx)
        tag = tags.invisible(render=rememberIt)[tags.invisible(render=locateIt)]
        self.render(tag, wantDeferred=True).addCallback(
            lambda result: self.assertEquals(result, "bar"))

    def test_deferredFromNestedFunc(self):
        def outer(ctx, data):
            def inner(ctx, data):
                return defer.succeed(tags.p['Hello'])
            return inner
        self.render(tags.invisible(render=outer), wantDeferred=True).addCallback(
            lambda result: self.assertEquals(result, '<p>Hello</p>'))

    def test_dataContextCreation(self):
        data = {'foo':'oof', 'bar':'rab'}
        doc = tags.p(data=data)[tags.slot('foo'), tags.slot('bar')]
        doc.fillSlots('foo', tags.invisible(data=tags.directive('foo'), render=str))
        doc.fillSlots('bar', lambda ctx,data: data['bar'])
        self.assertEquals(flat.flatten(doc), '<p>oofrab</p>')

    def test_leaky(self):
        def foo(ctx, data):
            ctx.tag.fillSlots('bar', tags.invisible(data="two"))
            return ctx.tag

        result = self.render(
            tags.div(render=foo, data="one")[
                tags.slot("bar"),
                tags.invisible(render=str)])

        self.assertEquals(result, '<div>one</div>')


class TestMultipleRenderWithDirective(Base):
    def test_it(self):
        class Cool(object):
            def __init__(self):
                self.counter = 0

            def count(self, context, data):
                self.counter += 1
                return self.counter

        it = Cool()

        tag = tags.html(data={'counter': it.count})[
            tags.invisible(data=tags.directive('counter'))[
                str
            ]
        ]
        precompiled = self.render(tag, precompile=True)
        val = self.render(precompiled)
        self.assertSubstring('1', val)
        val2 = self.render(precompiled)
        self.assertSubstring('2', val2)


class TestEntity(Base):
    def test_it(self):
        val = self.render(entities.nbsp)
        self.assertEquals(val, '&#160;')

    def test_nested(self):
        val = self.render(tags.html(src=entities.quot)[entities.amp])
        self.assertEquals(val, '<html src="&quot;">&amp;</html>')

    def test_xml(self):
        val = self.render([entities.lt, entities.amp, entities.gt])
        self.assertEquals(val, '&lt;&amp;&gt;')


class TestNoneAttribute(Base):

    def test_simple(self):
        val = self.render(tags.html(foo=None)["Bar"])
        self.assertEquals(val, "<html>Bar</html>")

    def test_slot(self):
        val = self.render(tags.html().fillSlots('bar', None)(foo=tags.slot('bar'))["Bar"])
        self.assertEquals(val, "<html>Bar</html>")
    test_slot.skip = "Attribute name flattening must happen later for this to work"

    def test_deepSlot(self):
        val = self.render(tags.html().fillSlots('bar', lambda c,d: None)(foo=tags.slot('bar'))["Bar"])
        self.assertEquals(val, "<html>Bar</html>")
    test_deepSlot.skip = "Attribute name flattening must happen later for this to work"

    def test_deferredSlot(self):
        self.render(tags.html().fillSlots('bar', defer.succeed(None))(foo=tags.slot('bar'))["Bar"],
                    wantDeferred=True).addCallback(
            lambda val: self.assertEquals(val, "<html>Bar</html>"))
    test_deferredSlot.skip = "Attribute name flattening must happen later for this to work"


class TestKey(Base):
    def test_nested(self):
        val = []
        def appendKey(ctx, data):
            val.append(ctx.key)
            return ctx.tag
        self.render(
            tags.div(key="one", render=appendKey)[
                tags.div(key="two", render=appendKey)[
                    tags.div(render=appendKey)[
                        tags.div(key="four", render=appendKey)]]])
        self.assertEquals(val, ["one", "one.two", "one.two", "one.two.four"])



class TestDeferFlatten(Base):

    def flatten(self, obj):
        """
        Flatten the given object using L{twist.deferflatten} and a simple context.

        Return the Deferred returned by L{twist.deferflatten}.
        it.
        """
        # Simple context with None IData
        ctx = context.WovenContext()
        ctx.remember(None, inevow.IData)
        return twist.deferflatten(obj, ctx, lambda bytes: None)


    def test_errorPropogation(self):
        # A generator that raises an error
        def gen(ctx, data):
            yield 1
            raise Exception('This is an exception!')
            yield 2

        # The actual test
        notquiteglobals = {}
        def finished(spam):
            print 'FINISHED'
        def error(failure):
            notquiteglobals['exception'] = failure.value
        def checker(result):
            if not isinstance(notquiteglobals['exception'], Exception):
                self.fail('deferflatten did not errback with the correct failure')
            return result
        d = self.flatten(gen)
        d.addCallback(finished)
        d.addErrback(error)
        d.addBoth(checker)
        return d


    def test_failurePropagation(self):
        """
        Passing a L{Deferred}, the current result of which is a L{Failure}, to
        L{twist.deferflatten} causes it to return a L{Deferred} which will be
        errbacked with that failure.  The original Deferred will also errback
        with that failure even after having been passed to
        L{twist.deferflatten}.
        """
        error = RuntimeError("dummy error")
        deferred = defer.fail(error)

        d = self.flatten(deferred)
        self.assertFailure(d, RuntimeError)
        d.addCallback(self.assertIdentical, error)

        self.assertFailure(deferred, RuntimeError)
        deferred.addCallback(self.assertIdentical, error)

        return defer.gatherResults([d, deferred])


    def test_resultPreserved(self):
        """
        The result of a L{Deferred} passed to L{twist.deferflatten} is the
        same before and after the call.
        """
        result = 1357
        deferred = defer.succeed(result)
        d = self.flatten(deferred)
        deferred.addCallback(self.assertIdentical, result)
        return defer.gatherResults([d, deferred])
