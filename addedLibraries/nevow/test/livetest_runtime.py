from nevow import loaders, tags
from nevow.livetrial import testcase


class SetNodeContent(testcase.TestCase):
    jsClass = u'Divmod.Runtime.Tests.SetNodeContent'



class AppendNodeContent(testcase.TestCase):
    jsClass = u'Divmod.Runtime.Tests.AppendNodeContent'



class AppendNodeContentScripts(testcase.TestCase):
    jsClass = u'Divmod.Runtime.Tests.AppendNodeContentScripts'



class ElementSize(testcase.TestCase):
    jsClass = u'Divmod.Runtime.Tests.ElementSize'


    def getWidgetDocument(self):
        """
        Return part of a document which contains some explicitly sized
        elements.  The client portion of this test will retrieve them by their
        class value and assert things about their size.
        """
        return tags.div[
            tags.div(class_='foo', style='height: 126px; width: 1px'),
            tags.div(class_='bar', style='padding: 1px 2px 3px 4px; height: 12px; width: 70px')]


class ElementsByTagNameShallow(testcase.TestCase):
    jsClass = u'Divmod.Runtime.Tests.ElementsByTagNameShallow'

    def getWidgetDocument(self):
        """
        Return part of a document which consists of an element with some
        immediate child and some grandchild.  The client portion of this test
        will make sure only the immediate children are returned by
        C{getElementsByTagNameShallow}.
        """
        return tags.div(class_="foo")[tags.p["foo"], tags.div[tags.p["bar"]]]


class PageSize(testcase.TestCase):
    jsClass = u'Divmod.Runtime.Tests.PageSize'



class TraversalOrdering(testcase.TestCase):
    jsClass = u'Divmod.Runtime.Tests.TraversalOrdering'

    def getWidgetDocument(self):
        """
        Return part of a document which contains nodes nested several layers
        deep.  The client side of this test will use their class names to
        determine that ordering of results from the DOM traversal function is
        correct.
        """
        return tags.div(_class='container')[
            tags.div(_class='left_child')[
                tags.div(_class='left_grandchild')],
            tags.div(_class='right_child')[
                tags.div(_class='right_grandchild')]]



class FindInRootNode(testcase.TestCase):
    jsClass = u'Divmod.Runtime.Tests.FindInRootNode'



class Standalone(testcase.TestCase):
    jsClass = u'Divmod.Runtime.Tests.Standalone'



class ElementPosition(testcase.TestCase):
    """
    Tests for the element position-getting methods
    """
    jsClass = u'Divmod.Runtime.Tests.ElementPosition'



class LoadScript(testcase.TestCase):
    """
    Tests for C{Divmod.Runtime.Platform.loadScript}.
    """
    jsClass = u'Divmod.Runtime.Tests.LoadScript'
