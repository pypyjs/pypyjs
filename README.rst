
PyPy.js:  PyPy compiled into JavaScript
=======================================

PyPy.  Compiled into JavaScript.  JIT-compiling to JavaScript at runtime.
Because why not.

This is a very-much-in-flux collection of supporting scripts and infrastructure
for my experimental emscripten/asmjs backend for PyPy, as described here:

    https://www.rfk.id.au/blog/entry/pypy-js-first-steps/

The actual PyPy backend is maintained as a git submodule on top of the
mainline PyPy repo:

    https://github.com/rfk/pypy

To build it you will need a 32bit python environment, along with this fork
of emscripten:

    https://github.com/rfk/emscripten

Run the build like so:

    $> cd ./pypy
    $> python ./rpython/bin/rpython --backend=js --opt=jit ./pypy/goal/targetpypystandalone.py

This will produce a file "pypy-js" containing the interpreter.  Take a look in the "demo" directory for an example of distributing this file.
