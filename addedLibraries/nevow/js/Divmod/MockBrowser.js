// -*- test-case-name: nevow.test.test_javascript.JSUnitTests -*-

/**
 * This module implements browser functionality for use within the
 * command-line unit tests.
 *
 * It mimics the behavior of Firefox 2.0's HTML DOM implementation well enough
 * to support common third-party libraries.  Ultimately we hope to be able to
 * make the behavior pluggable so that HTML DOM manipulation can be tested
 * with the semantics of any browser supported by Athena.
 *
 * Currently it has only been lightly tested with MochiKit, but it should be
 * gradually improved to facilitate better testing code which relies upon
 * other frameworks, such as scriptaculous and YUI.  Also, as noted in
 * Divmod.Test.TestRuntime, this mock browser implementation is currently not
 * even complete enough to test all of our own Runtime object; maintainers
 * should feel free (and encouraged!) to expand this module to fit the needs
 * of fully testing that code.
 */

// import Divmod

/**
 * A fake node, the primary datatype for the entire DOM.
 *
 * @see: http://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#ID-1950641247
 *
 * @ivar ownerDocument: a document, to which this node belongs.
 *
 */
Divmod.MockBrowser.Node = Divmod.Class.subclass("Divmod.MockBrowser.Node");
Divmod.MockBrowser.Node.methods(
    /**
     * Internal helper to let a document set itself as the owner of this
     * node.
     */
    function _setOwnerDocument(self, ownerDocument) {
        self.ownerDocument = ownerDocument;
    },

    /**
     * Internal mock DOM notification that the parent of this node has
     * changed.
     */
    function _setParent(self, newParent) {
        var justAdded = (self.parentNode === undefined);
        self.parentNode = newParent;
        if (justAdded) {
            self._insertedIntoDocument();
        }
    },

    /**
     * Internal mock DOM notification that the node was inserted into the
     * document.
     */
    function _insertedIntoDocument(self) {
    },

    /*
     * Return an array of all L{Element} instances with the given tag name
     * which live below the given elements.
     *
     * @type tagName: C{String}
     * @param tagName: Tag name to look for.
     *
     * @type parents: C{Array} of L{Element}
     * @param parents: Sequence of parent nodes below which to search.
     *
     * @rtype: C{Array} of L{Element}.
     */
    function _getElementsByTagName(self, tagName, parents) {
        tagName = tagName.toUpperCase();
        var elements = [];
        var node;
        for(var i = 0; i < parents.length; i++) {
            node = parents[i];
            if(node.nodeType !== self.ELEMENT_NODE) {
                continue;
            }
            if(node.tagName === tagName || tagName === '*') {
                elements.push(node);
            }
            elements = elements.concat(
                self._getElementsByTagName(tagName, node.childNodes));
        }
        return elements;
    },

    function __init__(self) {
        self.ELEMENT_NODE = 1;
        self.TEXT_NODE = 3;
        self.DOCUMENT_NODE = 9;
        self.childNodes = [];
    });



Divmod.MockBrowser.Document = Divmod.MockBrowser.Node.subclass("Divmod.MockBrowser.Document");

/**
 * This is a mock document that can be used in the tests where there is no
 * "document" object.
 *
 * Relevant specifications:
 *  http://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#i-Document
 *  http://www.w3.org/TR/REC-DOM-Level-1/level-one-html.html#ID-1006298752
 *
 * @ivar _allElements: all elements ever created by this document.
 *
 * @ivar body: A <BODY> L{Element}, similar to the one provided by web
 * browsers.
 */
Divmod.MockBrowser.Document.methods(
    /**
     * Create a mock browser with a "body" element.
     */
    function __init__(self) {
        Divmod.MockBrowser.Document.upcall(self, '__init__');
        self.nodeType = self.DOCUMENT_NODE;
        self._allElements = [];
        self.DEFAULT_HEIGHT = 20;
        self.DEFAULT_WIDTH = 300;
        self.body = self.createElement("body");
        self.body._containingDocument = self;
    },

    /**
     * Create an L{Element} with the given tag name.
     */
    function createElement(self, tagName) {
        var el = Divmod.MockBrowser.Element(tagName);
        el._setOwnerDocument(self);
        self._allElements.push(el);
        return el;
    },

    /**
     * Return the most recently created L{Element} with the given 'id'
     * attribute.  If no such element exists, mimic Firefox's behavior and
     * return 'null'.
     *
     * @param id: a string.
     */
    function getElementById(self, id) {
        for (var i = self._allElements.length - 1; i >= 0; i--) {
            var eachElement = self._allElements[i];
            if (eachElement.id === id &&
                eachElement._getContainingDocument() == self) {
                return eachElement;
            }
        }
        return null;
    },

    /**
     * Create a L{TextNode} with the given text.
     */
    function createTextNode(self, text) {
        var aNode = Divmod.MockBrowser.TextNode(text);
        aNode._setOwnerDocument(self);
        return aNode;
    },

    /**
     * Return all L{Element} instances in this document which have the
     * specified tag name.
     */
    function getElementsByTagName(self, tagName) {
        return self._getElementsByTagName(tagName, [self.body]);
    });


/**
 * A fake node containing some text.
 *
 * Relevant specifications:
 *  http://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#ID-1312295772
 */

Divmod.MockBrowser.TextNode = Divmod.MockBrowser.Node.subclass("Divmod.MockBrowser.TextNode");
Divmod.MockBrowser.TextNode.methods(
    /**
     * Create a text node.  Private.  Use L{Document.createTextNode} if you
     * want to create one of these.
     */
    function __init__(self, nodeValue) {
        Divmod.MockBrowser.TextNode.upcall(self, '__init__');
        self.nodeType = self.TEXT_NODE;
        self.nodeValue = nodeValue;
        self.length = nodeValue.length;
    });

Divmod.MockBrowser.DOMError = Divmod.Error.subclass("Divmod.MockBrowser.DOMError");

/**
 * A mock DOM Element which simulates the behavior of elements in Firefox 2.0.
 *
 * Relevant specifications:
 *  http://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#ID-745549614
 *  http://www.w3.org/TR/REC-DOM-Level-1/level-one-html.html#ID-011100101
 *
 * @ivar _attributes: an object with attributes for each DOM attribute.
 *
 * @ivar tagName: a string, the name of this element.  This should be an HTML
 * tag name.
 *
 * @ivar style: a simple object which exists to catch HTML DOM 'style'
 * assignments.
 *
 * @ivar className: The name of the class of this node.
 */
Divmod.MockBrowser.Element = Divmod.MockBrowser.Node.subclass(
    "Divmod.MockBrowser.Element");
Divmod.MockBrowser.Element.methods(
    /**
     * Create an element with a given tag name.  Private.  Use
     * L{Document.createElement} instead.
     */
    function __init__(self, tagName) {
        Divmod.MockBrowser.Element.upcall(self, '__init__');
        self.nodeType = self.ELEMENT_NODE;
        self._attributes = {};
        self.tagName = tagName.toUpperCase();
        self.style = {};
        self.childNodes = [];
        self.className = '';
        self.clientHeight = 0;
        self.clientWidth = 0;
    },

    /**
     * This method is only for use in tests, and has no analogue in a browser.
     * It is for setting the width and height of directly-created elements.
     *
     * @param width: an integer, the desired clientWidth of this node.
     *
     * @param height: an integer, the desired clientHeight of this node.
     */
    function setMockElementSize(self, width, height) {
        self.clientWidth = width;
        self.clientHeight = height;
    },

    /**
     * String representation of mock browser elements for debugging.
     */
    function toString(self) {
        var s = '<{MOCK}';
        s += self.tagName;
        var showeq = function (a, b) {
            s += ' ';
            s += a;
            s += "=";
            s += '"';
            s += b;
            s += '"';
        }
        for (var attrib in self._attributes) {
            showeq(attrib, self._attributes[attrib]);
        }
        var q = '';
        for (var stylelem in self.style) {
            q += stylelem;
            q += ': ';
            q += self.style[stylelem];
            q += '; ';
        }
        if (q) {
            showeq("{style}", q);
        }
        if (self.childNodes.length > 0) {
            s += '>...</';
            s += self.tagName;
            s += '>';
        } else {
            s += ' />';
        }
        return s;
    },

    /**
     * Append a child to this element.
     */
    function appendChild(self, child) {
        self.childNodes.push(child);
        child._setParent(self);
    },

    /**
     * Stick a child into this element, before the reference element.
     *
     * @param newChildNode: The new node to put in the child list.
     * @param referenceNode: The reference node (the node to put
     * C{newChildNode} before).
     *
     * @throw Divmod.MockBrowser.DOMError: Raised if C{referenceNode} is not a
     * child of C{self}.
     */
    function insertBefore(self, newChildNode, referenceNode) {
        if(referenceNode === null) {
            self.appendChild(newChildNode);
            return newChildNode;
        }
        for(var i = 0; i < self.childNodes.length; i++) {
            if(self.childNodes[i] == referenceNode) {
                self.childNodes.splice(i, 0, newChildNode);
                newChildNode._setParent(self);
                return newChildNode;
            }
        }
        throw Divmod.MockBrowser.DOMError("no such reference node");
    },

    /**
     * Remove a child from this element.
     */
    function removeChild(self, child) {
        var idx = -1;
        for (var i = 0; i < self.childNodes.length; i++) {
            var eachNode = self.childNodes[i];
            if (eachNode === child) {
                idx = i;
            }
        }
        if (idx == -1) {
            throw new Divmod.MockBrowser.DOMError("no such node");
        }
        self.childNodes.splice(idx, 1);
        child.parentNode = null;
    },

    /**
     * Replaces the child node oldChild with newChild in the list of children,
     * and returns the oldChild node. If the newChild is already in the tree,
     * it is first removed.
     *
     * Note: strictly speaking, this is a method on the Node interface, not the
     * Element interface.  However, invoking the implementation of this method
     * on other Node subclasses is probably an error.  At least on Firefox 1.5,
     * they silently ignore this call (likewise for appendChild and
     * removeChild).
     *
     * @param newChild: The new node to put in the child list.
     *
     * @param oldChild: The node being replaced in the list.
     *
     * @return: The node replaced.
     *
     * @throw Divmod.MockBrowser.DOMError: Raised if oldChild is not a child of
     *     this node.
     *
     */
    function replaceChild(self, newChild, oldChild) {
        for (var i = 0; i < self.childNodes.length; ++i) {
            if (self.childNodes[i] === oldChild) {
                self.childNodes[i]._setParent(null);
                self.childNodes[i] = newChild;
                newChild._setParent(self);
                return oldChild;
            }
        }
        throw Divmod.MockBrowser.DOMError("no such node");
    },

    /**
     * Emulate Firefox's Element.setAttribute, setting the attribute for
     * retrieval by 'getAttribute', except for certain special cases such as
     * 'class', which are also represented as attributes.
     *
     * (Currently, only 'class' is special-cased, but we may wish to do others
     * later, such as 'id' and 'style'.)
     */
    function setAttribute(self, name, value) {
        if (name == 'class') {
            self.className = value;
        }
        self._attributes[name] = value;
    },

    /**
     * Removes the atribute C{name} from this element.  Subsequent calls to
     * C{getAttribute} which are passed C{name} will return C{undefined} until
     * the attribute is re-set.
     */
    function removeAttribute(self, name) {
        delete self._attributes[name];
    },

    /**
     * Handle node insertion event by sending it on to all this element's
     * children and setting this element's size.
     */
    function _insertedIntoDocument(self) {
        Divmod.MockBrowser.Element.upcall(self, '_insertedIntoDocument');
        for (var i = 0; i < self.childNodes.length; i++) {
            self.childNodes[i]._insertedIntoDocument();
        }
        var doc = self._getContainingDocument();
        if (doc !== undefined) {
            self.setMockElementSize(doc.DEFAULT_WIDTH, doc.DEFAULT_HEIGHT);
        }
    },

    /**
     * Retrieve the L{Document} object that is associated with this Element's
     * parent hierarchy, if one exists, otherwise return undefined.
     */
    function _getContainingDocument(self) {
        var node = self;
        while (node) {
            if (node._containingDocument) {
                return node._containingDocument;
            }
            node = node.parentNode;
        }
    },

    /**
     * Emulate DOM's Element.getAttribute.
     */
    function getAttribute(self, name) {
        return self._attributes[name];
    },

    /**
     * Return an array of all L{Element} instances with the given tag name
     * which live below this element.
     *
     * @type tagName: C{String}
     * @param tagName: Tag name to look for.
     *
     * @rtype: C{Array} of L{Element}.
     */
    function getElementsByTagName(self, tagName) {
        return self._getElementsByTagName(tagName, self.childNodes);
    });


/* Only install ourselves as a global document if there isn't already a global
 * document.  This should minimise the impact of this module.
 */
if (Divmod.namedAny("document") === undefined) {
    document = Divmod.MockBrowser.Document();
    DOMException = Divmod.MockBrowser.DOMError;
}
