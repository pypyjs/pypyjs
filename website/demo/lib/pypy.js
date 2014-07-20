


function PyPyJS(opts) {

  // Default stdin to a closed file.
  // Calling code may override this to handle stdin.
  this.stdin = function() {
    return null;
  }

  // Default stdout and stderr to /dev/null.
  // Calling code may override these to handle output.
  this.stdout = this.stderr = function(x) { }

};


// A simple file-fetching wrapper around XMLHttpRequest,
// that treats paths as relative to the pypy.js root url..
//
PyPyJS.prototype.fetch = function fetch(relpath, cb) {
  if (!this.fetch.rootURL) {
    this.fetch.rootURL = "./";
    // A little hackery to find the URL of this very file.
    // Throw an error, then parse the stack trace looking for filenames.
    var errlines = (new Error()).stack.split("\n");
    SEARCHLOOP: for (var i = 0; i < errlines.length; i++) {
      var endpos = errlines[i].lastIndexOf("pypy.js");
      if (endpos !== -1) {
        var starts = ["@", "at "];
        for (j = 0; j < starts.length; j++) {
          var startpos = errlines[i].indexOf(starts[j]);
          if (startpos !== -1 && startpos < endpos) {
            startpos += starts[j].length;
            this.fetch.rootURL =  errlines[i].substring(startpos, endpos);
            break SEARCHLOOP;
          }
        }
      }
    }
  }
  var xhr = new XMLHttpRequest();
  xhr.onload = function() {
    if (xhr.status >= 400) {
      cb(xhr)
    } else {
      return cb(null, xhr);
    }
  };
  xhr.open('GET', this.fetch.rootURL + relpath, true);
  xhr.send(null);
};


// A wrapper to load and initialize the emscripten-compiled VM module.
// This does a bit of hackery on the 'Module' object to leave the VM
// in an initialized-but-idle state, ready to receive code.
//
PyPyJS.prototype.initialize = function initialize(cb) {

  // Fetch the emscripten-compiled asmjs code.
  // We will need to eval() this in a scope with a custom 'Module' var.
  console.log("fetching asmjs code...");
  this.fetch("pypy.vm.js", (function(err, xhr) {

    if (err) return cb(err);

    var moduleCode = xhr.responseText;
    var Module = {};

    // XXX TODO: take memory size as an initialization option.
    // XXX TODO: maybe even take a pre-allocated buffer?
    Module.TOTAL_MEMORY = 256 * 1024 * 1024;

    // We will set up the filesystem manually when we're ready.
    Module.noFSInit = true;
    Module.thisProgram = "/lib/pypyjs/pypy.js";
    Module.filePackagePrefixURL = PyPyJS.prototype.fetch.rootURL;

    // Don't start or stop the program, just set it up.
    // We'll call the API functions ourself.
    Module.noInitialRun = true;
    Module.noExitRuntime = true;

    // Route stdout to an overridable method on the object.
    var stdin = (function stdin() {
      return this.stdin();
    }).bind(this);
 
    // Route stdout to an overridable method on the object.
    // We buffer the output for efficiency.
    var stdout_buffer = []
    var stdout = (function stdout(x) {
      var c = String.fromCharCode(x);
      stdout_buffer.push(c);
      if (c === "\n" || stdout_buffer.length >= 128) {
        this.stdout(stdout_buffer.join(""));
        stdout_buffer = [];
      }
    }).bind(this);

    // Route stderr to an overridable method on the object.
    // We do not buffer stderr.
    var stderr = (function stderr(x) {
      var c = String.fromCharCode(x);
      this.stderr(c);
    }).bind(this);

    // We'll use this to hook into completion of various init tasks.
    var dependenciesFulfilled = function () {};

    // Eval the code.  This will probably take quite a while in Firefox
    // as it parses and compiles all the functions.  The result is that
    // our "Module" object is populated with all the exported VM functions.
    console.log("evaluating asmjs code...");
    eval(moduleCode);

    // Load the filesystem data.
    FS.init(stdin, stdout, stderr);
    console.log("loading filesystem data...");
    this.fetch("stdlib.js", (function(err, xhr) {
      if (err) return cb(err);

      // We need 'Module' to be in the local scope of the eval'd code.
      return (function(err, xhr, Module) {
        // This makes a bunch of calls to the filesystem API
        // to initialize from the loaded data.
        console.log("preparing the filesystem...");
        eval(xhr.responseText)

        // Complete initialization once the filesystem is in place.
        dependenciesFulfilled = (function() {
          // Initialize the VM state.
          console.log("initialising the vm...");
          Module._rpython_startup_code();
          var pypy_home = Module.intArrayFromString("/lib/pypyjs/pypy.js");
          pypy_home = Module.allocate(pypy_home, 'i8', Module.ALLOC_NORMAL);
          Module._pypy_setup_home(pypy_home, 0);
          Module._free(pypy_home);
          // Make the module available on this object.
          // This allows it to execute code in the VM.
          console.log("pypy.js is ready!");
          this._module = Module;
          return cb(null);
        }).bind(this);
      }).bind(this)(err, xhr, Module);
    }).bind(this));

  }).bind(this));
}


// Method to evaluate some python code.
// This passes the given python code to the VM for execution.
// Currently it is not possible to obtain any output from the code,
// except for watching its stdout/stderr streams.  If an uncaught
// exception occurs then this method will return -1, otherwise it
// returns zero.
//
// XXX TODO: maybe we should throw an error if there's an error?
//
PyPyJS.prototype.eval = function push(code) {
  var Module = this._module;
  var code_chars = Module.intArrayFromString(code);
  var code_ptr = Module.allocate(code_chars, 'i8', Module.ALLOC_NORMAL);
  if (!code_ptr) {
    return -1;
  }
  var res = Module._pypy_execute_source(code_ptr);
  Module._free(code_ptr);
  return res;
}


// XXX TODO: expose the filesystem for manipulation by calling code.
