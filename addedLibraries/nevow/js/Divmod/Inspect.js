
/**
 * Various tools for introspecting objects at runtime.
 */

// import Divmod

/**
 * Retrieve an C{Array} of C{String}s naming the methods defined on the given
 * class and its parent classes.
 */
Divmod.Inspect.methods = function methods(cls) {
    if (typeof cls != "function") {
        throw new Error("Only classes have methods.")
    }
    var result = [];
    return result.concat(Divmod.dir(cls.prototype)).sort();
};

