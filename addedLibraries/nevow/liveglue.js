
var nevow_clientHandleId;       /* This variable must be defined in your HTML.
                                 */

var liveevil_unload = false;
var auto_open = true;

var last_request = null;
var last_server_message_time = null;

var disconnectListeners = [];

var inputListeners = [];
var listenerId = 0;

var base_url = this.location.toString();
var queryParamIndex = base_url.indexOf('?');
var userAgent = navigator.userAgent.toLowerCase();

if (queryParamIndex != -1) {
  base_url = base_url.substring(0, queryParamIndex);
 }

if (base_url.charAt(base_url.length-1) != '/') {
  base_url += '/';
 }

base_url += 'livepage_client/'


function createRequest() {
    if (window.XMLHttpRequest) {
      req = new XMLHttpRequest();
    } else {
        req = new ActiveXObject("Microsoft.XMLHTTP")
    }
    reqObj = new Object()
    reqObj.request = req
    return reqObj
}

function connect(outputNum) {
  var xmlhttp = createRequest();
  last_request = xmlhttp.request;
  xmlhttp.request.onreadystatechange = function() {
    if (xmlhttp.request.readyState == 4) {
      if (xmlhttp.request.responseText) {
        last_server_message_time = new Date()
        eval(xmlhttp.request.responseText)
        if (!liveevil_unload && auto_open) {
          connect(outputNum + 1)
        }
      } else {
        for (var i=0; i<disconnectListeners.length; i++) {
          disconnectListeners[i]()
          disconnectListeners = []
        }
        last_request = null
      }
    }
  }
  var U = base_url + nevow_clientHandleId + "/output?outputNum=" + outputNum;
  xmlhttp.request.open("GET", U, true);
  xmlhttp.request.send(null);
}


if (userAgent.indexOf("msie") != -1) {
    /* IE specific stuff */
    /* Abort last request so we don't 'leak' connections */
    window.attachEvent("onbeforeunload", function() { if (last_request != null) {last_request.abort();} } )
    /* Set unload flag */
    window.attachEvent("onbeforeunload", function() { liveevil_unload = true; } )
} else if (document.implementation && document.implementation.createDocument) {
    /* Mozilla specific stuff (onbeforeunload is in v1.7+ only) */
    window.addEventListener("beforeunload", function() { liveevil_unload = true; }, false)
}


function listener(callWhenAllDone) {
    this.listenerId = listenerId
    listenerId += 1
    this.events = []
    this.callWhenAllDone = callWhenAllDone
    this.fired = false
    this.inputDone = function(what) {
        var found = false
        for (var i=0; i<this.events.length; i++) {
            if (this.events[i] == what) {
                this.events.splice(i, 1)
                found = true
                break
            }
        }
        if (this.events.length == 0) {
            if (this.fired) {
                alert("Tried to fire twice :(")
            } else {
                this.callWhenAllDone()
                this.fired = true
            }
        }
    }
}


function listenForInputEvents(callWhenAllDone) {
    var newListener = new listener(callWhenAllDone)
    inputListeners.push(newListener)
    return newListener
}


function stopListening(theListener) {
    for (var i=0; i<inputListeners.length; i++) {
        if (inputListeners[i] == theListener) {
            inputListeners.splice(i, 1)
            break
        }
    }
    if (theListener.events.length == 0) {
        theListener.callWhenAllDone()
    }
}

function addDisconnectListener(callback) {
    disconnectListeners.push(callback)
    return callback
}

function delDisconnectListener(theListener) {
    for (var i=0; i<disconnectListeners.length; i++) {
	if (disconnectListeners[i] == theListener){
	    disconnectListeners.splice(i, 1)
	    break
	}
    }
}

function nevow_clientToServerEvent(theTarget, evalAfterDone) {
    if (theTarget != 'close' && liveevil_unload) {
        // Server had previously closed the output; let's open it again.
        if (auto_open) {
            liveevil_unload = false }
        connect(0)
    }
    var additionalArguments = ''
    for (i = 2; i<arguments.length; i++) {
        additionalArguments += '&arguments='
        additionalArguments += encodeURIComponent(arguments[i])
    }
    var input = createRequest()
    input.request.onreadystatechange = function() {
        if (input.request.readyState == 4) {
            eval(input.request.responseText)
            if (evalAfterDone) {
               eval(evalAfterDone)
            }
            for (var i=0; i<input.events.length; i++) {
                input.events[i].inputDone(input.request)
            }
        }
    }
    input.events = []
    for (var i=0; i<inputListeners.length; i++) {
        inputListeners[i].events.push(input.request)
        input.events.push(inputListeners[i])
    }
    input.request.open(
      "GET",
      base_url +
      nevow_clientHandleId +
      "/input?" +
      "handler-path=&handler-name=" +
      encodeURIComponent(theTarget) +
      additionalArguments)

    input.request.send(null)
}

function nevow_setNode(node, to) {
    document.getElementById(node).innerHTML = to;
}

function nevow_appendNode(node, what) {
    var oldnode = document.getElementById(node);
    var newspan = document.createElement('span');
    newspan.innerHTML = what;
    for (i=0; i<newspan.childNodes.length; i++) {
        oldnode.appendChild(newspan.childNodes[i]);
    }
}

function nevow_prependNode(node, what) {
  var oldnode = document.getElementById(node);
  var newspan = document.createElement('span');
  newspan.innerHTML = what;
  for (i=newspan.childNodes.length-1; i>=0; i--){
    if (oldnode.childNodes.length == 0)
      oldnode.appendChild(newspan.childNodes[i]);
    else
      oldnode.insertBefore(newspan.childNodes[i], oldnode.childNodes[0]);
  }
}

function nevow_insertNode(node, before) {
    var oldnode = document.getElementById('before');
    var newspan = document.createElement('span');
    newspan.innerHTML = what;
    var previous = oldnode;
    for (i=0; i<newspan.childNodes.length; i++) {
        previous.parentNode.insertBefore(newspan.childNodes[i], previous);
        previous = newspan.childNodes[i];
    }
}

function nevow_closeLive(evalAfterDone) {
    // Tell connect() not to complain at us when the server closes the
    // connection with no serverToClientEvent
    liveevil_unload = true
    var old_auto_open = auto_open
    auto_open = false
    // Tell the server we know we're done, send us an empty event
    // evalAfterDone will be evalled after the server sends us an empty event
    nevow_clientToServerEvent('close', '', evalAfterDone)
    auto_open = old_auto_open
}


var server = {
    handle: function(handlerName) {
        var args = [handlerName, '']
        for (var i = 1; i < arguments.length; i++) {
            args.push(arguments[i])
        }
        nevow_clientToServerEvent.apply(this, args)
    }
};

function nevow_startLivePage() {
  if (nevow_clientHandleId == null) {
    alert('UNSUPPORTED!  USE AT YOUR OWN RISK!');
    var x = createRequest();
    x.request.onreadstatechange = function () {
      if (x.request.readyState == 4) {
        nevow_clientHandleId = x.request.responseText;
        nevow_startLivePage();
      }
    };
    x.request.open("GET", base_url + "new");
    x.request.send(null);
  } else {
    connect(0);
  }
}


var nevow_origOnLoad = window.onload;
function nevow_onLoad() {
    if (nevow_origOnLoad) {
      if(typeof(nevow_origOnLoad) == "string") {
        eval(nevow_origOnLoad);
      }
      else {
        nevow_origOnLoad();
      }
    }      
    if (auto_open) {
        nevow_startLivePage();
    }
}
window.onload = nevow_onLoad;

