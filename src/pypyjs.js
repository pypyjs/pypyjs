//
//  pypyjs:  an experimental in-browser python environment.
//

// When transpiled from es6 to es5, this code will get wrapped
// in a function that takes the encosing global scope as argument.
// This might be the 'window' object in a browser, or the 'global'
// object in nodejs.

if (typeof globalScope === 'undefined') {
  globalScope = {};
}

let _dirname;

// Find the directory containing this very file.
// It can be quite difficult depending on execution environment...
if (typeof __dirname === 'undefined') {
  _dirname = './';

  // A little hackery to find the URL of this very file.
  // Throw an error, then parse the stack trace looking for filenames.
  const errlines = (new Error()).stack.split('\n');
  errlines.forEach((line) => {
    const match = /(at Anonymous function \(|at |@)(.+\/)pypyjs.js/.exec(line);
    if (match) {
      _dirname = match[2];
    }
  });
} else {
  _dirname = __dirname;
}

if (_dirname.charAt(_dirname.length - 1) !== '/') {
  _dirname += '/';
}


// Ensure we have references to 'Promise' and 'FunctionPromise'
// constructors, pulling them in from global scope if possible.
let Promise;
let FunctionPromise;

// Ensure we have reference to a 'Promise' constructor.
if (typeof Promise === 'undefined') {
  if (globalScope && typeof globalScope.Promise !== 'undefined') {
    Promise = globalScope.Promise;
  } else if (typeof require === 'function') {
    Promise = require('./Promise.min.js');
  } else if (typeof load === 'function') {
    load(_dirname + 'Promise.min.js');
    if (typeof Promise === 'undefined') {
      if (globalScope && typeof globalScope.Promise !== 'undefined') {
        Promise = globalScope.Promise;
      }
    }
  }
}

if (typeof Promise === 'undefined') {
  throw new Error('Promise object not found');
}

// Ensure we have reference to a 'FunctionPromise' constructor.
if (typeof FunctionPromise === 'undefined') {
  if (globalScope && typeof globalScope.FunctionPromise !== 'undefined') {
    FunctionPromise = globalScope.FunctionPromise;
  } else if (typeof require === 'function') {
    FunctionPromise = require('./FunctionPromise.js');
  } else if (typeof load === 'function') {
    load(_dirname + 'FunctionPromise.js');
    if (typeof FunctionPromise === 'undefined') {
      if (globalScope && typeof globalScope.FunctionPromise !== 'undefined') {
        FunctionPromise = globalScope.FunctionPromise;
      }
    }
  }
}

if (typeof FunctionPromise === 'undefined') {
  throw new Error('FunctionPromise object not found');
}

let fs;
let path;
// Some extra goodies for nodejs.
if (typeof process !== 'undefined') {
  if (Object.prototype.toString.call(process) === '[object process]') {
    fs = require('fs');
    path = require('path');
  }
}

// Create functions for handling default stdio streams.
// These will be shared by all VM instances by default.
//
// We default stdout and stderr to process outputs if available,
// printing/logging functions otherwise, and /dev/null if nothing
// else is available.  Unfortunately there's no good way to read
// synchronously from stdin in javascript, so that's always /dev/null.

const devNull = {
  stdin: function stdin() {
    return null;
  },
  stdout: function stdout() { },
  stderr: function stderr() { }
};

const stdio = {
  stdin: null,
  stdout: null,
  stderr: null
};

stdio.stdin = devNull.stdin;

if (typeof process !== 'undefined') {
  if (typeof process.stdout !== 'undefined') {
    stdio.stdout = function stdout(byte) { process.stdout.write(byte); };
  }

  if (typeof process.stderr !== 'undefined') {
    stdio.stderr = function stderr(byte) { process.stderr.write(byte); };
  }
}

let _print;
let _printErr;
if (typeof window === 'undefined') {
  // print, printErr from v8, spidermonkey
  if (typeof print !== 'undefined') {
    _print = print;
  }

  if (typeof printErr !== 'undefined') {
    _printErr = printErr;
  }
}

if (typeof console !== 'undefined') {
  if (typeof _print === 'undefined') {
    _print = console.log.bind(console);
  }

  if (typeof _printErr === 'undefined') {
    _printErr = console.error.bind(console);
  }
}

if (stdio.stdout === null && typeof _print !== 'undefined') {
  // print()/console.log() will add a newline, so we buffer until we
  // receive one and then let it add it for us.
  const buffer = [];
  stdio.stdout = function stdout(data) {
    for (let i = 0; i < data.length; i++) {
      const byte = data.charAt(i);
      if (byte !== '\n') {
        buffer.push(byte);
      } else {
        _print(buffer.join(''));
        buffer.splice(undefined, buffer.length);
      }
    }
  };
}

if (stdio.stderr === null && typeof _printErr !== 'undefined') {
  // printErr()/console.error() will add a newline, so we buffer until we
  // receive one and then let it add it for us.
  const buffer = [];
  stdio.stderr = function stderr(data) {
    for (let i = 0; i < data.length; i++) {
      const byte = data.charAt(i);
      if (byte !== '\n') {
        buffer.push(byte);
      } else {
        _printErr(buffer.join(''));
        buffer.splice(undefined, buffer.length);
      }
    }
  };
}

if (stdio.stdout === null) {
  stdio.stdout = devNull.stdout;
}

if (stdio.stderr === null) {
  stdio.stderr = devNull.stderr;
}

// Main class representing the PyPy VM.
// This is our primary export and return value.

function pypyjs(opts) {
  const _opts = opts || {};
  this.rootURL = _opts.rootURL;
  this.totalMemory = _opts.totalMemory || 128 * 1024 * 1024;
  this.autoLoadModules = _opts.autoLoadModules || true;
  this._pendingModules = {};
  this._loadedModules = {};
  this._allModules = {};

  // Allow opts to override default IO streams.
  this.stdin = _opts.stdin || stdio.stdin;
  this.stdout = _opts.stdout || stdio.stdout;
  this.stderr = _opts.stderr || stdio.stderr;

  // Default to finding files relative to this very file.
  if (!this.rootURL && !pypyjs.rootURL) {
    pypyjs.rootURL = _dirname;
  }

  if (this.rootURL && this.rootURL.charAt(this.rootURL.length - 1) !== '/') {
    this.rootURL += '/';
  }

  // If we haven't already done so, fetch and load the code for the VM.
  // We do this once and cache the result for re-use, so that we don't
  // have to pay asmjs compilation overhead each time we create the VM.

  if (!pypyjs._vmBuilderPromise) {
    pypyjs._vmBuilderPromise = this.fetch('pypyjs.vm.js').then((xhr) => {
      // Parse the compiled code, hopefully asynchronously.
      // Unfortunately our use of Function constructor here doesn't
      // play very well with nodejs, where things like 'module' and
      // 'require' are not in the global scope.  We have to pass them
      // in explicitly as arguments.
      const funcBody = [

        // This is the compiled code for the VM.
        xhr.responseText,
        '\n',

        // Ensure that some functions are available on the Module,
        // for linking with jitted code.
        'if (!Module._jitInvoke && typeof _jitInvoke !== \'undefined\') {',
        '  Module._jitInvoke = _jitInvoke;',
        '}',

        // Keep some functions that are not exported by default, but
        // which appear in this scope when evaluating the above.
        'Module._emjs_make_handle = _emjs_make_handle;',
        'Module._emjs_free = _emjs_free;',

        // Call dependenciesFulfilled if it won't be done automatically.
        'dependenciesFulfilled=function() { inDependenciesFulfilled(FS); };',
        'if(typeof memoryInitializer==="undefined"||!memoryInitializer||(!ENVIRONMENT_IS_WEB&&!ENVIRONMENT_IS_WORKER))dependenciesFulfilled();',
      ].join('\r\n');
      return new FunctionPromise('Module', 'inDependenciesFulfilled', 'require',
                             'module', '__filename', '_dirname', funcBody);
    });
  }

  // Create a new instance of the compiled VM, bound to local state
  // and a local Module object.
  this._ready = new Promise((resolve, reject) => {
    // Initialize the Module object.
    // We make it available on this object so that we can use
    // its methods to execute code in the VM.
    const Module = {};
    this._module = Module;
    Module.TOTAL_MEMORY = this.totalMemory;

    // We will set up the filesystem manually when we're ready.
    Module.noFSInit = true;
    Module.thisProgram = '/lib/pypyjs/pypyjs.js';
    Module.filePackagePrefixURL = this.rootURL || pypyjs.rootURL;
    Module.memoryInitializerPrefixURL = this.rootURL || pypyjs.rootURL;
    Module.locateFile = function locateFile(name) {
      return (this.rootURL || pypyjs.rootURL) + name;
    };

    // Don't start or stop the program, just set it up.
    // We'll call the API functions ourself.
    Module.noInitialRun = true;
    Module.noExitRuntime = true;

    let stdoutBuffer = [];
    // Route stdin to an overridable method on the object.
    const stdin = () => {
      if (stdoutBuffer.length) {
        this.stdout(stdoutBuffer.join(''));
        stdoutBuffer = [];
      }
      return this.stdin();
    };

    // Route stdout to an overridable method on the object.
    // We buffer the output for efficiency.
    const stdout = (byte) => {
      const char = String.fromCharCode(byte);
      stdoutBuffer.push(char);
      if (char === '\n' || stdoutBuffer.length >= 128) {
        this.stdout(stdoutBuffer.join(''));
        stdoutBuffer = [];
      }
    };

    // Route stderr to an overridable method on the object.
    // We do not buffer stderr.
    const stderr = (byte) => this.stderr(String.fromCharCode(byte));

    // This is where execution will continue after loading
    // the memory initialization data, if any.
    let initializedResolve;
    let initializedReject;
    const initializedP = new Promise(function promise(_resolve, _reject) {
      initializedResolve = _resolve;
      initializedReject = _reject;
    });

    const dependenciesFulfilled = (_fs) => {
      this.FS = _fs;

      // Initialize the filesystem state.
      try {
        this.FS.init(stdin, stdout, stderr);
        Module.FS_createPath('/', 'lib/pypyjs/lib_pypy', true, false);
        // Hackery so the same file will work with py2 and py3.
        // We only ever put our module files into lib_pypy.
        Module.FS_createPath('/', 'lib/pypyjs/lib-python/2.7', true, false);
        Module.FS_createPath('/', 'lib/pypyjs/lib-python/3', true, false);
        initializedResolve();
      } catch (err) {
        initializedReject(err);
      }
    };

    // Begin fetching the metadata for available python modules.
    // With luck these can download while we jank around compiling
    // all of that javascript.
    // XXX TODO: also load memory initializer this way.
    const moduleDataP = this.fetch('modules/index.json');

    pypyjs._vmBuilderPromise.then((vmBuilder) => {
      const args = [
        Module,
        dependenciesFulfilled,
        typeof require === 'undefined' ? undefined : require,
        typeof module === 'undefined' ? undefined : module,
        typeof __filename === 'undefined' ? undefined : __filename,
        typeof _dirname === 'undefined' ? undefined : _dirname
      ];

      // This links the async-compiled module into our Module object.
      vmBuilder.apply(null, args);
      return initializedP;
    }).then(() => {
      // Continue with processing the downloaded module metadata.
      return moduleDataP.then((xhr) => {
        // Store the module index, and load any preload modules.
        const modIndex = JSON.parse(xhr.responseText);
        this._allModules = modIndex.modules;
        if (modIndex.preload) {
          Object.keys(modIndex.preload).forEach((name) => {
            this._writeModuleFile(name, modIndex.preload[name]);
          });
        }

        // It's finally safe to launch the VM.
        Module.run();
        Module._rpython_startup_code();
        let pypy_home = Module.intArrayFromString('/lib/pypyjs/pypyjs.js');
        pypy_home = Module.allocate(pypy_home, 'i8', Module.ALLOC_NORMAL);
        Module._pypy_setup_home(pypy_home, 0);
        Module._free(pypy_home);
        const initCode = `
import js
import traceback
import sys; sys.platform = 'js'
# For python3, pypy does some lazy-initialization stuff
# with stdio streams that isn't triggered when you use
# it as a library instead of an exe.  Fix it up.
def create_stdio(fd, mode, name, errors=None):
  import io
  return io.open(fd, mode, buffering=1, errors=errors, closefd=False)
if not hasattr(sys, 'stdin'):
  sys.stdin = sys.__stdin__ = create_stdio(0, 'r', '<stdin>')
  sys.stdout = sys.__stdout__ = create_stdio(1, 'w', '<stdout>')
  sys.stderr = sys.__stderr = create_stdio(2, 'w', '<stderr>', 'backslashreplace')
# Create a "__main__" module in which we'll execute code.
import types
top_level_scope = {'__name__': '__main__', '__package__': None}
main = types.ModuleType('__main__')
main.__dict__.update(top_level_scope)
sys.modules['__main__'] = main
top_level_scope = main`;

        let code = Module.intArrayFromString(initCode);
        code = Module.allocate(code, 'i8', Module.ALLOC_NORMAL);
        if (!code) {
          throw new pypyjs.Error('Failed to allocate memory');
        }

        const res = Module._pypy_execute_source(code);
        if (res < 0) {
          throw new pypyjs.Error('Failed to execute python code');
        }

        Module._free(code);
      });
    })
    .then(resolve, reject);
  });
}

// A simple file-fetching wrapper around XMLHttpRequest,
// that treats paths as relative to the pypyjs.js root url.
//
pypyjs.prototype.fetch = function fetch(relpath, responseType) {
  const rootURL = this.rootURL || pypyjs.rootURL;

  // For the web, use XMLHttpRequest.
  if (typeof XMLHttpRequest !== 'undefined') {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.onload = function onload() {
        if (xhr.status >= 400) {
          reject(xhr);
        } else {
          resolve(xhr);
        }
      };

      xhr.open('GET', rootURL + relpath, true);
      xhr.responseType = responseType || 'text';
      xhr.send(null);
    });
  }

  // For nodejs, use fs.readFile.
  if (typeof fs !== 'undefined' && typeof fs.readFile !== 'undefined') {
    return new Promise((resolve, reject) => {
      fs.readFile(path.join(rootURL, relpath), (err, data) => {
        if (err) return reject(err);
        resolve({ responseText: data.toString() });
      });
    });
  }

  // For spidermonkey, use snarf (which has a binary read mode).
  if (typeof snarf !== 'undefined') {
    return new Promise((resolve) => {
      const data = snarf(rootURL + relpath);
      resolve({ responseText: data });
    });
  }

  // For d8, use read() and readbuffer().
  if (typeof read !== 'undefined' && typeof readbuffer !== 'undefined') {
    return new Promise((resolve) => {
      const data = read(rootURL + relpath);
      resolve({ responseText: data });
    });
  }

  return new Promise((resolve, reject) => {
    reject('unable to fetch files');
  });
};

function _escape(value) {
  return value.replace(/\\/g, '\\\\').replace(/'/g, '\\\'');
}

// Method to execute python source directly in the VM.
//
// This is the basic way to push code into the pypyjs VM.
// Calling code should not use it directly; rather we use it
// as a primitive to build up a nicer execution API.
//
pypyjs.prototype._execute_source = function _execute_source(code) {
  const Module = this._module;
  let code_ptr;

  return new Promise(function promise(resolve, reject) {
    const _code = `try:
  ${code.trim()}
except Exception:
  typ, val, tb = sys.exc_info()
  err_name = getattr(typ, '__name__', str(typ))
  err_msg = str(val)
  err_trace = traceback.format_exception(typ, val, tb)
  err_trace = err_trace[:1] + err_trace[2:]
  err_trace = ''.join(err_trace)
  js.globals['pypyjs']._lastErrorName = err_name
  js.globals['pypyjs']._lastErrorMessage = err_msg
  js.globals['pypyjs']._lastErrorTrace = err_trace
`;

    const code_chars = Module.intArrayFromString(_code);
    code_ptr = Module.allocate(code_chars, 'i8', Module.ALLOC_NORMAL);
    if (!code_ptr) {
      throw new pypyjs.Error('Failed to allocate memory');
    }

    const res = Module._pypy_execute_source(code_ptr);
    if (res < 0) {
      throw new pypyjs.Error('Error executing python code');
    }

    Module._free(code_ptr);

    // XXX TODO: races/re-entrancy on _lastError?
    if (pypyjs._lastErrorName) {
      const err = new pypyjs.Error(
        pypyjs._lastErrorName,
        pypyjs._lastErrorMessage,
        pypyjs._lastErrorTrace
      );
      pypyjs._lastErrorName = null;
      pypyjs._lastErrorMessage = null;
      pypyjs._lastErrorTrace = null;
      reject(err);
    }

    resolve(null);
  });
};

// Method to determine when the interpreter is ready.
//
// This method returns a promise that will resolve once the interpreter
// is ready for use.
//
pypyjs.prototype.ready = function ready() {
  return this._ready;
};

// Method to execute some python code.
//
// This passes the given python code to the VM for execution.
// It's fairly directly analogous to the 'exec" statement in python.
// It is not possible to directly access the result of the code, if any.
// Rather you should store it into a variable and then use the get() method.
//
pypyjs.prototype.exec = function exec(code, options) {
  return this._ready.then(() => {
    let promise = Promise.resolve();

    // Find any "import" statements in the code,
    // and ensure the modules are ready for loading.
    if (this.autoLoadModules) {
      promise = promise.then(() => {
        return this.findImportedNames(code);
      })
      .then((imports) => {
        return this.loadModuleData.apply(this, imports);
      });
    }

    let _code;

    if (options && options.file) {
      try {
        this.Module.FS.unlink(options.file);
      } catch (e) {
        if (e.errno !== 2) {
          console.error(e);
        }
      }
      this.Module.FS_createDataFile(options.file, '', code, true, false, true);
      // Now we can execute the code in custom top-level scope.
      _code = `top_level_scope['__file__'] = '${options.file}'; execfile('${options.file}', top_level_scope.__dict__)`;
    } else {
      _code = `exec('''${_escape(code)}''', top_level_scope.__dict__)`;
    }

    return promise.then(() => this._execute_source(_code));
  });
};

// Method to evaluate an expression.
//
// This method evaluates an expression and returns its value (assuming the
// value can be translated into javascript).  It's fairly directly analogous
// to the "eval" function in python.
//
// For backwards-compatibility reasons, it will also evaluate statements.
// This behaviour is deprecated and will be removed in a future release.
//
pypyjs.prototype.eval = function evaluate(expr) {
  return this._ready.then(() => {
    // First try to execute it as an expression.
    const code = `r = eval('${_escape(expr)}', top_level_scope.__dict__)`;
    return this._execute_source(code);
  }).then(() => this.get('r', true), (err) => {
    if (err && err.name && err.name !== 'SyntaxError') {
      throw err;
    }

    // If that failed, try again via exec().
    if (typeof console !== 'undefined') {
      console.warn('Calling pypyjs.eval() with statements is deprecated.');
      console.warn('Use eval() for expressions, exec() for statements.');
    }

    return this.exec(expr);
  });
};

// Method to evaluate some python code from a file..
//
// This fetches the named file and passes it to the VM for execution.
//
pypyjs.prototype.execfile = function execfile(filename) {
  return this.fetch(filename).then((xhr) => {
    const code = xhr.responseText;
    return this.exec(code, { file: `/lib/pypyjs/lib_pypy/${filename}` });
  });
};

// Method to read a python variable.
//
// This tries to convert the value in the named python variable into an
// equivalent javascript value and returns it.  It will fail if the variable
// does not exist or contains a value that cannot be converted.
//
pypyjs._resultsID = 0;
pypyjs._resultsMap = {};
pypyjs.prototype.get = function get(name, _fromGlobals) {
  const resid = `${(pypyjs._resultsID++)}`;
  let reference;
  // We can read from global scope for internal use; don't do this from calling code!
  if (_fromGlobals) {
    reference = `globals()['${escape(name)}']`;
  } else {
    reference = `top_level_scope.${_escape(name)}`;
  }

  return this._ready.then(() => {
    const code = `
  try:
    _pypyjs_getting = ${reference}
  except (KeyError, AttributeError):
    _pypyjs_getting = js.undefined
  js.globals['pypyjs']._resultsMap['${resid}'] = js.convert(_pypyjs_getting)
  del _pypyjs_getting`;
    return this._execute_source(code);
  }).then(() => {
    const res = pypyjs._resultsMap[resid];
    delete pypyjs._resultsMap[resid];
    return res;
  });
};

// Method to set a python variable to a javascript value.
//
// This generates a handle to the given object, and arranges for the named
// python variable to reference it via that handle.
//
pypyjs.prototype.set = function set(name, value) {
  return this._ready.then(() => {
    const Module = this._module;
    const handle = Module._emjs_make_handle(value);
    const _name = _escape(name);
    const code = `top_level_scope.${_name} = js.Value(${handle})`;
    return this._execute_source(code);
  });
};

// Method to run an interactive REPL.
//
// This method takes takes callback function implementing the user
// input prompt, and runs a REPL loop using it.  The prompt function
// may either return the input as a string, or a promise resolving to
// the input as a string.  If not specified, we read from stdin (which
// works fine in e.g. nodejs, but is almost certainly not what you want
// in the browser, because it's blocking).
//
pypyjs.prototype.repl = function repl(prmpt) {
  let _prmpt;
  if (!prmpt) {
    // By default we read from the provided stdin function, but unfortunately
    // it defaults to a closed file.
    let buffer = '';
    _prmpt = (ps1) => {
      let input;
      this.stdout(ps1);
      let char = this.stdin();
      while (char) {
        const idx = char.indexOf('\n');
        if (idx >= 0) {
          input = buffer + char.substr(0, idx + 1);
          buffer = char.substr(idx + 1);
          return input;
        }
        buffer += char;
        char = this.stdin();
      }
      input = buffer;
      buffer = '';
      return input;
    };
    // For nodejs, we can do an async prompt atop process.stdin,
    // unless we're using a custom stdin function.
    let useProcessStdin = true;
    if (typeof process === 'undefined') {
      useProcessStdin = false;
    } else if (typeof process.stdin === 'undefined') {
      useProcessStdin = false;
    } else {
      if (this.stdin !== devNull.stdin) {
        if (this.stdin !== pypyjs._defaultStdin) {
          useProcessStdin = false;
        } else if (pypyjs.stdin !== devNull.stdin) {
          useProcessStdin = false;
        }
      }
    }
    if (useProcessStdin) {
      _prmpt = (ps1) => {
        return new Promise((resolve) => {
          this.stdout(ps1);
          const slurp = function slurp() {
            process.stdin.once('readable', () => {
              let chunk = process.stdin.read();
              if (chunk === null) {
                slurp();
              } else {
                chunk = chunk.toString();
                const idx = chunk.indexOf('\n');
                if (idx < 0) {
                  buffer += chunk;
                  slurp();
                } else {
                  resolve(buffer + chunk.substr(0, idx + 1));
                  buffer = chunk.substr(idx + 1);
                }
              }
            });
          };

          slurp();
        });
      };
    }
  }

  // Set up an InteractiveConsole instance,
  // then loop forever via recursive promises.
  return this._ready
    .then(() => this.loadModuleData('code'))
    .then(() => this._execute_source('import code'))
    .then(() => this._execute_source('c = code.InteractiveConsole(top_level_scope.__dict__)'))
    .then(() => this._repl_loop(_prmpt, '>>> '));
};

pypyjs.prototype._repl_loop = function _repl_loop(prmpt, ps1) {
  // Prompt for input, which may happen via async promise.
  return Promise.resolve()
    .then(() => prmpt.call(this, ps1))
    .then((input) => {
      // Push it into the InteractiveConsole, a line at a time.
      let p = Promise.resolve();
      input.split('\n').forEach((line) => {
        // Find any "import" statements in the code,
        // and ensure the modules are ready for loading.
        if (this.autoLoadModules) {
          p = p.then(() => this.findImportedNames(line))
               .then((imports) => this.loadModuleData.apply(this, imports));
        }

        const code = `r = c.push('${_escape(line)}')`;
        p = p.then(() => this._execute_source(code));
      });
      return p;
    }).then(() => this.get('r', true))
      .then((r) => {
        // If r == 1, we're in a multi-line definition.
        // Adjust the prompt accordingly.
        if (r) {
          return this._repl_loop(prmpt, '... ');
        }
        return this._repl_loop(prmpt, '>>> ');
      });
};

// Method to look for "import" statements in a code string.
// Returns a promise that will resolve to a list of imported module names.
//
// XXX TODO: this is far from complete and should not be done with a regex.
// Perhaps we can call into python's "ast" module for this parsing?
//
const importStatementRE = /(from\s+([a-zA-Z0-9_\.]+)\s+)?import\s+\(?\s*([a-zA-Z0-9_\.\*]+(\s+as\s+[a-zA-Z0-9_]+)?[ \t]*,?[ \t]*)+[ \t]*\)?/g;
pypyjs.prototype.findImportedNames = function findImportedNames(code) {
  const imports = [];
  let match;
  importStatementRE.lastIndex = 0;

  const pushImport = (relmod) => (submod) => imports.push(relmod + submod.split(/\s*as\s*/)[0]);

  while ((match = importStatementRE.exec(code)) !== null) {
    let relmod = match[2];
    if (relmod) {
      relmod = relmod + '.';
    } else {
      relmod = '';
    }

    let submods = match[0].split('import')[1];
    while (submods && /[\s(]/.test(submods.charAt(0))) {
      submods = submods.substr(1);
    }

    while (submods && /[\s)]/.test(submods.charAt(submods.length - 1))) {
      submods = submods.substr(0, submods.length - 1);
    }

    submods = submods.split(/\s*,\s*/);
    submods.forEach(pushImport(relmod));
  }
  return Promise.resolve(imports);
};

// Method to load the contents of a python module, along with
// any dependencies.  This populates the relevant paths within
// the VMs simulated filesystem so that is can find and import
// the specified module.
//
pypyjs.prototype.loadModuleData = function loadModuleData(/* names */) {
  // Each argument is a name that we want to import.
  // We must find the longest prefix that is an available module
  // and load it along with all its dependencies.
  const modules = Array.prototype.slice.call(arguments);
  return this._ready.then(() => {
    const toLoad = {};
    NEXTNAME: for (let i = 0; i < modules.length; i++) {
      let name = modules[i];

      // Find the nearest containing module for the given name.
      // Note that it may not match a module at all, in which case we ignore it.
      while (true) {
        if (this._allModules[name]) {
          break;
        }

        name = name.substr(0, name.lastIndexOf('.'));
        if (!name) continue NEXTNAME;
      }

      this._findModuleDeps(name, toLoad);
    }

    return Promise.all(Object.keys(toLoad).map((name) => this._loadModuleData(name)));
  });
};

pypyjs.prototype._findModuleDeps = function _findModuleDeps(name, seen) {
  const _seen = seen ? seen : {};
  const deps = [];

  // If we don't know about this module, ignore it.
  if (!this._allModules[name]) {
    return _seen;
  }

  // Depend on any explicitly-named imports.
  const imports = this._allModules[name].imports;
  if (imports) {
    for (let i = 0; i < imports.length; i++) {
      deps.push(imports[i]);
    }
  }

  // Depend on the __init__.py for packages.
  if (this._allModules[name].dir) {
    deps.push(name + '.__init__');
  }

  // Include the parent package, if any.
  const idx = name.lastIndexOf('.');
  if (idx !== -1) {
    deps.push(name.substr(0, idx));
  }

  // Recurse for any previously-unseen dependencies.
  _seen[name] = true;
  for (let i = 0; i < deps.length; i++) {
    if (!_seen[deps[i]]) {
      this._findModuleDeps(deps[i], _seen);
    }
  }

  return _seen;
};

pypyjs.prototype._loadModuleData = function _loadModuleData(name) {
  // If we've already loaded this module, we're done.
  if (this._loadedModules[name]) {
    return Promise.resolve();
  }

  // If we're already in the process of loading it, use the existing promise.
  if (this._pendingModules[name]) {
    return this._pendingModules[name];
  }

  // If it's a package directory, there's not actually anything to do.
  if (this._allModules[name].dir) {
    return Promise.resolve();
  }

  // We need to fetch the module file and write it out.
  const modfile = this._allModules[name].file;
  const promise = this.fetch(`modules/${modfile}`)
  .then((xhr) => {
    const contents = xhr.responseText;
    this._writeModuleFile(name, contents);
    delete this._pendingModules[name];
  });
  this._pendingModules[name] = promise;
  return promise;
};

pypyjs.prototype._writeModuleFile = function _writeModuleFile(name, data) {
  const Module = this._module;
  const file = this._allModules[name].file;

  // Create the containing directory first.
  const dir = file.split('/').slice(0, -1).join('/');
  try {
    Module.FS_createPath('/lib/pypyjs/lib_pypy', dir, true, false);
  } catch (err) {
    console.error(err);
  }

  // Now we can safely create the file.
  // To ensure proper utf8 encoding we need to write it as bytes.
  // XXX TODO: find a way to avoid this overhead.
  const fullpath = '/lib/pypyjs/lib_pypy/' + file;
  const len = Module.lengthBytesUTF8(data);
  const arr = new Uint8Array(len);
  Module.stringToUTF8Array(data, arr, 0, len + 1);
  try {
    this.FS.unlink(fullpath);
  } catch (err) {
    if (err.errno !== 2) {
      console.error(err);
    }
  }
  Module.FS_createDataFile(fullpath, '', arr, true, false, true);
  this._loadedModules[name] = true;
};

// An error class for reporting python exceptions back to calling code.
// XXX TODO: this could be a lot more user-friendly than a opaque error...

pypyjs.Error = function pypyjsError(name, message, trace) {
  let message_ = message;
  let name_ = name;
  if (name_ && typeof message_ === 'undefined') {
    message_ = name_;
    name_ = '';
  }

  this.name = name_ || 'pypyjs.Error';
  this.message = message_ || 'pypyjs Unknown Error';
  this.trace = trace || '';
};

pypyjs.Error.prototype = new Error();
pypyjs.Error.prototype.constructor = pypyjs.Error;

// XXX TODO: expose the filesystem for manipulation by calling code.

// Add convenience methods directly on the 'pypyjs' function, that
// will invoke corresponding methods on a default VM instance.
// This makes it look like 'pypyjs' is a singleton VM instance.

pypyjs.stdin = stdio.stdin;
pypyjs.stdout = stdio.stdout;
pypyjs.stderr = stdio.stderr;

pypyjs._defaultVM = null;
pypyjs._defaultStdin = function defaultStdin() { return pypyjs.stdin(...arguments); };
pypyjs._defaultStdout = function defaultStdout() { return pypyjs.stdout(...arguments); };
pypyjs._defaultStderr = function defaultStderr() { return pypyjs.stderr(...arguments); };

const PUBLIC_NAMES = ['ready', 'exec', 'eval', 'execfile', 'get', 'set',
                      'repl', 'loadModuleData'];

PUBLIC_NAMES.forEach((name) => {
  pypyjs[name] = function anon() {
    if (!pypyjs._defaultVM) {
      pypyjs._defaultVM = new pypyjs({
        stdin: pypyjs._defaultStdin,
        stdout: pypyjs._defaultStdout,
        stderr: pypyjs._defaultStderr
      });
    }
    return pypyjs._defaultVM[name].apply(pypyjs._defaultVM, arguments);
  };
});

// For nodejs, run a repl when invoked directly from the command-line.
if (typeof require !== 'undefined' && typeof module !== 'undefined') {
  if (require.main === module) {
    pypyjs.repl().catch((err) => {
      console.log(err);
    });
  }
}

if (typeof globalScope.pypyjs === 'undefined') {
  globalScope.pypyjs = pypyjs;
}

if (typeof module !== 'undefined') {
  if (typeof module.exports !== 'undefined') {
    module.exports = pypyjs;
  }
}
