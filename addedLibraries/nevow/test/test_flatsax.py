# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from nevow.testutil import TestCase

from nevow.flat.flatsax import parse, parseString
from nevow.flat import flatten
from nevow.stan import Tag, slot

def norm(s):
    return ' '.join(s.split())

class Basic(TestCase):
    """
    Tests for Nevow documents which are loaded via L{xml.sax} from XHTML
    templates.
    """
    def _tagChildren(self, tag):
        """
        Return a list of the children of C{tag} which are themselves L{Tag}s.
        """
        return [x for x in tag.children if isinstance(x, Tag)]


    def test_tagLocation(self):
        """
        L{Tag} instances returned by L{parse} have a C{filename} attribute
        which gives the name of the file from which they were parsed, a
        C{lineNumber} attribute giving the line number on which the tag was
        seen in that file, and a C{columnNumber} attribute giving the column
        number at which the tag was seen in that file.
        """
        fName = self.mktemp()
        fObj = file(fName, 'w')
        fObj.write(
            '<html>\n'
            '  <head>\n'
            '    <title>\n'
            '      Hello, world.\n'
            '    </title>\n'
            '  </head>\n'
            '  <body>\n'
            '    Hi.\n'
            '  </body>\n'
            '</html>\n')
        fObj.close()
        [html] = parse(file(fName))
        [head, body] = self._tagChildren(html)
        [title] = self._tagChildren(head)
        self.assertEqual(html.filename, fName)
        self.assertEqual(html.lineNumber, 1)
        self.assertEqual(html.columnNumber, 0)
        self.assertEqual(head.filename, fName)
        self.assertEqual(head.lineNumber, 2)
        self.assertEqual(head.columnNumber, 2)
        self.assertEqual(title.filename, fName)
        self.assertEqual(title.lineNumber, 3)
        self.assertEqual(title.columnNumber, 4)
        self.assertEqual(body.filename, fName)
        self.assertEqual(body.lineNumber, 7)
        self.assertEqual(body.columnNumber, 2)


    def test_attrLocation(self):
        """
        I{attr} L{Tag} instances returned by L{parse} have a C{filename}
        attribute which gives the name of the file from which they were parsed,
        a C{lineNumber} attribute giving the line number on which the tag was
        seen in that file, and a C{columnNumber} attribute giving the column
        number at which the tag was seen in that file.
        """
        fName = self.mktemp()
        fObj = file(fName, 'w')
        fObj.write(
            '<html xmlns:nevow="http://nevow.com/ns/nevow/0.1">\n'
            '    <nevow:attr name="foo" />\n'
            '</html>\n')
        fObj.close()
        [html] = parse(file(fName))
        attr = html.attributes['foo']
        self.assertEqual(attr.filename, fName)
        self.assertEqual(attr.lineNumber, 2)
        self.assertEqual(attr.columnNumber, 4)


    def test_slotLocation(self):
        """
        L{slot} instances returned by L{parse} have the same C{filename},
        C{lineNumber}, and C{columnNumber} attributes as L{Tag} instances do.
        """
        fName = self.mktemp()
        fObj = file(fName, 'w')
        fObj.write(
            '<html xmlns:nevow="http://nevow.com/ns/nevow/0.1">\n'
            '    <nevow:slot name="foo" />\n'
            '</html>')
        fObj.close()
        [html] = parse(file(fName))
        [foo] = [x for x in html.children if isinstance(x, slot)]
        self.assertEqual(foo.filename, fName)
        self.assertEqual(foo.lineNumber, 2)
        self.assertEqual(foo.columnNumber, 4)


    def test_parseString(self):
        xml = '''<html></html>'''
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_attrs(self):
        xml = '''<p class="foo"></p>'''
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_xmlns(self):
        xml = '''<html xmlns="http://www.w3.org/1999/xhtml"></html>'''
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_processingInstruction(self):
        xml = '''<html></html>'''
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_doctype(self):
        xml = (
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
            '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
            '<html></html>')
        self.failUnlessEqual(norm(xml), norm(flatten(parseString(xml))))

    def test_entities(self):
        xml = """<p>&amp;</p>"""
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_cdata(self):
        xml = '<script type="text/javascript"><![CDATA[&lt;abc]]></script>'
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_comment(self):
        xml = '<!-- comment &amp;&pound; --><html></html>'
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_commentWhereSpacingMatters(self):
        """
        Explicitly test that spacing in comments is maintained.
        """
        xml = """<head>
<!--[if IE]>
<style>
div.logo {
    margin-left: 10px;
}
</style>
<![endif]-->
</head>"""
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_unicodeComment(self):
        xml = '<!-- \xc2\xa3 --><html></html>'
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_xmlAttr(self):
        xml = '<html xml:lang="en"></html>'
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_badNamespace(self):
        xml = '<html foo:bar="wee"><abc:p>xyz</abc:p></html>'
        self.failUnlessEqual(xml, flatten(parseString(xml)))
    test_badNamespace.skip = (
        'the standard 2.3 sax parser likes all namespaces to be defined '
        'so this test fails. it does pass with python-xml')

    def test_switchns(self):
        xml = (
            '<html xmlns="http://www.w3.org/1999/xhtml">'
            '<p>in default namespace</p>'
            '<foo:div xmlns:foo="http://www.w3.org/1999/xhtml">'
            '<foo:p>in foo namespace</foo:p></foo:div></html>')
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_otherns(self):
        xml = (
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:xf="http://www.w3.org/2002/xforms"><p>'
            'in default namespace</p><xf:input><xf:label>'
            'in another namespace</xf:label></xf:input></html>')
        self.failUnlessEqual(xml, flatten(parseString(xml)))

    def test_invisiblens(self):
        """
        Test that invisible tags do not get output with a namespace.
        """
        xml = (
            '<p xmlns:n="http://nevow.com/ns/nevow/0.1">'
            '<n:invisible>123</n:invisible></p>')
        self.failUnlessEqual('<p>123</p>', flatten(parseString(xml)))
