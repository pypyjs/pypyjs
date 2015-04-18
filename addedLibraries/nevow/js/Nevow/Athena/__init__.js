// -*- test-case-name: nevow.test.test_javascript -*-

// import Divmod
// import Divmod.Base
// import Divmod.Runtime

// import Nevow

Nevow.Athena.NAME = 'Nevow.Athena';
Nevow.Athena.__repr__ = function() {
    return '[' + this.NAME + ']';
};


Nevow.Athena.toString = function() {
    return this.__repr__();
};


Nevow.Athena.XMLNS_URI = 'http://divmod.org/ns/athena/0.7';


Nevow.Athena.PageWidget = Divmod.Class.subclass("Nevow.Athena.PageWidget");

/**
 * A page-level widget.  This is the class responsible for handling state at
 * the level of the whole Athena page; it is the client-side peer of LivePage.
 *
 * @ivar pageUnloaded: a boolean which tracks whether the page has already
 * been unloaded, so we do not erroneously pop up the "connection lost!"
 * widget every time the user clicks on a link.
 */
Nevow.Athena.PageWidget.methods(
    /**
     * Create a PageWidget.
     *
     * @param livepageID: A identifier for the server-side half of this page
     * object.
     * @type livepageID: C{String}
     *
     * @param deliveryChannelFactory: a 1-argument callable, that takes this
     * PageWidget, and returns a ReliableMessageDelivery for it.
     * @type deliveryChannelFactory: C{Function}
     */
    function __init__(self,
                      livepageID,
                      deliveryChannelFactory) {
        self.livepageID = livepageID;
        self.deliveryChannel = deliveryChannelFactory(self);
        self.pageUnloaded = false;
        self.remoteCalls = {};
        self.disconnectNotifications = [];
        self.remoteCallCount = 0;
        self.connectionState = Nevow.Athena.CONNECTED;
    },

    /**
     * Construct an event handler function that dispatches to a method on
     * self.
     */
    function makeHandler(self, evtName) {
        var thunk = function (evtObj) {
            return self[evtName](evtObj);
        };
        return thunk;
    },

    /**
     * DOM event handler for key-press events.  This method handles all
     * keypress events sent to the window.
     *
     * This handler exists because when the escape key is pressed, the default
     * global 'onkeypress' event handler of the window will stop the window,
     * instantly terminating any active XMLHttpRequest connections and
     * preventing any future ones.  This handler will prevent that default
     * behavior, otherwise leaving the event unmolested.
     */
    function onkeypress(self, event) {
        if (event.keyCode === Nevow.Athena.KEYCODE_ESCAPE) {
            event.preventDefault();
            return true;
        }
        return true;
    },

    /**
     * This event handler reacts to the 'onbeforeunload' event to notify the
     * server as quickly as possible that this is the last processable event
     * and the page should be instantly disconnected.  We also set the
     * pageUnloaded flag here, to prevent post-unload display of the
     * connection-lost notification.
     */
    function onbeforeunload(self, event) {
        self.pageUnloaded = true;
        self.deliveryChannel.sendCloseMessage();
    },

    /* Actions dispatched from delivery channel. */

    /**
     * Action that indicates we have received a response to a previous
     * invocation of RemoteReference.callRemote.
     */
    function action_respond(self, responseId, success, result) {
        var d = self.remoteCalls[responseId];
        delete self.remoteCalls[responseId];

        if (success) {
            d.callback(result);
        } else {
            d.errback(Divmod.namedAny(result[0]).apply(null, result[1]));
        }
    },

    /**
     * No-op action, for testing.
     */
    function action_noop(self) {
    },

    /**
     * Page-level 'call' action, to invoke a method on a global object with
     * some given arguments.  Invoke the method and responds with a 'respond'
     * message.  The given function may return a Deferred.
     *
     * @param functionName: the global identifier of a method to call
     *
     * @param requestId: an opaque identifier for the request, which will be
     * relayed back to the server when the response is available.
     */
    function action_call(self, functionName, requestId, funcArgs) {
        var path = [null];
        var method = Divmod.namedAny(functionName, path);
        var target = path.pop();
        var result = undefined;
        var success = true;
        try {
            result = method.apply(target, funcArgs);
        } catch (error) {
            result = error;
            success = false;
        }

        var isDeferred = false;

        if (result == undefined) {
            result = null;
        } else {
            /* if it quacks like a duck ...  this sucks!!!  */
            isDeferred = (result.addCallback && result.addErrback);
        }

        if (isDeferred) {
            result.addCallbacks(function(result) {
                self.deliveryChannel.addMessage(
                    ['respond', [requestId, true, result]]);
            }, function(err) {
                self.deliveryChannel.addMessage(
                    ['respond', [requestId, false, err.error]]);
            });
        } else {
            self.deliveryChannel.addMessage(['respond', [requestId, success, result]]);
        }
    },

    /**
     * The server has closed the connection.
     */
    function action_close(self) {
        self.deliveryChannel.stop();
    },

    /**
     * Invoke a function when this page is disconnected.
     */
    function notifyOnDisconnect(self, thunk) {
        self.disconnectNotifications.push(thunk);
    },

    /**
     * This page's connection has been lost.  Display a dialog that explains
     * that fact, and errback all remaining outgoing calls.
     *
     * @param reason: a string explaining the reason for the connection being
     * dropped.
     */
    function connectionLost(self, reason) {
        if (self.connectionState == Nevow.Athena.DISCONNECTED) {
            Divmod.debug("transport", "Warning: duplicate close notification.");
            return;
        }
        if (!self.pageUnloaded) {
            self.showDisconnectDialog();
        }
        // XXX TODO: 'clean' disconnection notification, so that the user can
        // see if they perform some event that unloads the page?  it would be
        // nice to desaturate it or something, but bleh, that's not possible
        // on the web... --glyph
        Divmod.debug('transport', 'Closed');
        self.connectionState = Nevow.Athena.DISCONNECTED;
        var calls = self.remoteCalls;
        self.remoteCalls = {};
        for (var k in calls) {
            Divmod.msg("Errbacking an existing call");
            calls[k].errback(new Error("Connection lost"));
        }
        for (var i = 0; i < self.disconnectNotifications.length; i++) {
            self.disconnectNotifications[i](reason);
        }
    },

    /**
     * Generate a string, the URL of the transport endpoint URL for this
     * livepage.  Transport endpoint URLs are the URLs to which JSON message
     * queues should be posted and retrieved; they are an internal
     * implementation detail of Athena and not a user-visible page.  According
     * to the rules defined by the Python side of athena, for a page with a
     * transport root of
     *
     *   http://localhost/some/stuff/here
     *
     * the transport URL for a page with livepageID 1234 will be
     *
     *   http://localhost/some/stuff/here/1234/transport
     */
    function transportURL(self) {
        return self.baseURL() + 'transport';
    },

    /**
     * Generate a string, the unambiguous URL of the server peer of this page
     * object.
     */
    function baseURL(self) {
        var outURL = Divmod._location;

        if (outURL == undefined) {
            outURL = window.location.toString();
        }

        var queryParamIndex = outURL.indexOf('?');

        if (queryParamIndex != -1) {
            outURL = outURL.substring(0, queryParamIndex);
        }

        if (outURL.charAt(outURL.length - 1) != '/') {
            outURL += '/';
        }

        outURL += self.livepageID + '/';
        return outURL;
    },

    /**
     * Send a 'call' message to the server and return a Deferred which will
     * fire when it is responded to.
     *
     * @param remoteRef: the remote reference which is invoking the method.
     *
     * @param methodName: a string, the name of the method on the server's
     * object.
     *
     * @param args: an array, the list of positional arguments to pass.
     *
     * @param kwargs: an object with attributes representing the keyword
     * arguments to pass to the server.
     */
    function sendCallRemote(self, remoteRef, methodName, args, kwargs) {
        var objectID = remoteRef.objectID;
        if (self.connectionState == Nevow.Athena.DISCONNECTED) {
            return Divmod.Defer.fail(new Error("Connection lost"));
        }

        var resultDeferred = Divmod.Defer.Deferred();
        var requestId = 'c2s' + self.remoteCallCount;

        self.remoteCallCount++;
        self.remoteCalls[requestId] = resultDeferred;

        self.deliveryChannel.addMessage(
            ['call', [requestId, methodName, objectID, args, kwargs]]);

        setTimeout(function() {
            resultDeferred.addErrback(
                function(err) {
                    var errclass;
                    if (remoteRef.node !== undefined) {
                        errclass = Nevow.Athena.athenaIDFromNode(remoteRef.node);
                    } else {
                        errclass = "unknown";
                    }
                    self.showErrorDialog(methodName, err, errclass);
                });
            }, 0);

        return resultDeferred;
    },

    /**
     * Display an error dialog to the user, containing some information
     * about the uncaught error C{err}, which occurred while trying to call
     * the remote method C{methodName}.  To avoid this happening, errbacks
     * should be added synchronously to the deferred returned by L{callRemote}
     * (the errback that triggers this dialog is added via setTimeout(..., 0))
     */
    function showErrorDialog(self, methodName, err, errclass) {
        var e = document.createElement("div");
        e.style.padding = "12px";
        e.style.border = "solid 1px #666666";
        e.style.position = "absolute";
        e.style.whiteSpace = "nowrap";
        e.style.backgroundColor = "#FFFFFF";
        e.style.zIndex = 99;
        e.className = "athena-error-dialog-" + errclass;

        var titlebar = document.createElement("div");
        titlebar.style.borderBottom = "solid 1px #333333";

        var title = document.createElement("div");
        title.style.fontSize = "1.4em";
        title.style.color = "red";
        title.appendChild(
            document.createTextNode("Error"));

        titlebar.appendChild(title);

        e.appendChild(titlebar);

        e.appendChild(
            document.createTextNode("Your action could not be completed because an error occurred."));

// Useful for debugging sometimes, except it really isn't very pretty.
// toPrettyNode needs unit tests or something, though.
//         try {
//             e.appendChild(err.toPrettyNode());
//         } catch (err) {
//             alert(err);
//         }

        var errorLine = document.createElement("div");
        errorLine.style.fontStyle = "italic";
        errorLine.appendChild(
            document.createTextNode(
                err.toString() + ' caught while calling method "' + methodName + '"'));
        e.appendChild(errorLine);

        var line2 = document.createElement("div");
        line2.appendChild(
            document.createTextNode("Please retry."));
        e.appendChild(line2);

        var close = document.createElement("a");
        close.href = "#";
        close.onclick = function() {
            document.body.removeChild(e);
            return false;
        };
        close.style.display = "block";

        close.appendChild(
            document.createTextNode("Click here to close."));

        e.appendChild(close);

        document.body.appendChild(e);

        var elemDimensions = Divmod.Runtime.theRuntime.getElementSize(e);
        var pageDimensions = Divmod.Runtime.theRuntime.getPageSize();

        e.style.top  = Math.round(pageDimensions.h / 2 - elemDimensions.h / 2) + "px";
        e.style.left = Math.round(pageDimensions.w / 2 - elemDimensions.w / 2) + "px";
    },

    /**
     * Display an absolutely positioned dialog box that indicates that the
     * active connection to the server has been disabled and no further
     * interaction is possible without reloading the page.
     */
    function showDisconnectDialog(self) {
        var url = (Divmod._location +
                   '__athena_private__/connection-status-down.png');

        var img = document.createElement('img');
        img.src = url;

        var div = document.createElement('div');
        div.appendChild(img);
        div.appendChild(document.createElement('br'));
        div.appendChild(document.createTextNode('Connection to server lost! '));
        div.appendChild(document.createElement('br'));

        var a = document.createElement('a');
        a.appendChild(document.createTextNode('Click to attempt to reconnect.'));
        a.href = '#';
        a.onclick = function() {
            document.location = document.location;
            return false;
        };
        div.appendChild(a);

        div.className = 'nevow-connection-lost';
        div.style.textAlign = 'center';
        div.style.position = 'absolute';
        div.style.top = '1em';
        div.style.left = '1em';
        div.style.backgroundColor = '#fff';
        div.style.border = 'thick solid red';
        div.style.padding = '2em';
        div.style.margin = '2em';

        Divmod.msg("Appending connection status image to document.");
        document.body.appendChild(div);

        var setInvisible = function() {
            img.style.visibility = 'hidden';
            setTimeout(setVisible, 1000);
        };
        var setVisible = function() {
            img.style.visibility = 'visible';
            setTimeout(setInvisible, 1000);
        };
        setVisible();
    },

    /**
     * Dispatch an event.
     */
    function dispatchEvent(self, widget, eventName, handlerName, callable) {
        var result = false;
        self.deliveryChannel.pause();
        try {
            try {
                result = callable.call(widget);
            } catch (err) {
                Divmod.err(
                    err,
                    "Dispatching " + eventName +
                    " to " + handlerName +
                    " on " + widget +
                    " failed.");
            }
        } catch (err) {
            self.deliveryChannel.unpause();
            throw err;
        }
        self.deliveryChannel.unpause();
        return result;
    });

Nevow.Athena.ReliableMessageDelivery = Divmod.Class.subclass('Nevow.Athena.ReliableMessageDelivery');

/**
 * A L{ReliableMessageDelivery} is a queue through which messages may be
 * reliably delivered from and to the Athena server.
 *
 * @ivar outputFactory: a callable which takes 1 argument (a boolean
 * indicating whether the request should be issued synchronously) returns an
 * L{HTTPRequestOutput} object.
 *
 * @ivar page: a L{PageWidget} object, used to dispatch action_ methods which
 * correspond to the messages received.
 */

Nevow.Athena.ReliableMessageDelivery.methods(
    function __init__(self,
                      outputFactory,
                      page) {
        self.running = false;
        self.messages = [];
        self.ack = -1;
        self.seq = -1;
        self._paused = 0;
        self.failureCount = 0;
        self.outputFactory = outputFactory;
        self.requests = [];
        self.page = page;
        if (page === undefined) {
            throw new Error("Must supply a page.");
        }
    },

    function start(self) {
        self.running = true;
        if (self.requests.length == 0) {
            self.flushMessages();
        }
    },

    function stop(self) {
        self.running = false;
        for (var i = 0; i < self.requests.length; ++i) {
            self.requests[i].abort();
        }
        self.requests = null;
        self.page.connectionLost('Connection closed by remote host');
    },

    function acknowledgeMessage(self, ack) {
        while (self.messages.length && self.messages[0][0] <= ack) {
            self.messages.shift();
        }
    },

    /**
     * A message representing a list of actions to take, of the format
     * [[sequenceNumber, [actionName, actionArguments]], ...] has been
     * received from the server.  Dispatch those messages to methods named
     * action_* on this object.
     */
    function messageReceived(self, message) {
        self.pause();
        if (message.length) {
            if (self.ack + 1 >= message[0][0]) {
                var ack = self.ack;
                self.ack = Divmod.max(self.ack, message[message.length - 1][0]);
                for (var i = 0; i < message.length; ++i) {
                    var msg = message[i];
                    var seq = msg[0];
                    var payload = msg[1];
                    var actionName = payload[0];
                    var actionArgs = payload[1];
                    if (seq > ack) {
                        try {
                            self.page['action_'+actionName].apply(self.page, actionArgs);
                        } catch (e) {
                            Divmod.err(e, 'Action handler ' + payload[0] +
                                       ' for ' + seq + ' failed.');
                        }
                    }
                }
            } else {
                Divmod.debug("transport",
                             "Sequence gap!  " + self.page.livepageID +
                             " went from " + self.ack + " to " + message[0][0]);
            }
        }
        self.unpause();
    },

    function pause(self) {
        self._paused += 1;
    },

    function unpause(self) {
        self._paused -= 1;
        if (self._paused == 0) {
            self.flushMessages();
        }
    },

    function addMessage(self, msg) {
        ++self.seq;
        self.messages.push([self.seq, msg]);
        self.flushMessages();
    },

    function flushMessages(self) {
        if (!self.running || self._paused) {
            return;
        }

        var outgoingMessages = self.messages;

        if (outgoingMessages.length == 0) {
            if (self.requests.length != 0) {
                return;
            }
        }

        if (self.requests.length > 1) {
            self.failureCount -= 1;
            self.requests[0].abort();
        }

        var theRequest = self.outputFactory().send(self.ack, outgoingMessages);

        self.requests.push(theRequest);
        theRequest.deferred.addCallback(function(result) {
            self.failureCount = 0;
            self.acknowledgeMessage(result[0]);
            self.messageReceived(result[1]);
        });
        theRequest.deferred.addErrback(function(err) {
            self.failureCount += 1;
        });
        theRequest.deferred.addCallback(function(ign) {
            for (var i = 0; i < self.requests.length; ++i) {
                if (self.requests[i] === theRequest) {
                    self.requests.splice(i, 1);
                    break;
                }
            }
            if (self.failureCount < 3) {
                if (!theRequest.aborted) {
                    self.flushMessages();
                }
            } else {
                self.stop();
            }
        });
    },

    /**
     * Tear down all currently pending requests, and send a final notification
     * to the server that this page has been unloaded, and the connection must
     * be shut down immediately.  This request must be synchronous, because in
     * the browser we cannot emit or receive any asynchronous events after the
     * 'onbeforeunload' handler has returned.
     *
     * Unfortunately, there is a bug in Firefox (and probably other browsers)
     * where the user's browser locks up while the final synchronous request
     * is being made.  Therefore, we want to absolutely minimize the amount of
     * time spent in this method.  In order to accomplish this, all messages
     * that have not yet been acknowledged are dropped from the queue and the
     * final basket case is special: its sequence identifier is "close", as is
     * its message.
     */
    function sendCloseMessage(self) {
        self.stop();
        self.outputFactory(true).send(self.ack, [["unload", ["close", []]]]);
    });

Nevow.Athena.AbortableHTTPRequest = Divmod.Class.subclass("Nevow.Athena.AbortableHTTPRequest");
Nevow.Athena.AbortableHTTPRequest.methods(
    function __init__(self,
                      request,
                      deferred) {
        self.request = request;
        self.deferred = deferred;
        self.aborted = false;
    },

    function abort(self) {
        self.aborted = true;
        self.request.abort();
    });

Nevow.Athena.HTTPRequestOutput = Divmod.Class.subclass('Nevow.Athena.HTTPRequestOutput');
Nevow.Athena.HTTPRequestOutput.methods(
    function __init__(self,
                      baseURL,
                      /* optional */
                      queryArgs /* = [] */,
                      headers /* = [] */,
                      synchronous /* = false */) {
        if (synchronous === undefined) {
            synchronous = false;
        }
        self.baseURL = baseURL;
        self.queryArgs = queryArgs;
        self.headers = headers;
        self.synchronous = synchronous;
    },

    function send(self, ack, message) {
        var serialized = Divmod.Base.serializeJSON([ack, message]);
        var response = Divmod.Runtime.theRuntime.getPage(
            self.baseURL,
            self.queryArgs,
            'POST',
            self.headers,
            serialized,
            self.synchronous);
        var requestWrapper = new Nevow.Athena.AbortableHTTPRequest(
            response[0], response[1]);
        requestWrapper.deferred.addCallback(function(result) {
            if (result.status == 200) {
                return eval('(' + result.response + ')');
            }
            throw new Error("Request failed: " + result.status);
        });
        return requestWrapper;
    });

Nevow.Athena.CONNECTED = 'connected';
Nevow.Athena.DISCONNECTED = 'disconnected';

Nevow.Athena.getAttribute = function() {
    /* Deprecated alias */
    return Divmod.Runtime.theRuntime.getAttribute.apply(Divmod.Runtime.theRuntime, arguments);
};

Nevow.Athena.athenaIDFromNode = function(n) {
    var athenaID = n.id;
    if (athenaID != undefined) {
        var junk = athenaID.split(":");
        if (junk[0] === 'athena' ) {
            return parseInt(junk[1]);
        }
    }
    return null;
};

Nevow.Athena.athenaClassFromNode = function(n) {
    var athenaClass = Divmod.Runtime.theRuntime.getAttribute(
        n, 'class', Nevow.Athena.XMLNS_URI, 'athena');
    if (athenaClass != null) {
        var cls = Divmod.namedAny(athenaClass);
        if (cls == undefined) {
            throw new Error('NameError: ' + athenaClass);
        } else {
            return cls;
        }
    } else {
        return null;
    }
};

Nevow.Athena.nodeByDOM = function(node) {
    /*
     * Return DOM node which represents the LiveFragment, given the node itself
     * or any child or descendent of that node.
     */
    for (var n = node; n != null; n = n.parentNode) {
        var nID = Nevow.Athena.athenaIDFromNode(n);
        if (nID != null) {
            return n;
        }
    }
    throw new Error("nodeByDOM passed node with no containing Athena Ref ID");
};

Nevow.Athena.RemoteReference = Divmod.Class.subclass('Nevow.Athena.RemoteReference');

/**
 * L{RemoteReference} is an object that can send an asynchronous remote method
 * call to the athena server.
 *
 * @ivar objectID: an integer, identifying the server-side peer of this
 * object.
 *
 * @ivar page: a L{PageWidget} to use to send the underlying messages, or
 * undefined to indicate that the default global page (Nevow.Athena.page)
 * should be used.
 */
Nevow.Athena.RemoteReference.methods(
    function __init__(self, objectID, /* optional */ page) {
        if (typeof objectID != "number") {
            throw new Error("Invalid object identifier: " + objectID);
        }
        self.objectID = objectID;
        self.page = page;
    },

    /**
     * Retrieve the L{PageWidget} to use to send callRemote messages to.
     *
     * @return: a L{PageWidget} in this L{RemoteReference}'s 'page' attribute,
     * the global page widget (Nevow.Athena.page) if none is specified.
     */
    function getPageWidget(self) {
        if (self.page === undefined) {
            return Nevow.Athena.page;
        }
        return self.page;
    },

    /**
     * Invoke this RemoteReference's page's sendCallRemote method to send a
     * 'call' message to the server.
     */
    function _call(self, methodName, args, kwargs) {
        return self.getPageWidget().sendCallRemote(
            self, methodName, args, kwargs);
    },

    function callRemote(self, methodName /*, ... */) {
        var args = [];
        for (var idx = 2; idx < arguments.length; idx++) {
            args.push(arguments[idx]);
        }
        return self._call(methodName, args, {});
    },

    function callRemoteKw(self, methodName, kwargs) {
        return self._call(methodName, [], kwargs);
    });

/**
 * Given a Node, find all of its children (to any depth) with the
 * given attribute set to the given value.  Note: you probably don't
 * want to call this directly; instead, see
 * C{Nevow.Athena.Widget.nodesByAttribute}.
 */
Nevow.Athena.NodesByAttribute = function(root, attrName, attrValue) {
    return Divmod.Runtime.theRuntime.nodesByAttribute(root, attrName, attrValue);
};

Nevow.Athena.FirstNodeByAttribute = function(root, attrName, attrValue) {
    return Divmod.Runtime.theRuntime.firstNodeByAttribute(root, attrName, attrValue);
};

/**
 * Given a Node, find the single child node (to any depth) with the
 * given attribute set to the given value.  If there are more than one
 * Nodes which satisfy this constraint or if there are none at all,
 * throw an error.  Note: you probably don't want to call this
 * directly; instead, see C{Nevow.Athena.Widget.nodeByAttribute}.
 */
Nevow.Athena.NodeByAttribute = function(root, attrName, attrValue, /* optional */ defaultNode) {
    return Divmod.Runtime.theRuntime.nodeByAttribute(root, attrName, attrValue, defaultNode);
};

Nevow.Athena.server = new Nevow.Athena.RemoteReference(0);
var server = Nevow.Athena.server;

/**
 * The keycode for the 'ESC' key.
 */
Nevow.Athena.KEYCODE_ESCAPE = 27;


/**
 * Create a ReliableMessageDelivery hooked in to the appropriate global state
 * to manage the connection associated with the page.
 */
Nevow.Athena._createMessageDelivery = function (page) {
    return Nevow.Athena.ReliableMessageDelivery(
        function (synchronous /* = false */) {
            if (synchronous === undefined) {
                synchronous = false;
            }
            return Nevow.Athena.HTTPRequestOutput(
                page.transportURL(),
                [],
                [['Livepage-Id', page.livepageID],
                 ['Content-Type', 'text/x-json+athena']],
                synchronous);
        },
        page);
};


/**
 * Invoke the loaded method of the given widget and all of its child widgets.
 */
Nevow.Athena._recursivelyLoad = function _recursivelyLoad(widget) {
    if (widget.loaded) {
        widget.loaded();
    }
    for (var i = 0; i < widget.childWidgets.length; ++i) {
        Nevow.Athena._recursivelyLoad(widget.childWidgets[i]);
    }
};


/**
 * Athena Widgets
 *
 * This module defines a base class useful for adding behaviors to
 * discrete portions of a page.  These widgets can be independent of
 * other content on the same page, allowing separately developed
 * widgets to be combined, or multiple instances of a single widget to
 * appear repeatedly on the same page.
 */


/**
 * Error class thrown when an attempt is made to invoke a method which is
 * either undefined or unexposed.
 */
Nevow.Athena.NoSuchMethod = Divmod.Error.subclass("Nevow.Athena.NoSuchMethod");


/**
 * Error class thrown when an attempt is made to remove a child from a widget
 * which is not its parent.
 */
Nevow.Athena.NoSuchChild = Divmod.Error.subclass("Nevow.Athena.NoSuchChild");

Nevow.Athena.Widget = Nevow.Athena.RemoteReference.subclass('Nevow.Athena.Widget');
Nevow.Athena.Widget.methods(
    function __init__(self, widgetNode) {
        self.node = widgetNode;
        self.childWidgets = [];
        self.widgetParent = null;
        Nevow.Athena.Widget.upcall(self, "__init__",
                                   Nevow.Athena.athenaIDFromNode(widgetNode));
    },

    function addChildWidget(self, newChild) {
        self.childWidgets.push(newChild);
        newChild.setWidgetParent(self);
    },

    /**
     * Add a widget with the given ID, class, and markup as a child of this
     * widget.  Any required modules which have not already been imported will
     * be imported.
     *
     * @type info: Opaque handle received from the server where a
     * LiveFragment/Element was passed.
     *
     * @return: A Deferred which will fire with the newly created widget
     * instance once it has been added as a child.
     */
    function addChildWidgetFromWidgetInfo(self, info) {
        return self._addChildWidgetFromComponents(
            info.requiredModules,
            info.requiredCSSModules,
            info.id,
            info['class'],
            info.children,
            info.initArguments,
            info.markup
            );
    },

    /**
     * Actual implementation of dynamic widget instantiation.
     */
    function _addChildWidgetFromComponents(self,
                                           requiredModules,
                                           requiredCSSModules, widgetID,
                                           widgetClassName, children,
                                           initArguments, markup) {

        var moduleIndex;
        var childIndex;

        var importDeferreds;
        var allImportsDone;
        var topNode;
        var topWidgetClass;
        var childWidgetClass;
        var topWidget;
        var childWidget;
        var childInitArgs;
        var childNode;
        var childID;
        var parentWidget;

        var moduleURL;
        var moduleName;
        var moduleParts;
        var moduleObj;

        if (widgetID in Nevow.Athena.Widget._athenaWidgets) {
            throw new Error("You blew it.");
        }

        for (var i = 0; i < requiredCSSModules.length; i++) {
            /* we're doing this blindly; we don't know when this will
             * complete, but it doesn't matter hugely */
            Divmod.Runtime.theRuntime.loadStylesheet(requiredCSSModules[i]);
        }

        importDeferreds = [];
        for (moduleIndex = 0; moduleIndex < requiredModules.length; ++moduleIndex) {
            moduleName = requiredModules[moduleIndex][0];
            moduleURL = requiredModules[moduleIndex][1];

            moduleParts = moduleName.split('.');
            moduleObj = Divmod._global;

            for (var i = 0; i < moduleParts.length; ++i) {
                var partName = moduleParts[i];
                if (moduleObj[partName] === undefined) {
                    moduleObj[partName] = {
                        '__name__': moduleObj.__name__ + '.' + partName};
                }
                moduleObj = moduleObj[partName];
            }

            importDeferreds.push(
                Divmod.Runtime.theRuntime.loadScript(
                    moduleURL));
        }
        allImportsDone = Divmod.Defer.DeferredList(
            importDeferreds,
            /* fireOnOneCallback= */false,
            /* fireOnOneErrback= */true);
        allImportsDone.addCallback(
            function(ignored) {
                topNode = Divmod.Runtime.theRuntime.firstNodeByAttribute(
                    Divmod.Runtime.theRuntime.importNode(
                        Divmod.Runtime.theRuntime.parseXHTMLString(markup).documentElement,
                        true),
                    'id', Nevow.Athena.Widget.translateAthenaID(widgetID));

                topWidgetClass = Divmod.namedAny(widgetClassName);
                if (topWidgetClass === undefined) {
                    throw new Error("Bad class: " + widgetClassName);
                }

                initArguments.unshift(topNode);
                topWidget = topWidgetClass.apply(null, initArguments);
                Nevow.Athena.Widget._athenaWidgets[widgetID] = topWidget;

                for (childIndex = 0; childIndex < children.length; ++childIndex) {
                    childWidgetClass = Divmod.namedAny(children[childIndex]['class']);
                    childInitArgs = children[childIndex]['initArguments'];
                    childID = children[childIndex]['id'];

                    if (childID in Nevow.Athena.Widget._athenaWidgets) {
                        throw new Error("You blew it: " + childID);
                    }

                    childNode = Divmod.Runtime.theRuntime.firstNodeByAttribute(
                        topNode, 'id', Nevow.Athena.Widget.translateAthenaID(childID));

                    if (childWidgetClass === undefined) {
                        throw new Error("Broken: " + children[childIndex]['class']);
                    }

                    childInitArgs.unshift(childNode);
                    childWidget = childWidgetClass.apply(null, childInitArgs);

                    Nevow.Athena.Widget._athenaWidgets[childID] = childWidget;

                    parentWidget = Nevow.Athena.Widget.get(childNode.parentNode);
                    parentWidget.addChildWidget(childWidget);
                }
                self.addChildWidget(topWidget);

                Nevow.Athena._recursivelyLoad(topWidget);

                return topWidget;
            });

        return allImportsDone;
    },

    function setWidgetParent(self, widgetParent) {
        self.widgetParent = widgetParent;
    },


    /**
     * Schedule a function to be called after a specified delay.
     *
     * @type seconds: number
     * @param seconds: The number of seconds to wait.
     *
     * @type callable: function
     * @param callable: The function to call after the delay.
     *
     */
    function callLater(self, seconds, callable) {
        return Divmod.Runtime.DelayedCall(seconds * 1000, callable);
    },


    /**
     * Connect a DOM event on my node to a method on me, causing the method
     * with the event's name to be called on me when that event occurs.
     *
     * @param domEventName: the name of an event in the DOM, such as
     * "onclick", "onscroll", "onchange", etc.
     *
     * @param methodName: the method name on this widget to use.  Note that
     * you must connect the event to a method on this widget.  If unspecified,
     * this will be the same as L{domEventName}.
     *
     * @param domNode: a node (this widget's node, or one of its descendants)
     * where the event will be handled.  If unspecified, this will be the
     * widget's node.
     */
    function connectDOMEvent(self, domEventName, /* optional*/
                             methodName, domNode) {
        if (domNode === undefined) {
            domNode = self.node;
        }
        if (methodName === undefined) {
            methodName = domEventName;
        }
        domNode[domEventName] = Nevow.Athena.Widget._makeEventHandler(
            domEventName, methodName);
    },


    function nodeByAttribute(self, attrName, attrValue, /* optional */ defaultNode) {
        return Divmod.Runtime.theRuntime.nodeByAttribute(self.node, attrName, attrValue, defaultNode);
    },

    function firstNodeByAttribute(self, attrName, attrValue) {
        return Divmod.Runtime.theRuntime.firstNodeByAttribute(self.node, attrName, attrValue);
    },


    /**
     * Return translated version of the ID attribute value for the
     * provided id.
     */
    function translateNodeId(self, id) {
        return 'athenaid:' + self.objectID + '-' + id;
    },

    function nodeById(self, id) {
        var translatedId = self.translateNodeId(id);
        return Divmod.Runtime.theRuntime.getElementByIdWithNode(self.node, translatedId);
    },

    function nodesByAttribute(self, attrName, attrValue) {
        return Divmod.Runtime.theRuntime.nodesByAttribute(self.node, attrName, attrValue);
    },

    /**
     * Remove the given child widget from this widget.
     *
     * @param child: A widget which is currently a child of this widget.
     */
    function removeChildWidget(self, child) {
        for (var i = 0; i < self.childWidgets.length; ++i) {
            if (self.childWidgets[i] === child) {
                self.childWidgets.splice(i, 1);
                child.setWidgetParent(null);
                return;
            }
        }
        throw Nevow.Athena.NoSuchChild();
    },

    /**
     * Remove all the child widgets from this widget.
     */
    function removeAllChildWidgets(self) {
        for (var i=0; i<self.childWidgets.length; i++) {
            self.childWidgets[i].setWidgetParent(null);
        }
        self.childWidgets = [];
    },

    /**
     * Locally remove this widget from its parent and from the general widget
     * tracking system.
     */
    function _athenaDetachClient(self) {
        for (var i = 0; i < self.childWidgets.length; ++i) {
            self.childWidgets[i]._athenaDetachClient();
        }
        if (self.widgetParent !== null) {
            self.widgetParent.removeChildWidget(self);
        }
        delete Nevow.Athena.Widget._athenaWidgets[self.objectID];
        self.detached();
    },

    /**
     * Disconnect this widget from its server-side component and remove it from
     * the tracking collection.
     *
     * This function will *not* work correctly if the parent/child
     * relationships of this widget do not exactly match the parent/child
     * relationships of the corresponding fragments or elements on the server.
     */
    function detach(self) {
        var result = self.callRemote('_athenaDetachServer');
        result.addCallback(
            function(ignored) {
                self._athenaDetachClient();
            });
        return result;
    },

    /**
     * Application-level callback invoked when L{detach} succeeds or when the
     * server invokes the detach logic from its side.
     *
     * This is invoked after this widget has been disassociated from its parent
     * and from the page.
     *
     * Override this.
     */
    function detached(self) {
    });

/**
 * Create a function that will return a handler for a DOM event.
 *
 * This function is a part of the above L{connectDOMEvent} implementation, but
 * must be a separate top-level function due to a bug in IE.
 *
 * http://www.bazon.net/mishoo/articles.epl?art_id=824
 */
Nevow.Athena.Widget._makeEventHandler = function (domEventName, methodName) {
    return function () {
        return Nevow.Athena.Widget.handleEvent(this, domEventName, methodName);
    };
};

Nevow.Athena.Widget._athenaWidgets = {};

/**
 * Given any node within a Widget (the client-side representation of a
 * LiveFragment), return the instance of the Widget subclass that corresponds
 * with that node, creating that Widget subclass if necessary.
 */
Nevow.Athena.Widget.get = function(node) {
    var widgetNode = Nevow.Athena.nodeByDOM(node);
    var widgetId = Nevow.Athena.athenaIDFromNode(widgetNode);
    if (Nevow.Athena.Widget._athenaWidgets[widgetId] == null) {
        var widgetClass = Nevow.Athena.athenaClassFromNode(widgetNode);
        var initNode = document.getElementById('athena-init-args-' + widgetId);
        var initText = initNode.value;
        var initArgs = eval(initText);
        initArgs.unshift(widgetNode);
        Nevow.Athena.Widget._athenaWidgets[widgetId] = widgetClass.apply(null, initArgs);
    }
    return Nevow.Athena.Widget._athenaWidgets[widgetId];
};

Nevow.Athena.Widget.dispatchEvent = function (widget, eventName, handlerName, callable) {
    return Nevow.Athena.page.dispatchEvent(widget, eventName, handlerName, callable);
};

/**
 * Given a node and a method name in an event handling context, dispatch the
 * event to the named method on the widget which owns the given node.  This
 * also sets up error handling and does return value translation as
 * appropriate for an event handler.  It also pauses the outgoing message
 * queue to allow multiple messages from the event handler to be batched up
 * into a single request.
 */
Nevow.Athena.Widget.handleEvent = function handleEvent(node, eventName, handlerName) {
    var widget = Nevow.Athena.Widget.get(node);
    var method = widget[handlerName];
    var result = false;
    if (method === undefined) {
        Divmod.msg("Undefined event handler: " + handlerName);
    } else {
        result = Nevow.Athena.Widget.dispatchEvent(
            widget, eventName, handlerName,
            function() {
                return method.call(widget, node);
            });
    }
    return result;
};

/**
 * Return translated widget id.
 */
Nevow.Athena.Widget.translateAthenaID = function(widgetId) {
    return 'athena:' + widgetId;
};

/**
 * Retrieve the Widget with the given widget id.
 */
Nevow.Athena.Widget.fromAthenaID = function(widgetId) {
    var widget = Nevow.Athena.Widget._athenaWidgets[widgetId];
    if (widget != undefined) {
        return widget;
    }

    return Nevow.Athena.Widget.get(
        document.getElementById(Nevow.Athena.Widget.translateAthenaID(widgetId)));
};

Nevow.Athena.callByAthenaID = function(athenaID, methodName, varargs) {
    var widget = Nevow.Athena.Widget.fromAthenaID(athenaID);
    var method = widget[methodName];
    Divmod.debug('widget', 'Invoking ' + methodName + ' on ' + widget + '(' + widget[methodName] + ')');
    if (method == undefined) {
        throw new Error(widget + ' has no method ' + methodName);
    }
    return method.apply(widget, varargs);
};

Nevow.Athena.consoleDoc = (
    '<html>' +
    '  <head>' +
    '    <title>Log Console</title>' +
    '    <style type="text/css">' +
    '    body {' +
    '      background-color: #fff;' +
    '      color: #333;' +
    '      font-size: 8pt;' +
    '      margin: 0;' +
    '      padding: 0;' +
    '    }' +
    '    #console {' +
    '      font-family: monospace;' +
    '    }' +
    '    .log-message-error {' +
    '      margin: 0 0 0 0;' +
    '      padding: 0;' +
    '      border-bottom: 1px dashed #ccf;' +
    '      color: red;' +
    '    }' +
    '    .log-message-transport {' +
    '      margin: 0 0 0 0;' +
    '      padding: 0;' +
    '      border-bottom: 1px dashed #ccf;' +
    '      color: magenta;' +
    '    }' +
    '    .log-message-request {' +
    '      margin: 0 0 0 0;' +
    '      padding: 0;' +
    '      border-bottom: 1px dashed #ccf;' +
    '      color: blue;' +
    '    }' +
    '    .timestamp {' +
    '      display: block;' +
    '      font-weight: bold;' +
    '      color: #999;' +
    '    }' +
    '    </style>' +
    '  </head>' +
    '  <body>' +
    '    <div id="console">' +
    '    </div>' +
    '    <hr />' +
    '    <a id="clear" href="">Clear</button>' +
    '  </body>' +
    '</html>');

Nevow.Athena.IntrospectionWidget = Nevow.Athena.Widget.subclass('Nevow.Athena.IntrospectionWidget');
Nevow.Athena.IntrospectionWidget.methods(
    function __init__(self, node) {
        Nevow.Athena.IntrospectionWidget.upcall(self, '__init__', node);

        self.infoNodes = {
            'toggleDebugging': self.nodeByAttribute('class', 'toggle-debug')
        };

        self.infoNodes['toggleDebugging'].onclick = function() { self.toggleDebugging(); return false; };

        self.events = [];
        self.eventLimit = 1000;

        self._logWindow = null;
        self._logNode = null;

        Divmod.logger.addObserver(function(event) { self.observe(event); });

        self.setDebuggingDisplayStyle();
    },

    function observe(self, event) {
        self.events.push(event);
        if (self.events.length > self.eventLimit) {
            self.events.shift();
        }
        if (self._logNode != null) {
            self._addEvent(event);
        }
    },

    function _addEvent(self, event) {
        var node = self._logNode;
        var document = self._logWindow.document;

        var div = document.createElement('div');
        if (event['isError']) {
            div.setAttribute('class', 'log-message-error');
        } else if (event['channel']) {
            div.setAttribute('class', 'log-message-' + event['channel']);
        }
        div.appendChild(document.createTextNode(event['message']));
        node.appendChild(div);
        div.scrollIntoView(false);
    },

    function _clearEvents(self) {
        while (self._logNode.firstChild) {
            self._logNode.removeChild(self._logNode.firstChild);
        }
    },

    function _openLogWindow(self) {
        self._logWindow = window.open('', 'Nevow_Athena_Log_Window', 'width=640,height=480,scrollbars');
        self._logWindow.document.write(Nevow.Athena.consoleDoc);
        self._logWindow.document.close();
        self._logNode = self._logWindow.document.getElementById('console');
        self._logWindow.document.title = 'Mantissa Debug Log Viewer';
        for (var i = 0; i < self.events.length; i++) {
            self._addEvent(self.events[i]);
        }

        self._clearNode = self._logWindow.document.getElementById('clear');
        self._clearNode.onclick = function(event) { self._clearEvents(); return false; };
    },

    function _closeLogWindow(self) {
        if (self._logWindow) {
            self._logWindow.close();
            self._logWindow = null;
            self._logNode = null;
        }
    },

    function toggleDebugging(self) {
        Divmod.debugging ^= 1;
        self.setDebuggingDisplayStyle();
    },

    function setDebuggingDisplayStyle(self) {
        if (Divmod.debugging) {
            self.infoNodes['toggleDebugging'].setAttribute('class', 'nevow-athena-debugging-enabled');
            self._openLogWindow();
        } else {
            self.infoNodes['toggleDebugging'].setAttribute('class', 'nevow-athena-debugging-disabled');
            self._closeLogWindow();
        }
    });


/**
 * Instantiate Athena Widgets.
 */
Nevow.Athena.Widget._instantiateOneWidget = function(cls, node) {
    Divmod.debug("widget", "Found Widget class " + cls + ", instantiating.");
    var inst = cls.get(node);
    Divmod.debug("widget", "Widget class " + cls + " instantiated.");
    try {
        var widgetParent = Nevow.Athena.Widget.get(node.parentNode);
        widgetParent.addChildWidget(inst);
    } catch (noParent) {
        // Right now we're going to do nothing here.
        Divmod.debug("widget", "No parent found for widget " + inst);
    }
    if (inst.loaded != undefined) {
        inst.loaded();
        Divmod.debug("widget", "Widget class " + cls + " loaded.");
    }
    if (inst.nodeInserted != undefined) {
        inst.nodeInserted();
    }
};

Nevow.Athena.Widget._pageLoaded = false;
Nevow.Athena.Widget._waitingWidgets = {};
Nevow.Athena.Widget._widgetNodeAdded = function(nodeId) {
    Nevow.Athena.Widget._waitingWidgets[nodeId] = null;
    if (Nevow.Athena.Widget._pageLoaded) {
        if (Nevow.Athena.Widget._instantiationTimer == null) {
            Nevow.Athena.Widget._instantiationTimer = setTimeout(Nevow.Athena.Widget._instantiateWidgets, 1);
        }
    }
};

Nevow.Athena.Widget._instantiateWidgets = function() {
    var widgetIds = Nevow.Athena.Widget._waitingWidgets;
    Nevow.Athena.Widget._waitingWidgets = {};

    Nevow.Athena.Widget._instantiationTimer = null;

    for (var widgetId in widgetIds) {
        var node = document.getElementById(Nevow.Athena.Widget.translateAthenaID(widgetId));
        if (node == null) {
            Divmod.debug("widget", "Widget scheduled for addition was missing.  Id = " + widgetId);
        } else {
            var cls = Nevow.Athena.athenaClassFromNode(node);
            Nevow.Athena.Widget._instantiateOneWidget(cls, node);
        }
    }
};

/**
 * Initialize state in this module that only the server knows about.
 *
 * See the Python module "nevow.athena" for where this is expected to be
 * called; specifically the "_bootstraps" method of LivePage.
 *
 * @param pageClassName: a string, the fully-qualified name of a page class.
 *
 * @param clientID: a string, the unique identifier of the current page's live
 * server-side peer.
 */
Nevow.Athena.bootstrap = function (pageClassName, clientID) {
    var self = this;
    var pageClass = Divmod.namedAny(pageClassName);
    self.page = pageClass(clientID, Nevow.Athena._createMessageDelivery);
    Divmod.Base.addToCallStack(
        window, 'onkeypress', self.page.makeHandler('onkeypress'));


    Divmod.Runtime.theRuntime.addLoadEvent(function transportStartup() {
            Divmod.Runtime.theRuntime.addBeforeUnloadHandler(
                window, self.page.makeHandler('onbeforeunload'));
            Divmod.debug("transport", "starting up");
            self.page.deliveryChannel.start();
            Divmod.debug("transport", "started up");

            Divmod.debug("widget", "Instantiating live widgets");
            Nevow.Athena.Widget._pageLoaded = true;
            Nevow.Athena.Widget._instantiateWidgets();
            Divmod.debug("widget", "Finished instantiating live widgets");
        });
};

/**
 * Set up to have a function called when the LivePage connection has been
 * lost, either due to an explicit close, a timeout, or some other error.
 * The function will be invoked with one argument, probably a Failure
 * indicating the reason the connection was lost.
 */
Nevow.Athena.notifyOnDisconnect = function (disconnectHandler) {
    return Nevow.Athena.page.notifyOnDisconnect(disconnectHandler);
};
