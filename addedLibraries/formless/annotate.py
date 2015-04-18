# -*- test-case-name: formless.test -*-
# Copyright (c) 2004 Divmod.
# See LICENSE for details.


"""And the earth was without form, and void; and darkness was upon the face of the deep.
"""

import os
import sys
import inspect
import warnings
from zope.interface import implements
from zope.interface.interface import InterfaceClass, Attribute

from nevow import util


from formless import iformless


class count(object):
    def __init__(self):
        self.id = 0
    def next(self):
        self.id += 1
        return self.id

nextId = count().next


class InputError(Exception):
    """A Typed instance was unable to coerce from a string to the
    appropriate type.
    """
    def __init__(self, reason):
        self.reason = reason
    
    def __str__(self):
        return self.reason


class ValidateError(Exception):
    """A Binding instance was unable to coerce all it's arguments from a
    dictionary of lists of strings to the appropriate types.

    One use of this is to raise from an autocallable if an input is invalid.
    For example, a password is incorrect.
    
    errors must be a dictionary mapping argument names to error messages
    to display next to the arguments on the form.

    formErrorMessage is a string to display at the top of the form, not tied to
    any specific argument on the form.

    partialForm is a dict mapping argument name to argument value, allowing
    you to have the form save values that were already entered in the form.
    """
    def __init__(self, errors, formErrorMessage=None, partialForm=None):
        self.errors = errors
        self.formErrorMessage = formErrorMessage
        if partialForm is None:
            self.partialForm = {}
        else:
            self.partialForm = partialForm

    def __str__(self):
        return self.formErrorMessage



class Typed(Attribute):
    """A typed value. Subclasses of Typed are constructed inside of
    TypedInterface class definitions to describe the types of properties,
    the parameter types to method calls, and method return types.
    
    @ivar label: The short label which will describe this
        parameter/proerties purpose to the user.
    
    @ivar description: A long description which further describes the
        sort of input the user is expected to provide.
    
    @ivar default: A default value that may be used as an initial
        value in the form.

    @ivar required: Whether the user is required to provide a value

    @ivar null: The value which will be produced if required is False
        and the user does not provide a value

    @ivar unicode: Iff true, try to determine the character encoding
        of the data from the browser and pass unicode strings to
        coerce.
    """
    implements(iformless.ITyped)

    complexType = False
    strip = False
    label = None
    description = None
    default = ''
    required = False
    requiredFailMessage = 'Please enter a value'
    null = None
    unicode = False

    __name__ = ''

    def __init__(
        self,
        label=None,
        description=None,
        default=None,
        required=None,
        requiredFailMessage=None,
        null=None,
        unicode=None,
        **attributes):

        self.id = nextId()
        if label is not None:
            self.label = label
        if description is not None:
            self.description = description
        if default is not None:
            self.default = default
        if required is not None:
            self.required = required
        if requiredFailMessage is not None:
            self.requiredFailMessage = requiredFailMessage
        if null is not None:
            self.null = null
        if unicode is not None:
            self.unicode = unicode
        self.attributes = attributes

    def getAttribute(self, name, default=None):
        return self.attributes.get(name, default)

    def coerce(self, val, configurable):
        raise NotImplementedError, "Implement in %s" % util.qual(self.__class__)


#######################################
## External API; your code will create instances of these objects
#######################################

class String(Typed):
    """A string that is expected to be reasonably short and contain no
    newlines or tabs.

    strip: remove leading and trailing whitespace.
    """

    requiredFailMessage = 'Please enter a string.'
    # iff true, return the stripped value.
    strip = False

    def __init__(self, *args, **kwargs):
        try:
            self.strip = kwargs['strip']
            del kwargs['strip']
        except KeyError:
            pass
        Typed.__init__(self, *args, **kwargs)

    def coerce(self, val, configurable):
        if self.strip:
            val = val.strip()
        return val


class Text(String):
    """A string that is likely to be of a significant length and
    probably contain newlines and tabs.
    """


class Password(String):
    """Password is used when asking a user for a new password. The renderer
    user interface will possibly ask for the password multiple times to
    ensure it has been entered correctly. Typical use would be for
    registration of a new user."""
    requiredFailMessage = 'Please enter a password.'


class PasswordEntry(String):
    """PasswordEntry is used to ask for an existing password. Typical use
    would be for login to an existing account."""
    requiredFailMessage = 'Please enter a password.'


class FileUpload(Typed):
    requiredFailMessage = 'Please enter a file name.'

    def coerce(self, val, configurable):
        return val.filename


class Integer(Typed):

    requiredFailMessage = 'Please enter an integer.'

    def coerce(self, val, configurable):
        if val is None:
            return None
        try:
            return int(val)
        except ValueError:
            if sys.version_info < (2,3): # Long/Int aren't integrated
                try:
                    return long(val)
                except ValueError:
                    raise InputError("'%s' is not an integer." % val)
            
            raise InputError("'%s' is not an integer." % val)


class Real(Typed):

    requiredFailMessage = 'Please enter a real number.'

    def coerce(self, val, configurable):
        # TODO: This shouldn't be required; check.
        # val should never be None, but always a string.
        if val is None:
            return None
        try:
            return float(val)
        except ValueError:
            raise InputError("'%s' is not a real number." % val)


class Boolean(Typed):
    def coerce(self, val, configurable):
        if val == 'False':
            return False
        elif val == 'True':
            return True
        raise InputError("'%s' is not a boolean" % val)


class FixedDigitInteger(Integer):
    
    def __init__(self, digits = 1, *args, **kw):
        Integer.__init__(self, *args, **kw)
        self.digits = digits
        self.requiredFailMessage = \
            'Please enter a %d digit integer.' % self.digits

    def coerce(self, val, configurable):
        v = Integer.coerce(self, val, configurable)
        if len(str(v)) != self.digits:
            raise InputError("Number must be %s digits." % self.digits)
        return v


class Directory(Typed):
    
    requiredFailMessage = 'Please enter a directory name.'

    def coerce(self, val, configurable):
        # TODO: This shouldn't be required; check.
        # val should never be None, but always a string.
        if val is None:
            return None
        if not os.path.exists(val):
            raise InputError("The directory '%s' does not exist." % val)
        return val


class Choice(Typed):
    """Allow the user to pick from a list of "choices", presented in a drop-down
    menu. The elements of the list will be rendered by calling the function
    passed to stringify, which is by default "str".
    """

    requiredFailMessage = 'Please choose an option.'

    def __init__(self, choices=None, choicesAttribute=None, stringify=str,
                 valueToKey=str, keyToValue=None, keyAndConfigurableToValue=None,
                 *args, **kw):
        """
        Create a Choice.

        @param choices: an object adaptable to IGettable for an iterator (such
        as a function which takes (ctx, data) and returns a list, a list
        itself, a tuple, a generator...)

        @param stringify: a pretty-printer.  a function which takes an object
        in the list of choices and returns a label for it.

        @param valueToKey: a function which converts an object in the list of
        choices to a string that can be sent to a client.

        @param keyToValue: a 1-argument convenience version of
        keyAndConfigurableToValue

        @param keyAndConfigurableToValue:  a 2-argument function which takes a string such as
        one returned from valueToKey and a configurable, and returns an object
        such as one from the list of choices.
        """

        Typed.__init__(self, *args, **kw)
        self.choices = choices
        if choicesAttribute:
            self.choicesAttribute = choicesAttribute
        if getattr(self, 'choicesAttribute', None):
            warnings.warn(
                "Choice.choicesAttribute is deprecated. Please pass a function to choices instead.",
                DeprecationWarning,
                stacklevel=2)
            def findTheChoices(ctx, data):
                return getattr(iformless.IConfigurable(ctx).original, self.choicesAttribute)
            self.choices = findTheChoices

        self.stringify = stringify
        self.valueToKey=valueToKey

        if keyAndConfigurableToValue is not None:
            assert keyToValue is None, 'This should be *obvious*'
            self.keyAndConfigurableToValue = keyAndConfigurableToValue
        elif keyToValue is not None:
            self.keyAndConfigurableToValue = lambda x,y: keyToValue(x)
        else:
            self.keyAndConfigurableToValue = lambda x,y: str(x)


    def coerce(self, val, configurable):
        """Coerce a value with the help of an object, which is the object
        we are configuring.
        """
        return self.keyAndConfigurableToValue(val, configurable)


class Radio(Choice):
    """Type influencing presentation! horray!

    Show the user radio button choices instead of a picklist.
    """


class Any(object):
    """Marker which indicates any object type.
    """


class Object(Typed):
    complexType = True
    def __init__(self, interface=Any, *args, **kw):
        Typed.__init__(self, *args, **kw)
        self.iface = interface

    def __repr__(self):
        if self.iface is not None:
            return "%s(interface=%s)" % (self.__class__.__name__, util.qual(self.iface))
        return "%s(None)" % (self.__class__.__name__,)



class List(Object):
    implements(iformless.IActionableType)

    complexType = True
    def __init__(self, actions=None, header='', footer='', separator='', *args, **kw):
        """Actions is a list of action methods which may be invoked on one
        or more of the elements of this list. Action methods are defined
        on a TypedInterface and declare that they take one parameter
        of type List. They do not declare themselves to be autocallable
        in the traditional manner. Instead, they are passed in the actions
        list of a list Property to declare that the action may be taken on
        one or more of the list elements.
        """
        if actions is None:
            actions = []
        self.actions = actions
        self.header = header
        self.footer = footer
        self.separator = separator
        Object.__init__(self, *args, **kw)

    def coerce(self, data, configurable):
        return data

    def __repr__(self):
        if self.iface is not None:
            return "%s(interface=%s)" % (self.__class__.__name__, util.qual(self.iface))
        return self.__class__.__name__ + "()"

    def attachActionBindings(self, possibleActions):
        ## Go through and replace self.actions, which is a list of method
        ## references, with the MethodBinding instance which holds 
        ## metadata about this function.
        act = self.actions
        for method, binding in possibleActions:
            if method in act:
                act[act.index(method)] = binding

    def getActionBindings(self):
        return self.actions

class Dictionary(List):
    pass


class Table(Object):
    pass


class Request(Typed):
    """Marker that indicates that an autocallable should be passed the
    request when called. Including a Request arg will not affect the
    appearance of the rendered form.

    >>> def doSomething(request=formless.Request(), name=formless.String()):
    ...     pass
    >>> doSomething = formless.autocallable(doSomething)
    """
    complexType = True ## Don't use the regular form


class Context(Typed):
    """Marker that indicates that an autocallable should be passed the
    context when called. Including a Context arg will not affect the
    appearance of the rendered form.

    >>> def doSomething(context=formless.Context(), name=formless.String()):
    ...     pass
    >>> doSomething = formless.autocallable(doSomething)
    """
    complexType = True ## Don't use the regular form


class Button(Typed):
    def coerce(self, data, configurable):
        return data


class Compound(Typed):
    complexType = True
    def __init__(self, elements=None, *args, **kw):
        assert elements, "What is the sound of a Compound type with no elements?"
        self.elements = elements
        Typed.__init__(self, *args, **kw)

    def __len__(self):
        return len(self.elements)

    def coerce(self, data, configurable):
        return data


class Method(Typed):
    def __init__(self, returnValue=None, arguments=(), *args, **kw):
        Typed.__init__(self, *args, **kw)
        self.returnValue = returnValue
        self.arguments = arguments


class Group(Object):
    pass


def autocallable(method, action=None, visible=False, **kw):
    """Describe a method in a TypedInterface as being callable through the
    UI. The "action" paramter will be used to label the action button, or the
    user interface element which performs the method call.
    
    Use this like a method adapter around a method in a TypedInterface:
    
    >>> class IFoo(TypedInterface):
    ...     def doSomething():
    ...         '''Do Something
    ...         
    ...         Do some action bla bla'''
    ...         return None
    ...     doSomething = autocallable(doSomething, action="Do it!!")
    """
    method.autocallable = True
    method.id = nextId()
    method.action = action
    method.attributes = kw
    return method


#######################################
## Internal API; formless uses these objects to keep track of
## what names are bound to what types
#######################################


class Binding(object):
    """Bindings bind a Typed instance to a name. When TypedInterface is subclassed,
    the metaclass looks through the dict looking for all properties and methods.
    
    If a properties is a Typed instance, a Property Binding is constructed, passing
    the name of the binding and the Typed instance.
    
    If a method has been wrapped with the "autocallable" function adapter,
    a Method Binding is constructed, passing the name of the binding and the
    Typed instance. Then, getargspec is called. For each keyword argument
    in the method definition, an Argument is constructed, passing the name
    of the keyword argument as the binding name, and the value of the
    keyword argument, a Typed instance, as the binding typeValue.
    
    One more thing. When an autocallable method is found, it is called with
    None as the self argument. The return value is passed the Method
    Binding when it is constructed to keep track of what the method is
    supposed to return.
    """
    implements(iformless.IBinding)

    label = None
    description = ''

    def __init__(self, name, typedValue, id=0):
        self.id = id
        self.name = name
        self.typedValue = iformless.ITyped(typedValue)

        # pull these out to remove one level of indirection...
        if typedValue.description is not None:
            self.description = typedValue.description
        if typedValue.label is not None:
            self.label = typedValue.label
        if self.label is None:
            self.label = nameToLabel(name)
        self.default = typedValue.default
        self.complexType = typedValue.complexType

    def __repr__(self):
        return "<%s %s=%s at 0x%x>" % (self.__class__.__name__, self.name, self.typedValue.__class__.__name__, id(self))

    def getArgs(self):
        """Return a *copy* of this Binding.
        """
        return (Binding(self.name, self.original, self.id), )

    def getViewName(self):
        return self.original.__class__.__name__.lower()

    def configure(self, boundTo, results):
        raise NotImplementedError, "Implement in %s" % util.qual(self.__class__)

    def coerce(self, val, configurable):
        if hasattr(self.original, 'coerce'):
            return self.original.coerce(val)
        return val

class Argument(Binding):
    pass


class Property(Binding):
    action = 'Change'
    def configure(self, boundTo, results):
        ## set the property!
        setattr(boundTo, self.name, results[self.name])


class MethodBinding(Binding):
    typedValue = None
    def __init__(self, name, typeValue, id=0, action="Call", attributes = {}):
        Binding.__init__(self, name, typeValue,  id)
        self.action = action
        self.arguments = typeValue.arguments
        self.returnValue = typeValue.returnValue
        self.attributes = attributes

    def getAttribute(self, name):
        return self.attributes.get(name, None)

    def configure(self, boundTo, results):
        bound = getattr(boundTo, self.name)
        return bound(**results)

    def getArgs(self):
        """Make sure each form post gets a unique copy of the argument list which it can use to keep
        track of values given in partially-filled forms
        """
        return self.typedValue.arguments[:]


class ElementBinding(Binding):
    """An ElementBinding binds a key to an element of a container.
    For example, ElementBinding('0', Object()) indicates the 0th element
    of a container of Objects. When this ElementBinding is bound to
    the list [1, 2, 3], resolving the binding will result in the 0th element,
    the object 1.
    """
    pass


class GroupBinding(Binding):
    """A GroupBinding is a way of naming a group of other Bindings.
    The typedValue of a GroupBinding should be a Configurable.
    The Bindings returned from this Configurable (usually a TypedInterface)
    will be rendered such that all fields must/may be filled out, and all
    fields will be changed at once upon form submission.
    """
    def __init__(self, name, typedValue, id=0):
        """Hack to prevent adaption to ITyped while the adapters are still
        being registered, because we know that the typedValue should be
        a Group when we are constructing a GroupBinding.
        """
        self.id = id
        self.name = name
        self.typedValue = Group(typedValue)

        # pull these out to remove one level of indirection...
        self.description = typedValue.description
        if typedValue.label:
            self.label = typedValue.label
        else:
            self.label = nameToLabel(name)
        self.default = typedValue.default
        self.complexType = typedValue.complexType

    def configure(self, boundTo, group):
        print "CONFIGURING GROUP BINDING", boundTo, group


def _sorter(x, y):
    return cmp(x.id, y.id)


class _Marker(object):
    pass


def caps(c):
    return c.upper() == c


def nameToLabel(mname):
    labelList = []
    word = ''
    lastWasUpper = False
    for letter in mname:
        if caps(letter) == lastWasUpper:
            # Continuing a word.
            word += letter
        else:
            # breaking a word OR beginning a word
            if lastWasUpper:
                # could be either
                if len(word) == 1:
                    # keep going
                    word += letter
                else:
                    # acronym
                    # we're processing the lowercase letter after the acronym-then-capital
                    lastWord = word[:-1]
                    firstLetter = word[-1]
                    labelList.append(lastWord)
                    word = firstLetter + letter
            else:
                # definitely breaking: lower to upper
                labelList.append(word)
                word = letter
        lastWasUpper = caps(letter)
    if labelList:
        labelList[0] = labelList[0].capitalize()
    else:
        return mname.capitalize()
    labelList.append(word)
    return ' '.join(labelList)


def labelAndDescriptionFromDocstring(docstring):
    if docstring is None:
        docstring = ''
    docs = filter(lambda x: x, [x.strip() for x in docstring.split('\n')])
    if len(docs) > 1:
        return docs[0], '\n'.join(docs[1:])
    else:
        return None, '\n'.join(docs)


class MetaTypedInterface(InterfaceClass):
    """The metaclass for TypedInterface. When TypedInterface is subclassed,
    this metaclass' __new__ method is invoked. The Typed Binding introspection
    described in the Binding docstring occurs, and when it is all done, there will
    be three attributes on the TypedInterface class:
    
     - __methods__: An ordered list of all the MethodBinding instances
       produced by introspecting all autocallable methods on this
       TypedInterface

     - __properties__: An ordered list of all the Property Binding
       instances produced by introspecting all properties which have
       Typed values on this TypedInterface

     - __spec__: An ordered list of all methods and properties
    
    These lists are sorted in the order that the methods and properties appear
    in the TypedInterface definition.
    
    For example:
    
    >>> class Foo(TypedInterface):
    ...     bar = String()
    ...     baz = Integer()
    ...     
    ...     def frotz(): pass
    ...     frotz = autocallable(frotz)
    ...     
    ...     xyzzy = Float()
    ...     
    ...     def blam(): pass
    ...     blam = autocallable(blam)

    Once the metaclass __new__ is done, the Foo class instance will have three
    properties, __methods__, __properties__, and __spec__,
    """

    def __new__(cls, name, bases, dct):
        rv = cls = InterfaceClass.__new__(cls)
        cls.__id__ = nextId()
        cls.__methods__ = methods = []
        cls.__properties__ = properties = []
        cls.default = 'DEFAULT'
        cls.complexType = True
        possibleActions = []
        actionAttachers = []
        for key, value in dct.items():
            if key[0] == '_': continue

            if isinstance(value, MetaTypedInterface):
                ## A Nested TypedInterface indicates a GroupBinding
                properties.append(GroupBinding(key, value, value.__id__))

                ## zope.interface doesn't like these
                del dct[key]
                setattr(cls, key, value)
            elif callable(value):
                names, _, _, typeList = inspect.getargspec(value)

                _testCallArgs = ()

                if typeList is None:
                    typeList = []

                if len(names) == len(typeList) + 1:
                    warnings.warn(
                        "TypeInterface method declarations should not have a 'self' parameter",
                        DeprecationWarning,
                        stacklevel=2)
                    del names[0]
                    _testCallArgs = (_Marker,)

                if len(names) != len(typeList):
                    ## Allow non-autocallable methods in the interface; ignore them
                    continue

                argumentTypes = [
                    Argument(n, argtype, argtype.id) for n, argtype in zip(names[-len(typeList):], typeList)
                ]

                result = value(*_testCallArgs)

                label = None
                description = None
                if getattr(value, 'autocallable', None):
                    # autocallables have attributes that can set label and description
                    label = value.attributes.get('label', None)
                    description = value.attributes.get('description', None)

                adapted = iformless.ITyped(result, None)
                if adapted is None:
                    adapted = Object(result)

                # ITyped has label and description we can use
                if label is None:
                    label = adapted.label
                if description is None:
                    description = adapted.description

                defaultLabel, defaultDescription = labelAndDescriptionFromDocstring(value.__doc__)
                if defaultLabel is None:
                    # docstring had no label, try the action if it is an autocallable
                    if getattr(value, 'autocallable', None):
                        if label is None and value.action is not None:
                            # no explicit label, but autocallable has action we can use
                            defaultLabel = value.action

                if defaultLabel is None:
                    # final fallback: use the function name as label
                    defaultLabel = nameToLabel(key)

                if label is None:
                    label = defaultLabel
                if description is None:
                    description = defaultDescription

                theMethod = Method(
                    adapted, argumentTypes, label=label, description=description
                )

                if getattr(value, 'autocallable', None):
                    methods.append(
                        MethodBinding(
                            key, theMethod, value.id, value.action, value.attributes))
                else:
                    possibleActions.append((value, MethodBinding(key, theMethod)))
            else:
                if not value.label:
                    value.label = nameToLabel(key)
                if iformless.IActionableType.providedBy(value):
                    actionAttachers.append(value)
                properties.append(
                    Property(key, value, value.id)
                )
        for attacher in actionAttachers:
            attacher.attachActionBindings(possibleActions)
        methods.sort(_sorter)
        properties.sort(_sorter)
        cls.__spec__ = spec = methods + properties
        spec.sort(_sorter)
        cls.name = name

        # because attributes "label" and "description" would become Properties,
        # check for ones with an underscore prefix.
        cls.label = dct.get('_label', None)
        cls.description = dct.get('_description', None)
        defaultLabel, defaultDescription = labelAndDescriptionFromDocstring(dct.get('__doc__'))
        if defaultLabel is None:
            defaultLabel = nameToLabel(name)
        if cls.label is None:
            cls.label = defaultLabel
        if cls.description is None:
            cls.description = defaultDescription

        return rv


#######################################
## External API; subclass this to create a TypedInterface
#######################################

TypedInterface = MetaTypedInterface('TypedInterface', (InterfaceClass('TypedInterface'), ), {})

