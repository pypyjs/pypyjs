// import Nevow.TagLibrary

Nevow.TagLibrary.TabbedPane.TabbedPaneView = Divmod.Class.subclass('Nevow.TagLibrary.TabbedPaneView');
/**
 * L{Nevow.TagLibrary.TabbedPane.TabbedPane}'s view abstraction.
 *
 * @ivar nodeById: Callable which takes a node ID and returns a node.
 * @type nodeById: C{Function}
 *
 * @ivar selectedTabName: The name of the currently selected tab.
 * @type selectedTabName: C{String}
 */
Nevow.TagLibrary.TabbedPane.TabbedPaneView.methods(
    function __init__(self, nodeById, selectedTabName) {
        self.nodeById = nodeById;
        self.selectedTabName = selectedTabName;
    },

    /**
     * Figure out the name of the tab represented by the given DOM node.
     *
     * @param tabNode: A tab DOM node.
     * @type tabNode: DOM node
     *
     * @rtype: C{String}
     */
    function tabNameFromTabNode(self, tabNode) {
        return tabNode.childNodes[0].nodeValue;
    },

    /**
     * Get the pane node for the named tab.
     *
     * @param tabName: A tab name.
     * @type tabName: C{String}
     */
    function getNamedPaneNode(self, tabName) {
        if(self._elements === undefined) {
            self._elements = self._collectTabElements();
        }
        return self._elements[tabName].paneNode;
    },

    /**
     * Remove all children from the named pane and append C{replacementNode}.
     *
     * @param tabName: A tab name.
     * @type tabName: C{String}
     *
     * @type replacementNode: DOM node
     */
    function replaceNamedPaneContent(self, tabName, replacementNode) {
        var paneNode = self.getNamedPaneNode(tabName);
        while(0 < paneNode.childNodes.length) {
            paneNode.removeChild(paneNode.childNodes[0]);
        }
        paneNode.appendChild(replacementNode);
    },

    /**
     * Map tab names to tab and pane nodes.
     */
    function _collectTabElements(self) {
        var tabContainer = self.nodeById('tab-container');
        var tabNodes = tabContainer.getElementsByTagName('li');
        var paneContainer = self.nodeById('pane-container');
        var elems = {};
        for(var i = 0; i < tabNodes.length; i++) {
            elems[self.tabNameFromTabNode(tabNodes[i])] = {
                tabNode: tabNodes[i],
                paneNode: paneContainer.childNodes[i]};
        }
        return elems;
    },

    /**
     * Switch to the named tab.
     *
     * @param tabName: The name of the tab we're switching to.
     * @type tabName: C{String}
     */
    function selectNamedTab(self, tabName) {
        if(self._elements === undefined) {
            self._elements = self._collectTabElements();
        }
        var lastSelected = self._elements[self.selectedTabName];

        Divmod.Runtime.theRuntime.setAttribute(
            lastSelected.tabNode, 'class', 'nevow-tabbedpane-tab');
        Divmod.Runtime.theRuntime.setAttribute(
            lastSelected.paneNode, 'class', 'nevow-tabbedpane-pane');

        var newlySelected = self._elements[tabName];
        Divmod.Runtime.theRuntime.setAttribute(
            newlySelected.tabNode, 'class', 'nevow-tabbedpane-selected-tab');
        Divmod.Runtime.theRuntime.setAttribute(
            newlySelected.paneNode, 'class', 'nevow-tabbedpane-selected-pane');

        self.selectedTabName = tabName;
    });

Nevow.TagLibrary.TabbedPane.TabbedPane = Nevow.Athena.Widget.subclass(
    'Nevow.TagLibrary.TabbedPane.TabbedPane');

Nevow.TagLibrary.TabbedPane.TabbedPane.methods(
    function __init__(self, node, selectedTabName) {
        self._loaded = false;
        self._pendingTabSwitch = null;
        self.view = Nevow.TagLibrary.TabbedPane.TabbedPaneView(
            function nodeById(nodeID) {
                return self.nodeById(nodeID);
            }, selectedTabName);
        Nevow.TagLibrary.TabbedPane.TabbedPane.upcall(self, '__init__', node);
    },

    function loaded(self) {
        self.node.style.opacity = "";
        self._loaded = true;
        if(self._pendingTabSwitch !== null) {
            /* switch to the tab that was most recently clicked
               while we were busy loading */
            self.view.selectNamedTab(self._pendingTabSwitch);
        }
    },

    /**
     * Call C{selectNamedTab} on our view.
     *
     * @param tabNode: The tab node which was clicked.
     * @type tabNode: DOM node
     */
    function tabClicked(self, tabNode) {
        var tabName = self.view.tabNameFromTabNode(tabNode);
        if(self._loaded) {
            self.view.selectNamedTab(tabName);
            self.namedTabSelected(tabName);
        } else {
            self._pendingTabSwitch = tabName;
        }
    },

    /**
     * DOM event handler which calls C{tabClicked}.
     *
     * @param tabNode: The tab node which was clicked.
     * @type tabNode: DOM node
     */
    function dom_tabClicked(self, tabNode) {
        self.tabClicked(tabNode);
        return false;
    },
    
    /**
     * Called after the tab has changed, with the name of the newly-selected
     * tab.
     *
     * @param tabName: The name of the newly-selected tab.
     * @type tabName: C{String}
     */
    function namedTabSelected(self, tabName) {
    });

// backward compatibility

function setupTabbedPane(data, selectedTab) {
    for(i=0; i<data.length; i++) {

        tab = document.getElementById(data[i][0]);
        page = document.getElementById(data[i][1]);

        if(i == selectedTab) {
            tab.className = 'nevow-tabbedpane-selected-tab'
            page.className = 'nevow-tabbedpane-selected-pane';
        }

        tab.onclick = function() {

            for(i=0; i<data.length; i++) {
                tab = document.getElementById(data[i][0]);
                page = document.getElementById(data[i][1]);

                if(tab.id == this.id) {
                    tab.className = 'nevow-tabbedpane-selected-tab';
                    page.className = 'nevow-tabbedpane-selected-pane';
                }
                else {
                    tab.className = 'nevow-tabbedpane-tab';
                    page.className = 'nevow-tabbedpane-pane';
                }
            }
        }
    }
}

