
function debug(data) {
  self.postMessage({type: 'debug', data: data})
}

Error.stackTraceLimit = 200;

var Module = {};
Module.TOTAL_MEMORY = 128 * 1024 * 1024;
Module.noFSInit = true;
Module.noExitRuntime = true;

function stdin() {
  return null;
}

function stdout(x) {
  self.postMessage({type: 'stdout', data: x})
}

function stderr(x) {
  self.postMessage({type: 'stderr', data: x})
}

function onerror(e) {
  if (typeof console != 'undefined') {
    console.log(e.stack)
  }
  self.postMessage({type: 'error', data: e.toString()})
  throw e
}

debug('fetching filesystem stubs...')

try {
  importScripts('./lazyfiles.js');
} catch (e) {
  onerror(e)
}

Module.preRun = function() {
  try {
    // Create filesystem from lazy file metadata.
    FS.init(stdin, stdout, stderr);
    createLazyFiles(Module);
    // Sneakily replace _main with one that preps an interpreter.
    // Since we don't exit the runtime, this will set up the internal
    // state and them leave it for us to play with.
    Module['_main'] = function(argc, argv, wtf) {
      self.postMessage({type: 'status', data: 'loaded'})
      Module['_RPython_StartupCode']();
      var pypy_home = allocate(intArrayFromString(""), 'i8', ALLOC_NORMAL);
      Module['_pypy_setup_home'](pypy_home, 0);
      var pypy_code = allocate(intArrayFromString("import code\nc = code.InteractiveConsole()"), 'i8', ALLOC_NORMAL);
      Module['_pypy_execute_source'](pypy_code);
      Module['_free'](pypy_code);
      pypy_push_input("print 'welcome to pypy.js'", true)
      pypy_push_input("from test import pystone", true)
      self.postMessage({type: 'status', data: 'ready'})
      return 0;
    }
  } catch (e) {
    onerror(e)
  }
}

function pypy_push_input(code, nomsg) {
  try {
    if (!nomsg) self.postMessage({type: 'status', data: 'working'})
    code = "c.push('" + code.replace(/'/g, "\\'") + "')"
    var pypy_code = allocate(intArrayFromString(code), 'i8', ALLOC_NORMAL);
    var res = Module['_pypy_execute_source'](pypy_code);
    Module['_free'](pypy_code);
    if (!nomsg) self.postMessage({type: 'status', data: 'ready', res: res})
    return res
  } catch (e) {
    if (typeof console != 'undefined') {
      console.log(e.stack)
    }
    self.postMessage({type: 'error', data: e.toString()})
  }
}

debug('fetching asmjs code...')

try {
  importScripts('./pypy-js.js');
} catch (e) {
  onerror(e)
}

//var xhr = new XMLHttpRequest();
//xhr.open('GET', './pypy-js.js', false);
//xhr.send(null);
//if (xhr.status >= 400) {
//  throw new Error('failed to load pypy-js.js');
//}
//
//debug('loading asmjs code...')
//
//eval(xhr.responseText)

self.addEventListener('message', function(e) {
  var msg = e.data;
  switch (msg.type) {
    case 'input':
      pypy_push_input(msg.data);
      break;
  }
})
