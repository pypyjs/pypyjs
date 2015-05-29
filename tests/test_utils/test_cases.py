import sys
import textwrap
import traceback
import unittest

from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException

from .utils import website_url_path, make_diff


class BaseSeleniumTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseSeleniumTestCase, cls).setUpClass()
        cls.driver = webdriver.Firefox()
        cls.driver.set_window_position(0, 0)
        cls.index_url = "file://%s" % website_url_path("index.html")
        cls.editor_url = "file://%s" % website_url_path("editor.html")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        except:
            pass

    def tearDown(self):
        super(BaseSeleniumTestCase, self).tearDown()

        # Confirm a existing alert dialog, otherwise followed test will failed
        # with selenium.common.exceptions.UnexpectedAlertPresentException
        try:
            alert = self.driver.switch_to.alert
            alert.accept() # Confirm a alert dialog, otherwise
        except NoAlertPresentException:
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