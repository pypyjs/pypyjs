
PyPy.js:  PyPy compiled into JavaScript
=======================================

This is a version of the PyPy python interpreter, compiled into javascript
with emscripten.  It allows you to run a highly-compliant python environment
in pure javascript, either in a browser or in a server-side javascript shell.

Loading the Interpreter
-----------------------

To create a PyPy.js interpreter, you must load the file `lib/pypy.js`.  This
will create the global name `PyPyJS` which can be used to instantiate the
interpreter.  In browser::

    <!-- shim for ES6 `Promise` builtin -->
    <script src="./lib/Promise.min.js" type="text/javascript"></script>
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

TODO: document the options to `PyPyJS` constructor, e.g. how to customize
stdout or the virtualized filesystem.


Invoking the Interpreter
------------------------

There are three methods available for interacting with the interpreter:

* `vm.eval(code)`:  executes python code in the interpreter's global scope.
* `vm.set(name, value)`:  sets a variable in the interpreter's global scope.
* `vm.get(name)`:  copy a variable from the interpreter's global scope.

Only primitive value types can be retrieved from the interpreter via `get`.
This includes python numbers, strings, lists and dicts, but not custom
objects.

TODO: some simple examples.


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
    >>> print keys
    <TODO>
    >>> print list(keys)
    ["a", "b"]
    >>>

Python functions can be passed to javascript as callbacks like so::

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
to the function on the python side.  For example, this might fail because
the lambda can be garbage-collected by python before it is called from
javascript::

    >>> js.globals.setTimeout(lambda: 42, 1000)
    # [one second passes, during which a gc occurs]
    <RuntimeError object at 0x15d648>
    RPython traceback:
      ...
    Fatal RPython error: 
    >>>

This restriction may be relaxed in future, but is unlikely to go away 
entirely due to limitations of hooking into javascript's garbage collector.

TODO: more details on what you can and can't do with js objects

