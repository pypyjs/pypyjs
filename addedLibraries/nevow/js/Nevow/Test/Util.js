
/**
 * Utilities for testing.
 */

Nevow.Test.Util.Faker = Divmod.Class.subclass("Nevow.Test.Util.Faker");
/**
 * A Faker replaces attributes on various objects, makes a record of those
 * replacements, and restores their original values when it is stopped.  It is
 * generally intended to be created in a test case's setUp and C{stop()}ped in
 * that test case's tearDown.  It can be useful for any kind of temporary
 * replacement, but especially useful for replacing fragile global state.
 *
 * @ivar _fakes: an array of objects with 3 attributes.  'parent': the object
 * which has the attribute which was replaced, 'name': the name of the
 * attribute which was replaced, 'original': the original value of that
 * attribute.
 */
Nevow.Test.Util.Faker.methods(
    /**
     * Set up a list of objects which were mocked so they can be restored in
     * tearDown.
     */
    function __init__(self) {
        self._fakes = [];
    },

    /**
     * Safely replace an attribute for the duration of the test, such that it will
     * be restored in tearDown.
     *
     * @return: the new value, for convenience in expressions such as 'var
     * fakeThing = faker.fake("fakeThing", {})';
     */
    function fake(self, name, newValue, parent /* = Divmod._global */) {
        if (parent === undefined) {
            parent = Divmod._global;
        }
        self._fakes.push({parent: parent,
                name: name,
                original: parent[name]});
        parent[name] = newValue;
        return newValue;
    },

    /**
     * Put back all objects which were faked by this faker.
     */
    function stop(self) {
        for (var i = 0; i < self._fakes.length; i++) {
            var fake = self._fakes[i];
            fake.parent[fake.name] = fake.original;
        }
    });
