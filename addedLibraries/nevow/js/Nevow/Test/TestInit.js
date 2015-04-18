// -*- test-case-name: nevow.test.test_javascript.JSUnitTests.test_init -*-

// import Divmod.UnitTest
// import Nevow.Athena
// import Nevow.Test.Util

Nevow.Test.TestInit.InitTests = Divmod.UnitTest.TestCase.subclass(
    'Nevow.Test.TestInit.InitTests');
Nevow.Test.TestInit.InitTests.methods(
    /**
     * Set up a faker so that this test can fake global variables.
     */
    function setUp(self) {
        self.faker = Nevow.Test.Util.Faker();
    },
    /**
     * Restore global state to what it was before this test's faker was put
     * into effect.
     */
    function tearDown(self) {
        self.faker.stop();
    },

    /**
     * Bootstrapping the Nevow.Athena module should create a page widget
     * object of the requested class and assign it to Nevow.Athena.page, then
     * notify the page to bind its events to the global window.
     */
    function test_bootstrap(self) {
        var notAthena = {};
        var myWind = self.faker.fake('window', {});
        var SOME_ID = 'asdfjkl;';
        notAthena.bootstrap = Nevow.Athena.bootstrap;
        notAthena.bootstrap('Nevow.Athena.PageWidget', SOME_ID);
        self.assert(notAthena.page instanceof Nevow.Athena.PageWidget);
        self.assertIdentical(notAthena.page.livepageID, SOME_ID);

        var keyPressed = 0;
        notAthena.page.onkeypress = function () {
            keyPressed++;
        };
        myWind.onkeypress();
        self.assertIdentical(keyPressed, 1);
        myWind.onkeypress();
        self.assertIdentical(keyPressed, 2);

        var channelStarted = false;
        var beforeUnloaded = false;

        var notDeliveryChannel = {
            'start': function start() {
                channelStarted = true;
            }};

        notAthena.page.deliveryChannel = notDeliveryChannel;
        notAthena.page.onbeforeunload = function () {
            beforeUnloaded = true;
        };

        Divmod.Runtime.theRuntime.loadEvents[0]();
        self.assert(channelStarted);
        myWind.onbeforeunload();
        self.assert(beforeUnloaded);
    });
