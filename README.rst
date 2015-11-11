
PyPy.js:  PyPy compiled into JavaScript
=======================================

PyPy.  Compiled into JavaScript.  JIT-compiling to JavaScript at runtime.
Because why not.

This is a very-much-in-flux collection of supporting scripts and infrastructure
for an experimental emscripten/asmjs backend for PyPy.  You can read more about
the project (and try it out live!) here:

    http://pypyjs.org/

If you just want to use a pre-compiled PyPy.js interpreter, please download
a release bundle from the above website and follow the instructions in the
included `README <README.dist.rst>`_.

If you're like to work on the PyPy.js code itself, please see the details
in `CONTRIBUTING.rst <CONTRIBUTING.rst>`_.  All code is available under the
`MIT License <LICENSE.txt>`_.

For the history of the project, see `NEWS <NEWS.md>`_.


Repository Overview
~~~~~~~~~~~~~~~~~~~

+-------------------------+-------------------------------------------------------------------------------------+
| `pypyjs`_               | Main repository to built a PyPy.js release                                          |
+-------------------------+-------------------------------------------------------------------------------------+
| `pypy`_                 | Fork of PyPy with support for compiling to javascript                               |
+-------------------------+-------------------------------------------------------------------------------------+
| `pypyjs-release`_       | Latest release build of PyPy.js, as a handy git submodule                           |
+-------------------------+-------------------------------------------------------------------------------------+
| `pypyjs-release-nojit`_ | Latest release build of PyPy.js, without a JIT                                      |
+-------------------------+-------------------------------------------------------------------------------------+
| `pypyjs-examples`_      | Examples/snippets usage of `pypyjs-release`_ and `pypyjs-release-nojit`_            |
+-------------------------+-------------------------------------------------------------------------------------+
| `pypyjs.github.io`_     | source for `pypyjs.org`_ website use `pypyjs-release`_ and `pypyjs-release-nojit`_  |
+-------------------------+-------------------------------------------------------------------------------------+

.. _pypyjs: https://github.com/pypyjs/pypyjs
.. _pypy: https://github.com/pypyjs/pypy
.. _pypyjs-release: https://github.com/pypyjs/pypyjs-release
.. _pypyjs-release-nojit: https://github.com/pypyjs/pypyjs-release-nojit
.. _pypyjs-examples: https://github.com/pypyjs/pypyjs-examples
.. _pypyjs.github.io: https://github.com/pypyjs/pypyjs.github.io
.. _pypyjs.org: https://pypyjs.org
