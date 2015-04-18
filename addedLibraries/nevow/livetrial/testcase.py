import inspect, types, warnings

from twisted.trial import runner, unittest

from nevow import athena, loaders, tags, page


class TestCase(athena.LiveFragment, unittest.TestCase):
    """
    Server-side component of a B{N}evow B{I}nteractive B{T}est.

    TestCases are L{athena.LiveFragment}s which correspond to one or more test
    methods which will be invoked on the client.  They are responsible for
    specifying a JavaScript widget class which defines the client portion of
    this set of tests, specifying a document which will be rendered for that
    JavaScript widget, and defining any methods which the client may need to
    invoke during the test.
    """
    docFactory = loaders.stan(tags.div(render=tags.directive('testWidget')))

    def render_liveTest(self, ctx, data):
        warnings.warn(
            "liveTest renderer is deprecated, use the default "
            "docFactory and override getWidgetTag, getTestContainer, "
            "and/or getWidgetDocument instead",
            category=DeprecationWarning)
        return self.render_liveFragment(ctx, data)


    def render_testWidget(self, ctx, data):
        container = self.getTestContainer()
        widget = self.getWidgetTag()(render=tags.directive('liveFragment'))
        container.fillSlots('widget', widget[self.getWidgetDocument()])
        return ctx.tag[container]


    def getWidgetTag(self):
        """
        Return a Nevow tag object which will be used as the top-level widget
        node for this test case.

        Subclasses may want to override this.
        """
        return tags.div


    def getTestContainer(self):
        """
        Return a Nevow DOM object (generally a tag) with a C{widget} slot in
        it.  This will be used as the top-level DOM for this test case, and the
        actual widget will be used to fill the C{widget} slot.

        Subclasses may want to override this.
        """
        return tags.invisible[tags.slot('widget')]


    def getWidgetDocument(self):
        """
        Retrieve a Nevow DOM object (generally a tag) which will be placed
        inside this TestCase's widget node.

        Subclasses may want to override this.
        """
        return u''


    def head(self):
        """
        Return objects that should be rendered inside the <head> tag of the
        document for the test suite that this test case belongs to.  Typically
        instances of tags from L{nevow.tags}.

        Subclasses may want to override this
        """


    def __repr__(self):
        return object.__repr__(self)



class TestError(athena.LiveElement):
    """
    An element rendering an error that occurred during test collection.
    """
    docFactory = loaders.stan(tags.div(render=tags.directive('error')))

    def __init__(self, holder):
        holder.run(self)

    def addError(self, holder, error):
        self._error = error

    def head(self):
        """
        We have nothing to render in <head>.
        """

    def error(self, req, tag):
        return tag(_class='test-suite')[
            tags.pre[self._error.getTraceback()]]
    page.renderer(error)


class TestSuite(object):
    """
    A collection of test cases.
    """

    holderType = runner.ErrorHolder

    def __init__(self, name="Live Tests"):
        self.tests = []
        self.name = name


    def addTest(self, test):
        self.tests.append(test)


    def gatherInstances(self):
        l = []
        for test in self.tests:
            if isinstance(test, TestSuite):
                l.extend(test.gatherInstances())
            elif isinstance(test, self.holderType):
                l.append(TestError(test))
            else:
                test.name = '%s.%s' % (self.name, test.__name__)
                l.append(test())
        return l



class TestLoader(runner.TestLoader):
    """
    An object which discovers test cases and collects them into a suite.
    """
    modulePrefix = 'livetest_'

    def __init__(self):
        runner.TestLoader.__init__(self)
        self.suiteFactory = TestSuite


    def loadByName(self, name, recurse=False):
        thing = self.findByName(name)
        return self.loadAnything(thing, recurse)


    def loadMethod(self, method):
        raise NotImplementedError, 'livetests must be classes'


    def loadClass(self, klass):
        if not (isinstance(klass, type) or isinstance(klass, types.ClassType)):
            raise TypeError("%r is not a class" % (klass,))
        if not self.isTestCase(klass):
            raise ValueError("%r is not a test case" % (klass,))
        return klass


    def loadModule(self, module):
        if not isinstance(module, types.ModuleType):
            raise TypeError("%r is not a module" % (module,))
        suite = self.suiteFactory(module.__name__)
        for testClass in self._findTestClasses(module):
            suite.addTest(self.loadClass(testClass))
        return suite


    def isTestCase(self, obj):
        return isinstance(obj, (type, types.ClassType)) and issubclass(obj, TestCase) and obj is not TestCase


    def _findTestClasses(self, module):
        classes = []
        for name, val in inspect.getmembers(module):
            if self.isTestCase(val):
                classes.append(val)
        return self.sort(classes)
