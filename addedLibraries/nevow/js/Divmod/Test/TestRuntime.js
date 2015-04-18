// -*- test-case-name: nevow.test.test_javascript.JSUnitTests.test_runtime -*-

/**
 * Unit Tests for Divmod.Runtime.
 *
 * There are not enough tests here, because the unit test framework for
 * Javascript, and perhaps more importantly the mock browser document
 * implementation, were added long after the Runtime module was introduced.
 * However, as any functionality is changed or updated or bugs are fixed,
 * tests should be added here to verify various behaviors of the runtime.  Any
 * necessary functionality should be added to MockBrowser to facilitate those
 * tests.
 */

// import Divmod.UnitTest
// import Divmod.Runtime

Divmod.Test.TestRuntime.FakeRequest = Divmod.Class.subclass(
    'Divmod.Test.TestRuntime.FakeRequest');

/**
 * A fake implementation of http://www.w3.org/TR/XMLHttpRequest/ -
 * specifically as implemented by Firefox.
 */
Divmod.Test.TestRuntime.FakeRequest.methods(
    /**
     * Initialize attributes to starting values.
     */
    function __init__(self) {
        self.opened = null;
        self.sent = null;
        self._status = 0;
        self.headers = [];
        self.networkError = false;
    },

    /**
     * Implement http://www.w3.org/TR/XMLHttpRequest/#dfn-open by recording the
     * arguments passed.
     */
    function open(self, method, url, async) {
        self.opened = [method, url, async];
    },

    /**
     * Implement http://www.w3.org/TR/XMLHttpRequest/#dfn-send by recording the
     * arguments passed.
     */
    function send(self, data) {
        self.sent = [data];
    },

    /**
     * Implement http://www.w3.org/TR/XMLHttpRequest/#dfn-setrequestheader by
     * recording the header that was set in this object's 'headers' array.
     */
    function setRequestHeader(self, key, val) {
        if (self.opened === null) {
            // "1. If the state of the object is not OPEN raise an
            // INVALID_STATE_ERR exception and terminate these steps."
            throw new Error("INVALID_STATE_ERR: you didn't open the request first.");
        }
        self.headers.push([key, val]);
    });

/**
 * Define a 'getter' function for the "status" attribute on FakeRequest which
 * raises an exception when the 'networkError' attribute is set.
 *
 * Note: in general, the tests try to maintain compatibility with standard
 * ECMAScript, not using features particular to any specific runtime.
 * __defineGetter__ is a Firefox-specific extension, but there is no
 * standardized way to affect getting and setting attributes on objects in
 * javascript.  If we do implement a way to run the tests in browsers such as
 * IE and Opera, we may need to implement something different.
 */
Divmod.Test.TestRuntime.FakeRequest.prototype.__defineGetter__(
    "status",
    function () {
        if (this.networkError) {
            throw Divmod.Test.TestRuntime.FakeRequestStatusAccessError();
        }
        return this._status;
    });

Divmod.Test.TestRuntime.FakeRequestStatusAccessError = Divmod.Error.subclass(
    "Divmod.Test.TestRuntime.FakeRequestStatusAccessError");

Divmod.Test.TestRuntime.NetworkTests = Divmod.UnitTest.TestCase.subclass(
    'Divmod.Test.TestRuntime.NetworkTests');
/**
 * These tests cover functionality related to responding to XMLHttpRequest
 * objects.
 */
Divmod.Test.TestRuntime.NetworkTests.methods(
    /**
     * Create a platform object and reassign its makeHTTPRequest method, since
     * these tests should be for the logical state transitions associated with
     * the request, not browser-specific naming hacks.
     */
    function setUp(self) {
        self.platform = Divmod.Runtime.Platform();
        self.platform.makeHTTPRequest = function () {
            return self.makeHTTPRequest();
        }
    },

    /**
     * Stub implementation of the platform's makeHTTPRequest method, so that
     * we can control the behavior of the fake XMLHttpRequest object.
     */
    function makeHTTPRequest(self) {
        self.httpRequest = Divmod.Test.TestRuntime.FakeRequest();
        return self.httpRequest;
    },

    /**
     * getPage() should yield an array with two elements: an XMLHttpRequest
     * object that represents the request, and a Deferred which fires with a
     * string if the request succeeds.
     */
    function test_getPage(self) {
        var gp = self.platform.getPage('/hello/world');
        var realResult = null;
        self.assertIdentical(gp.length, 2);
        self.assertIdentical(gp[0], self.httpRequest);
        self.assertArraysEqual(self.httpRequest.opened,
                               ['GET', '/hello/world', true]);
        self.assertArraysEqual(self.httpRequest.sent, ['']);

        self.assert(gp[1] instanceof Divmod.Defer.Deferred);
        gp[1].addCallback(function (result) {
            realResult = result;
        });
        self.assertIdentical(realResult, null);
        self.httpRequest._status = 1234;
        self.httpRequest.responseText = "this is some text";
        self.httpRequest.readyState = Divmod.Runtime.Platform.XHR_DONE;
        self.httpRequest.onreadystatechange();
        self.assertIdentical(realResult.status, 1234);
        self.assertIdentical(realResult.response, "this is some text");
    },

    /**
     * getPage should translate its 'headers' array into calls to
     * 'setRequestHeader' on the XMLHttpRequest.
     */
    function test_getPageHeaders(self) {
        var gp = self.platform.getPage('/goodby/cruel/world', [], 'GET',
                                       [['Content-Type', 'text/html']]);
        self.assertIdentical(self.httpRequest.headers.length, 1);
        self.assertArraysEqual(self.httpRequest.headers[0],
                               ['Content-Type', 'text/html']);
    },

    /**
     * getPage should translate its 'args' array into a properly quoted URL
     * query string.
     */
    function test_getPageQueryString(self) {
        var gp = self.platform.getPage('/hello/again',
                                       [['q', 'where is the beef?']]);
        self.assertIdentical(self.httpRequest.opened.length, 3);
        self.assertArraysEqual(
            self.httpRequest.opened,
            ['GET', '/hello/again?q=where%20is%20the%20beef%3F', true]);
    },

    /**
     * getPage should return a Deferred which errbacks with the platform
     * exception in the case where the network has failed (detectable in
     * firefox by an error when attemtping to access the 'status' attribute in
     * the callback.)
     */
    function test_getPageNetworkFailure(self) {
        var gp = self.platform.getPage("/hello");
        var errbacked = false;
        self.httpRequest.networkError = true;
        self.httpRequest.readyState = Divmod.Runtime.Platform.XHR_DONE;
        self.httpRequest.onreadystatechange();
        gp[1].addErrback(function (err) {
            errbacked = true;
            self.assert(
                err instanceof
                Divmod.Test.TestRuntime.FakeRequestStatusAccessError);
        });
        self.assert(errbacked);
    },

    /**
     * getPage should pass the content to XMLHttpReqeust.send.
     */
    function test_getPageContent(self) {
        var gp = self.platform.getPage('/not/again', [], 'GET', [],
                                       'Hello, content!');
        self.assertIdentical(self.httpRequest.sent.length, 1);
        self.assertArraysEqual(self.httpRequest.sent,
                               ['Hello, content!']);
    },

    /**
     * getPage should make a synchronous request if you specifically pass a
     * 'synchronous' parameter set to 'true'.
     */
    function test_getPageSynchronous(self) {
        var gp = self.platform.getPage('/hello/world', [], 'GET', [],
                                       '', true);
        self.assertIdentical(self.httpRequest.sent.length, 1);
        self.assertArraysEqual(self.httpRequest.opened,
                               ['GET', '/hello/world', false]);
        //                                             ^ 'async' flag
    });



Divmod.Test.TestRuntime.RuntimeTests = Divmod.UnitTest.TestCase.subclass(
    'Divmod.Test.TestRuntime.RuntimeTests');
Divmod.Test.TestRuntime.RuntimeTests.methods(
    /**
     * Assert that the various *_NODE attributes are present with the correct
     * values.
     *
     * Note: Actually, there should be quite a few other attributes as well.
     * See
     * <http://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#ID-1950641247>.
     * Feel free to add them as necessary.
     */
    function _attributesTest(self, node) {
        self.assertIdentical(node.ELEMENT_NODE, 1);
        self.assertIdentical(node.TEXT_NODE, 3);
        self.assertIdentical(node.DOCUMENT_NODE, 9);
    },

    /**
     * Nodes should have L{ELEMENT_NODE} and L{TEXT_NODE} attributes.
     */
    function test_nodeAttributes(self) {
        var node = document.createElement('span');
        self._attributesTest(node);
    },

    /**
     * Documents should have L{ELEMENT_NODE} and L{TEXT_NODE} attributes.
     */
    function test_documentAttributes(self) {
        self._attributesTest(document);
    },

    /**
     * The nodeType property of a Document should be C{DOCUMENT_NODE}.
     */
    function test_documentNodeType(self) {
        self.assertIdentical(document.nodeType, document.DOCUMENT_NODE);
    },

    /**
     * The nodeType property of an element should be C{ELEMENT_NODE}.
     */
    function test_elementNodeType(self) {
        var node = document.createElement('span');
        self.assertIdentical(node.nodeType, document.ELEMENT_NODE);
    },

    /**
     * The nodeType property of a text node should be C{TEXT_NODE}.
     */
    function test_textNodeNodeType(self) {
        var node = document.createTextNode('foo');
        self.assertIdentical(node.nodeType, document.TEXT_NODE);
    },

    /**
     * Node.appendChild should accept a TextNode and add it to the childNodes
     * array.
     */
    function test_appendTextNode(self) {
        var words = 'words';
        var node = document.createElement('span');
        var text = document.createTextNode(words);
        node.appendChild(text);
        self.assertIdentical(node.childNodes.length, 1);
        self.assertIdentical(node.childNodes[0].nodeValue, words);
    },

    /**
     * When a node is removed from its parent with removeChild, the parentNode
     * property of the removed node should be set to null.
     */
    function test_removeChildClearsParent(self) {
        var parent = document.createElement('span');
        var child = document.createElement('span');
        parent.appendChild(child);
        parent.removeChild(child);
        self.assertIdentical(child.parentNode, null);
    },

    /**
     * Verify that C{insertBefore} sticks the new node at the right place in
     * the C{childNodes} array, and sets the appropriate parent.
     */
    function test_insertBefore(self) {
        var top = document.createElement('div');
        var reference = document.createElement('div');
        top.appendChild(reference);
        var toInsert = document.createElement('div');
        top.insertBefore(toInsert, reference);
        self.assertIdentical(toInsert.parentNode, top);
        self.assertIdentical(top.childNodes[0], toInsert);
        self.assertIdentical(top.childNodes[1], reference);
        self.assertIdentical(top.childNodes.length, 2);
    },

    /**
     * Verify that C{insertBefore} returns the inserted node.
     */
    function test_insertBeforeReturnValue(self) {
        var top = document.createElement('div');
        var reference = document.createElement('div');
        top.appendChild(reference);
        var toInsert = document.createElement('div');
        self.assertIdentical(top.insertBefore(toInsert, reference), toInsert);
    },

    /**
     * Verify that C{insertBefore} returns the inserted node when the
     * reference node is C{null}.
     */
    function test_insertBeforeReturnValueNoReference(self) {
        var top = document.createElement('div');
        var toInsert = document.createElement('div');
        self.assertIdentical(top.insertBefore(toInsert, null), toInsert);
    },

    /**
     * Verify that C{insertBefore} appends the node to its child array when
     * the reference node is C{null}.
     */
     function test_insertBeforeNoReference(self) {
        var top = document.createElement('div');
        var toInsert = document.createElement('div');
        top.insertBefore(toInsert, null);
        self.assertIdentical(toInsert.parentNode, top);
        self.assertIdentical(top.childNodes.length, 1);
        self.assertIdentical(top.childNodes[0], toInsert);
    },

    /**
     * C{insertBefore} should throw a C{DOMError} if its passed a non C{null}
     * reference node which is not one of its child nodes.
     */
    function test_insertBeforeBadReference(self) {
        self.assertThrows(
            DOMException,
            function() {
                document.createElement('div').insertBefore(
                    document.createElement('div'),
                    document.createElement('div'));
            });
    },

    /**
     * A node can be replaced in its parent's children list with the parent's
     * C{replaceNode} method.  C{replaceNode} returns the node which was
     * replaced.
     */
    function test_replaceChild(self) {
        var parent = document.createElement('SPAN');
        var oldChild = document.createElement('A');
        var newChild = document.createElement('B');

        parent.appendChild(document.createElement('BEFORE'));
        parent.appendChild(oldChild);
        parent.appendChild(document.createElement('AFTER'));

        var returned = parent.replaceChild(newChild, oldChild);
        self.assertIdentical(returned, oldChild);

        self.assertIdentical(parent.childNodes.length, 3);
        self.assertIdentical(parent.childNodes[0].tagName, 'BEFORE');
        self.assertIdentical(parent.childNodes[1].tagName, 'B');
        self.assertIdentical(parent.childNodes[2].tagName, 'AFTER');

        self.assertIdentical(oldChild.parentNode, null);
        self.assertIdentical(newChild.parentNode, parent);
    },

    /**
     * L{Element.replaceChild} should throw a L{DOMError} when invoked with an
     * old child argument which is not a child of the node.
     */
    function test_replaceChildThrows(self) {
        var parent = document.createElement('SPAN');
        var nonChild = document.createElement('A');
        var newChild = document.createElement('B');

        self.assertThrows(
            DOMException,
            function() {
                parent.replaceChild(newChild, nonChild);
            });
        self.assertIdentical(parent.childNodes.length, 0);
    },

    /**
     * Verify that traversal of nested nodes will result in retrieving all the
     * nodes in depth-first order.
     */
    function test_traverse(self) {
        var d = document;

        var firstNode = d.createElement('firstNode');
        var secondNode = d.createElement('secondNode');
        var thirdNode = d.createElement('thirdNode');
        var fourthNode = d.createElement('fourthNode');

        secondNode.appendChild(thirdNode);
        firstNode.appendChild(secondNode);
        firstNode.appendChild(fourthNode);
        var nodes = [];
        Divmod.Runtime.theRuntime.traverse(firstNode, function (aNode) {
            nodes.push(aNode);
            return Divmod.Runtime.Platform.DOM_DESCEND;
        });

        self.assertIdentical(nodes.length, 4);
        self.assertIdentical(nodes[0], firstNode);
        self.assertIdentical(nodes[1], secondNode);
        self.assertIdentical(nodes[2], thirdNode);
        self.assertIdentical(nodes[3], fourthNode);
    },

    /**
     * It should be possible to find a node with a particular id starting from
     * a node with implements the DOM API.
     *
     * Elements are documented here:
     *
     * http://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#ID-745549614
     */
    function test_getElementByIdWithNode(self) {
        var id = 'right';
        var node;
        var child;

        node = document.createElement('a');
        node.id = id;
        document.body.appendChild(node);
        self.assertIdentical(
            Divmod.Runtime.theRuntime.getElementByIdWithNode(node, id),
            node);

        self.assertThrows(
            Divmod.Runtime.NodeNotFound,
            function() {
                Divmod.Runtime.theRuntime.getElementByIdWithNode(
                    node, 'wrong');
            });

        node = document.createElement('a');
        child = document.createElement('b');
        child.id = 'wrong';
        node.appendChild(child);
        child = document.createElement('c');
        child.id = id;
        node.appendChild(child);
        document.body.appendChild(node);

        self.assertIdentical(
            Divmod.Runtime.theRuntime.getElementByIdWithNode(node, id).id,
            id);
    },

    /**
     * I{firstNodeByAttribute} should return the highest, left-most node in the
     * DOM with a matching attribute value.
     */
    function test_firstNodeByAttribute(self) {
        /*
         * Save some typing.
         */
        function find(root, attrName, attrValue) {
            return Divmod.Runtime.theRuntime.firstNodeByAttribute(
                root, attrName, attrValue);
        }
        var root = document.createElement('div');
        root.setAttribute('foo', 'bar');
        self.assertIdentical(find(root, 'foo', 'bar'), root);

        var childA = document.createElement('h1');
        childA.setAttribute('foo', 'bar');
        childA.setAttribute('baz', 'quux');
        root.appendChild(childA);
        self.assertIdentical(find(root, 'foo', 'bar'), root);
        self.assertIdentical(find(root, 'baz', 'quux'), childA);

        var childB = document.createElement('h2');
        childB.setAttribute('foo', 'bar');
        childB.setAttribute('baz', 'quux');
        root.appendChild(childB);
        self.assertIdentical(find(root, 'foo', 'bar'), root);
        self.assertIdentical(find(root, 'baz', 'quux'), childA);

        var childC = document.createElement('h3');
        childC.setAttribute('foo', 'bar');
        childC.setAttribute('baz', 'quux');
        childA.appendChild(childC);
        self.assertIdentical(find(root, 'foo', 'bar'), root);
        self.assertIdentical(find(root, 'baz', 'quux'), childA);

        var childD = document.createElement('h4');
        childD.setAttribute('corge', 'grault');
        childB.appendChild(childD);
        self.assertIdentical(find(root, 'corge', 'grault'), childD);
    },

    /**
     * I{firstNodeByAttribute} should throw an error if no node matches the
     * attribute name and value supplied.
     */
    function test_firstNodeByAttributeThrows(self) {
        var root = document.createElement('span');
        self.assertThrows(
            Divmod.Runtime.NodeAttributeError,
            function() {
                return Divmod.Runtime.theRuntime.firstNodeByAttribute(
                    root, 'foo', 'bar');
            });

        root.setAttribute('foo', 'quux');
        self.assertThrows(
            Divmod.Runtime.NodeAttributeError,
            function() {
                return Divmod.Runtime.theRuntime.firstNodeByAttribute(
                    root, 'foo', 'bar');
            });

        root.setAttribute('baz', 'bar');
        self.assertThrows(
            Divmod.Runtime.NodeAttributeError,
            function() {
                return Divmod.Runtime.theRuntime.firstNodeByAttribute(
                    root, 'foo', 'bar');
            });
    },

    /**
     * I{nodeByAttribute} should return the single node which matches the
     * attribute name and value supplied.
     */
    function test_nodeByAttribute(self) {
        function find(root, attrName, attrValue) {
            return Divmod.Runtime.theRuntime.nodeByAttribute(
                root, attrName, attrValue);
        };
        var root = document.createElement('div');
        root.setAttribute('foo', 'bar');
        self.assertIdentical(find(root, 'foo', 'bar'), root);

        root.setAttribute('foo', '');
        var childA = document.createElement('span');
        childA.setAttribute('foo', 'bar');
        root.appendChild(childA);
        self.assertIdentical(find(root, 'foo', 'bar'), childA);

        childA.setAttribute('foo', '');
        var childB = document.createElement('span');
        childB.setAttribute('foo', 'bar');
        root.appendChild(childB);
        self.assertIdentical(find(root, 'foo', 'bar'), childB);

        childB.setAttribute('foo', '');
        var childC = document.createElement('span');
        childC.setAttribute('foo', 'bar');
        childA.appendChild(childC);
        self.assertIdentical(find(root, 'foo', 'bar'), childC);

        childC.setAttribute('foo', '');
        var childD = document.createElement('span');
        childD.setAttribute('foo', 'bar');
        childB.appendChild(childD);
        self.assertIdentical(find(root, 'foo', 'bar'), childD);
    },

    /**
     * I{nodeByAttribute} should throw an error if more than one node matches
     * the specified attribute name and value.
     */
    function test_nodeByAttributeThrowsOnMultiple(self) {
        function find(root, attrName, attrValue) {
            return Divmod.Runtime.theRuntime.nodeByAttribute(
                root, attrName, attrValue);
        };

        var root = document.createElement('div');
        root.setAttribute('foo', 'bar');
        var childA = document.createElement('span');
        childA.setAttribute('foo', 'bar');
        root.appendChild(childA);
        self.assertThrows(
            Error,
            function() {
                return find(root, 'foo', 'bar');
            });

        childA.setAttribute('foo', '');
        var childB = document.createElement('span');
        childB.setAttribute('foo', 'bar');
        root.appendChild(childB);
        self.assertThrows(
            Error,
            function() {
                return find(root, 'foo', 'bar');
            });

        childB.setAttribute('foo', '');
        var childC = document.createElement('span');
        childC.setAttribute('foo', 'bar');
        childA.appendChild(childC);
        self.assertThrows(
            Error,
            function() {
                return find(root, 'foo', 'bar');
            });

        childC.setAttribute('foo', '');
        var childD = document.createElement('span');
        childD.setAttribute('foo', 'bar');
        childB.appendChild(childD);
        self.assertThrows(
            Error,
            function() {
                return find(root, 'foo', 'bar');
            });

        root.setAttribute('foo', '');
        childC.setAttribute('foo', 'bar');
        self.assertThrows(
            Error,
            function() {
                return find(root, 'foo', 'bar');
            });
    },

    /**
     * I{nodeByAttribute} should throw an error if no nodes match the specified
     * attribute name and value.
     */
    function test_nodeByAttributeThrowsOnMissing(self) {
        var root = document.createElement('span');
        self.assertThrows(
            Divmod.Runtime.NodeAttributeError,
            function() {
                return Divmod.Runtime.theRuntime.nodeByAttribute(
                    root, 'foo', 'bar');
            });

        root.setAttribute('foo', 'quux');
        self.assertThrows(
            Divmod.Runtime.NodeAttributeError,
            function() {
                return Divmod.Runtime.theRuntime.nodeByAttribute(
                    root, 'foo', 'bar');
            });

        root.setAttribute('baz', 'bar');
        self.assertThrows(
            Divmod.Runtime.NodeAttributeError,
            function() {
                return Divmod.Runtime.theRuntime.nodeByAttribute(
                    root, 'foo', 'bar');
            });
    },

    /**
     * I{nodesByAttribute} should return an array of all nodes which have
     * matching values for the specified attribute.
     */
    function test_nodesByAttribute(self) {
        var root = document.createElement('div');
        root.setAttribute('foo', 'bar');
        var childA = document.createElement('span');
        var childB = document.createElement('span');
        childB.setAttribute('foo', 'bar');
        root.appendChild(childA);
        root.appendChild(childB);

        var nodes = Divmod.Runtime.theRuntime.nodesByAttribute(
            root, 'foo', 'bar');
        self.assertIdentical(nodes.length, 2);
        self.assertIdentical(nodes[0], root);
        self.assertIdentical(nodes[1], childB);

        nodes = Divmod.Runtime.theRuntime.nodesByAttribute(
            root, 'baz', 'quux');
        self.assertIdentical(nodes.length, 0);
    },

    /**
     * L{Divmod.Runtime.Platform.loadStylesheet} should create an appropriate
     * C{<link>} element.
     */
    function test_loadStylesheet(self) {
        var location = 'http://test_loadStylesheet';
        var headNode = document.createElement('head');
        document.body.appendChild(headNode); // eh, whatever
        Divmod.Runtime.theRuntime.loadStylesheet(location);
        self.assertIdentical(headNode.childNodes.length, 1);
        var child = headNode.childNodes[0];
        self.assertIdentical(child.tagName, 'LINK');
        self.assertIdentical(child.getAttribute('rel'), 'stylesheet');
        self.assertIdentical(child.getAttribute('type'), 'text/css');
        self.assertIdentical(child.getAttribute('href'), location);
    });


Divmod.Test.TestRuntime.SpidermonkeyRuntimeTests = Divmod.UnitTest.TestCase.subclass(
    'Divmod.Test.TestRuntime.SpidermonkeyRuntimeTests');
/**
 * Tests for the Spidermonkey runtime.
 */
Divmod.Test.TestRuntime.SpidermonkeyRuntimeTests.methods(
    /**
     * I{addLoadEvent} should add the handler to the list of load events.
     */
    function test_addLoadEvent(self) {
        var marker = false;
        var handler = function handler() {
            marker = true;
        };

        self.assertIdentical(marker, false);
        Divmod.Runtime.theRuntime.addLoadEvent(handler);
        self.assertIdentical(marker, false);
        self.assertIdentical(Divmod.Runtime.theRuntime.loadEvents.length, 1);
        Divmod.Runtime.theRuntime.loadEvents[0]();
        self.assertIdentical(marker, true);
    });



Divmod.Test.TestRuntime.ConnectSingleDOMEventTestCase = Divmod.UnitTest.TestCase.subclass(
    'Divmod.Test.TestRuntime.ConnectSingleDOMEventTestCase');
/**
 * Tests for L{Divmod.Runtime.Platform.connectSingleDOMEvent}.
 */
Divmod.Test.TestRuntime.ConnectSingleDOMEventTestCase.methods(
    /**
     * Make an instance of a L{Divmod.Class} subclass which keeps track of
     * method calls.
     */
    function setUp(self) {
        var ConnectSingleDOMEventTester = Divmod.Class.subclass(
            'ConnectSingleDOMEventTester');
        ConnectSingleDOMEventTester.methods(
            function __init__(self) {
                self.onclickHandlerCalls = [];
                self.handlerReturnValue = {};
            },

            function onclickHandler(self, node) {
                self.onclickHandlerCalls.push(node);
                return self.handlerReturnValue;
            });
        self.handlerObject = ConnectSingleDOMEventTester();
    },

    /**
     * Verify that the handler set by
     * L{Divmod.Runtime.Platform.connectSingleDOMEvent} calls the method with
     * the given name on the handler object and passes it the node that the
     * DOM event handler was passed.
     */
    function test_callsMethod(self) {
        var node = {};
        Divmod.Runtime.theRuntime.connectSingleDOMEvent(
            'onclick', self.handlerObject, node, 'onclickHandler');
        node['onclick'](node);
        self.assertIdentical(
            self.handlerObject.onclickHandlerCalls.length, 1);
        self.assertIdentical(
            self.handlerObject.onclickHandlerCalls[0], node);
    },

    /**
     * Verify that the handler set by
     * L{Divmod.Runtime.Platform.connectSingleDOMEvent} returns the value it
     * got from the handler method.
     */
    function test_forwardsReturnValue(self) {
        var node = {};
        Divmod.Runtime.theRuntime.connectSingleDOMEvent(
            'onclick', self.handlerObject, node, 'onclickHandler');
        self.assertIdentical(
            node['onclick'](node),
            self.handlerObject.handlerReturnValue);
    },

    /**
     * Verify that the handler set by
     * L{Divmod.Runtime.Platform.connectSingleDOMEvent} removes itself after
     * it's called.
     */
    function test_removesHandlerAfterCall(self) {
        var node = {};
        Divmod.Runtime.theRuntime.connectSingleDOMEvent(
            'onclick', self.handlerObject, node, 'onclickHandler');
        node['onclick'](node);
        self.assertIdentical(node['onclick'], undefined);
    },

    /**
     * Verify that the handler set by
     * L{Divmod.Runtime.Platform.connectSingleDOMEvent} removes the handler
     * object's entry from L{Divmod.Runtime._eventHandlerObjects}.
     */
    function test_forgetsObject(self) {
        var node = {};
        Divmod.Runtime.theRuntime.connectSingleDOMEvent(
            'onclick', self.handlerObject, node, 'onclickHandler');
        /* sanity check */
        self.assertIdentical(
            Divmod.Runtime._eventHandlerObjects[
                self.handlerObject.__id__],
            self.handlerObject);
        node['onclick'](node);
        self.assertIdentical(
            Divmod.Runtime._eventHandlerObjects[
                self.handlerObject.__id__],
            undefined);
    });
