
PyPy.js:  PyPy compiled into JavaScript
=======================================

PyPy.  Compiled into JavaScript.  JIT-compiling to JavaScript at runtime.
Because why not.

This is a very-much-in-flux collection of supporting scripts and infrastructure
for an experimental emscripten/asmjs backend for PyPy, as described here:

    https://www.rfk.id.au/blog/entry/pypy-js-first-steps/

For the history of the project, see `NEWS <NEWS.md>`_.

The actual PyPy backend is maintained as a git submodule pointing to a fork
of a github clone of the upstream PyPy repository:

    https://github.com/rfk/pypy

You can get all the necessary code from within this top-level repository
by accessing it as a git submodule::

    $> git submodule update --init

Building pypyjs requires a 32-bit python environment and the emscripten-enabled
LLVM toolchain.  The recommended way to build is using the pre-built docker
image containing these dependencies::

    $> docker pull rfkelly/pypyjs-build

The Makefile knows how to use this image transparently during build and
test.  You can run various parts of the testsuite like this::

    $> make test-js-module
    $> make test-jit-backend

Do do a full build of the PyPy VM like this::

    $> make

Be prepared, this will take a *long* time.  It will eventually produce the file
`./build/pypy.vm.js` containing the code for the interpreter.  This goes
together with support files in `./lib/` to make a complete distribution.

To get a full release tarball, do::

    $> make release

Take a look in the `./website/js/` directory for an example of how to distribute
and use the resulting bundle.

To build from an in-progress branch of the pypy repository, check it out
in the submodule like so::

    $> cd ./deps/pypy
    $> git checkout whatever-branch
    $> cd ../../
    $> make

If you'd like to hack on PyPyJS, the following background reading will
be helpful:

  * http://pypy.readthedocs.org/en/latest/translation.html
  * http://pypy.readthedocs.org/en/latest/coding-guide.html

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
    API: `./lib/pypy.js`.
  * A script for bundling python modules into an indexed format that can be
    easily loaded into the browser:  `./tools/module_bundler.py`.

