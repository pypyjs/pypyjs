
PyPy.js:  PyPy compiled into JavaScript
=======================================

This is a version of the PyPy python interpreter, compiled into javascript
with emscripten.  It allows you to run a highly-compliant python environment
in pure javascript, either in a browser or in a server-side javascript shell.

Using the Interpreter
---------------------

To use the PyPy.js interpreter, you must load the file `lib/pypyjs.js`.  This
will create the global name `pypyjs` which represents the interpreter.
In the browser::

    <!-- shim for ES6 `Promise` builtin -->
    <script src="./lib/Promise.min.js" type="text/javascript"></script>
    <!-- shim for off-main-thread function compilation -->
    <script src="./lib/FunctionPromise.js" type="text/javascript"></script>
    <script src="./lib/pypyjs.js" type="text/javascript"></script>
    <script type="text/javascript">
      pypyjs.ready().then(function() {
        // this callback is fired when the interpreter is ready for use.
      })
    </script>

In nodejs or similar environments::

    const pypyjs = require("./lib/pypyjs.js");
    pypyjs.ready().then(function() {
      // this callback is fired when the interpreter is ready for use.
    })

The interpreter API is promise-driven, and loads and initializes its resources
asynchronously.  The `ready()` method returns a promise that will be fulfilled
when it is ready for use.

There are three core methods available for interacting with the interpreter:

* `exec(code)`:  executes python code in the interpreter's global scope.
* `set(name, value)`:  sets a variable in the interpreter's global scope.
* `get(name)`:  copy a variable from the interpreter's global scope.

Only primitive value types can be retrieved from the interpreter via `get()`.
This includes python numbers, strings, lists and dicts, but not custom
objects.

The following example evaluates a simple arithmetic expression via Python::

    function pyDouble(x) {
      return pypyjs.ready().then(function() {
        return pypyjs.set('x', x)  // copes the value of 'x' into python
      }).then(function() {
        return pypyjs.exec('x = x * 2');  // doubles the value in 'x' in python
      }).then(function() {
        return pypyjs.get('x')  // copies the value in 'x' out to javascript
      });
    }

    pyDouble(12).then(function(result) {
      console.log(result);  // prints '24'
    });


There is also an `eval()` function that evaluates expessions in the global
scope, similar to python's `eval()`::

    pypyjs.set('x', 7).then(function() {
      return pypyjs.eval('x * 3');  // evaluates and copies result to javascript
    }).then(function(x) {
      console.log(x);  // prints '21'
    });


If you have a python code file to execute, the `execfile()` helper method will
fetch it and pass it to the interpreter for execution::

    pypyjs.execfile("/path/to/some/file.py");


If you'd like to simulate an interactive python console, the helper method
`repl()` can be used to enter an interactive loop.  It takes a callback to
use as the input prompt, which it will call repeatedly to interact with the
user in a loop.  Here's an example using the jqConsole widget for input and
output::

    // Initialize the widget.
    var terminal = $('#terminal').jqconsole('', '>>> ');

    // Hook up output streams to write to the console.
    pypyjs.stdout = pypyjs.stderr = function(data) {
      terminal.Write(data, 'jqconsole-output');
    }

    // Interact by taking input from the console prompt.
    pypyjs.repl(function(ps1) {

      // The argument is ">>> " or "... " depending on REPL state.
      jqconsole.SetPromptLabel(ps1);

      // Return a promise if prompting for input asynchronously.
      return new Promise(function(resolve, reject) {
        jqconsole.Prompt(true, function (input) {
          resolve(input);
        });
      });
    });



Importing Python Modules
------------------------

The PyPy.js interpreter uses a virtualized in-memory filesystem, which makes
its import system a little fragile.  The source code for python modules must
be loaded into the virtual filesystem before they can be imported.

To make imports work as transparently as possible, PyPy.js ships with a bundled
copy of the Python standard library in `./lib/modules`, and includes an index
of all available modules and what they import in `./lib/modules/index.json`.
When you execute some python source code containing import statements, like
this::

    pypyjs.exec("import json; print json.dumps({'hello': 'world'})")

The PyPy.js interpreter shell will do the following:

  * Scan the python code for import statements, and build up a list
    of all module names that it imports.
  * Find the entries for those modules in `./lib/modules/index.json` and
    fetch the corresponding source files.
  * Write the source files into the virtualized filesystem of the
    interpreter.
  * Submit the code to the interpreter for execution.

This will usually work transparently, unless your code does any "hidden"
imports that cannot be easily detected by scanning the code.  For example,
the following would defeat the import system::

    pypyjs.exec("json = __import__('json')")  // fails with an ImportError

To work around this limitation, you can force loading of a particular module
like so::

    pypyjs.loadModuleData("json").then(function() {
      return pypyjs.exec("json = __import__('json')")  // works fine
    });

To add additional python modules to the distribution, use the script
`./tools/module_bundler.py` that comes with the release tarball.  It can
be used to add modules to the bundle::

    python ./tools/module_bundler.py add ./lib/modules custom.py
    python ./tools/module_bundler.py add ./lib/modules package_dir/

To remove unwanted modules from the bundle::

    python ./tools/module_bundler.py remove ./lib/modules shutil unittest

And to indicate that some modules should be eagerly loaded at interpreter
startup::

    python ./tools/module_bundler.py preload ./lib/modules antigravity


Interacting with the Host Environment
-------------------------------------

PyPy.js provides a `js` module that can be used to interact with the host
javascript environment.  As a simple example, it's possible to execute code
strings in the global javascript scope::

    >>> import js
    >>> js.eval("alert('hello world')")
    # [the browser displays "hello world"]
    >>>

Javascript objects are exposed to python via opaque wrappers, using python's
various magic double-underscore methods to appear more-or-less like native
python objects.  For example, it's possible to call the host `Math.log`
function as follows::

    >>> math = js.globals.Math
    >>> math.log(2)
    <js.Number 0.693147>
    >>>

Most primitive python types can be transparently copied between the PyPy.js
interpreter and the host javascript environment.  This includes numbers,
strings, lists and dicts, but not custom objects::

    >>> keys = js.globals.Object.keys({"a": 1, "b": 2})
    >>> print repr(keys)
    <js.Array handle=32>
    >>> print keys
    a,b
    >>> print list(keys[i] for i in keys)
    [<js.String 'a'>, <js.String 'b'>]
    >>>

Python functions can be passed to javascript as synchronous callbacks like
so::

    >>> def print_item(key, value, ctx):
    ...     print key, "=>", value
    ... 
    >>> keys.forEach(print_item)
    a => 0
    b => 1
    <js.Undefined>
    >>> 

Note that there is currently no integration between the garbage collector
in PyPy.js and the one in javascript.  This makes *asynchronous* callbacks a
little tricky.  You must manually keep references alive on the python side
for as long as they're held by javascript.

For example, the following will fail because the lambda is garbage-collected
by python before it gets called by javascript::

    >>> js.globals.setTimeout(lambda: sys.stdout.write('hello\n'), 5000)
    <js.Number 2134.000000>
    >>> gc.collect()
    0
    >>> 
    <RuntimeError object at 0x15d908>
    RPython traceback:
      ...
    >>>

In general, you should use module-level functions for asynchronous callbacks,
and should wrap them with the `js.Function()` constructor to create a stable
mapping between the javascript and python objects.  For example::

    >>> @js.Function
    >>> def hello():
    ...   print "hello"
    ... 
    >>> js.globals.setTimeout(hello, 1000)
    <js.Number 872.000000>
    # [one second passes]
    hello
    >>> 

Some of these restrictions may be relaxed in future, but they're unlikely to
go away entirely due to javascript's limited facilities for introspecting the
garbage collector.


Customizing the Interpreter
---------------------------

You can customize the behaviour of the interpreter by creating a new instance
of the `pypyjs` object, and passing an options object to the constructor.
Like this::

    var vm = new pypyjs({
      totalMemory:  256 * 1024 * 1024,
      stdout: function(data) {
        $('#output').innerHTML += data
      },
    });

The new instance will be a completely independent interpreter, on which you
can call all of the methods outlined above::

    vm.ready().then(function() {
      return vm.set('x', 42)
    }).then(function() {
      return vm.exec('x = x * 2')
    }).then(function() {
      return vm.get('x')
    }).then(function(x) {
      console.log(x);  // prints '84'
    });


It is safe to create multiple `pypyjs` interpreter objects inside a single
javascript interpreter, and they will be completely isolated from each other.

The available options are:

    * totalMemory:  the amount of heap memory to allocate for the interpreter,
                    in bytes
    * stdin:  function to simulate standard input; should return input chars
              when called.
    * stdout:  function to simulate standard output; will be called with
               output chars.
    * stderr:  function to simulate standard error; will be called with error
               output chars.
    * autoLoadModules:  boolean, whether to automatically load module source
                        files for import statements (see below).


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
