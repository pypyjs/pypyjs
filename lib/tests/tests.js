//
// A very minimal testsuite for the PyPy.js shell code.
// We should do something a lot nicer than this...
//

var pypyjs;
if (typeof pypyjs === 'undefined') {
  if (typeof require !== 'undefined') {
    pypyjs = require('../pypyjs.js');
  } else if (typeof loadRelativeToScript !== 'undefined') {
    loadRelativeToScript('../pypyjs.js');
  } else if (typeof load !== 'undefined') {
    load('pypyjs.js');
  }
}

var log
if (typeof console !== 'undefined') {
  log = console.log.bind(console);
} else {
  log = print;
}

var pypyjsTestResult = vm.ready()

// First, check that python-level errors will actually fail the tests.
.then(function() {
  return vm.exec("raise ValueError(42)");
})
.then(function() {
  throw new Error("Python exception did not trigger js Error");
}, function(err) {
  if (! err instanceof pypyjs.Error) {
    throw new Error("Python exception didn't trigger vm.Error instance");
  }
  if (err.name !== "ValueError" || err.message !== "42") {
    throw new Error("Python exception didn't trigger correct error info");
  }
})

// Check that the basic set-exec-get cycle works correctly.
.then(function() {
  return vm.set("x", 7);
})
.then(function() {
  return vm.exec("x = x * 2");
})
.then(function() {
  return vm.get("x");
})
.then(function(x) {
  if (x !== 14) {
    throw new Error("set-exec-get cycle failed");
  }
})

// Check that eval() works correctly.
.then(function() {
  return vm.eval("x + 1");
})
.then(function(x) {
  if (x !== 15) {
    throw new Error("eval failed");
  }
})

// Check that we can read non-existent names and get 'undefined'
// - for top_level_scope
.then(function() {
  return vm.get("nonExistentName")
})
.then(function(x) {
  if (typeof x !== "undefined") {
    throw new Error("name should have been undefined");
  }
})
// - for globals()
.then(function() {
  return pypyjs.get("nonExistentName", true)
})
.then(function(x) {
  if (typeof x !== "undefined") {
    throw new Error("name should have been undefined");
  }
})

// Check that get() propagates errors other than involved in getting the variable.
.then(function() {
  return pypyjs.get("__name__ + 5");
}).catch(function(exc) {
  if (typeof exc === "undefined") {
    throw new Error("expected to receive an exception");
  } else if ("TypeError" !== exc.name) {
    throw new Error("expected to receive a TypeError");
  }
})

// Check that we execute in correctly-__name__'d python scope.
.then(function() {
  return vm.exec("assert __name__ == '__main__', __name__")
})

// Check that sys.platform tells us something sensible.
.then(function() {
  return vm.exec("import sys; assert sys.platform == 'js'");
})

// Check that multi-line exec will work correctly.
.then(function() {
  return vm.exec("x = 2\ny = x * 3");
})
.then(function() {
  return vm.get("y")
})
.then(function(y) {
  if (y !== 6) {
    throw new Error("multi-line exec didn't work");
  }
})

// Check that multi-import statements will work correctly.
.then(function() {
  return vm.exec("import os\nimport time\nimport sys\nx=time.time()")
})
.then(function() {
  return vm.get("x")
})
.then(function(x) {
  if (!x) {
    throw new Error("multi-line import didn't work");
  }
})

// Check that you can create additional VMs using `new`
.then(function() {
  var vm2 = new pypyjs()
  return vm2.exec("x = 17").then(function() {
    return vm2.get("x")
  }).then(function(x) {
    if (x !== 17) {
      throw new Error("newly-created VM didn't work right")
    }
  }).then(function() {
    return vm2.get("y")
  }).then(function(y) {
    if (typeof y !== "undefined") {
      throw new Error("name should have been undefined in new VM");
    }
  })
})

// Report success or failure at the end of the chain.
.then(function(res) {
  log("TESTS PASSED!");
}, function(err) {
  log("TESTS FAILED!");
  log(err);
  throw err;
});
