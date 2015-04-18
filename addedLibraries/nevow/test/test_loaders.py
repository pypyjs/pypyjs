# Copyright (c) 2004-2009 Divmod.
# See LICENSE for details.

import os

from twisted.trial import unittest, util

from nevow import context
from nevow import flat
from nevow.flat.flatstan import _PrecompiledSlot
from nevow import loaders
from nevow import tags as t

class TestDocFactories(unittest.TestCase):

    def _preprocessorTest(self, docFactory):
        def preprocessor(uncompiled):
            self.assertEquals(len(uncompiled), 1)
            uncompiled = uncompiled[0]
            self.assertEquals(uncompiled.tagName, 'div')
            self.assertEquals(len(uncompiled.children), 2)
            self.assertEquals(uncompiled.children[0].tagName, 'span')
            self.assertEquals(uncompiled.children[0].children, ['Hello'])
            self.assertEquals(uncompiled.children[1].tagName, 'span')
            self.assertEquals(uncompiled.children[1].children, ['world'])
            return t.div['goodbye.']
        doc = docFactory.load(preprocessors=[preprocessor])
        self.assertEquals(doc, ['<div>goodbye.</div>'])


    def test_stanPreprocessors(self):
        """
        Test that the stan loader properly passes uncompiled documents to
        preprocessors it is given.
        """
        factory = loaders.stan(
            t.div[t.span['Hello'], t.span['world']])
        return self._preprocessorTest(factory)


    def test_stan(self):
        doc = t.ul(id='nav')[t.li['one'], t.li['two'], t.li['three']]
        df = loaders.stan(doc)
        self.assertEquals(df.load()[0], '<ul id="nav"><li>one</li><li>two</li><li>three</li></ul>')


    def test_stanPrecompiled(self):
        """
        Test that a stan loader works with precompiled documents.

        (This behavior will probably be deprecated soon, but we need to test
        that it works right until we remove it.)
        """
        doc = flat.precompile(t.ul(id='nav')[t.li['one'], t.li['two'], t.slot('three')])
        df = loaders.stan(doc)
        loaded = df.load()
        self.assertEqual(loaded[0], '<ul id="nav"><li>one</li><li>two</li>')
        self.failUnless(isinstance(loaded[1], _PrecompiledSlot))
        self.assertEqual(loaded[1].name, 'three')
        self.assertEqual(loaded[2], '</ul>')


    def test_htmlstr(self):
        doc = '<ul id="nav"><li>a</li><li>b</li><li>c</li></ul>'
        df = loaders.htmlstr(doc)
        self.assertEquals(df.load()[0], doc)
    test_htmlstr.suppress = [
        util.suppress(message=
                      r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                      "Please start using xmlfile and/or xmlstr.")]


    def test_htmlfile(self):
        doc = '<ul id="nav"><li>a</li><li>b</li><li>c</li></ul>'
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(doc)
        f.close()
        df = loaders.htmlfile(temp)
        self.assertEquals(df.load()[0], doc)
    test_htmlfile.suppress = [
        util.suppress(message=
                      r"\[v0.8\] htmlfile is deprecated because it's buggy. "
                      "Please start using xmlfile and/or xmlstr.")]


    def test_htmlfile_slots(self):
        doc = '<nevow:slot name="foo">Hi there</nevow:slot>'
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(doc)
        f.close()
        df = loaders.htmlfile(temp)
        self.assertEquals(df.load()[0].children, ['Hi there'])
    test_htmlfile_slots.suppress = [
        util.suppress(message=
                      r"\[v0.8\] htmlfile is deprecated because it's buggy. "
                      "Please start using xmlfile and/or xmlstr.")]


    def test_xmlstr(self):
        doc = '<ul id="nav"><li>a</li><li>b</li><li>c</li></ul>'
        df = loaders.xmlstr(doc)
        self.assertEquals(df.load()[0], doc)


    def test_xmlstrPreprocessors(self):
        """
        Test that the xmlstr loader properly passes uncompiled documents to
        preprocessors it is given.
        """
        factory = loaders.xmlstr(
            '<div><span>Hello</span><span>world</span></div>')
        return self._preprocessorTest(factory)


    def test_xmlfile(self):
        doc = '<ul id="nav"><li>a</li><li>b</li><li>c</li></ul>'
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(doc)
        f.close()
        df = loaders.xmlfile(temp)
        self.assertEquals(df.load()[0], doc)


    def test_xmlfilePreprocessors(self):
        """
        Test that the xmlstr loader properly passes uncompiled documents to
        preprocessors it is given.
        """
        xmlFile = self.mktemp()
        f = file(xmlFile, 'w')
        f.write('<div><span>Hello</span><span>world</span></div>')
        f.close()
        factory = loaders.xmlfile(xmlFile)
        return self._preprocessorTest(factory)


    def test_patterned(self):
        """Test fetching a specific part (a pattern) of the document.
        """
        doc = t.div[t.p[t.span(pattern='inner')['something']]]
        df = loaders.stan(doc, pattern='inner')
        self.assertEquals(df.load()[0].tagName, 'span')
        self.assertEquals(df.load()[0].children[0], 'something')


    def test_ignoreDocType(self):
        doc = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<html><body><p>Hello.</p></body></html>'''
        df = loaders.xmlstr(doc, ignoreDocType=True)
        self.assertEquals(flat.flatten(df), '<html><body><p>Hello.</p></body></html>')

    def test_ignoreComment(self):
        doc = '<!-- skip this --><p>Hello.</p>'
        df = loaders.xmlstr(doc, ignoreComment=True)
        self.assertEquals(flat.flatten(df), '<p>Hello.</p>')


class TestDocFactoriesCache(unittest.TestCase):

    doc = '''
    <div>
    <p nevow:pattern="1">one</p>
    <p nevow:pattern="2">two</p>
    </div>
    '''

    nsdoc = '''
    <div xmlns:nevow="http://nevow.com/ns/nevow/0.1">
    <p nevow:pattern="1">one</p>
    <p nevow:pattern="2">two</p>
    </div>
    '''

    stan = t.div[t.p(pattern='1')['one'],t.p(pattern='2')['two']]

    def test_stan(self):

        loader = loaders.stan(self.stan)
        self.assertEquals( id(loader.load()), id(loader.load()) )

        loader = loaders.stan(self.stan, pattern='1')
        self.assertEquals( id(loader.load()), id(loader.load()) )

        l1 = loaders.stan(self.stan, pattern='1')
        l2 = loaders.stan(self.stan, pattern='1')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )

        l1 = loaders.stan(self.stan, pattern='1')
        l2 = loaders.stan(self.stan, pattern='2')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )


    def test_htmlstr(self):
        loader = loaders.htmlstr(self.doc)
        self.assertEquals( id(loader.load()), id(loader.load()) )

        loader = loaders.htmlstr(self.doc, pattern='1')
        self.assertEquals( id(loader.load()), id(loader.load()) )

        l1 = loaders.htmlstr(self.doc, pattern='1')
        l2 = loaders.htmlstr(self.doc, pattern='1')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )

        l1 = loaders.htmlstr(self.doc, pattern='1')
        l2 = loaders.htmlstr(self.doc, pattern='2')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )
    test_htmlstr.suppress = [
        util.suppress(message=
                      r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                      "Please start using xmlfile and/or xmlstr.")]


    def test_htmlfile(self):
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(self.doc)
        f.close()

        loader = loaders.htmlfile(temp)
        self.assertEquals( id(loader.load()), id(loader.load()) )

        l1 = loaders.htmlfile(temp, pattern='1')
        l2 = loaders.htmlfile(temp, pattern='1')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )

        l1 = loaders.htmlfile(temp, pattern='1')
        l2 = loaders.htmlfile(temp, pattern='2')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )
    test_htmlfile.suppress = [
        util.suppress(message=
                      r"\[v0.8\] htmlfile is deprecated because it's buggy. "
                      "Please start using xmlfile and/or xmlstr.")]


    def test_htmlfileReload(self):
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(self.doc)
        f.close()

        loader = loaders.htmlfile(temp)
        r = loader.load()
        self.assertEquals(id(r), id(loader.load()))
        os.utime(temp, (os.path.getatime(temp), os.path.getmtime(temp)+5))
        self.assertNotEqual(id(r), id(loader.load()))
    test_htmlfileReload.suppress = [
        util.suppress(message=
                      r"\[v0.8\] htmlfile is deprecated because it's buggy. "
                      "Please start using xmlfile and/or xmlstr.")]



    def test_xmlstr(self):

        loader = loaders.xmlstr(self.nsdoc)
        self.assertEquals( id(loader.load()), id(loader.load()) )

        loader = loaders.xmlstr(self.nsdoc, pattern='1')
        self.assertEquals( id(loader.load()), id(loader.load()) )

        l1 = loaders.xmlstr(self.nsdoc, pattern='1')
        l2 = loaders.xmlstr(self.nsdoc, pattern='1')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )

        l1 = loaders.xmlstr(self.nsdoc, pattern='1')
        l2 = loaders.xmlstr(self.nsdoc, pattern='2')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )


    def test_xmlSlotDefault(self):
        """
        An I{nevow:slot} tag in an XML template may have a I{default}
        attribute specifying a value for the slot if it is not otherwise
        given one.
        """
        slotsdoc = '''
        <div xmlns:nevow="http://nevow.com/ns/nevow/0.1">
        <nevow:slot name="1" />
        <nevow:slot name="2" default="3" />
        </div>
        '''
        loader = loaders.xmlstr(slotsdoc)
        loaded = loader.load()
        self.assertEquals(loaded[1].default, None)
        self.assertEquals(loaded[3].default, "3")


    def test_xmlfile(self):

        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(self.nsdoc)
        f.close()

        loader = loaders.xmlfile(temp)
        self.assertEquals( id(loader.load()), id(loader.load()) )

        loader = loaders.xmlfile(temp, pattern='1')
        self.assertEquals( id(loader.load()), id(loader.load()) )

        l1 = loaders.xmlfile(temp, pattern='1')
        l2 = loaders.xmlfile(temp, pattern='1')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )

        l1 = loaders.xmlfile(temp, pattern='1')
        l2 = loaders.xmlfile(temp, pattern='2')
        self.assertNotEqual( id(l1.load()), id(l2.load()) )

    def test_xmlfileReload(self):

        temp = self.mktemp()
        f = file(temp, 'w')
        f.write(self.nsdoc)
        f.close()

        loader = loaders.xmlfile(temp)
        r = loader.load()
        self.assertEquals(id(r), id(loader.load()))
        os.utime(temp, (os.path.getatime(temp), os.path.getmtime(temp)+5))
        self.assertNotEqual(id(r), id(loader.load()))

    def test_reloadAfterPrecompile(self):
        """
        """
        # Get a filename
        temp = self.mktemp()

        # Write some content
        f = file(temp, 'w')
        f.write('<p>foo</p>')
        f.close()

        # Precompile the doc
        ctx = context.WovenContext()
        doc = loaders.htmlfile(temp)
        pc = flat.precompile(flat.flatten(doc), ctx)

        before = ''.join(flat.serialize(pc, ctx))


        # Write the file with different content and make sure the
        # timestamp changes
        f = file(temp, 'w')
        f.write('<p>bar</p>')
        f.close()
        os.utime(temp, (os.path.getatime(temp), os.path.getmtime(temp)+5))

        after = ''.join(flat.serialize(pc, ctx))

        self.assertIn('foo', before)
        self.assertIn('bar', after)
        self.failIfEqual(before, after)
    test_reloadAfterPrecompile.todo = \
        'Fix so that disk templates are reloaded even after a precompile. ' \
        'Probably just a matter of making the DocSerializer really lazy'


class TestContext(unittest.TestCase):
    """Check that each of the standard loaders supports load with and without a
    context.
    """

    def test_stan(self):
        doc = t.p['hello']
        self._withAndWithout(loaders.stan(doc))

    def test_xmlstr(self):
        doc = '<p>hello</p>'
        self._withAndWithout(loaders.xmlstr(doc))

    def test_xmlfile(self):
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write('<p>hello</p>')
        f.close()
        self._withAndWithout(loaders.xmlfile(temp))

    def test_htmlstr(self):
        doc = '<p>hello</p>'
        self._withAndWithout(loaders.htmlstr(doc))
    test_htmlstr.suppress = [
        util.suppress(message=
                      r"\[v0.8\] htmlstr is deprecated because it's buggy. "
                      "Please start using xmlfile and/or xmlstr.")]

    def test_htmlfile(self):
        temp = self.mktemp()
        f = file(temp, 'w')
        f.write('<p>hello</p>')
        f.close()
        self._withAndWithout(loaders.htmlfile(temp))
    test_htmlfile.suppress = [
        util.suppress(message=
                      r"\[v0.8\] htmlfile is deprecated because it's buggy. "
                      "Please start using xmlfile and/or xmlstr.")]

    def _withAndWithout(self, loader):
        ctx = context.WovenContext()
        self.assertEquals(loader.load(), ['<p>hello</p>'])
        self.assertEquals(loader.load(ctx), ['<p>hello</p>'])


class TestParsing(unittest.TestCase):

    def test_missingSpace(self):
        doc = '<p xmlns:nevow="http://nevow.com/ns/nevow/0.1"><nevow:slot name="foo"/> <nevow:slot name="foo"/></p>'
        ## This used to say htmlstr, and this test failed because microdom ignores whitespace;
        ## This test passes fine using xmlstr. I am not going to fix this because microdom is too
        ## hard to fix. If you need this, switch to xmlstr.
        result = loaders.xmlstr(doc).load()
        # There should be a space between the two slots
        self.assertEquals(result[2], ' ')
