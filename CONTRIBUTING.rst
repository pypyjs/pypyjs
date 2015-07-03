
Contributing to PyPy.js
=======================

Welcome!  Thanks for your interest in the PyPy.js project.

If you'd like to hack on PyPy.js, the following background reading on
general PyPy development will be helpful:

  * http://pypy.readthedocs.org/en/latest/translation.html
  * http://pypy.readthedocs.org/en/latest/coding-guide.html


Getting the Code
----------------

Our codebase consists of two separate repositories:

  * A fork of the main PyPy project codebase: https://github.com/pypyjs/pypy
  * This wrapper repository: https://github.com/pypyjs/pypyjs

For development you should clone the `pypyjs` repository, which includes the
`pypy` one as a git submodule::

    $> git clone https://github.com/pypyjs/pypyjs
    $> cd pypyjs
    $> git submodule update --init

We have the following major components in the PyPy repo:

  * An "emscripten" build platform definition, which teaches pypy's rpython
    toolchain how to compile things with emscripten:
    `./deps/pypy/rpython/translator/platform/emscripten_platform/`.
  * An rpython JIT backend that emits asmjs at runtime:
    `./deps/pypy/rpython/jit/backend/asmjs/`.
  * A "js" builtin module for the resulting interperter, to allow interaction
    with the host javascript environment:
    `./deps/pypy/pypy/module/js/`.

Along with these wrappers to help working with the resulting interpreter:

  * A wrapper to load up the compiled VM and expose it via a nice javascript
    API: `./lib/pypyjs.js`.
  * A script for bundling python modules into an indexed format that can be
    easily loaded into the browser:  `./tools/module_bundler.py`.


Building
--------

Building pypyjs requires a 32-bit python environment and the emscripten-enabled
LLVM toolchain.  The recommended way to build is using the pre-built docker
image containing these dependencies::

    $> docker pull rfkelly/pypyjs-build

The Makefile knows how to use this image to run the tests without doing a full
build of the interpreter::

    $> make test

Or you can run specific parts of the testsuite using the following targets::

    $> make test-jit-backend
    $> make test-js-module

The default Makefile target will perform a fresh build::

    $> make

Be prepared, this will take a *long* time.  It will eventually produce the file
`./build/pypy.vm.js` containing the code for the interpreter.  This goes
together with support files in `./lib/` to make a complete distribution.

To get a full release tarball, do::

    $> make release

Take a look in the `./website/js/` directory for an example of how to
distribute and use the resulting bundle.

To build from an in-progress branch of the pypy repository, check it out
in the submodule like so::

    $> cd ./deps/pypy
    $> git checkout whatever-branch
    $> cd ../../
    $> make


Contributing
------------

If you've fixed a bug or added a new feature, we welcome your contribution
via github's standard pull-request process:

  https://help.github.com/articles/creating-a-pull-request/

Before opening a pull-request, please ensure that:

  * you've run the test suite and it passes successfully.
  * you've added yourself to CONTRIBUTORS.txt, and agree to license your
    contributions under the terms of the project's license.

We'll try to get back to you within a few days at most.  Don't hesitate to
comment in the request if it looks like you've been forgotten.
