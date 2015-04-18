// -*- test-case-name: nevow.test.test_javascript.JavaScriptTestSuite.testJSBase

/***

    This code was adapted and taken from MochiKit

    See <http://mochikit.com/> for documentation, downloads, license, etc.

    (c) 2005 Bob Ippolito.  All rights Reserved.

***/

// import Divmod

Divmod.Base.NotFound = Divmod.Class.subclass("Divmod.Base.NotFound");

Divmod.Base.reprString = function(o) {
    return ('"' + o.replace(/([\"\\])/g, '\\$1') + '"'
        ).replace(/[\f]/g, "\\f"
        ).replace(/[\b]/g, "\\b"
        ).replace(/[\n]/g, "\\n"
        ).replace(/[\t]/g, "\\t"
        ).replace(/[\r]/g, "\\r");
};

Divmod.Base.registerJSON = function(name, check, wrap, /* optional */override) {
        /***

            Register a JSON serialization function.  JSON serialization
            functions should take one argument and return an object
            suitable for JSON serialization:

            - string
            - number
            - boolean
            - undefined
            - object
                - null
                - Array-like (length property that is a number)
                - Objects with a "json" method will have this method called
                - Any other object will be used as {key:value, ...} pairs

            If override is given, it is used as the highest priority
            JSON serialization, otherwise it will be used as the lowest.

        ***/
        Divmod.Base.jsonRegistry.register(name, check, wrap, override);
};

Divmod.Base.serializeJSON = function(o) {
    /***

        Create a JSON serialization of an object, note that this doesn't
        check for infinite recursion, so don't do that!

    ***/
    var objtype = typeof o;
    if (objtype == "undefined") {
        return "undefined";
    } else if (objtype == "number" || objtype == "boolean") {
        return o + "";
    } else if (o === null) {
        return "null";
    }
    var reprString = Divmod.Base.reprString;
    if (objtype == "string") {
        return reprString(o);
    }
    // recurse
    var me = arguments.callee;
    // short-circuit for objects that support "json" serialization
    // if they return "self" then just pass-through...
    var newObj;
    if (typeof o.__json__ == "function") {
        newObj = o.__json__();
        if (o !== newObj) {
            return me(newObj);
        }
    }
    if (typeof o.json == "function") {
        newObj = o.json();
        if (o !== newObj) {
            return me(newObj);
        }
    }
    // array
    if (objtype != "function" && typeof o.length == "number") {
        var res = [];
        for (var i = 0; i < o.length; i++) {
            var val = me(o[i]);
            if (typeof val != "string") {
                val = "undefined";
            }
            res.push(val);
        }
        return "[" + res.join(", ") + "]";
    }
    // look in the registry
    try {
        newObj = Divmod.Base.jsonRegistry.match(o);
        if (o !== newObj) {
            return me(newObj);
        }
    } catch (e) {
        if (e != Divmod.Base.NotFound) {
            // something really bad happened
            throw e;
        }
    }
    // it's a function with no adapter, bad
    if (objtype == "function") {
        return null;
    }
    // generic object code path
    res = [];
    for (var k in o) {
        var useKey;
        if (typeof k == "number") {
            useKey = '"' + k + '"';
        } else if (typeof k == "string") {
            useKey = reprString(k);
        } else {
            // skip non-string or number keys
            continue;
        }
        val = me(o[k]);
        if (typeof val != "string") {
            // skip non-serializable values
            continue;
        }
        res.push(useKey + ":" + val);
    }
    return "{" + res.join(", ") + "}";
};

Divmod.Base.AdapterRegistry = Divmod.Class.subclass("Divmod.Base.AdapterRegistry");

Divmod.Base.AdapterRegistry.methods(
    function __init__(self) {
        /***

            A registry to facilitate adaptation.

            Pairs is an array of [name, check, wrap] triples

            All check/wrap functions in this registry should be of the same arity.

        ***/

        self.pairs = []
    },
    function register(self, name, check, wrap, /* optional */ override) {
        /***

            The check function should return true if the given arguments are
            appropriate for the wrap function.

            If override is given and true, the check function will be given
            highest priority.  Otherwise, it will be the lowest priority
            adapter.

        ***/
        if (override) {
            self.pairs.unshift([name, check, wrap]);
        } else {
            self.pairs.push([name, check, wrap]);
        }
    },
    function match(self /* ... */) {
        /***

            Find an adapter for the given arguments.

            If no suitable adapter is found, throws NotFound.

        ***/
        for (var i = 0; i < self.pairs.length; i++) {
            var pair = self.pairs[i];
            if (pair[1].apply(self, arguments)) {
                return pair[2].apply(self, arguments);
            }
        }
        throw Divmod.Base.NotFound;
    },
    function unregister(self, name) {
        /***

            Remove a named adapter from the registry

        ***/
        for (var i = 0; i < self.pairs.length; i++) {
            var pair = self.pairs[i];
            if (pair[0] == name) {
                self.pairs.splice(i, 1);
                return true;
            }
        }
        return false;
    }
);

Divmod.Base._newCallStack = function(target, path, once) {
    var callStack = [];
    var rval = function () {
        for (var i = 0; i < callStack.length; i++) {
            if (callStack[i].apply(target, arguments) === false) {
                break;
            }
        }
        if (once) {
            try {
                target[path] = null;
            } catch (e) {
                // pass
            }
        }
    };
    rval.callStack = callStack;
    return rval;
};

Divmod.Base.addToCallStack = function(target, path, func, once) {
    var existing = target[path];
    var regfunc = existing;
    if (!(typeof existing == 'function' && typeof existing.callStack == "object" && existing.callStack != null)) {
        regfunc = Divmod.Base._newCallStack(target, path, once);
        if (typeof existing == 'function') {
            regfunc.callStack.push(existing);
        }
        target[path] = regfunc;
    }
    regfunc.callStack.push(func);
};

Divmod.Base.addLoadEvent = function(func) {
    /**
     * This function is deprecated; use
     * Divmod.Runtime.theRuntime.addLoadEvent() instead.
     */

    // Even though we don't import Divmod.Runtime, it's almost guaranteed to be
    // imported anyway. We can't actually import it, because that would create
    // circular imports which Athena can't handle, and this function is now
    // deprecated anyway.
    Divmod.Runtime.theRuntime.addLoadEvent(func);
};

Divmod.Base.jsonRegistry = Divmod.Base.AdapterRegistry();
