"""Main entry point"""

import sys

# PyPy.js doesn't have an "argv" so we'll need to set it.
if sys.platform == "js":
    sys.argv = ["python -m unittest"]
if sys.argv[0].endswith("__main__.py"):
    sys.argv[0] = "python -m unittest"

__unittest = True

from .main import main, TestProgram, USAGE_AS_MAIN
TestProgram.USAGE = USAGE_AS_MAIN

main(module=None)
