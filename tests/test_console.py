#!/usr/bin/env python

"""
    selenium unitests with "console" page
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from __future__ import absolute_import, print_function

import textwrap
import unittest
import sys
import os

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

if __package__ != "tests":
    # Hack to make it possible to run this file directly
    __package__="tests"
    sys.path.insert(0,
        os.path.join(os.path.dirname(__file__), "..")
    )
    import tests

from .test_utils.test_cases import BaseSeleniumTestCase


class PyPyJSSeleniumTests(BaseSeleniumTestCase):
    """
    Request and init PyPyJS in setUpClass
    and no complete reload before every tests
    """

    @classmethod
    def setUpClass(cls):
        super(PyPyJSSeleniumTests, cls).setUpClass()
        cls.driver.set_window_size(1000, 650) # min.size to see the complete console
        cls.driver.get(cls.index_url)

        print("\nWait for init 'PyPy.js console'...", file=sys.stderr)
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


if __name__ == "__main__":
    unittest.main(
        verbosity=3,
        # failfast=True,

        # run a specific test, e.g.:
        # argv=("selenium_tests", "PyPyJSSeleniumLowLevelTests",)
        # argv=("selenium_tests", "PyPyJSSeleniumTests.test_js_module",)
    )