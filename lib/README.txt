
This directory contains all the files needed to deploy a basic PyPyJS
environment.  Specifically, we have:

  * pypy.js:           public-facing API to the PyPy VM
  * pypy.vm.js:        the PyPy VM itself, as built by rpython+emscripten
  * pypy.vm.js.lzmem:  compressed memory initializer data for the PyPy VM

And the following dependencies, which are distributed in accordance with their
open-source license:

  * Promise.min.js:      es6-compatible Promise library
  * FunctionPromise.js:  lib for parsing function code off the main thread
  * modules/*:           bundled collection of python standard library modules

