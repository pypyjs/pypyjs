
"""

Test module for L{nevow.utils}

"""

try:
    set
except NameError:
    from sets import Set as set

from itertools import count
from os import utime
from os.path import getmtime

from twisted.trial.unittest import TestCase

from nevow.util import UnexposedMethodError, Expose, CachedFile

class ExposeTestCase(TestCase):
    def test_singleExpose(self):
        """
        Test exposing a single method with a single call to an Expose instance.
        """
        expose = Expose()

        class Foo(object):
            def bar(self):
                return 'baz'
            expose(bar)

        self.assertEquals(list(expose.exposedMethodNames(Foo())), ['bar'])
        self.assertEquals(expose.get(Foo(), 'bar')(), 'baz')


    def test_multipleExposeCalls(self):
        """
        Test exposing multiple methods, each with a call to an Expose instance.
        """
        expose = Expose()

        class Foo(object):
            def bar(self):
                return 'baz'
            expose(bar)


            def quux(self):
                return 'fooble'
            expose(quux)


        self.assertEquals(list(expose.exposedMethodNames(Foo())), ['bar', 'quux'])
        self.assertEquals(expose.get(Foo(), 'bar')(), 'baz')
        self.assertEquals(expose.get(Foo(), 'quux')(), 'fooble')


    def test_multipleExposeArguments(self):
        """
        Test exposing multiple methods with a single call to an Expose
        instance.
        """
        expose = Expose()

        class Foo(object):
            def bar(self):
                return 'baz'

            def quux(self):
                return 'fooble'

            expose(bar, quux)

        self.assertEquals(list(expose.exposedMethodNames(Foo())), ['bar', 'quux'])
        self.assertEquals(expose.get(Foo(), 'bar')(), 'baz')
        self.assertEquals(expose.get(Foo(), 'quux')(), 'fooble')


    def test_inheritanceExpose(self):
        """
        Test that overridden methods are not exposed.
        """
        expose = Expose()

        class Foo(object):
            def bar(self):
                return 'baz'
            expose(bar)

        class Quux(Foo):
            def bar(self):
                return 'BAZ'

        self.assertEquals(list(expose.exposedMethodNames(Quux())), [])
        self.assertRaises(UnexposedMethodError, expose.get, Quux(), 'bar')


    def test_inheritanceReexpose(self):
        """
        Test that overridden methods can also be re-exposed.
        """
        expose = Expose()

        class Foo(object):
            def bar(self):
                return 'baz'
            expose(bar)

        class Quux(object):
            def bar(self):
                return 'smokey'
            expose(bar)

        self.assertEquals(list(expose.exposedMethodNames(Quux())), ['bar'])
        self.assertEquals(expose.get(Quux(), 'bar')(), 'smokey')


    def test_inheritanceExposeMore(self):
        """
        Test that expose calls in a subclass adds to the parent's exposed
        methods.
        """
        expose = Expose()

        class Foo(object):
            def bar(self):
                return 'baz'
            expose(bar)

        class Quux(Foo):
            def smokey(self):
                return 'stover'
            def pogo(self):
                return 'kelly'
            def albert(self):
                return 'alligator'
            expose(smokey, pogo)

        self.assertEquals(set(expose.exposedMethodNames(Quux())), set(['pogo', 'smokey', 'bar']))
        self.assertEquals(expose.get(Quux(), 'bar')(), 'baz')
        self.assertEquals(expose.get(Quux(), 'smokey')(), 'stover')
        self.assertEquals(expose.get(Quux(), 'pogo')(), 'kelly')
        self.assertRaises(UnexposedMethodError, expose.get, Quux(), 'albert')
        self.assertEquals(Quux().albert(), 'alligator')


    def test_multipleInheritanceExpose(self):
        """
        Test that anything exposed on the parents of a class which multiply
        inherits from several other class are all exposed on the subclass.
        """
        expose = Expose()

        class A(object):
            def foo(self):
                return 'bar'
            expose(foo)

        class B(object):
            def baz(self):
                return 'quux'
            expose(baz)

        class C(A, B):
            def quux(self):
                pass
            expose(quux)

        self.assertEquals(set(expose.exposedMethodNames(C())), set(['quux', 'foo', 'baz']))
        self.assertEquals(expose.get(C(), 'foo')(), 'bar')
        self.assertEquals(expose.get(C(), 'baz')(), 'quux')


    def test_multipleInheritanceExposeWithoutSubclassCall(self):
        """
        Test that anything exposed on the parents of a class which multiply
        inherits from several other class are all exposed on the subclass.
        """
        expose = Expose()

        class A(object):
            def foo(self):
                return 'bar'
            expose(foo)

        class B(object):
            def baz(self):
                return 'quux'
            expose(baz)

        class C(A, B):
            pass

        self.assertEquals(set(expose.exposedMethodNames(C())), set(['foo', 'baz']))
        self.assertEquals(expose.get(C(), 'foo')(), 'bar')
        self.assertEquals(expose.get(C(), 'baz')(), 'quux')


    def test_unexposedMethodInaccessable(self):
        """
        Test that trying to get a method which has not been exposed raises an
        exception.
        """
        expose = Expose()

        class A(object):
            def foo(self):
                return 'bar'

        self.assertRaises(UnexposedMethodError, expose.get, A(), 'foo')
        self.assertRaises(UnexposedMethodError, expose.get, A(), 'bar')


    def test_getUnexposedWithDefault(self):
        """
        Test that a default can be supplied to Expose.get and it is returned if
        and only if the requested method is not exposed.
        """
        expose = Expose()

        class A(object):
            def foo(self):
                return 'bar'
            expose(foo)

        self.assertEquals(expose.get(A(), 'foo', None)(), 'bar')
        self.assertEquals(expose.get(A(), 'bar', None), None)


    def test_exposeReturnValue(self):
        """
        Test that the first argument is returned by a call to an Expose
        instance.
        """
        expose = Expose()
        def f():
            pass
        def g():
            pass
        self.assertIdentical(expose(f), f)
        self.assertIdentical(expose(f, g), f)


    def test_exposeWithoutArguments(self):
        """
        Test that calling an Expose instance with no arguments raises a
        TypeError.
        """
        expose = Expose()
        self.assertRaises(TypeError, expose)


    def test_exposedInstanceAttribute(self):
        """
        Test that exposing an instance attribute works in basically the same
        way as exposing a class method and that the two do not interfer with
        each other.
        """
        expose = Expose()

        class Foo(object):
            def __init__(self):
                # Add an exposed instance attribute
                self.bar = expose(lambda: 'baz')

            def quux(self):
                return 'quux'
            expose(quux)

        self.assertEquals(
            set(expose.exposedMethodNames(Foo())),
            set(['bar', 'quux']))
        self.assertEquals(expose.get(Foo(), 'bar')(), 'baz')
        self.assertEquals(expose.get(Foo(), 'quux')(), 'quux')



class CachedFileTests(TestCase):
    def setUp(self):
        self.testFile = self.mktemp()
        file(self.testFile, 'w').close()

        counter = count()
        self.cache = CachedFile(self.testFile, lambda path: counter.next())

    def test_cache(self):
        """
        Test that loading a file twice returns the cached version the second
        time.
        """
        o1 = self.cache.load()
        o2 = self.cache.load()
        self.assertEqual(o1, o2)

    def test_cacheModifiedTime(self):
        """
        Test that loading a cached file with a different mtime loads the file
        again.
        """
        mtime = getmtime(self.testFile)
        o = self.cache.load()
        # sanity check
        self.assertEqual(o, 0)

        utime(self.testFile, (mtime + 100, mtime + 100))
        o = self.cache.load()
        self.assertEqual(o, 1)

        utime(self.testFile, (mtime, mtime))
        o = self.cache.load()
        self.assertEqual(o, 2)

    def test_cacheInvalidate(self):
        """
        Test that calling invalidate really invalidates the cache.
        """
        self.assertEqual(self.cache.load(), 0)
        self.cache.invalidate()
        self.assertEqual(self.cache.load(), 1)

    def test_loadArgs(self):
        """
        Test that additional arguments are correctly passed through to the
        loader.
        """
        marker = object()
        def _loadMe(path, otherArg, otherKwarg):
            self.assertIdentical(otherArg, marker)
            self.assertIdentical(otherKwarg, marker)

        CachedFile(self.testFile, _loadMe).load(marker, otherKwarg=marker)

    def test_loaderException(self):
        """
        Test that an exception raised from the loader does not break the
        L{CachedFile}.
        """
        counter = count()

        def _loadMe(path, crashMe=False):
            if crashMe:
                raise Exception('It is an exception!')
            return counter.next()

        cf = CachedFile(self.testFile, _loadMe)

        # Can we still load after the first attempt raises an exception?
        self.assertRaises(Exception, cf.load, True)
        self.assertEqual(cf.load(), 0)

        # Cache should be valid now, so a broken loader shouldn't matter
        self.assertEqual(cf.load(True), 0)

        # A second broken load
        cf.invalidate()

        self.assertRaises(Exception, cf.load, True)
        self.assertEqual(cf.load(), 1)
