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

    start_dir = os.path.join(os.path.dirname(__file__))
    top_level_dir = os.path.join(start_dir, "..")
    suite = loader.discover(start_dir, top_level_dir=top_level_dir)

    runner = unittest.TextTestRunner(
        verbosity=2,
        # failfast=True,
    )
    result = runner.run(suite)
    sys.exit(len(result.errors) + len(result.failures))
