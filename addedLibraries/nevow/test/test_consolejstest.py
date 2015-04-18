# Copyright (c) 2006 Divmod.
# See LICENSE for details.

"""
Test the dependency tracking and javascript generation code in
L{nevow.jsutil}.
"""

from textwrap import dedent
from twisted.internet.utils import getProcessOutput
from twisted.trial.unittest import TestCase
from nevow.testutil import setJavascriptInterpreterOrSkip
from nevow.jsutil import getDependencies, generateTestScript
from nevow import athena

class _ConsoleJSTestMixin:
    """
    Things that might be useful for testing JavaScript interaction functions
    from L{nevow.testutil}.
    """

    def _getPackages(self):
        """
        @return: the mapping of all javascript packages plus some fake modules
        """
        packages = athena.allJavascriptPackages()
        packages.update(
            {'ConsoleJSTestFoo': self._outputToTempFile(
                        'print("hello from ConsoleJSTestFoo");'),
             'ConsoleJSTestFoo.Bar': self._outputToTempFile(
                            dedent(
                                '''
                                // import ConsoleJSTestFoo
                                print("hello from ConsoleJSTestFoo.Bar");
                                ''')),
             'ConsoleJSTestFoo.Baz': self._outputToTempFile(
                            dedent(
                                '''
                                // import ConsoleJSTestFoo
                                // import ConsoleJSTestFoo.Bar
                                print("hello from ConsoleJSTestFoo.Baz");
                                '''))})
        return packages

    def _outputToTempFile(self, s):
        """
        Write the contents of string C{s} to a tempfile and return the
        filename that was used

        @param s: file contents
        @type s: C{str}

        @return: filename
        @rtype: C{str}
        """
        fname = self.mktemp()
        fObj = file(fname, 'w')
        fObj.write(s)
        fObj.close()
        return fname

class DependenciesTestCase(TestCase, _ConsoleJSTestMixin):
    """
    Tests for L{getDependencies}
    """
    def test_getDependenciesNoModules(self):
        """
        Test that L{getDependencies} returns the empty list when the js module
        it's passed doesn't explicitly import anything and the C{bootstrap} and
        C{ignore} parameters are empty
        """
        deps = getDependencies(
                self._outputToTempFile(''), ignore=(), bootstrap=())
        self.assertEqual(len(deps), 0)


    def test_getDependenciesBootstrap(self):
        """
        Test that L{getDependencies} returns a list containing only the
        bootstrap modules when the js module it's passed doesn't explicitly
        import anything and the "ignore" parameter is empty.
        """
        bootstrap = ['ConsoleJSTestFoo.Bar', 'ConsoleJSTestFoo.Baz']

        deps = getDependencies(
                self._outputToTempFile(''),
                ignore=(),
                bootstrap=bootstrap,
                packages=self._getPackages())
        self.assertEqual([d.name for d in deps], bootstrap)


    def test_getDependenciesIgnore(self):
        """
        Test that L{getDependencies} observes the C{ignore} parameter
        """
        deps = getDependencies(
                self._outputToTempFile(
                    dedent(
                        '''
                        // import ConsoleJSTestFoo.Bar
                        // import ConsoleJSTestFoo.Baz
                        ''')),
                ignore=('ConsoleJSTestFoo.Bar',),
                bootstrap=(),
                packages=self._getPackages())

        self.assertEqual([d.name for d in deps], ['ConsoleJSTestFoo', 'ConsoleJSTestFoo.Baz'])

    def test_getDependenciesAll(self):
        """
        Test that L{getDependencies} works if we import a single module which
        in turn depends on multiple modules
        """
        fname = self._outputToTempFile(
            '// import ConsoleJSTestFoo.Baz')

        deps = getDependencies(
                fname,
                ignore=(),
                bootstrap=(),
                packages=self._getPackages())

        self.assertEqual([d.name for d in deps], ['ConsoleJSTestFoo', 'ConsoleJSTestFoo.Bar', 'ConsoleJSTestFoo.Baz'])



class JSGenerationTestCase(TestCase, _ConsoleJSTestMixin):
    """
    Tests for L{generateTestScript}
    """
    javascriptInterpreter = None

    def test_generateTestScript(self):
        """
        Test for L{generateTestScript}
        """
        fname = self._outputToTempFile(
                    dedent(
                        '''
                        // import ConsoleJSTestFoo.Bar
                        // import ConsoleJSTestFoo.Baz
                        print("hello from the test module");
                        '''))

        deps = getDependencies(
                fname,
                ignore=(),
                bootstrap=(),
                packages=self._getPackages())

        script = generateTestScript(
                    fname,
                    dependencies=deps)

        scriptfname = self._outputToTempFile(script)

        def gotResult(s):
            self.assertEqual(s.split('\n'),
                             ['hello from ConsoleJSTestFoo',
                              'hello from ConsoleJSTestFoo.Bar',
                              'hello from ConsoleJSTestFoo.Baz',
                              'hello from the test module',
                              ''])

        result = getProcessOutput(self.javascriptInterpreter, ('-f', scriptfname))
        result.addCallback(gotResult)
        return result

setJavascriptInterpreterOrSkip(JSGenerationTestCase)
