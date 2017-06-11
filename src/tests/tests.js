//
// A very minimal testsuite for the PyPy.js shell code.
// We should do something a lot nicer than this...
//
if (typeof pypyjs === 'undefined') {
  if (typeof require !== 'undefined') {
    pypyjs = require('../pypyjs.js');
  } else if (typeof loadRelativeToScript !== 'undefined') {
    loadRelativeToScript('../pypyjs.js');
  } else if (typeof load !== 'undefined') {
    load('pypyjs.js');
  }
}

let log;
if (typeof console !== 'undefined') {
  log = console.log.bind(console);
} else {
  log = print;
}

const vm = new pypyjs();

const pypyjsTestResult = vm.ready();

// First, check that python-level errors will actually fail the tests.
pypyjsTestResult
.then(() => vm.exec('raise ValueError(42)'))
.then(() => { throw new Error('Python exception did not trigger js Error'); },
(err) => {
  if (!(err instanceof pypyjs.Error)) {
    throw new Error('Python exception didn\'t trigger vm.Error instance: ' + err);
  }
  if (err.name !== 'ValueError' || err.message !== '42') {
    throw new Error('Python exception didn\'t trigger correct error info: ' + err);
  }
})

// Check that the basic set-exec-get cycle works correctly.
.then(() => vm.set('x', 7))
.then(() => vm.exec('x = x * 2'))
.then(() => vm.get('x'))
.then((x) => {
  if (x !== 14) {
    throw new Error('set-exec-get cycle failed');
  }
})

// Check that eval() works correctly.
.then(() => vm.eval('x + 1'))
.then((x) => {
  if (x !== 15) {
    throw new Error('eval failed');
  }
})

// Check that we can read non-existent names and get 'undefined'
.then(() => vm.get('nonExistentName'))
.then((x) => {
  if (typeof x !== 'undefined') {
    throw new Error('name should have been undefined');
  }
})
// - for globals()
.then(() => vm.get('nonExistentName', true))
.then((x) => {
  if (typeof x !== 'undefined') {
    throw new Error('name should have been undefined');
  }
})

// Check that get() propagates errors other than involved in getting the variable.
.then(() => {
  return vm.get('__name__ + 5')
  .then(
    () => { throw new Error('should have thrown an error'); },
    (exc) => {
      if (typeof exc === 'undefined') {
        throw new Error('expected to receive an exception');
      } else if (exc.name !== 'TypeError') {
        throw new Error('expected to receive a TypeError');
      }
    }
  );
})

// Check that we execute in correctly-__name__'d python scope.
.then(() => vm.exec('assert __name__ == \'__main__\', __name__'))

// Check that sys.platform tells us something sensible.
.then(() => vm.exec('import sys; assert sys.platform == \'js\''))

// Check that multi-line exec will work correctly.
.then(() => vm.exec('x = 2\ny = x * 3'))
.then(() => vm.get('y'))
.then((y) => {
  if (y !== 6) {
    throw new Error('multi-line exec didn\'t work');
  }
})

// Check that multi-import statements will work correctly.
.then(() => vm.exec('import os\nimport time\nimport sys\nx=time.time()'))

// Check that multi-import statements will work correctly.
.then(() => vm.exec('import os\nimport time\nimport sys\nx=time.time()'))
.then(() => vm.get('x'))
.then((x) => {
  if (!x) {
    throw new Error('multi-line import didn\'t work');
  }
})

// Check that you can create additional VMs using `new`
.then(() => {
  const vm2 = new pypyjs();
  return vm2.exec('x = 17')
        .then(() => vm2.get('x'))
        .then((x) => {
          if (x !== 17) {
            throw new Error('newly-created VM didn\'t work right');
          }
        })
        .then(() => vm2.get('y'))
        .then((y) => {
          if (typeof y !== 'undefined') {
            throw new Error('name should have been undefined in new VM');
          }
        });
})

// Test use of top-level methods on default vm instance
.then(() => {
  return pypyjs.eval('3 + 4')
        .then((x) => {
          if (x !== 7) {
            throw new Error('top-level method method didn\'t work right');
          }
        });
})

// Report success or failure at the end of the chain.
.then(() => {
  log('TESTS PASSED!');
},
(err) => {
  log('TESTS FAILED!');
  log(err);
  throw err;
});
