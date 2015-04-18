
var loadObservers = [];

var addLoadObserver = function(observer) {
    loadObservers.push(observer);
}

var loadNotify = function() {
    for (var i in loadObservers) {
        loadObservers[i]();
    }
    loadObservers = [];
}

var numPassed = 0;
var numFailed = 0;

var passed = function(whichTest) {
    numPassed += 1;
    document.getElementById('test-'+whichTest).className = 'test-passes';
    document.getElementById('test-passes').innerHTML = numPassed;
}

var failed = function(whichTest, text) {
    numFailed += 1;
    var testRow = document.getElementById('test-'+whichTest)
    testRow.className = 'test-failures';
    testRow.childNodes[0].title = text;
    document.getElementById('test-failures').innerHTML = numFailed;
}

var setContentLocation = function(newLocation) {
    return document.getElementById('testframe').contentDocument.location = newLocation;
}

