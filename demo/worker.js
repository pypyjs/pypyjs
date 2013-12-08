
function debug(data) {
  self.postMessage({type: 'debug', data: data})
}

var Module = {};
Module.TOTAL_MEMORY = 268435456 / 8;
Module.noFSInit = true;
Module.noExitRuntime = true;
Module.noInitialRun = true;

function stdin() {
  return null;
}

function stdout(x) {
  self.postMessage({type: 'stdout', data: x})
}

function stderr(x) {
  self.postMessage({type: 'stderr', data: x})
}

debug('fetching filesystem stubs...')

importScripts('./lazyfiles.js');

Module.preRun = function() {
  FS.init(stdin, stdout, stderr);
  createLazyFiles(Module);
}

//importScripts('./pypy-js.js');

debug('fetching asmjs code...')

var xhr = XMLHttpRequest();
xhr.open('GET', './pypy-js.js', false);
xhr.send(null);
if (xhr.status >= 400) {
  throw new Error('failed to load pypy-js.js');
}

debug('loading asmjs code...')

eval(xhr.responseText)

debug('setting up the runtime environment...')

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

function pypy_push_input(code, nomsg) {
  if (!nomsg) self.postMessage({type: 'status', data: 'working'})
  code = "c.push('" + code.replace(/'/g, "\\'") + "')"
  var pypy_code = allocate(intArrayFromString(code), 'i8', ALLOC_NORMAL);
  var res = Module['_pypy_execute_source'](pypy_code);
  Module['_free'](pypy_code);
  if (!nomsg) self.postMessage({type: 'status', data: 'ready'})
  return res
}

Module.callMain(["-c", ""]);

self.addEventListener('message', function(e) {
  var msg = e.data;
  switch (msg.type) {
    case 'input':
      pypy_push_input(msg.data);
      break;
  }
})
