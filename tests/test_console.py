#!/usr/bin/env python

"""
    Quick HowTo setup a test environment and run this file:

    ~ $ virtualenv pypyjs_env
    ~ $ cd pypyjs_env/
    ~/pypyjs_env $ source bin/activate
    (pypyjs_env)~/pypyjs_env $ pip install --upgrade pip
    (pypyjs_env)~/pypyjs_env $ pip install selenium
    (pypyjs_env)~/pypyjs_env $ pip install -e git+https://github.com/pypyjs/pypyjs.git#egg=pypyjs
    (pypyjs_env)~/pypyjs_env $ cd src/pypyjs/
    (pypyjs_env)~/pypyjs_env/src/pypyjs$ ./runtests.py

    TODO:
     * merge same code parts with 'editor' branch after both branches are merges
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


class PyPyJSSeleniumTests(BaseSeleniumTestCase):
    """
    Request and init PyPyJS in setUpClass
    and no complete reload before every tests
    """

    @classmethod
    def setUpClass(cls):
        super(PyPyJSSeleniumTests, cls).setUpClass()
        cls.driver.get(cls.index_url)

        print("\nWait for init...", file=sys.stderr)
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
            "vm.exec('%s').then(selenium_vm_run_done, selenium_vm_run_done);"
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

    def assertExecConsole(self, python_script, console_output, timeout=10):
        """
        Execute the given python_script and check the console output.
        """
        self.clear_console()
        self._execute_code(python_script, timeout)
        self.assertConsole(console_output)

    def test_execute_escaping(self):
        self.assertExecConsole("""
            print 'single quote'
        """, """
            single quote
        """)

        self.assertExecConsole("""
            print "double quote"
        """, """
            double quote
        """)

        self.assertExecConsole("""
            print "a 'single quote' in double quote"
        """, """
            a 'single quote' in double quote
        """)

        self.assertExecConsole("""
            print 'a "double quote" in single quote'
        """, """
            a "double quote" in single quote
        """)

        self.assertExecConsole("""
            print "a\\nnew line"
        """, """
            a
            new line
        """)

        self.assertExecConsole("""
            print "OK\\nisn't it?"
        """, """
            OK
            isn't it?
        """)

    def test_execute_multiline(self):
        self.assertExecConsole("""
            print "one"
            print "two"
        """, """
            one
            two
        """)

        self.assertExecConsole("""
            for i in range(2):
                print i

            print "OK"
        """, """
            0
            1
            OK
        """)

    def test_standard_out_streams(self):
        self.assertExecConsole("""
            import sys
            sys.stdout.write("to sys.stdout\\n")
            sys.stderr.write("to sys.stderr\\n")
        """, """
            to sys.stdout
            to sys.stderr
        """)

    def test_pystone_imports_and_runs(self):
        self.clear_console()
        self._execute_code("""
            from test import pystone; # work-a-round for https://github.com/pypyjs/pypyjs/issues/109
            pystone.main(1)
        """)
        console_text = self._get_console_text()
        self.assertIn("Pystone(1.1) time for 1 passes = 0", console_text)
        self.assertIn("This machine benchmarks at", console_text)
        self.assertIn("pystones/second", console_text)



if __name__ == "__main__":
    unittest.main(
        verbosity=3,
        # failfast=True,

        # run a specific test, e.g.:
        # argv=("selenium_tests", "PyPyJSSeleniumLowLevelTests",)
        # argv=("selenium_tests", "PyPyJSSeleniumTests.test_js_module",)
    )
