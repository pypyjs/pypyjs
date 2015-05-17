#!/usr/bin/env python

"""
    Quick HowTo setup a test environment and run this file:

    ~ $ virtualenv pypyjs_env
    ~ $ cd pypyjs_env/
    ~/pypyjs_env $ source bin/activate
    (pypyjs_env)~/pypyjs_env $ pip install --upgrade pip
    (pypyjs_env)~/pypyjs_env $ pip install selenium
    (pypyjs_env)~/pypyjs_env $ pip install -e git+https://github.com/rfk/pypyjs.git#egg=pypyjs
    (pypyjs_env)~/pypyjs_env $ cd src/pypyjs/
    (pypyjs_env)~/pypyjs_env/src/pypyjs$ ./runtests.py

"""

from __future__ import absolute_import, print_function

import difflib
import os
import posixpath
import textwrap
import traceback
import unittest
import sys

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


def make_diff(block1, block2):
    d = difflib.Differ()

    block1 = block1.replace("\\n", "\\n\n").split("\n")
    block2 = block2.replace("\\n", "\\n\n").split("\n")

    diff = d.compare(block1, block2)

    result = ["%2s %s\n" % (line, i) for line, i in enumerate(diff)]
    return "".join(result)


def website_path(sub_path):
    path = posixpath.abspath(posixpath.join(os.path.dirname(__file__), "..", "website", sub_path))
    assert os.path.exists(path), "path %r doesn't exists!" % path
    return path


class BaseSeleniumTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseSeleniumTestCase, cls).setUpClass()
        cls.driver = webdriver.Firefox()
        cls.driver.set_window_size(1024, 768)
        cls.driver.set_window_position(0, 0)
        path = website_path("index.html")
        cls.index_url = "file://%s" % path

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        except:
            pass

    def out(self, *args):
        print(*args, file=sys.stderr)

    def _verbose_assertion_error(self, driver):
        self.out("\n")
        self.out("*" * 79)
        traceback.print_exc()
        self.out(" -" * 40)

        page_source = driver.page_source

        if not page_source.strip():
            self.out("[page coure is empty!]")
        else:
            page_source = "\n".join([line for line in page_source.splitlines() if line.rstrip()])
            self.out(page_source)

        self.out("*" * 79)
        self.out("\n")
        raise

    def _get_console_text(self):
        console = self.driver.find_element_by_id("console")
        console_text = console.text
        return console_text.strip()

    def assertConsole(self, txt):
        console_text = self._get_console_text()
        
        txt = textwrap.dedent(txt).strip()
        msg = textwrap.dedent("""

            *** Console output is: ***
            %s

            *** the reference: ***
            %s

            *** diff: ***
            %s
        """) % (
            console_text, txt, make_diff(console_text, txt)
        )
        self.assertEqual(console_text, txt, msg=msg)


class PyPyJSSeleniumLowLevelTests(BaseSeleniumTestCase):
    """
    Tests that reload the page completely.
    This will take relative long time :(
    """

    def setUp(self):
        self.driver.get(self.index_url)
        try:
            self.out("\nWait for console...")
            self.assertEqual(self.driver.title, "PyPy.js")

            check = WebDriverWait(self.driver, 10).until(
                expected_conditions.text_to_be_present_in_element(
                    (By.ID, "console"), ">>>"
                )
            )
            self.assertTrue(check)
        except Exception:
            self._verbose_assertion_error(self.driver)

        # clear the console content:
        self.driver.execute_script('jqconsole.Reset()')

    def test(self):
        self.driver.execute_script('vm.eval("import sys;print(sys.version)")')
        self.assertConsole("""
            2.7.8 (?, May 17 2015, 07:02:41)
            [PyPy 2.5.0]
        """)


class PyPyJSSeleniumTests(BaseSeleniumTestCase):
    """
    Request and init PyPyJS in setUpClass
    and no complete reload before every tests
    """

    @classmethod
    def setUpClass(cls):
        super(PyPyJSSeleniumTests, cls).setUpClass()
        cls.driver.get(cls.index_url)

        cls.out("\nWait for init...")
        assert "PyPy.js" == cls.driver.title

        check = WebDriverWait(cls.driver, 10).until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "console"), ">>>"
            )
        )
        assert check

    def clear_console(self):
        self.driver.execute_script('jqconsole.Reset()')
        self.assertConsole("")  # is empty?

    def setUp(self):
        self.clear_console()

    def _execute_code(self, txt, timeout=10):
        txt=txt.replace("\\", "\\\\")
        txt=txt.replace("'", "\\'")
        script = "\\n".join(textwrap.dedent(txt).strip().splitlines())

        # Add a element to DOM tree to trigger the end of vm.eval() call:
        self.driver.execute_script(
            "$('body').append( $('<div/>').attr('id','selenium_vm_run') );"
        )
        run_element = self.driver.find_element_by_id("selenium_vm_run")

        script2 = (
            "function selenium_vm_run_done() {$( '#selenium_vm_run' ).remove();}"
            # "vm.exec('%s').then(selenium_vm_run_done, selenium_vm_run_done);"
            "vm._execute_source('%s').then(selenium_vm_run_done, selenium_vm_run_done);"
        ) % script

        # self.out('\nExecute script: %s' % script)
        self.driver.execute_script(script2)

        # Wait that vm.eval() is really finished: The added DOM element will be remove
        try:
            check = WebDriverWait(self.driver, timeout).until(
                expected_conditions.staleness_of(run_element)
            )
        except TimeoutException:
            msg=(
                "Timeout reached while execution of:\n"
                "-----------------------------------\n"
                "%s\n"
                "-----------------------------------\n"
                "Console output:\n"
                "-----------------------------------\n"
                "%s\n"
                "-----------------------------------\n"
            ) % (script, self._get_console_text())
            self.fail(msg=msg)
        else:
            self.assertTrue(check)

    def assertExecution(self, python_script, console_output, timeout=10):
        self._execute_code(python_script, timeout)
        self.assertConsole(console_output)

    def test_execute_escaping(self):
        self.assertExecution("""
            print 'single quote'
        """, """
            single quote
        """)

        self.clear_console()
        self.assertExecution("""
            print "double quote"
        """, """
            double quote
        """)

        self.clear_console()
        self.assertExecution("""
            print "a 'single quote' in double quote"
        """, """
            a 'single quote' in double quote
        """)

        self.clear_console()
        self.assertExecution("""
            print 'a "double quote" in single quote'
        """, """
            a "double quote" in single quote
        """)

        self.clear_console()
        self.assertExecution("""
            print "a\\nnew line"
        """, """
            a
            new line
        """)

        self.clear_console()
        self.assertExecution("""
            print "OK\\nisn't it?"
        """, """
            OK
            isn't it?
        """)

    def test_execute_multiline(self):
        self.assertExecution("""
            print "one"
            print "two"
        """, """
            one
            two
        """)

        self.clear_console()
        self.assertExecution("""
            for i in range(2):
                print i

            print "OK"
        """, """
            0
            1
            OK
        """)

    def test_sys_version(self):
        self.assertExecution("""
            import sys
            print sys.version
        """, """
            2.7.8 (?, May 17 2015, 07:02:41)
            [PyPy 2.5.0]
        """)

        self.clear_console()

        self.assertExecution("""
            for path in sys.path:
                print path
        ""","""
            /lib/pypyjs/lib_pypy/__extensions__
            /lib/pypyjs/lib_pypy
            /lib/pypyjs/lib-python/2.7
            /lib/pypyjs/lib-python/2.7/lib-tk
            /lib/pypyjs/lib-python/2.7/plat-linux2
        """)


    def test_sys_platform(self):
        """
        https://github.com/rfk/pypyjs/issues/49
        """
        self.assertExecution("""
            import sys
            print sys.platform
        """, """
            js
        """)

    def test_name(self):
        """
        https://github.com/rfk/pypyjs/issues/104
        vm._execute_source("print __name__") -> __builtin__
        vm.exec("print __name__") -> __main__
        """
        self.assertExecution("print __name__ ", "__main__")

    def test_pickle(self):
        """
        https://github.com/rfk/pypyjs/issues/83
        """
        self.assertExecution("""
            import cPickle as pickle
            d = pickle.dumps({'foo': 'bar'})
            print d
            print pickle.loads(d)
        """, """
            (dp1
            S'foo'
            p2
            S'bar'
            p3
            s.
            {'foo': 'bar'}
        """)
        self.clear_console()
        self.assertExecution("""
            import pickle
            print pickle.loads(pickle.dumps({'a': 'a'}))
        """, """
            {'a': 'a'}
        """)

    def test_js_module1(self):
        self.assertExecution("""
            import js
            math = js.globals.Math
            print(math.log(2))
        """, """
            0.6931471805599453
        """)

    def test_js_module2(self):
        """
        https://github.com/rfk/pypyjs/issues/56
        """
        self.assertExecution("""
            import js
            js.eval('var one = 1')
            js.eval('one')
        """, """
            <js.Number 1.000000>
        """)

    def test_module_random(self):
        """
        https://github.com/rfk/pypyjs/issues/4
        """
        self.assertExecution("""
            import random
            print random.__file__
        """, """
            /lib/pypyjs/lib_pypy/random.py
        """)

    def test_module_pprint(self):
        """
        https://github.com/rfk/pypyjs/issues/5
        """
        self.assertExecution("""
            import pprint
            print pprint.__file__
        """, """
            /lib/pypyjs/lib_pypy/pprint.py
        """)

    def test_module_platform(self):
        """
        https://github.com/rfk/pypyjs/issues/6
        """
        self.assertExecution("""
            import platform
            print platform.__file__
        """, """
            /lib/pypyjs/lib_pypy/platform.py
        """)
        
    def test_module_os(self):
        self.assertExecution("""
            import os
            print os.__file__
        """, """
            /lib/pypyjs/lib_pypy/os.py
        """)

    def test_imports(self):

        # hack a list of available modules:
        libpath = website_path("js/pypy.js-0.3.0/lib/modules")
        module_names = [
            os.path.splitext(item)[0]
            for item in sorted(os.listdir(libpath))
            if not item.startswith("_") and item.endswith(".py")
        ]

        good = failed = 0
        total_count = len(module_names)
        self.out("\nTry to import %i modules:" % total_count)
        for no, module_name in enumerate(sorted(module_names)):
            python_script = """
                try:
                    import %(name)s
                except (ImportError, NameError) as err:
                    print "Error importing '%(name)s': %%s" %% err
                else:
                    print "Import '%(name)s', ok."
            """ % {"name":module_name}
            self.clear_console()
            self._execute_code(python_script)
            response = self._get_console_text()
            if "ok" in response:
                good += 1
            elif "Error" in response:
                failed += 1
            else:
                self.fail(msg=response)
            self.out("\t%i/%i: %s" % (no, total_count, response))

            if failed >= 10:
                self.fail("import test failed more than 10 times. Abort the test.")

        self.assertEqual(failed, 0)



if __name__ == "__main__":
    unittest.main(
        verbosity=3,
        # failfast=True,

        # run a specific test, e.g.:
        # argv=("selenium_tests", "PyPyJSSeleniumLowLevelTests",)
        # argv=("selenium_tests", "PyPyJSSeleniumTests.test_js_module",)
    )