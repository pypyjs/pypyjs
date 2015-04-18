// import Divmod.Runtime
// import Nevow.Athena

Nevow.Athena.Tests.WidgetInitializerArguments = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.WidgetInitializerArguments');
Nevow.Athena.Tests.WidgetInitializerArguments.methods(
    function __init__(self, node) {
        Nevow.Athena.Tests.WidgetInitializerArguments.upcall(self, '__init__', node);
        self.args = [];
        for (var i = 2; i < arguments.length; ++i) {
            self.args.push(arguments[i]);
        }
    },

    function test_widgetInitializationArguments(self) {
        return self.callRemote('test', self.args);
    });


Nevow.Athena.Tests.CallRemoteTestCase = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.CallRemoteTestCase');
Nevow.Athena.Tests.CallRemoteTestCase.methods(
    /**
     * Test that calling a method which is not exposed properly results in a
     * failed Deferred.
     */
    function test_invalidRemoteMethod(self) {
        return self.assertFailure(
            self.callRemote("noSuchMethod"),
            [Nevow.Athena.NoSuchMethod]);
    });

Nevow.Athena.Tests.ClientToServerArgumentSerialization = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.ClientToServerArgumentSerialization');
Nevow.Athena.Tests.ClientToServerArgumentSerialization.methods(
    function test_clientToServerArgumentSerialization(self) {
        var L = [1, 1.5, 'Hello world'];
        var O = {'hello world': 'object value'};
        return self.callRemote('test', 1, 1.5, 'Hello world', L, O);
    });

Nevow.Athena.Tests.ClientToServerResultSerialization = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.ClientToServerResultSerialization');
Nevow.Athena.Tests.ClientToServerResultSerialization.methods(
    function test_clientToServerResultSerialization(self) {
        var L = [1, 1.5, 'Hello world'];
        var O = {'hello world': 'object value'};
        var d = self.callRemote('test', 1, 1.5, 'Hello world', L, O);
        d.addCallback(function(result) {
            self.assertEquals(result[0], 1);
            self.assertEquals(result[1], 1.5);
            self.assertEquals(result[2], 'Hello world');
            self.assertEquals(result[3][0], 1);
            self.assertEquals(result[3][1], 1.5);
            self.assertEquals(result[3][2], 'Hello world');
            self.assertEquals(result[4]['hello world'], 'object value');
        });
        return d;
    });

Nevow.Athena.Tests.ExceptionFromServer = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.ExceptionFromServer');
Nevow.Athena.Tests.ExceptionFromServer.methods(
    function test_exceptionFromServer(self) {
        var d;
        var s = 'This exception should appear on the client.';
        d = self.callRemote('testSync', s);
        d.addCallbacks(
            function(result) {
                self.fail('Erroneously received a result: ' + result);
            },
            function(f) {
                var idx = f.error.message.indexOf(s);
                if (idx == -1) {
                    self.fail('Did not find expected message in error message: ' + f.error.message);
                }
            });
        return d;
    });

Nevow.Athena.Tests.JSONRoundtrip = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.JSONRoundtrip');
Nevow.Athena.Tests.JSONRoundtrip.methods(
    function test_jsonRoundTrip(self) {
        return self.callRemote('test');
    },

    function identity(self, value) {
        return value;
    });

Nevow.Athena.Tests.AsyncExceptionFromServer = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.AsyncExceptionFromServer');
Nevow.Athena.Tests.AsyncExceptionFromServer.methods(
    function test_asyncExceptionFromServer(self) {
        var d;
        var s = 'This exception should appear on the client.';
        d = self.callRemote('testAsync', s);
        d.addCallbacks(
            function(result) {
                self.fail('Erroneously received a result: ' + result);
            },
            function(f) {
                var idx = f.error.message.indexOf(s);
                if (idx == -1) {
                    self.fail('Did not find expected message in error message: ' + f.error.message);
                }
            });
        return d;
    });

Nevow.Athena.Tests.ExceptionFromClient = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.ExceptionFromClient');
Nevow.Athena.Tests.ExceptionFromClient.methods(
    function test_exceptionFromClient(self) {
        var d;
        d = self.callRemote('loopbackError');
        d.addCallbacks(
            function (result) {
            },
            function (f) {
                self.fail('Received unexpected exception: ' + f.error.message);
            });
        return d;
    },

    function generateError(self) {
        throw new Error('This is a test exception');
    });

Nevow.Athena.Tests.AsyncExceptionFromClient = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.AsyncExceptionFromClient');
Nevow.Athena.Tests.AsyncExceptionFromClient.methods(
    function test_asyncExceptionFromClient(self) {
        var d;
        d = self.callRemote('loopbackError');
        d.addCallbacks(
            function (result) {
                if (!result) {
                    self.fail('Received incorrect Javascript exception or no traceback.');
                }
            },
            function (f) {
                self.fail('Received unexpected exception: ' + f.error.message);
            });
        return d;
    },

    function generateError(self) {
        return Divmod.Defer.fail(Error('This is a deferred test exception'));
    });


/**
 * Helper class used to verify that a Python object which provides
 * nevow.inevow.IAthenaTransportable can specify a JavaScript class which
 * will be instantiated to represent it in the browser.
 */
Nevow.Athena.Tests.CustomTransportable = Divmod.Class.subclass(
    'Nevow.Athena.Tests.CustomTransportable');
Nevow.Athena.Tests.CustomTransportable.methods(
    function __init__(self, firstArgument, secondArgument, thirdArgument) {
        self.firstArgument = firstArgument;
        self.secondArgument = secondArgument;
        self.thirdArgument = thirdArgument;
    });


Nevow.Athena.Tests.ServerToClientArgumentSerialization = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.ServerToClientArgumentSerialization');
Nevow.Athena.Tests.ServerToClientArgumentSerialization.methods(
    function test_serverToClientArgumentSerialization(self) {
        return self.callRemote('test');
    },

    function reverse(self, anInteger, aFloat, aString, anObject, aCustomObject) {
        self.assertEquals(anInteger, 1);
        self.assertEquals(aFloat, 1.5);
        self.assertEquals(aString, 'hello');
        self.assertEquals(anObject['world'], 'value');
        self.failUnless(aCustomObject instanceof Nevow.Athena.Tests.CustomTransportable);
        self.assertEquals(aCustomObject.firstArgument, "Hello");
        self.assertEquals(aCustomObject.secondArgument, 5);
        self.assertEquals(aCustomObject.thirdArgument, "world");
    });

Nevow.Athena.Tests.ServerToClientResultSerialization = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.ServerToClientResultSerialization');
Nevow.Athena.Tests.ServerToClientResultSerialization.methods(
    function test_serverToClientResultSerialization(self) {
        return self.callRemote('test');
    },

    function reverse(self) {
        return [1, 1.5, 'hello', {'world': 'value'}];
    });

Nevow.Athena.Tests.WidgetInATable = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.WidgetInATable');
Nevow.Athena.Tests.WidgetInATable.methods(
    function test_widgetInATable(self) {
        // Nothing to do
    });

Nevow.Athena.Tests.WidgetIsATable = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.WidgetIsATable');
Nevow.Athena.Tests.WidgetIsATable.methods(
    function test_widgetIsATable(self) {
        // Nothing to do
    });

Nevow.Athena.Tests.ChildParentRelationshipTest = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.ChildParentRelationshipTest');
Nevow.Athena.Tests.ChildParentRelationshipTest.methods(
    function checkParent(self, proposedParent) {
        self.assertEquals(self.widgetParent, proposedParent);
    },

    function test_childParentRelationship(self) {
        var deferredList = function(finalDeferred, counter) {
            if (counter == 0) {
                finalDeferred.callback(null);
            }
            var callback = function(ignored) {
                counter -= 1;
                Divmod.log('test', 'One more down, ' + counter + ' to go.');
                if (counter == 0) {
                    finalDeferred.callback(null);
                }
            };
            return callback;
        };

        var result = self.callRemote('getChildCount');

        result.addCallback(function(count) {
            Divmod.log('test', 'Discovered I have ' + count + ' children');
            var d = new Divmod.Defer.Deferred();
            d.addCallback(function() { self.node.style.border = 'thin solid green'; });
            var cb = deferredList(d, count);
            self.assertEquals(self.childWidgets.length, count);
            for (var i = 0; i < self.childWidgets.length; i++) {
                var childWidget = self.childWidgets[i];
                childWidget.checkParent(self);
                childWidget.test_childParentRelationship().addCallback(cb).addErrback(function(err) { d.errback(err); });
            }
            return d;
        });
        return result;
    });

Nevow.Athena.Tests.AutomaticClass = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.AutomaticClass');
Nevow.Athena.Tests.AutomaticClass.methods(
    function test_automaticClass(self) {
        // Nothing to do here
    });


Nevow.Athena.Tests.ImportBeforeLiteralJavaScript = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.ImportBeforeLiteralJavaScript');
Nevow.Athena.Tests.ImportBeforeLiteralJavaScript.methods(
    function test_importBeforeLiteralJavaScript(self) {
        self.assertEquals(importBeforeLiteralJavaScriptResult, false);
    });

Nevow.Athena.Tests.AthenaHandler = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.AthenaHandler');
Nevow.Athena.Tests.AthenaHandler.methods(
    /**
     * Call the given object if it is a function.  eval() it if it is a string.
     */
    function _execute(self, thisObject, stringOrFunction) {
        if (typeof stringOrFunction === 'string') {
            return (
                function() {
                    return eval(stringOrFunction);
                }).call(thisObject);
        } else if (typeof stringOrFunction === 'function') {
            return stringOrFunction.call(thisObject);
        } else {
            self.fail(
                "_execute() given something that is neither a " +
                "string nor a function: " + stringOrFunction);
        }
    },

    function test_athenaHandler(self) {
        self.handled = false;
        var button = self.node.getElementsByTagName('button')[0];
        var onclick = button.onclick;
        self.assertEquals(self._execute(button, onclick), false);
        self.assertEquals(self.handled, true);
    },

    function handler(self, evt) {
        self.handled = true;
        return false;
    });

/**
 * Simple widget to be dynamically instantiated for testing nodeInserted
 * behaviour.
 */
Nevow.Athena.Tests.NodeInsertedHelper = Nevow.Athena.Widget.subclass('Nevow.Athena.Tests.NodeInsertedHelper');
Nevow.Athena.Tests.NodeInsertedHelper.methods(
    /**
     * Detect whether nodeInserted is called; Athena should do this when (and
     * only when) instantiating us statically.
     */
    function nodeInserted(self) {
        self.inserted = true;
    });

Nevow.Athena.Tests.NodeLocation = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.NodeLocation');
Nevow.Athena.Tests.NodeLocation.methods(
    function test_firstNodeByAttribute(self) {
        var node = self.childWidgets[0].firstNodeByAttribute("class", "foo");
        self.assertEquals(node.className, "foo");
        self.assertEquals(node.tagName.toLowerCase(), "label");
    },

    /**
     * Test that nodeById finds the node.
     */
    function test_nodeById(self) {
        var node = self.childWidgets[0].childWidgets[0].nodeById('username');
        self.assertEquals(node.className, 'bar');
        self.assertEquals(node.tagName.toLowerCase(), 'input');
    },

    /**
     * Test that nodeById finds the node in the parent widget, not the child
     * widget.
     */
    function test_nodeByIdParent(self) {
        var node = self.childWidgets[0].nodeById('username');
        self.assertEquals(node.className, 'foo');
        self.assertEquals(node.tagName.toLowerCase(), 'input');
    },

    /**
     * Test that ID mangling mangles label.for as well as id attributes. Label
     * and for must be equal.
     */
    function test_matchingLabelForAndId(self) {
        var label = self.childWidgets[0].firstNodeByAttribute("class", "foo");
        var labelForAttribute = Divmod.Runtime.theRuntime.getAttribute(label, "for");
        var input = self.childWidgets[0].nodeById('username');
        self.assertEquals(labelForAttribute, input["id"]);
    },

    /**
     * Test that nodeById throws NodeNotFound when the node cannot be located.
     */
    function test_nodeByIdNotFound(self) {
        var _find = function () { return self.childWidgets[0].nodeById('nonexistent'); };
        self.assertThrows(Divmod.Runtime.NodeNotFound, _find);
    },

    function addDynamicWidget(self, child, method) {
        var d = child.callRemote(method);
        d.addCallback(
            function (widgetInfo) {
                return child.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        return d;
    },

    /**
     * Test that nodeById is able to locate nodes in a dynamically instantiated
     * widget that has not yet been added as a child somewhere in the browser
     * document.
     */
    function test_nodeByIdInDynamicOrphan(self) {
        var child = self.childWidgets[1];
        var d = self.addDynamicWidget(child, 'getDynamicWidget');
        d.addCallback(
            function (widget) {
                var node = widget.nodeById('username');
                self.assertEquals(node.className, 'foo');
                self.assertEquals(node.tagName.toLowerCase(), 'input');
            });
        return d;
    },

    /**
     * Test that nodeById is able to locate nodes in a dynamically instantiated
     * widget that has already been added as a child somewhere in the browser
     * document.
     */
    function test_nodeByIdInDynamicChild(self) {
        var child = self.childWidgets[1];
        var d = self.addDynamicWidget(child, 'getDynamicWidget');
        d.addCallback(
            function (widget) {
                child.node.appendChild(widget.node);
                var node = widget.nodeById('username');
                self.assertEquals(node.className, 'foo');
                self.assertEquals(node.tagName.toLowerCase(), 'input');
            });
        return d;
    },

    function test_nodeByIdNotFoundInDynamicOrphan(self) {
        var child = self.childWidgets[1];
        var d = self.addDynamicWidget(child, 'getDynamicWidget');
        d.addCallback(
            function (widget) {
                var _find = function () { return widget.nodeById('nonexistent'); };
                self.assertThrows(Divmod.Runtime.NodeNotFound, _find);
            });
        return d;
    },

    /**
     * Detect whether nodeInserted is called; Athena should do this when (and
     * only when) instantiating us statically.
     */
    function nodeInserted(self) {
        self.inserted = true;
    },

    /**
     * Test that nodeInserted is called on a widget that is statically
     * instantiated.
     */
    function test_staticWidget(self) {
        self.assertEqual(self.inserted, true);
    },

    /**
     * Test that nodeInserted is *not* called on a widget that is dynamically
     * instantiated.
     */
    function test_dynamicWidget(self) {
        var child = self.childWidgets[1];
        var d = self.addDynamicWidget(child, 'getNodeInsertedHelper');
        d.addCallback(
            function (widget) {
                self.assertNotEqual(widget.inserted, true);
            });
        return d;
    });


Nevow.Athena.Tests.DynamicWidgetClass = Nevow.Athena.Widget.subclass('Nevow.Athena.Tests.DynamicWidgetClass');
Nevow.Athena.Tests.DynamicWidgetClass.methods(
    function someMethod(self) {
        /*
         * Do something that hits our Fragment on the server to make sure we
         * can.
         */
        return self.callRemote('someMethod');
    });


/**
 * Test that retrieving several LiveFragments from the server using a
 * method call returns something which can be passed to
 * L{Nevow.Athena.Widget.getDynamicWidgetInfo} to add new widgets to the
 * page.
 */
Nevow.Athena.Tests.DynamicWidgetInstantiation = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.DynamicWidgetInstantiation');
Nevow.Athena.Tests.DynamicWidgetInstantiation.methods(
    /**
     * Test that a s->c C{callRemote} can pass a widget.
     *
     * In other words, test that this python code:
     * C{self.callRemote('takeWidget', widget)} works correctly.
     */
    function test_childWidgetAsArgument(self) {
        // ask the server to make a remote call
        var d = self.callRemote("getDynamicWidgetLater");
        d.addCallback(
            function (ignored) {
                var d2 = self._childWidgetAsArgumentDeferred.addCallback(
                    function (childWidget) {
                        self.assertEqual(childWidget.widgetParent, self);
                        var d3 = childWidget.callRemote('someMethod');
                        d3.addCallback(
                            function (ret) {
                                self.assertEqual(ret, 'foo');
                        });
                        return d3;
                });
                return d2;
        });
        return d;
    },

    /**
     * A callable which the server can C{callRemote}, passing a widget as an
     * argument.  C{widgetinfo} is the marshalled form of the widget.
     *
     * @return null because we cannot, at present, serialize widgets from
     * client to server.
     */
    function sendWidgetAsArgument(self, widgetinfo) {
        self._childWidgetAsArgumentDeferred =
                self.addChildWidgetFromWidgetInfo(widgetinfo);
        return null;
    },

    /**
     * Test that widgets with non-XHTML namespaces can be sent server to
     * client.
     *
     * The widget returned by the server should be rebuilt with the same
     * C{namespaceURI} it was given at render time.
     */
    function test_nonXHTMLWidgetReturn(self) {
        var result = self.callRemote("getNonXHTMLWidget");
        result.addCallback(
            function _(info) {
                return self.addChildWidgetFromWidgetInfo(info)
            });
        result.addCallback(
            function (childWidget) {
                self.assertEqual(childWidget.widgetParent, self);
                self.assertEqual(childWidget.node.namespaceURI,
                        'http://www.w3.org/2000/svg');
            });
        return result;
    },

    /**
     * Test the API for adding a widget based on an ID, class name, and
     * __init__ arguments to an existing page.
     */
    function test_addChildWidgetFromComponents(self) {
        var widgetID;
        var widgetClass;

        /*
         * Get a widget from the server
         */
        var result = self.callRemote('getDynamicWidgetInfo');
        result.addCallback(
            function(widgetInfo) {
                widgetID = widgetInfo.id;
                widgetClass = widgetInfo.klass;

                /*
                 * Server isn't going to give us any markup because markup is
                 * fugly.  So, construct the widget's root node ourselves.  It
                 * still needs to have all the special attributes for anything
                 * to work right.
                 */
                return self._addChildWidgetFromComponents(
                    [], [], widgetID, widgetClass, [], [],
                    '<span xmlns="http://www.w3.org/1999/xhtml" id="athena:' +
                    widgetID + '" class="' + widgetClass + '" />');
            });
        result.addCallback(
            function(childWidget) {
                self.assertEqual(Nevow.Athena.Widget.get(childWidget.node), childWidget);
                self.assertEqual(childWidget.widgetParent, self);
                self.assertEqual(self.childWidgets[self.childWidgets.length - 1], childWidget);
                return childWidget.someMethod();
            });
        result.addCallback(
            function(methodResult) {
                self.assertEqual(methodResult, 'foo');
            });
        return result;
    },

    /**
     * Test the API for adding a widget based on a messy pile of data.
     */
    function test_addChildWidgetFromWidgetInfo(self) {
        var result = self.callRemote('getDynamicWidget');
        result.addCallback(
            function(widget) {
                return self.addChildWidgetFromWidgetInfo(widget);
            });
        result.addCallback(
            function(widget) {
                self.assertEqual(Nevow.Athena.Widget.get(widget.node), widget);
                self.assertEqual(widget.widgetParent, self);
                self.assertEqual(self.childWidgets[self.childWidgets.length - 1], widget);

                return widget.someMethod();
            });
        result.addCallback(
            function(methodResult) {
                self.assertEqual(methodResult, 'foo');
            });
        return result;
    },

    /**
     * Verify that removeChildWidget sets the specified widget's parent to null
     * and removes it from the parent's children array.
     */
    function test_removeChildWidget(self) {
        var result = self.callRemote('getDynamicWidget');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.removeChildWidget(widget);
                self.assertEqual(widget.widgetParent, null);
                for (var i = 0; i < self.childWidgets.length; ++i) {
                    self.assertNotEqual(self.childWidgets[i], widget);
                }
            });
        return result;
    },

    /**
     * Verify that removeChildWidget throws the appropriate error when an
     * attempt is made to remove a child from a widget which is not its parent.
     */
    function test_invalidRemoveChildWidget(self) {
        self.assertThrows(
            Nevow.Athena.NoSuchChild,
            function() {
                self.removeChildWidget({});
            });
    },

    /**
     * Test that removeAllChildWidgets leaves the child widget list empty
     * and ensures that the removed widgets have a null parent.
     */
    function test_removeAllChildWidgets(self) {
        var result = self.callRemote('getDynamicWidget');
        result.addCallback(
            function(widget) {
                return self.addChildWidgetFromWidgetInfo(widget);
            });
        result.addCallback(
            function(widget) {
                self.removeAllChildWidgets();
                self.assertEqual(widget.widgetParent, null);
                self.assertEqual(self.childWidgets.length, 0);
            });
        return result;
    },

    /**
     * Helper for L{test_detachOrphan} and L{test_serverSideDetachOrphan}.
     *
     * @param detach: A one-argument callable which will be invoked with a
     * widget and should detach it in whatever way is being tested and return a
     * Deferred which fires when the detach has been completed.
     */
    function _detachTest(self, detach) {
        var result = self.callRemote('getAndRememberDynamicWidget');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                /*
                 * Orphan it.
                 */
                self.removeChildWidget(widget);

                /*
                 * Sanity check
                 */
                self.failUnless(
                    widget.objectID in Nevow.Athena.Widget._athenaWidgets);

                /*
                 * Actually get rid of it.
                 */
                var d = detach(widget);

                d.addCallback(
                    function(ignored) {
                        return widget;
                    });
                return d
            });
        result.addCallback(
            function(widget) {
                /*
                 * Locally, athena should not be tracking or referencing this
                 * object any more.
                 */
                self.failIf(
                    widget.objectID in Nevow.Athena.Widget._athenaWidgets);

                /*
                 * The server should also have forgotten about it.
                 */
                return self.callRemote("assertSavedWidgetRemoved");
            });
        return result;
    },

    /**
     * Verify that a widget with no parent can be disassociated from its
     * server-side component and removed from Athena's tracking.
     */
    function test_detachOrphan(self) {
        return self._detachTest(
            function(widget) {
                return widget.detach();
            });
    },

    /**
     * Similar to L{test_detachOrphan}, but perform the detach using the
     * server-side API.
     */
    function test_serverSideDetachOrphan(self) {
        return self._detachTest(
            function(widget) {
                return self.callRemote('detachSavedDynamicWidget');
            });
    },

    /**
     * Helper for L{test_detachedCallback} and L{test_remoteDetachedCallback}.
     *
     * @param detach: A one-argument callable which will be invoked with a
     * widget and should detach it in whatever way is being tested and return a
     * Deferred which fires when the detach has been completed.
     */
    function _detachedCallbackTest(self, detach) {
        var detachCalls = [];
        var result = self.callRemote('getAndRememberDynamicWidget');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                /*
                 * Make sure we notice the detached callback.
                 */
                function detached() {
                    var id = widget.objectID;
                    var notWidget = Nevow.Athena.Widget._athenaWidgets[id];
                    detachCalls.push([widget.widgetParent, notWidget]);
                };

                widget.detached = detached;

                /*
                 * Do the detach.
                 */
                return detach(widget);
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(detachCalls.length, 1);
                self.assertEqual(detachCalls[0][0], null);
                self.assertEqual(detachCalls[0][1], undefined);
            });
        return result;
    },

    /**
     * Verify that the C{detached} widget callback is invoked when a widget is
     * detached from this side of the connection.
     */
    function test_detachedCallback(self) {
        return self._detachedCallbackTest(
            function(widget) {
                return widget.detach();
            });
    },

    function _testDetachWithChildren(self, detach) {
        var parent = null;
        var child = null;
        var result = self.callRemote('getAndSaveDynamicWidgetWithChild');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                parent = widget;
                child = widget.childWidgets[0];
                return widget.detach();
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(parent.childWidgets.length, 0);
                self.assertEqual(parent.widgetParent, null);
                self.assertEqual(child.widgetParent, null);

                var widgets = Nevow.Athena.Widget._athenaWidgets;
                self.failIf(parent.objectID in widgets);
                self.failIf(child.objectID in widgets);
            });
        return result;
    },

    /**
     * Like C{test_detach}, but cover the case where a detached widget has
     * children itself.  Verify that the children are detached as well.
     */
    function test_detachWithChildren(self) {
        return self._testDetachWithChildren(
            function(widget) {
                return widget.detach();
            });
    },

    /**
     * Like C{test_detach}, but cover the case where a detached widget has
     * children itself.  Verify that the children are detached as well.
     */
    function test_serverSideDetachWithChildren(self) {
        return self._testDetachWithChildren(
            function(widget) {
                return widget.callRemote('detachSavedDynamicWidget');
            });
    },

    /**
     * Test dynamic instantiation of a widget defined in a module which has not
     * yet been imported.
     */
    function test_dynamicImportWidget(self) {
        /*
         * Sanity check
         */
        self.assertEqual(Nevow.Athena.Tests.Resources, undefined);

        var result = self.callRemote("getWidgetWithImports");
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.failUnless(widget instanceof Nevow.Athena.Tests.Resources.ImportWidget);
            });
        return result;
    }
    );

/**
 * Test that calling Widget.get() on a node which is not part of any Widget
 * throws an error.
 */
Nevow.Athena.Tests.GettingWidgetlessNodeRaisesException = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.GettingWidgetlessNodeRaisesException');
Nevow.Athena.Tests.GettingWidgetlessNodeRaisesException.methods(
    function test_gettingWidgetlessNodeRaisesException(self) {
        var result;
        var threw;
        try {
            result = Nevow.Athena.Widget.get(document.head);
            threw = false;
        } catch (err) {
            threw = true;
        }
        if (!threw) {
            self.fail("No error thrown by Widget.get() - returned " + result + " instead.");
        }
    });

Nevow.Athena.Tests.RemoteMethodErrorShowsDialog = Nevow.Athena.Test.TestCase.subclass('RemoteMethodErrorShowsDialog');
Nevow.Athena.Tests.RemoteMethodErrorShowsDialog.methods(
    function test_remoteMethodErrorShowsDialog(self) {
        var getDialogs = function() {
            return Nevow.Athena.NodesByAttribute(
                        document.body,
                        "class",
                        "athena-error-dialog-" + Nevow.Athena.athenaIDFromNode(self.node));
        }

        return self.callRemote("raiseValueError").addErrback(
            function(err) {
                /* we added the errback before the setTimeout()
                   in callRemote() fired, so it won't get the error */

                self.assertEquals(getDialogs().length, 0);

                var D = self.callRemote("raiseValueError");

                /* we make another deferred to return from this method
                   because the test machinery will add callbacks to D,
                   which will get run before athena adds the errback,
                   resulting in a test failure */

                var waitD = Divmod.Defer.Deferred();

                /* setTimeout() the callback-adding, because we want
                   the callback to run after athena has added the
                   error dialog errback to the callRemote() deferred */

                setTimeout(function() {
                    D.addCallback(
                        function() {
                            var dialogs = getDialogs();

                            if(dialogs.length == 1) {
                                document.body.removeChild(dialogs[0]);
                                waitD.callback(null);
                            } else {
                                waitD.errback(
                                    new Error("expected 1 dialog, got " + dialogs.length));
                            }
                        });
                    }, 0);
                return waitD;
            });
    });


Nevow.Athena.Tests.DelayedCallTests = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.DelayedCallTests');
Nevow.Athena.Tests.DelayedCallTests.methods(
    /**
     * Verify correct behavior in the trivial case of a call scheduled for a
     * short period of time in the future.
     */
    function test_callLater(self) {
        var result = Divmod.Defer.Deferred();
        var finished = false;
        function delayed() {
            finished = true;
            result.callback(null);
        };
        self.callLater(0, delayed);
        self.failIf(finished);
        return result;
    },

    /**
     * Verify that when a DelayedCall is cancelled, it does not run.
     */
    function test_cancelDelayedCall(self) {
        var finished = false;
        function delayed() {
            finished = true;
        };
        var call = self.callLater(0, delayed);
        call.cancel();

        /*
         * Let a little time pass and then make sure the above call never ran.
         */
        var result = Divmod.Defer.Deferred();
        var counter = 3;
        function check() {
            if (counter > 0) {
                counter -= 1;
                self.callLater(0, check);
                return;
            }
            try {
                self.failIf(finished);
            } catch (err) {
                result.errback(err);
                return;
            }
            result.callback(null);
        };
        self.callLater(0, check);
        return result;
    },

    /**
     * Verify that three calls separately scheduled for different times run in
     * the appropriate order.
     */
    function test_callLaterOrdering(self) {
        var result = Divmod.Defer.Deferred();
        var calls = [];
        function first() {
            calls.push("first");
        };
        function second() {
            calls.push("second");
        };
        function third() {
            calls.push("third");
            result.callback(null);
        };

        /*
         * This also happens to serve as a test for the seconds/milliseconds
         * conversion code, since sub-millisecond fractional times are
         * collapsed to 0 (at least by Firefox 1.5).
         */
        self.callLater(0.02, second);
        self.callLater(0.03, third);
        self.callLater(0.01, first);

        result.addCallback(
            function(ignored) {
                self.assertEqual(calls.length, 3);
                self.assertEqual(calls[0], "first");
                self.assertEqual(calls[1], "second");
                self.assertEqual(calls[2], "third");
            });
        return result;
    });


Nevow.Athena.Tests.DynamicStylesheetFetching = Nevow.Athena.Test.TestCase.subclass('Nevow.Athena.Tests.DynamicStylesheetFetching');
/**
 * Tests for CSS module fetching when dynamic widget instantiation is
 * involved.
 */
Nevow.Athena.Tests.DynamicStylesheetFetching.methods(
    /**
     * C{<link>} tags should appear in the document's C{<head>} when a widget
     * with CSS dependencies is dynamically instantiated.
     */
    function test_dynamicInstantiation(self) {
        var D = self.callRemote('getWidgetWithCSSDependencies');
        var cssURLs;
        D.addCallback(
            function(t) {
                cssURLs = t[1];
                return self.addChildWidgetFromWidgetInfo(t[0]);
            });
        D.addCallback(
            function(widget) {
                var head = document.getElementsByTagName('head')[0];
                var links = head.getElementsByTagName('link');
                var stylesheets = [];
                for(var i = 0; i < links.length; i++) {
                    if(links[i].getAttribute('rel') === 'stylesheet'
                        && links[i].getAttribute('type') === 'text/css') {
                        stylesheets.push(links[i].getAttribute('href'));
                    }
                }
                self.assertEqual(stylesheets.length, cssURLs.length);
                for(var i = 0; i < cssURLs.length; i++) {
                    self.assertEqual(stylesheets[i], cssURLs[i]);
                }
            });
        return D;
    });
