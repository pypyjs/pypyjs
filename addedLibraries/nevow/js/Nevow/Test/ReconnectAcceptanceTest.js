
/**
 * This module contains a page which can reconnect when forcibly disconnected.
 * Its Python half is in nevow.athena.test.acceptance.reconnect.
 */

// import Nevow.Athena

Nevow.Test.ReconnectAcceptanceTest.ReconnectingPage = (
    Nevow.Athena.PageWidget.subclass(
        "Nevow.Athena.ReconnectAcceptanceTest.ReconnectingPage"));

Nevow.Test.ReconnectAcceptanceTest.ReconnectingPage.methods(
    /**
     * When the connection is lost, unconditionally attempt to reconnect.
     */
    function connectionLost(self, reason) {
        var gp = Divmod.Runtime.theRuntime.getPage(
            "http://localhost:8080/?__athena_reconnect__=1"
            );
        gp[1].addCallback(function (result) {
            self.__init__(eval(result.response), Nevow.Athena._createMessageDelivery);
            self.deliveryChannel.start();
            // There's only one live element on this page, so cheat.
            Nevow.Athena.server.callRemote("giveElementID", 1);
        });
    });

