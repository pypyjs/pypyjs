# Copyright (c) 2004 Divmod.
# See LICENSE for details.


from nevow import tags, flat, testutil, context, loaders, stan

from nevow.inevow import IQ


simple = tags.html[tags.div(pattern="foo")]
tooMany = tags.html[tags.div(pattern="foo"), tags.div(pattern="foo")]
notEnough = tags.html[tags.div[tags.span["Hello"]]]


class OnePatternTestCase(testutil.TestCase):
    """
    Test various C{IQ.onePattern} implementations.
    """
    _patternDiv = tags.div(pattern="foo")

    _simpleStan = tags.html[_patternDiv]

    _simpleSlot = tags.slot('slotname')[_patternDiv]

    _tooManyPatternsSiblingStan = tags.html[
        tags.div(pattern="foo"),
        tags.div(pattern="foo")]

    _manyPatternsLinealStan = tags.html(pattern="foo")[
        tags.div(pattern="foo"),
        "extra content"]


    def _testQuery(self, container, expected):
        pattern = IQ(container).onePattern('foo')

        # The pattern node has had its pattern special removed - put it back,
        # so we can perform a comparison
        self.assertEqual(pattern.pattern, None)
        pattern.pattern = 'foo'

        self.assertEqual(str(pattern), str(expected))


    def test_tagQuery(self):
        return self._testQuery(
            self._simpleStan, self._patternDiv)


    def test_contextQuery(self):
        return self._testQuery(
            context.WovenContext(tag=self._simpleStan),
            self._patternDiv)


    def test_listQuery(self):
        return self._testQuery(
            flat.precompile(self._simpleStan),
            self._patternDiv)


    def test_loaderQuery(self):
        return self._testQuery(
            loaders.stan(self._simpleStan),
            self._patternDiv)


    def test_slotQuery(self):
        return self._testQuery(
            self._simpleSlot,
            self._patternDiv)


    def test_precompiledSlotQuery(self):
        return self._testQuery(
            flat.precompile(self._simpleSlot),
            self._patternDiv)


    def _testTooManyPatterns(self, obj):
        """
        Test that the L{IQ} adapter for C{obj} provides a L{onePattern} method
        which raises L{stan.TooManyNodes} if passed a pattern name for which
        there are multiple pattern nodes.
        """
        self.assertRaises(stan.TooManyNodes, IQ(obj).onePattern, 'foo')


    def test_stanTooManySiblingPatterns(self):
        """
        Test that a Tag with children with the same pattern name causes
        onePattern to raise L{TooManyNodes}.
        """
        return self._testTooManyPatterns(self._tooManyPatternsSiblingStan)


    def test_contextTooManySiblingPatterns(self):
        """
        Like L{test_stanTooManySiblingPatterns} but for a WovenContext.
        """
        return self._testTooManyPatterns(
            context.WovenContext(tag=self._tooManyPatternsSiblingStan))


    def test_listTooManySiblingPatterns(self):
        """
        Like L{test_stanTooManySiblingPatterns} but for a list.
        """
        return self._testTooManyPatterns([self._tooManyPatternsSiblingStan])


    def test_precompiledTooManySiblingPatterns(self):
        """
        Like L{test_stanTooManySiblingPatterns} but for a precompiled document.
        """
        P = flat.precompile(self._tooManyPatternsSiblingStan)
        return self._testTooManyPatterns(P)


    def test_loaderTooManySiblingPatterns(self):
        """
        Like L{test_stanTooManySiblingPatterns} but for a loader.
        """
        return self._testTooManyPatterns(loaders.stan(self._tooManyPatternsSiblingStan))


    def test_stanMultipleLinealPatterns(self):
        """
        Test that calling onePattern a Tag with a pattern and a child with the
        same pattern
        """
        return self._testQuery(
            self._manyPatternsLinealStan,
            self._manyPatternsLinealStan)


    def test_contextMultipleLinealPatterns(self):
        return self._testQuery(
            context.WovenContext(tag=self._manyPatternsLinealStan),
            self._manyPatternsLinealStan)


    def test_listMultipleLinealPatterns(self):
        return self._testQuery(
            [self._manyPatternsLinealStan],
            self._manyPatternsLinealStan)


    def test_precompiledMultipleLinealPatterns(self):
        P = flat.precompile(self._manyPatternsLinealStan)
        return self._testQuery(
            P,
            P[0].tag)


    def test_loaderMultipleLinealPatterns(self):
        return self._testQuery(
            loaders.stan(self._manyPatternsLinealStan),
            loaders.stan(self._manyPatternsLinealStan).load()[0].tag)


    def test_tagNotEnough(self):
        self.assertRaises(stan.NodeNotFound, IQ(notEnough).onePattern, 'foo')

    def test_contextNotEnough(self):
        self.assertRaises(
            stan.NodeNotFound, 
            IQ(context.WovenContext(tag=notEnough)).onePattern, 'foo')

    def test_contextTagQuery(self):
        T = simple.clone(deep=False)
        T.pattern = "outer"
        C = context.WovenContext(tag=T)
        new = IQ(C).onePattern('outer')
        self.assertEquals(new.tagName, 'html')

    def test_listNotEnough(self):
        P = flat.precompile(notEnough)
        self.assertRaises(stan.NodeNotFound, IQ(P).onePattern, 'foo')

    def test_loaderNotEnough(self):
        L = loaders.stan(notEnough)
        self.assertRaises(stan.NodeNotFound, IQ(L).onePattern, 'foo')


multiple = tags.html[tags.div(pattern="foo", bar="one"), tags.span(pattern="foo", bar="two")]


class TestAll(testutil.TestCase):
    def verify(self, them):
        them = list(them)
        self.assertEquals(len(them), 2)
        self.assertEquals(them[0].tagName, 'div')
        self.assertEquals(them[1].tagName, 'span')
        self.assertEquals(them[0].attributes['bar'], 'one')
        self.assertEquals(them[1].attributes['bar'], 'two')

    def testTagPatterns(self):
        self.verify(
            IQ(multiple).allPatterns('foo'))

    def testContextPatterns(self):
        self.verify(
            IQ(context.WovenContext(tag=multiple)).allPatterns('foo'))

    def testListPatterns(self):
        self.verify(
            IQ(flat.precompile(multiple)).allPatterns('foo'))

    def testLoaderPatterns(self):
        self.verify(
            IQ(loaders.stan(multiple)).allPatterns('foo'))


class TestGenerator(testutil.TestCase):
    def verify(self, it):
        one = it(color="red")
        two = it(color="blue")
        three = it(color="green")
        four = it(color="orange")
        self.assertEquals(one.attributes['color'], 'red')
        self.assertEquals(one.attributes['bar'], 'one')
        self.assertEquals(two.attributes['color'], 'blue')
        self.assertEquals(two.attributes['bar'], 'two')
        self.assertEquals(three.attributes['color'], 'green')
        self.assertEquals(three.attributes['bar'], 'one')
        self.assertEquals(four.attributes['color'], 'orange')
        self.assertEquals(four.attributes['bar'], 'two')

    def testTagGenerators(self):
        self.verify(
            IQ(multiple).patternGenerator('foo'))

    def testTagMissing(self):
        self.assertRaises(stan.NodeNotFound, IQ(notEnough).patternGenerator, 'foo')

    def testContextGenerators(self):
        self.verify(
            IQ(context.WovenContext(tag=multiple)).patternGenerator('foo'))

    def testContextMissing(self):
        self.assertRaises(stan.NodeNotFound, IQ(context.WovenContext(tag=notEnough)).patternGenerator, 'foo')

    def testListGenerators(self):
        self.verify(
            IQ(flat.precompile(multiple)).patternGenerator('foo'))

    def testListMissing(self):
        self.assertRaises(stan.NodeNotFound, IQ(flat.precompile(notEnough)).patternGenerator, 'foo')

    def testLoaderGenerators(self):
        self.verify(
            IQ(loaders.stan(multiple)).patternGenerator('foo'))

    def testTagMissing(self):
        self.assertRaises(stan.NodeNotFound, IQ(loaders.stan(notEnough)).patternGenerator, 'foo')

    def testClonableDefault(self):
        orig = tags.p["Hello"]
        gen = IQ(flat.precompile(notEnough)).patternGenerator('foo', orig)
        new = gen.next()
        self.assertEquals(new.tagName, 'p')
        self.assertNotIdentical(orig, new)

    def testNonClonableDefault(self):
        gen = IQ(flat.precompile(notEnough)).patternGenerator('foo', 'bar')
        new = gen.next()
        self.assertEquals(new, 'bar')

    def testXmlMissing(self):
        self.assertRaises(stan.NodeNotFound, IQ(stan.xml('<html>hello</html>')).patternGenerator, 'foo')


    def test_listOfTagPatternGenerator(self):
        """
        Querying a list which contains a tag for patterns gives back the tag if
        the tag has a matching pattern special.
        """
        patterns = IQ([tags.div(pattern="foo", bar="baz")]).patternGenerator("foo")
        for i in xrange(3):
            self.assertEqual(patterns.next().attributes['bar'], "baz")
