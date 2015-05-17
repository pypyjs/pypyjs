#!/usr/bin/env python

"""
    run unittests
    ~~~~~~~~~~~~~

    run all tests:

    ./runtests.py
"""

from __future__ import absolute_import, print_function

import os
import unittest

if __name__ == "__main__":
    loader = unittest.TestLoader()

    this_dir = os.path.join(os.path.dirname(__file__), "tests")
    suite = loader.discover(this_dir)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
