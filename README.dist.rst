
PyPy.js:  PyPy compiled into JavaScript
=======================================

This is a version of the PyPy python interpreter, compiled into javascript
with emscripten.  It allows you to run a highly-compliant python environment
in pure javascript, either in a browser or in a server-side javascript shell.

Loading the Interpreter
-----------------------

To create a PyPy.js interpreter, you must load the file `lib/pypy.js`.  This
will create the global name `PyPyJS` which can be used to instantiate the
interpreter.  In the browser::

    <!-- shim for ES6 `Promise` builtin -->
    <script src="./lib/Promise.min.js" type="text/javascript"></script>
    <script src="./lib/FunctionPromise.js" type="text/javascript"></script>
    <script src="./lib/pypy.js" type="text/javascript"></script>
    <script type="text/javascript">
      var vm = new PyPyJS();
      vm.ready.then(function() {
        // this callback is fired when the interpreter is ready for use.
      })
    </script>

In nodejs or similar environments::

    const PyPyJS = require("./lib/pypy.js");
    var vm = new PyPyJS();
    vm.ready.then(function() {
      // this callback is fired when the interpreter is ready for use.
    })

The interpreter API is promise-driven, and loads and initializes its resources
asynchronously.  You must wait for its `ready` promise to be fulfilled before
attempting to interact with the interpreter.

It is safe to create multiple `PyPyJS` interpreter objects inside a single
javascript interpreter.  They will be completely isolated from each other.

You can customize the behaviour of the interpreter by passing an options
object to the `PyPyJS` constructor, like this::

    var vm = new PyPyJS({
      totalMemory:  256 * 1024 * 1024,
      stdout: function(data) {
        $('#output').innerHTML += data
      },
    });

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


Invoking the Interpreter
------------------------

There are three core methods available for interacting with the interpreter:

* `vm.eval(code)`:  executes python code in the interpreter's global scope.
* `vm.set(name, value)`:  sets a variable in the interpreter's global scope.
* `vm.get(name)`:  copy a variable from the interpreter's global scope.

Only primitive value types can be retrieved from the interpreter via `get`.
This includes python numbers, strings, lists and dicts, but not custom
objects.

The following example evaluates a simple arithmetic expression via Python::

    function pyDouble(x) {
      vm.set('x', x).then(function() {
        return vm.eval('x = x * 2');
      }).then(function() {
        return vm.get('x')
      });
    }

    pyDouble(12).then(function(result) {
      console.log(result);  // prints '24'
    });

If you have a python code file to execute, the `execfile` helper method will
fetch it and pass it to the interpreter for execution::

    vm.execfile("/path/to/some/file.py");




Using Python Modules
--------------------

The PyPy.js interpreter uses a virtualized in-memory filesystem, which makes
its import system a little fragile.  The source code for python modules must
be loaded into the virtual filesystem before they can be imported.

To make imports work as transparently as possible, PyPy.js ships with a bundled
copy of the Python standard library in `./lib/modules`, and includes an index
of all available modules and what they import in `./lib/modules/index.json`.
When you execute some python source code containing import statements, like
this::

    vm.eval("import json; print json.dumps({'hello': 'world'})")

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

    vm.eval("json = __import__('json')")  // fails with an ImportError

To work around this limitation, you can force loading of a particular module
like so::

    vm.loadModuleData("json").then(function() {
      return vm.eval("json = __import__('json')")  // works fine
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
    >>> print list(keys)
    ["a", "b"]
    >>>

Python functions can be passed to javascript as synchronous callbacks like
so::

    >>> def print_item(item):
    ...   print item
    ...
    >>> # TODO: check this
    >>> js.globals.

    >>> def hello():
    ...   print "hello"
    ... 
    >>> js.globals.setTimeout(hello, 1000)
    <js.Number 872.000000>
    # [one second passes]
    hello
    >>> 

However, note that there is currently no integration between the garbage
collector in PyPy.js and the one in javascript.  You *must* hold a reference
to the function on the python side.  For example, this could fail if the
lambda is garbage-collected by python before it is called from javascript::

    >>> js.globals.setTimeout(lambda: 42, 1000)
    # [one second passes, during which a gc occurs]
    <RuntimeError object at 0x15d648>
    RPython traceback:
      ...
    Fatal RPython error: 
    >>>

This restriction may be relaxed in future, but is unlikely to go away 
entirely due to limitations of hooking into javascript's garbage collector.

