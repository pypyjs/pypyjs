# Copyright (c) 2004 Divmod.
# See LICENSE for details.

import inspect, os.path

class UnexposedMethodError(Exception):
    """
    Raised on any attempt to get a method which has not been exposed.
    """


class Expose(object):
    """
    Helper for exposing methods for various uses using a simple decorator-style
    callable.

    Instances of this class can be called with one or more functions as
    positional arguments.  The names of these functions will be added to a list
    on the class object of which they are methods.

    @ivar attributeName: The attribute with which exposed methods will be
    tracked.
    """
    def __init__(self, doc=None):
        self.doc = doc


    def __call__(self, *funcObjs):
        """
        Add one or more functions to the set of exposed functions.

        This is a way to declare something about a class definition, similar to
        L{zope.interface.implements}.  Use it like this::

        | magic = Expose('perform extra magic')
        | class Foo(Bar):
        |     def twiddle(self, x, y):
        |         ...
        |     def frob(self, a, b):
        |         ...
        |     magic(twiddle, frob)

        Later you can query the object::

        | aFoo = Foo()
        | magic.get(aFoo, 'twiddle')(x=1, y=2)

        The call to C{get} will fail if the name it is given has not been
        exposed using C{magic}.

        @param funcObjs: One or more function objects which will be exposed to
        the client.

        @return: The first of C{funcObjs}.
        """
        if not funcObjs:
            raise TypeError("expose() takes at least 1 argument (0 given)")
        for fObj in funcObjs:
            fObj.exposedThrough = getattr(fObj, 'exposedThrough', [])
            fObj.exposedThrough.append(self)
        return funcObjs[0]


    def exposedMethodNames(self, instance):
        """
        Return an iterator of the names of the methods which are exposed on the
        given instance.
        """
        for k, callable in inspect.getmembers(instance, inspect.isroutine):
            if self in getattr(callable, 'exposedThrough', []):
                yield k


    _nodefault = object()
    def get(self, instance, methodName, default=_nodefault):
        """
        Retrieve an exposed method with the given name from the given instance.

        @raise UnexposedMethodError: Raised if C{default} is not specified and
        there is no exposed method with the given name.

        @return: A callable object for the named method assigned to the given
        instance.
        """
        method = getattr(instance, methodName, None)
        exposedThrough = getattr(method, 'exposedThrough', [])
        if self not in getattr(method, 'exposedThrough', []):
            if default is self._nodefault:
                raise UnexposedMethodError(self, methodName)
            return default
        return method


def escapeToXML(text, isattrib = False):
    """Borrowed from twisted.xish.domish

    Escape text to proper XML form, per section 2.3 in the XML specification.

     @type text: L{str}
     @param text: Text to escape

     @type isattrib: L{bool}
     @param isattrib: Triggers escaping of characters necessary for use as attribute values
    """
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    if isattrib:
        text = text.replace("'", "&apos;")
        text = text.replace("\"", "&quot;")
    return text


def getPOSTCharset(ctx):
    """Locate the unicode encoding of the POST'ed form data.

    To work reliably you must do the following:

      - set the form's enctype attribute to 'multipart/form-data'
      - set the form's accept-charset attribute, probably to 'utf-8'
      - add a hidden form field called '_charset_'

    For instance::

      <form action="foo" method="post" enctype="multipart/form-data" accept-charset="utf-8">
        <input type="hidden" name="_charset_" />
        ...
      </form>
    """

    from nevow import inevow

    request = inevow.IRequest(ctx)
    
    # Try the magic '_charset_' field, Mozilla and IE set this.
    charset = request.args.get('_charset_',[None])[0]
    if charset:
        return charset

    # Look in the 'content-type' request header
    contentType = request.received_headers.get('content-type')
    if contentType:
        charset = dict([ s.strip().split('=') for s in contentType.split(';')[1:] ]).get('charset')
        if charset:
            return charset

    return 'utf-8'


from twisted.python.reflect import qual, namedAny
from twisted.python.util import uniquify

from twisted.internet.defer import Deferred, succeed, maybeDeferred, DeferredList
from twisted.python import failure
from twisted.python.failure import Failure
from twisted.python import log


## The tests rely on these, but they should be removed ASAP
def remainingSegmentsFactory(ctx):
    return tuple(ctx.tag.postpath)


def currentSegmentsFactory(ctx):
    return tuple(ctx.tag.prepath)

class _RandomClazz(object):
    pass
class _NamedAnyError(Exception):
    'Internal error for when importing fails.'

def _namedAnyWithBuiltinTranslation(name):
    if name == '__builtin__.function':
        name='types.FunctionType'
    elif name == '__builtin__.method':
        return _RandomClazz # Hack
    elif name == '__builtin__.instancemethod':
        name='types.MethodType'
    elif name == '__builtin__.NoneType':
        name='types.NoneType'
    elif name == '__builtin__.generator':
        name='types.GeneratorType'
    return namedAny(name)

# Import resource_filename from setuptools's pkg_resources module if possible
# because it handles resources in .zip files. If it's not provide a version
# that assumes the resource is directly available on the filesystem. 
try:
    from pkg_resources import resource_filename
except ImportError:
    def resource_filename(modulename, resource_name):
        modulepath = namedAny(modulename).__file__
        return os.path.join(os.path.dirname(os.path.abspath(modulepath)), resource_name)



class CachedFile(object):
    """
    Helper for caching operations on files in the filesystem.
    """
    def __init__(self, path, loader):
        """
        @type path: L{str}
        @param path: The path to the associated file in the filesystem.

        @param loader: A callable that returns the relevant data; invoked when
        the cache is empty or stale.
        """

        self.path = path
        self.loader = loader
        self.invalidate()

    def invalidate(self):
        """
        Invalidate the cache, forcing a reload from disk at the next attempted
        load.
        """
        self._mtime = None

    def load(self, *args, **kwargs):
        """
        Load this file. Any positional or keyword arguments will be passed
        along to the loader callable, after the path itself.
        """
        currentTime = os.path.getmtime(self.path)
        if self._mtime is None or currentTime != self._mtime:
            self._cachedObj = self.loader(self.path, *args, **kwargs)
            self._mtime = currentTime

        return self._cachedObj
