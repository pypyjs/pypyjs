
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
  * A "js" builtin module for the resulting interpreter, to allow interaction
    with the host javascript environment:
    `./deps/pypy/pypy/module/js/`.

Along with these wrappers to help working with the resulting interpreter:

  * A wrapper to load up the compiled VM and expose it via a nice javascript
    API: `./src/pypyjs.js`.
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

For an experimental python3 build, do::

    $> make release3

Similar to the default release, the corresponding pypy repository is here::

    $> cd ./deps/pypy3
    $> git checkout whatever-branch
    $> cd ../../
    $> make


Transpiling es6
~~~~~~~~~~~~~~~

PyPy.js is written using es6 and is transpiled to es5 using `babeljs`_.
To run the code though the transpiler you need `gulp`_ and you'll need a few
other node_modules, and nodejs ofcourse (I'm assuming you have those installed,
npm comes with node).

To install the node_modules you need to run `npm install` in the root of the
repository. And you'll need to install gulp globaly like this::

    $> npm install gulp -g

When you run `gulp` in the repository the es6 source in /src is transpiled to
es5 and that's copied to /lib.

.. _babeljs: https://babeljs.io
.. _gulp: https://gulpjs.com


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


Github, Bitbucket, Branches, Merges, etc
----------------------------------------

This project is maintained in a github clone of the PyPy project's mercurial
repository, largely because the original author likes working in git.  This
can make the status of various branches a little confusing, so here's a quick
summary:

  * `master` in github tracks upstream head on https://bitbhucket.org/pypy/pypy
  * `branches/FOO` in github tracks upstream mercurial branch "FOO"
  * `pypyjs` tracks the latest upstream release branch, with additional
    commits to add PyPy.js-specific functionality
  * `pypyjs3` tracks the latest upstream py3k branch, with additional
    commits to add PyPy.js-specific functionality

Like upstream PyPy, this means that the default build is a python2 interpreter,
but you can easily build a python3 interpreter by selecting the appropriate
branch.

The `pypyjs3` branch is a little special, as it contains modifications to the
pypy interpreter (under the "./pypy" directory) but *not* changes to the
compilation toolchain (under the "./rpython" directory).  This is done to
prevent having to maintain those chances in two places.  We build the python3
release by running the compilation toolchain from the `pypyjs` branch on
the interpreter code from the `pypyjs3` branch.  See the Makefile for the
gory details.

