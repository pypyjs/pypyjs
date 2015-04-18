// -*- test-case-name: nevow.test.test_javascript.JSUnitTests.test_tabbedPane -*-

// import Divmod.UnitTest
// import Nevow.Test.WidgetUtil
// import Nevow.TagLibrary.TabbedPane

Nevow.Test.TestTabbedPane.TabbedPaneViewTests = Divmod.UnitTest.TestCase.subclass(
    'Nevow.Test.TestTabbedPane.TabbedPaneViewTests');
/**
 * Tests for L{Nevow.TagLibrary.TabbedPane.TabbedPaneView}.
 */
Nevow.Test.TestTabbedPane.TabbedPaneViewTests.methods(
    /**
     * L{Nevow.TagLibrary.TabbedPane.TabbedPaneView.tabNameFromTabNode} should
     * get the right value.
     */
    function test_tabNameFromTabNode(self) {
        var view = Nevow.TagLibrary.TabbedPane.TabbedPaneView(null, null);
        var name = 'test_tabNameFromTabNode';
        var tabNode = document.createElement('li');
        tabNode.appendChild(document.createTextNode(name));
        self.assertIdentical(
            view.tabNameFromTabNode(tabNode), name);
    },

    /**
     * Make a tab container node containing tabs with the given names.
     */
    function _makeTabContainerNode(self, tabNames, selected) {
        var tabContainerNode = document.createElement('ul');
        var tabNode = document.createElement('li');
        for(var i = 0; i < tabNames.length; i++) {
            var tabNode = document.createElement('li');
            var className;
            if(i === selected) {
                className = 'nevow-tabbedpane-selected-tab';
            } else {
                className = 'nevow-tabbedpane-tab';
            }
            tabNode.setAttribute('class', className);
            tabNode.appendChild(document.createTextNode(tabNames[i]));
            tabContainerNode.appendChild(tabNode);
        }
        return tabContainerNode;
    },

    /**
     * Make a pane container node containing the given number of panes.
     */
    function _makePaneContainerNode(self, paneCount, selected) {
        var paneContainerNode = document.createElement('div');
        for(var i = 0; i < paneCount; i++) {
            var paneNode = document.createElement('div');
            var className;
            if(i === selected) {
                className = 'nevow-tabbedpane-selected-pane';
            } else {
                className = 'nevow-tabbedpane-pane';
            }
            paneNode.setAttribute('class', className);
            paneContainerNode.appendChild(paneNode);
        }
        return paneContainerNode;
    },

    /**
     * L{Nevow.TagLibrary.TabbedPane.TabbedPaneView.getNamedPaneNode} should
     * return the right node.
     */
    function test_getNamedPaneNode(self) {
        var tabContainerNode = self._makeTabContainerNode(
            ['foo', 'bar'], 0);
        var paneContainerNode = self._makePaneContainerNode(2, 0);
        var secondPaneNode = paneContainerNode.childNodes[1];
        var view = Nevow.TagLibrary.TabbedPane.TabbedPaneView(
            function nodeById(id) {
                return {
                    'pane-container': paneContainerNode,
                    'tab-container': tabContainerNode
                }[id];
            }, 'foo');
        self.assertIdentical(
            view.getNamedPaneNode('bar'), secondPaneNode);
    },

    /**
     * L{Nevow.TagLibrary.TabbedPane.TabbedPaneView.replaceNamedPaneContent}
     * should append the given node and remove any existing ones.
     */
    function test_replaceNamedPaneContent(self) {
        var tabContainerNode = self._makeTabContainerNode(
            ['foo', 'bar'], 0);
        var paneContainerNode = self._makePaneContainerNode(2, 0);
        var secondPaneNode = paneContainerNode.childNodes[1];
        secondPaneNode.appendChild(document.createTextNode('HI'));
        secondPaneNode.appendChild(document.createElement('div'));
        var view = Nevow.TagLibrary.TabbedPane.TabbedPaneView(
            function nodeById(id) {
                return {
                    'pane-container': paneContainerNode,
                    'tab-container': tabContainerNode
                }[id];
            }, 'foo');
        var replacementNode = document.createElement('div');
        view.replaceNamedPaneContent('bar', replacementNode);
        self.assertIdentical(secondPaneNode.childNodes.length, 1);
        self.assertIdentical(
            secondPaneNode.childNodes[0], replacementNode);
    },

    /**
     * L{Nevow.TagLibrary.TabbedPane.TabbedPaneView.selectNamedTab} should
     * select the right tab node.
     */
    function test_selectNamedTab(self) {
        var tabContainerNode = self._makeTabContainerNode(
            ['first tab node', 'second tab node'], 0);
        var firstTabNode = tabContainerNode.childNodes[0];
        var secondTabNode = tabContainerNode.childNodes[1];
        var paneContainerNode = self._makePaneContainerNode(2, 0);
        var firstPaneNode = paneContainerNode.childNodes[0];
        var secondPaneNode = paneContainerNode.childNodes[1];

        var view = Nevow.TagLibrary.TabbedPane.TabbedPaneView(
            function nodeById(id) {
                return {
                    'pane-container': paneContainerNode,
                    'tab-container': tabContainerNode
                }[id];
            }, 'first tab node');
        view.selectNamedTab('second tab node');
        self.assertIdentical(
            firstTabNode.getAttribute('class'), 'nevow-tabbedpane-tab');
        self.assertIdentical(
            firstPaneNode.getAttribute('class'), 'nevow-tabbedpane-pane');
        self.assertIdentical(
            secondTabNode.getAttribute('class'),
            'nevow-tabbedpane-selected-tab');
        self.assertIdentical(
            secondPaneNode.getAttribute('class'),
            'nevow-tabbedpane-selected-pane');
    });


Nevow.Test.TestTabbedPane.StubTabbedPaneView = Divmod.Class.subclass(
    'Nevow.Test.TestTabbedPane.StubTabbedPaneView');
/**
 * Stub L{Nevow.TagLibrary.TabbedPane.TabbedPaneView}.
 *
 * @ivar tabName: Value to return from L{tabNameFromTabNode}.
 * @type tabName: C{String}
 *
 * @ivar selectedTabName: The name of the currently selected tab.
 * @type selectedTabName: C{String}
 *
 * @ivar tabNodes: Sequence of nodes passed to L{tabNameFromTabNode}.
 * @type tabNodes: C{Array}
 */
Nevow.Test.TestTabbedPane.StubTabbedPaneView.methods(
    function __init__(self, tabName, selectedTabName) {
        self.tabName = tabName;
        self.selectedTabName = selectedTabName;
        self.tabNodes = [];
    },

    /**
     * Store C{tabNode} and return L{tabName}.
     */
    function tabNameFromTabNode(self, tabNode) {
        self.tabNodes.push(tabNode);
        return self.tabName;
    },

    /**
     * Set L{selectedTabName} to C{tabName}.
     */
    function selectNamedTab(self, tabName) {
        self.selectedTabName = tabName;
    });


Nevow.Test.TestTabbedPane.TabbedPaneTests = Divmod.UnitTest.TestCase.subclass(
    'Nevow.Test.TestTabbedPane.TabbedPaneTests');
/**
 * Tests for L{Nevow.TagLibrary.TabbedPane.TabbedPane}.
 */
Nevow.Test.TestTabbedPane.TabbedPaneTests.methods(
    /**
     * L{Nevow.TagLibrary.TabbedPane.TabbedPane.dom_tabClicked} should call
     * C{tabClicked}.
     */
    function test_dom_tabClicked(self) {
        var controller = Nevow.TagLibrary.TabbedPane.TabbedPane(
            Nevow.Test.WidgetUtil.makeWidgetNode());
        var theTabNode;
        controller.tabClicked = function tabClicked(node) {
            theTabNode = node;
        }
        var tabNode = {};
        self.assertIdentical(controller.dom_tabClicked(tabNode), false);
        self.assertIdentical(theTabNode, tabNode);
    },

    /**
     * L{Nevow.TagLibrary.TabbedPane.TabbedPane.tabClicked} should call the
     * appropriate view methods.
     */
    function test_tabClicked(self) {
        var selectedTabName = 'some boring thing';
        var controller = Nevow.TagLibrary.TabbedPane.TabbedPane(
            Nevow.Test.WidgetUtil.makeWidgetNode(), selectedTabName);
        controller.loaded();
        var theSelectedTab;
        controller.namedTabSelected = function(selectedTab) {
            theSelectedTab = selectedTab;
        }
        var tabNode = {};
        var tabName = 'test_tabClicked';
        var view = Nevow.Test.TestTabbedPane.StubTabbedPaneView(
            tabName, selectedTabName);
        controller.view = view;
        controller.tabClicked(tabNode);
        self.assertIdentical(view.tabNodes.length, 1);
        self.assertIdentical(view.tabNodes[0], tabNode);
        self.assertIdentical(view.selectedTabName, tabName);
        self.assertIdentical(theSelectedTab, tabName);
    },

    /**
     * L{Nevow.TagLibrary.TabbedPane.TabbedPane.dom_tabClicked} should defer
     * any tab change until C{loaded} has been called.
     */
    function test_dom_tabClickedLoaded(self) {
        var selectedTabName = 'some boring thing';
        var tabNode = {};
        var tabName = 'test_dom_tabClickedLoaded';
        var controller = Nevow.TagLibrary.TabbedPane.TabbedPane(
            Nevow.Test.WidgetUtil.makeWidgetNode(), selectedTabName);
        var view = Nevow.Test.TestTabbedPane.StubTabbedPaneView(
            tabName, selectedTabName);
        controller.view = view;
        self.assertIdentical(controller.dom_tabClicked(tabNode), false);
        self.assertIdentical(view.tabNodes.length, 1);
        self.assertIdentical(view.tabNodes[0], tabNode);
        self.assertIdentical(view.selectedTabName, selectedTabName);
        controller.loaded();
        self.assertIdentical(view.selectedTabName, tabName);
    });


Nevow.Test.TestTabbedPane.TabbedPaneFetcher = Nevow.Athena.Widget.subclass(
    'Nevow.Test.TestTabbedPane.TabbedPaneFetcher');
/**
 * Trivial L{Nevow.Athena.Widget} subclass which fetches a tabbed pane widget
 * remotely.
 */
Nevow.Test.TestTabbedPane.TabbedPaneFetcher.methods(
    /**
     * Fetch a tabbed pane widget and add it as a child.
     */
    function dom_getTabbedPane(self) {
        var result = self.callRemote('getTabbedPane');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.node.appendChild(widget.node);
            });
        return false;
    });
