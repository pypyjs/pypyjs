
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

You can get all the necessary code from within this top-level repository
by accessing it as a git submodule::

    $> git submodule init
    $> git submodule update

Building pypyjs requires a 32-bit python environment and the emscripten-enabled
LLVM toolchain.  The recommended way to build is using the pre-built docker
image containing these dependencies::

    $> docker pull rfkelly/pypyjs-build

The Makefile knows how to use this image during the build::

    $> make

Be prepared, this will take a *long* time.  It will eventually produce the file
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


