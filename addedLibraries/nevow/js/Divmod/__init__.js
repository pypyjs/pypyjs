
Divmod.debugging = false;

/**
 * Initialize state in this module that only the server knows about.
 *
 * See the Python module "nevow.athena" for where this is expected to be
 * called.
 *
 * @param transportRoot: a string, the URL where the root of the server-side
 * Athena transport hierarchy for the current page is located.
 */
Divmod.bootstrap = function (transportRoot) {
    this._location = transportRoot;
};


Divmod.baseURL = function() {
    // Use "cached" value if it exists
    if (Divmod._baseURL != undefined) {
        return Divmod._baseURL;
    }
    var nevowURL = Nevow.Athena.page.baseURL();
    // "Cache" and return
    Divmod._baseURL = nevowURL;
    return Divmod._baseURL;
};


Divmod.importURL = function(moduleName) {
    return Divmod.baseURL() + 'jsmodule/' + moduleName;
};


/**
 * Create an object with properties from C{keys} bound to the corresponding
 * objects from C{values}.  This is like C{dict(zip(keys, values))} in Python.
 *
 * @type keys: Array of strings
 * @param keys: The names of the properties to bind on the resulting object.
 *
 * @type values: Array of anything
 * @param values: The values to which to bind the properties.
 *
 * @rtype: object
 * @return: An object where C{o[keys[i]] == values[i]} for all values of C{i}
 * from C{[i..keys.length)}.
 *
 * @throw Error: Thrown if C{keys.length != values.length}.
 */
Divmod.objectify = function objectify(keys, values) {
    if (keys.length != values.length) {
        throw Error("Lengths of keys and values must be the same.");
    }

    var result = {};
    for (var i = 0; i < keys.length; ++i) {
        result[keys[i]] = values[i];
    }
    return result;
};


Divmod._global = this;


/* Retrieve an object via its fully-qualified javascript name.
 *
 * @type name: C{string}
 * @param name: The name of an object.  For example, "Divmod.namedAny".
 *
 * @type path: C{array}
 * @param path: An optional output array.  If provided, it will have the
 * superior objects on the path to the given object pushed onto it.  For
 * example, for "foo.bar.baz", C{foo} and then C{foo.bar} will be pushed
 * onto it.
 */
Divmod.namedAny = function(name, /* optional output */ path) {
    var namedParts = name.split('.');
    var obj = Divmod._global;
    for (var i = 0; i < namedParts.length; ++i) {
        obj = obj[namedParts[i]];
        if (obj == undefined) {
            Divmod.debug('widget', 'Failed in namedAny for ' + name + ' at ' + namedParts[i]);
            break;
        }
        if (i != namedParts.length - 1 && path != undefined) {
            path.push(obj);
        }
    }
    return obj;
};


Divmod.max = function(a, b) {
    if (a >= b) {
        return a;
    } else {
        return b;
    }
};


Divmod.vars = function(obj) {
    var L = [];
    for (var i in obj) {
        L.push([i, obj[i]]);
    }
    return L;
};


Divmod.dir = function(obj) {
    var L = [];
    for (var i in obj) {
        L.push(i);
    }
    return L;
};


Divmod.__classDebugCounter__ = 0;

/**
 * This tracks the number of instances of L{Divmod.Class} subclasses.
 */
Divmod.__instanceCounter__ = 0;

Divmod._CONSTRUCTOR = {};

Divmod.Class = function() {};

/**
 * Create a new subclass.
 *
 * Passing a module object for C{classNameOrModule} and C{subclassName} will
 * result in the subclass being added to the global variables, allowing for a
 * more concise method of defining a subclass.
 *
 * @type classNameOrModule: C{String} or a module object
 * @param classNameOrModule: Name of the new subclass or the module object
 *     C{subclassName} should be created in
 *
 * @type subclassName: C{String} or C{undefined}
 * @param subclassName: Name of the new subclass if C{classNameOrModule} is a
 *     module object
 *
 * @rtype: C{Divmod.Class}
 */
Divmod.Class.subclass = function(classNameOrModule, /* optional */ subclassName) {
    Divmod.__classDebugCounter__ += 1;

    /*
     * subclass() must always be called on Divmod.Class or an object returned
     * from subclass() - so in this execution context, C{this} is the "class"
     * object.
     */
    var superClass = this;

    /*
     * Create a function which basically serves the purpose of type.__call__ in Python:
     */
    var subClass = function(asConstructor) {
        var self;
        if (this instanceof subClass) {
            /*
             * If the instance is being created using C{new Class(args)},
             * C{this} will already be an object with the appropriate
             * prototype, so we can skip creating one ourself.
             */
            self = this;
        } else {
            /*
             * If the instance is being created using just C{Class(args)} (or,
             * similarly, C{Class.apply(null, args)} or C{Class.call(null,
             * args)}), then C{this} is actually some random object - maybe the
             * global execution context object, maybe the window, maybe a
             * pseudo-namespace object (ie, C{Divmod}), maybe null.  Whichever,
             * invoke C{new subClass(Divmod._CONSTRUCTOR)} to create an object
             * with the right prototype without invoking C{__init__}.
             */
            self = new subClass(Divmod._CONSTRUCTOR);
        }
        /*
         * Once we have an instance, if C{asConstructor} is not the magic internal
         * object C{Divmod._CONSTRUCTOR}, pass all our arguments on to the
         * instance's C{__init__}.
         */
        if (asConstructor !== Divmod._CONSTRUCTOR) {
            Divmod.__instanceCounter__++;

            /* set an ID unique to this instance */
            self.__id__ = Divmod.__instanceCounter__;

            self.__class__ = subClass;
            self.__init__.apply(self, arguments);
        }

        /*
         * We've accomplished... Something.  Either we made a blank, boring
         * instance of a particular class, or we actually initialized an
         * instance of something (possibly something that we had to create).
         * Whatever it is, give it back to our caller to enjoy.
         */
        return self;
    };

    /*
     * This is how you spell inheritance in JavaScript.
     */
    subClass.prototype = new superClass(Divmod._CONSTRUCTOR);

    /*
     * Make the subclass subclassable in the same way.
     */
    subClass.subclass = Divmod.Class.subclass;

    /*
     * Copy class methods and attributes, so that you can do
     * polymorphism on class methods (useful for things like
     * Nevow.Athena.Widget.get in widgets.js).
     */
    for (var varname in superClass) {
        if ((varname != 'prototype') &&
            (varname != 'constructor') &&
            (varname != '__name__') &&
            (superClass[varname] != undefined)) {
            subClass[varname] = superClass[varname];
        }
    }

    subClass.upcall = function(otherThis, methodName) {
        var funcArgs = [];
        for (var i = 2; i < arguments.length; ++i) {
            funcArgs.push(arguments[i]);
        }
        var superResult = superClass.prototype[methodName].apply(otherThis, funcArgs);
        return superResult;
    };

    subClass.method = function(methodName, methodFunction) {
        if (methodFunction != undefined) {
            Divmod.debug('deprecation', 'method() just takes a function now (called with name = ' + methodName +').');
        } else {
            methodFunction = methodName;
            methodName = methodFunction.name;
        }

        if (methodName == undefined) {
            /* Sorry (IE).
             */
            var methodSource = methodFunction.toString();
            methodName = methodSource.slice(methodSource.indexOf(' ') + 1, methodSource.indexOf('('));
        }

        subClass.prototype[methodName] = function() {
            var args = [this];
            for (var i = 0; i < arguments.length; ++i) {
                args.push(arguments[i]);
            }
            return methodFunction.apply(this, args);
        };
    };

    subClass.methods = function() {
        for (var i = 0; i < arguments.length; ++i) {
            subClass.method(arguments[i]);
        }
    };


    /**
     * Return C{true} if class C{a} is a subclass of class {b} (or is {b}).
     * Return C{false} otherwise.
     */
    subClass.subclassOf = function(superClass) {
        return (subClass.prototype instanceof superClass
                || subClass == superClass);
    };

    if (subclassName !== undefined) {
        className = classNameOrModule.__name__ + '.' + subclassName;
        classNameOrModule[subclassName] = subClass;
    } else {
        className = classNameOrModule;
    }

    var classIdentifier;
    if(className === undefined) {
        classIdentifier = '#' + Divmod.__classDebugCounter__;
    } else {
        classIdentifier = className;
    }

    /*
     * Make the subclass identifiable somehow.
     */
    subClass.__name__ = className;

    subClass.toString = function() {
        return '<Class ' + classIdentifier + '>';
    };
    subClass.prototype.toString = function() {
        return '<"Instance" of ' + classIdentifier + '>';
    };
    return subClass;
};


Divmod.Class.prototype.__init__ = function() {
    /* throw new Error("If you ever hit this code path something has gone horribly wrong");
     */
};

/**
 * Base class for all error classes.
 *
 * @ivar stack: On Firefox, a string describing the call stack at the time the
 * error was instantiated (/not/ thrown).
 */
Divmod.Error = Divmod.Class.subclass("Divmod.Error");
Divmod.Error.methods(
    function __init__(self, /* optional */ message) {
        self.message = message;
        self.stack = Error().stack;
    },

    /**
     * Represent this error as a string.
     *
     * @rtype: string
     * @return: This error, as a string.
     */
    function toString(self) {
        return self.__name__ + ': ' + self.message;
    });

/**
 * Sequence container index out of bounds.
 */
Divmod.IndexError = Divmod.Error.subclass("Divmod.IndexError");


/**
 * Base class for all warning classes.
 */
Divmod.Warning = Divmod.Class.subclass("Divmod.Warning");
Divmod.DeprecationWarning = Divmod.Warning.subclass("Divmod.DeprecationWarning");

Divmod.Module = Divmod.Class.subclass('Divmod.Module');
Divmod.Module.method(
    function __init__(self, name) {
        self.name = name;
    });


Divmod.Logger = Divmod.Class.subclass('Divmod.Logger');
Divmod.Logger.methods(
    function __init__(self) {
        self.observers = [];
    },

    function addObserver(self, observer) {
        self.observers.push(observer);
        return function() {
            self._removeObserver(observer);
        };
    },

    function _removeObserver(self, observer) {
        for (var i = 0; i < self.observers.length; ++i) {
            if (observer === self.observers[i]) {
                self.observers.splice(i, 1);
                return;
            }
        }
    },

    function _emit(self, event) {
        var errors = [];
        var obs = self.observers.slice();
        for (var i = 0; i < obs.length; ++i) {
            try {
                obs[i](event);
            } catch (e) {
                self._removeObserver(obs[i]);
                errors.push([e, "Log observer caused error, removing."]);
            }
        }
        return errors;
    },

    function emit(self, event) {
        var errors = self._emit(event);
        while (errors.length) {
            var moreErrors = [];
            for (var i = 0; i < errors.length; ++i) {
                var e = self._emit({'isError': true, 'error': errors[i][0], 'message': errors[i][1]});
                for (var j = 0; j < e.length; ++j) {
                    moreErrors.push(e[j]);
                }
            }
            errors = moreErrors;
        }
    },

    function err(self, error, /* optional */ message) {
        var event = {'isError': true, 'error': error};
        if (message != undefined) {
            event['message'] = message;
        } else {
            event['message'] = error.message;
        }
        self.emit(event);
    },

    function msg(self, message) {
        var event = {'isError': false, 'message': message};
        self.emit(event);
    });


Divmod.logger = new Divmod.Logger();
Divmod.msg = function() {
    return Divmod.logger.msg.apply(Divmod.logger, arguments);
};

Divmod.err = function() {
    return Divmod.logger.err.apply(Divmod.logger, arguments);
};

Divmod.debug = function(kind, msg) {
    Divmod.logger.emit({'isError': false,
            'message': msg, 'debug': true,
            'channel': kind});
};

Divmod.log = Divmod.debug;

/**
 * Emit a warning log event.  Warning events have four keys::
 *
 *   isError, which is always C{false}.
 *
 *   message, which is a human-readable explanation of the warning.
 *
 *   category, which is a L{Divmod.Warning} subclass categorizing the warning.
 *
 *   channel, which is always C{'warning'}.
 */
Divmod.warn = function warn(message, category) {
    Divmod.logger.emit({'isError': false,
                'message': message,
                'category': category,
                'channel': 'warning'});
};

/*
 * Set up the Firebug console as a Divmod log observer.
 */
Divmod.logger.addObserver(function (evt) {
        if (evt.isError) {
            console.log("Divmod error: " + evt.message);
            console.log(evt.error);
        } else {
            console.log("Divmod log: " + evt.message);
        }
});



/**
 * Return C{true} if the two arrays contain identical elements and C{false}
 * otherwise.
 */
Divmod.arraysEqual = function arraysEqual(a, b) {
    if (!(a instanceof Array && b instanceof Array)) {
        return false;
    }
    if (a.length !== b.length) {
        return false;
    }
    for (var i in a) {
        if (!(i in b && a[i] === b[i])) {
            return false;
        }
    }
    for (var i in b) {
        if (!(i in a)) {
            return false;
        }
    }
    return true;
};
