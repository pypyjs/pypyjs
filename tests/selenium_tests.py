
"""
    Quick HowTo setup a test environment and run this file:

    ~ $ virtualenv pypyjs_env
    ~ $ cd pypyjs_env/
    ~/pypyjs_env $ source bin/activate
    (pypyjs_env)~/pypyjs_env $ pip install --upgrade pip
    (pypyjs_env)~/pypyjs_env $ pip install selenium
    (pypyjs_env)~/pypyjs_env $ pip install -e git+https://github.com/rfk/pypyjs.git#egg=pypyjs
    (pypyjs_env)~/pypyjs_env $ cd src/pypyjs/tests
    (pypyjs_env)~/pypyjs_env/src/pypyjs/tests$ python selenium_tests.py


"""

import posixpath
import traceback
import unittest
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


class BaseSeleniumTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseSeleniumTestCase, cls).setUpClass()
        cls.driver = webdriver.Firefox()
        cls.driver.set_window_size(1024, 768)
        cls.driver.set_window_position(0, 0)
        path = posixpath.abspath(posixpath.join("..", "website", "index.html"))
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

    def assertConsole(self, *lines):
        console = self.driver.find_element_by_id("console")
        console_text = console.text
        console_lines = tuple([
            txt.strip()
            for txt in console_text.split("\n")
            if txt.strip()
        ])
        self.assertEqual(console_lines, lines)


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
        self.assertConsole(
            "2.7.8 (?, Apr 09 2015, 15:06:24)",
            "[PyPy 2.5.0]",
        )


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

    def setUp(self):
        self.driver.execute_script('jqconsole.Reset()')
        self.assertConsole()  # is empty?

    def _execute(self, *args):
        for arg in args:
            self.driver.execute_script('vm.eval("%s")' % arg)

    def test_sys_version(self):
        self._execute(
            "import sys",
            "print(sys.version)"
        )
        self.assertConsole(
            "2.7.8 (?, Apr 09 2015, 15:06:24)",
            "[PyPy 2.5.0]",
        )

    def test_sys_platform(self):
        """
        https://github.com/rfk/pypyjs/issues/49
        """
        self._execute(
            "import sys",
            "print(sys.platform)"
        )
        self.assertConsole("js")

    def test_name(self):
        self._execute(
            "print(__name__)"
        )
        self.assertConsole('__main__')

    def test_pickle(self):
        """
        https://github.com/rfk/pypyjs/issues/83
        """
        self._execute(
            "import pickle",
            "print(pickle.loads(pickle.dumps({'a': 'a'})))"
        )
        self.assertConsole("{'a': 'a'}")


if __name__ == "__main__":
    unittest.main(
        verbosity=3,
        # failfast=True
    )