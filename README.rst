
PyPy.js:  PyPy compiled into JavaScript
=======================================

PyPy.  Compiled into JavaScript.  JIT-compiling to JavaScript at runtime.
Because why not.

This is a very-much-in-flux collection of supporting scripts and infrastructure
for my experimental emscripten/asmjs backend for PyPy, as described here:

    https://www.rfk.id.au/blog/entry/pypy-js-first-steps/

The actual PyPy backend is maintained as a git submodule pointing to a fork
of a github clone of the upstream PyPy repository:

    https://github.com/rfk/pypy

You can get all the necessary code by checking out this repository and doing::

    $> git submodule init
    $> git submodule update

Building it requires a 32-bit python environment and the emscripten-enabled
LLVM toolchain.  The makefile can build these automatically for you::

    $> make deps
    $> source ./build/deps/bin/activate

Be warned, this will take a *long* time.  Once it's done you can build
the pypy.vm.js javascript file with::

    $> make

Again, this will take a *long* time.  It will eventually produce the file
`./build/pypy.vm.js` containing the code for the interpreter.  Take a look in
the `./website/demo` directory for an example of how to distribute and use
this file.

To build from an in-progress branch of the pypy repository, check it out
in the submodule like so::

    $> cd ./deps/pypy
    $> git checkout whatever-branch
    $> cd ../../
    $> make

You can also run the testsuite like this::

    $> make test-jit-backend


If you'd like to hack on PyPyJS, the following background reading will
be helpful:

  * http://pypy.readthedocs.org/en/latest/translation.html
  * http://pypy.readthedocs.org/en/latest/coding-guide.html


