from nevow import tags, flat, context
from nevow.testutil import TestCase

class TestTags(TestCase):
    def test_inlineJS(self):
        # there is a tendency for people to change inlineJS to something like this:
        #
        #   return script(type="text/javascript")[xml('\n//<![CDATA[\n'), s, xml(\n//]]>\n']
        #
        # however, this is broken because it replaces & < and > with entities,
        # which is wrong. If the CDATA thingers are omitted, then it is correct
        # by the XML spec, but not in reality, because browsers do not resolve
        # entities in script tags for historic reasons, and the content of
        # script tags is defined to be CDATA by XHTML, even without CDATA
        # directives.
        #
        # Anyway, the end result is that & becomes &amp; resulting in a syntax
        # error.

        ctx = context.WovenContext()
        tag = tags.inlineJS('correct && elegant;')
        flatted = flat.flatten(tag, ctx)
        self.failIf('&amp;' in flatted)


    def test_directiveComparison(self):
        """
        Test that only directives with the same name compare equal.
        """
        foo = tags.directive('foo')
        foo2 = tags.directive('foo')
        bar = tags.directive('bar')
        self.assertEquals(foo, foo)
        self.assertEquals(foo, foo2)
        self.failIfEqual(foo, bar)


    def test_directiveHashing(self):
        """
        Test that only directives with the same name hash to the same thing.
        """
        foo = tags.directive('foo')
        foo2 = tags.directive('foo')
        bar = tags.directive('bar')
        self.assertEquals(hash(foo), hash(foo2))

        # XXX What if 'foo' and 'bar' accidentally hash equal in some version
        # of Python?
        self.failIfEqual(hash(foo), hash(bar))
