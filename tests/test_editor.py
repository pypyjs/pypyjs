#!/usr/bin/env python

"""
    selenium unitests with "editor" page
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import absolute_import, print_function

import os
import textwrap
import unittest
import sys

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
from .test_utils.utils import website_url_path


class EditorTests(BaseSeleniumTestCase):
    """
    Request and init PyPyJS in setUpClass
    and no complete reload before every tests
    """

    @classmethod
    def setUpClass(cls):
        super(EditorTests, cls).setUpClass()
        cls.driver.set_window_size(800, 900) # min.size to see the complete editor & console
        cls.driver.get(cls.editor_url)

        print("\nWait for init 'PyPy.js editor'...", file=sys.stderr)
        assert "PyPy.js" == cls.driver.title

        check = WebDriverWait(cls.driver, 10).until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "console"), "Welcome to PyPy.js!"
            )
        )
        assert check

    def run_code(self, code):
        """
        paste the given code into CodeMirror editor and click on 'run' button
        here we don't do a WebDriverWait() call!
        """
        code=code.replace("\\", "\\\\")
        code=code.replace("'", "\\'")
        code2 = "\\n".join(textwrap.dedent(code).strip().splitlines())

        # remove #run_info text for safety catch the execution run end:
        self.driver.execute_script('$("#run_info").text("");')

        # self.out("\nExecute script: '%s'" % script)
        self.driver.execute_script("CodeMirrorEditor.setValue('%s');" % code2)
        # editor_code = self.driver.execute_script("return CodeMirrorEditor.getValue();")
        # self.out("from editor: %r" % editor_code)

        # execute by clicking on the #run button
        self.driver.find_element_by_id("run").click()

    def execute_editor(self, code, timeout=10):
        self.run_code(code)

        # Wait that #run_info is filled with e.g.: "Run in 123ms"
        try:
            check = WebDriverWait(self.driver, timeout).until(
                expected_conditions.text_to_be_present_in_element(
                    (By.ID, "run_info"), "Run in "
                )
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
            ) % (code, self._get_console_text())
            self.fail(msg=msg)
        else:
            self.assertTrue(check)

        run_info_element = self.driver.find_element_by_id("run_info")
        run_info = run_info_element.text
        # self.out("\n%s" % run_info)
        return run_info

    def assertEditor(self, code, output):
        run_info = self.execute_editor(code)
        self.assertConsole(output)
        self.assertIn("OK", run_info)
        self.assertNotIn("Error", run_info)

    def test_execute_editor(self, script=None):
        self.execute_editor("""
            print "Hello PyPy.js!"
        """)
        self.assertConsole("""
            Hello PyPy.js!
        """)
        console_text = self.driver.execute_script('return $("#console").text();')
        console_text = console_text.strip()
        self.assertEqual(console_text, "Hello PyPy.js!")

    def test_execute_escaping(self):
        self.assertEditor("""
            print 'single quote'
        """, """
            single quote
        """)
    
        self.assertEditor("""
            print "double quote"
        """, """
            double quote
        """)
    
        self.assertEditor("""
            print "a 'single quote' in double quote"
        """, """
            a 'single quote' in double quote
        """)
    
        self.assertEditor("""
            print 'a "double quote" in single quote'
        """, """
            a "double quote" in single quote
        """)
    
        self.assertEditor("""
            print "a\\nnew line"
        """, """
            a
            new line
        """)
    
        self.assertEditor("""
            print "OK\\nisn't it?"
        """, """
            OK
            isn't it?
        """)

    def test_execute_multiline(self):
        self.assertEditor("""
            print "one"
            print "two"
        """, """
            one
            two
        """)

        self.assertEditor("""
            for i in range(2):
                print i

            print "OK"
        """, """
            0
            1
            OK
        """)

    def test_standard_out_streams(self):
        self.assertEditor("""
            import sys
            sys.stdout.write("to sys.stdout\\n")
            sys.stderr.write("to sys.stderr\\n")
        """, """
            to sys.stdout
            to sys.stderr
        """)

    def test_sys_version(self):
        self.assertEditor("""
            import sys
            print sys.version
        """, """
            2.7.8 (?, May 22 2015, 10:47:53)
            [PyPy 2.5.0]
        """)

        self.assertEditor("""
            import sys
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
        self.assertEditor("""
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
        self.assertEditor("print __name__ ", "__main__")

    def test_pickle(self):
        """
        https://github.com/rfk/pypyjs/issues/83
        """
        self.assertEditor("""
            import cPickle as pickle # remove docstring if https://github.com/rfk/pypyjs/issues/109 is fixed
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
        self.assertEditor("""
            import pickle # remove docstring if https://github.com/rfk/pypyjs/issues/109 is fixed
            print pickle.loads(pickle.dumps({'foo': 1}))
        """, """
            {'foo': 1}
        """)

    def test_js_module1(self):
        self.assertEditor("""
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
        self.assertEditor("""
            import js
            js.eval('var one = 123.456')
            print js.eval('one')
        """, """
            123.456
        """)

    def test_js_alert(self):
        self.run_code("""
            import js
            js.eval("alert('hello world')")
            print "OK"
        """)
        alert_is_present = WebDriverWait(self.driver, timeout=5).until(
            expected_conditions.alert_is_present()
        )
        self.assertTrue(alert_is_present)

        alert = self.driver.switch_to.alert
        self.assertEqual(alert.text, "hello world")

    def test_js_decorator(self):
        self.assertEditor("""
            import js

            @js.Function
            def decorated():
                print "second"

            js.globals.setTimeout(decorated, 10)
            print "first"
        """, """
            first
            second
        """)

    def test_module_random(self):
        """
        https://github.com/rfk/pypyjs/issues/4
        """
        self.assertEditor("""
            import random # remove docstring if https://github.com/rfk/pypyjs/issues/109 is fixed
            print random.__file__
        """, """
            /lib/pypyjs/lib_pypy/random.py
        """)

    def test_module_pprint(self):
        """
        https://github.com/rfk/pypyjs/issues/5
        """
        self.assertEditor("""
            import pprint # remove docstring if https://github.com/rfk/pypyjs/issues/109 is fixed
            pprint.pprint({"foo":range(10), "bar":range(10,20)})
        """, """
            {'bar': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
             'foo': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
        """)

    def test_module_platform(self):
        """
        https://github.com/rfk/pypyjs/issues/6
        """
        self.assertEditor("""
            import platform # remove docstring if https://github.com/rfk/pypyjs/issues/109 is fixed
            print platform.__file__
        """, """
            /lib/pypyjs/lib_pypy/platform.py
        """)

    def test_module_os(self):
        self.assertEditor("""
            import os
            print os.__file__
        """, """
            /lib/pypyjs/lib_pypy/os.py
        """)

    def test_import(self):
        """
        test  __import__
        """
        self.assertEditor("""
            try:
                print sys.version
            except NameError:
                print "OK"
            sys = __import__('sys')
            print sys.platform
        """, """
            OK
            js
        """)

    def _get_module_names(self):
        # Request indirect the content of /website/js/pypy.js-0.3.0/lib/modules/index.json
        # startup a VM:
        self.execute_editor("print 'init done'")
        self.assertEqual(self._get_console_text(), "init done")

        # get 'vm._allModules'
        vm_all_modules = self.driver.execute_script("return vm._allModules")
        # self.out(pprint.pformat(vm_all_modules))

        # hack a list of available modules:
        libpath = os.path.normpath(website_url_path("js/pypy.js-0.3.1/lib/modules"))
        module_names = [
            os.path.splitext(item)[0]
            for item in sorted(os.listdir(libpath))
            if not item.startswith("_") and item.endswith(".py")
        ]
        # module_names = ["sys", "random", "this"]

        # Check if all collected module_names exist in vm._allModules
        for module_name in module_names:
            self.assertIn(module_name, vm_all_modules)

        return module_names

    def _get_import_test_code(self):
        return textwrap.dedent("""
            import js

            modules = js.globals.vm._allModules

            module_names = [str(m) for m in modules]
            print "%i modules (unfiltered)" % len(module_names)

            module_names = [n for n in module_names if "_" not in n]
            module_names = [n for n in module_names if "." not in n]
            print "%i modules (filtered)" % len(module_names)

            good = failed = 0
            for no, module_name in enumerate(module_names):
                print "%3i - import %-20s" % (no, module_name),
                try:
                    __import__(module_name)
                except ImportError as err:
                    print "ERROR: %s" % err
                    failed += 1
                else:
                    print "OK"
                    good += 1

            print "%i worked imports - %i failed imports" % (good, failed)
        """)

    def _assertModuleImports(self, code):
        run_info = self.execute_editor(code)

        console_text = self._get_console_text()
        try:
            self.assertIn(console_text, "worked imports ")
            self.assertIn(console_text, "failed imports")
            self.assertIn(console_text, "OK")
            self.assertNotIn(console_text, "ERROR")
            self.assertNotIn(console_text, "Abort test")

            self.assertIn("OK", run_info)
            self.assertNotIn("Error", run_info)
        except AssertionError as err:
            msg=(
                "ERROR: %s\n"
                "-----------------------------------\n"
                "Console output:\n"
                "-----------------------------------\n"
                "%s\n"
                "-----------------------------------\n"
            ) % (err, console_text)
            self.fail(msg=msg)

    def test_imports1(self):
        code = self._get_import_test_code()
        self._assertModuleImports(code)

    def test_imports2(self):
        code = self._get_import_test_code()

        # work-a-round for: https://github.com/rfk/pypyjs/issues/127
        module_names = self._get_module_names()
        code += "\n".join(["# import %s" % module_name for module_name in module_names])

        self._assertModuleImports(code)

    def test_namespace(self):
        self.assertEditor("""
            import sys
            print "locals:", locals()
            print "globals:", globals()
        """, """
            locals: {'__name__': '__main__', '__builtins__': <module '__builtin__' (built-in)>, '__package__': None, 'sys': <module 'sys' (built-in)>}
            globals: {'__name__': '__main__', '__builtins__': <module '__builtin__' (built-in)>, '__package__': None, 'sys': <module 'sys' (built-in)>}
        """)

        # We get a fresh PyPyJS(), so sys is not imported anymore:
        self.assertEditor("""
            print "locals:", locals()
            print "globals:", globals()
        """, """
            locals: {'__name__': '__main__', '__builtins__': <module '__builtin__' (built-in)>}
            globals: {'__name__': '__main__', '__builtins__': <module '__builtin__' (built-in)>}
        """)


if __name__ == "__main__":
    unittest.main(
        verbosity=3,
        # failfast=True,

        # run a specific test, e.g.:
        # argv=("test_editor", "EditorTests",)
        argv=("test_editor",
            "EditorTests.test_imports1",
            "EditorTests.test_imports2",
        )
        # argv=("test_editor",
        #     "EditorTests.test_js_alert",
        #     "EditorTests.test_js_decorator",
        # )
    )