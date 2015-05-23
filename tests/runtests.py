#!/usr/bin/env python

"""
    run unittests
    ~~~~~~~~~~~~~
"""

from __future__ import absolute_import, print_function

import os
import unittest
import sys

if __name__ == "__main__":
    loader = unittest.TestLoader()

    this_dir = os.path.join(os.path.dirname(__file__))
    suite = loader.discover(this_dir)

    runner = unittest.TextTestRunner(
        verbosity=2,
        # failfast=True,
    )
    result = runner.run(suite)
    sys.exit(len(result.errors) + len(result.failures))