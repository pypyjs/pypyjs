import posixpath
import traceback
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import sys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains


class BaseSeleniumTestCase(unittest.TestCase):
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



class PyPyJSSeleniumTests(BaseSeleniumTestCase):
    @classmethod
    def setUpClass(cls):
        super(PyPyJSSeleniumTests, cls).setUpClass()
        cls.driver = webdriver.Firefox()
        cls.driver.set_window_size(1024,768)
        cls.driver.set_window_position(0,0)
        path = posixpath.abspath(posixpath.join("..", "website", "index.html"))
        cls.index_url = "file://%s" % path

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        except:
            pass

    # def setUp(self):
    #     self.driver = webdriver.Firefox()
    #
    #
    # def tearDown(self):
    #     self.driver.close()
    def assertConsole(self, lines):
        console = self.driver.find_element_by_id("console")
        console_text = console.text
        console_lines = [txt.strip() for txt in console_text.split("\n") if txt.strip()]
        self.assertEqual(console_lines, lines)

    def test(self):
        self.driver.get(self.index_url)
        try:
            self.out("\nWait for console...")
            self.assertIn("PyPy.js", self.driver.title)

            check = WebDriverWait(self.driver, 10).until(
                expected_conditions.presence_of_element_located(
                    (By.CLASS_NAME, "jqconsole-output")
                )
            )
            self.assertTrue(check)

            check = WebDriverWait(self.driver, 10).until(
                expected_conditions.text_to_be_present_in_element(
                    (By.ID, "console"), ">>>"
                )
            )
            self.assertTrue(check)

            self.assertConsole([
                "Welcome to PyPy.js!",
                ">>>",
            ])

            self.driver.execute_script('vm.eval("import sys;print(sys.version)")')
            self.assertConsole([
                "Welcome to PyPy.js!",
                "2.7.8 (?, Apr 09 2015, 15:06:24)",
                "[PyPy 2.5.0]",
                ">>>",
            ])
            return

            # console=self.driver.find_element_by_id("console")
            # console.click() # Set the focus to the console element
            #
            # console = self.driver.find_element_by_id("console")
            # console.send_keys("import sys;print(sys.version)")
            # console.send_keys(Keys.RETURN)
            #
            # check = WebDriverWait(self.driver, 2).until(
            #     expected_conditions.text_to_be_present_in_element(
            #         (By.ID, "console"), ">>> foo bar"
            #     )
            # )
            # # self.driver.implicitly_wait(5)
            # self.assertConsole([
            #     "Welcome to PyPy.js!",
            #     ">>> foo bar",
            # ])

        except Exception:
            self._verbose_assertion_error(self.driver)




if __name__ == "__main__":
    unittest.main()