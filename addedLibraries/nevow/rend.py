# Copyright (c) 2004 Divmod.
# See LICENSE for details.

"""Page, Fragment and other standard renderers.

This module contains classes and function responsible for rendering
dynamic content and a few useful mixin classes for inheriting common
functionality.

Mostly, you'll use the renderers:

 - B{Page} - Nevow's main resource type for rendering web pages and
   locating child resource.
 - B{Fragment} - useful for rendering more complex parts of a document
   that require a set of data_* and render_* methods.
 - B{sequence} - render each item in a sequence.
 - B{mapping} - publish a dictionary by filling slots
"""

from time import time as now
from cStringIO import StringIO
import random
import warnings

from zope.interface import implements, providedBy

import twisted.python.components as tpc
from twisted.python.reflect import qual, accumulateClassList

from nevow.context import WovenContext, NodeNotFound, PageContext
from nevow import inevow, tags, flat, util, url
from nevow.util import log

import formless
from formless import iformless, annotate


def _getPreprocessors(inst):
    """
    Accumulate elements from the sequences bound at the C{preprocessors}
    attribute on all classes in the inheritance hierarchy of the class of
    C{inst}.  A C{preprocessors} attribute on the given instance overrides
    all preprocessors from the class inheritance hierarchy.
    """
    if 'preprocessors' in vars(inst):
        return inst.preprocessors
    preprocessors = []
    accumulateClassList(
        inst.__class__,
        'preprocessors',
        preprocessors)
    return preprocessors



class RenderFactory(object):
    implements(inevow.IRendererFactory)

    def renderer(self, context, name):
        """Return a renderer with the given name.
        """

        # The named renderer can be parameterised, i.e. 'renderIt one,two,three'
        args = []
        if name.find(' ') != -1:
            name, args = name.split(None, 1)
            args = [arg.strip() for arg in args.split(',')]

        callable = getattr(self, 'render_%s' % name, None)
        if callable is None:
            warnings.warn(
                "Renderer %r missing on %s will result in an exception." % (
                    name, qual(type(self))),
                category=DeprecationWarning,
                stacklevel=1)
            callable = lambda *a, **kw: context.tag[
                "The renderer named '%s' was not found in %r." % (name, self)]

        if args:
            return callable(*args)

        return callable

    render_sequence = lambda self, context, data: sequence(context, data)
    render_mapping = lambda self, context, data: mapping(context, data)
    render_string = lambda self, context, data: string(context, data)
    render_xml = lambda self, context, data: context.tag.clear()[tags.xml(data)]
    render_data = lambda self, context, data_: data(context, data_)


class MacroFactory(object):
    implements(inevow.IMacroFactory)

    def macro(self, ctx, name):
        """Return a macro with the given name.
        """
        # The named macro can be parameterized, i.e. 'macroFoo foo,bar,baz'
        args = []
        if name.find(' ') != -1:
            name, args = name.split(None, 1)
            args = [arg.strip() for arg in args.split(',')]

        callable = getattr(self, 'macro_%s' % name, None)
        if callable is None:
            callable = lambda ctx, *args: ctx.tag[
                "The macro named '%s' was not found in %r." % (name, self)]

        if args:
            ## Macros are expanded in TagSerializer by calling them with a single arg, the context
            return lambda ctx: callable(ctx, *args)

        return callable


class DataNotFoundError(Exception):
    """Raised when a data directive could not be resolved on the page or its
    original attribute by the DataFactory.
    """


class DataFactory(object):
    implements(inevow.IContainer)

    def child(self, context, n):
        args = []
        if n.find(' ') != -1:
            name, args = n.split(None, 1)
            args = [arg.strip() for arg in args.split(',')]
        else:
            name = n

        callable = getattr(self, 'data_%s' % name, None)
        ## If this page doesn't have an appropriate data_* method...
        if callable is None:
            ## See if our self.original has an IContainer...
            container = inevow.IContainer(self.original, None)
            if container is None:
                raise DataNotFoundError("The data named %r was not found in %r." % (name, self))
            else:
                ## And delegate to it if so.
                return container.child(context, n)

        if args:
            return callable(*args)

        return callable


class FreeformChildMixin:
    """Mixin that handles locateChild for freeform segments."""
    def locateChild(self, ctx, segments):
        request = inevow.IRequest(ctx)
        ## The method or property name we are going to validate against/affect
        bindingName = None

        name = segments[0]
        if name.startswith('freeform_post!'):
            configurableName, bindingName = name.split('!')[1:3]
        elif name.startswith('freeform-action-post!'):
            configurableName, request.args['freeform-actee'] = name.split('!')[1:3]
            bindingName = request.args['freeform-action'][0]
        if bindingName:
            ctx.remember(self, inevow.IResource)
            ctx.remember(request, inevow.IRequest)
            cf = iformless.IConfigurableFactory(self)
            def checkC(c):
                if c is not None:
                    return self.webFormPost(request, self, c, ctx, bindingName, request.args)
            return util.maybeDeferred(cf.locateConfigurable, ctx, configurableName).addCallback(checkC)
        return NotFound

    def child_freeform_hand(self, ctx):
        carryoverHand = inevow.IHand(ctx, None)
        if carryoverHand is not None:
            inevow.ISession(ctx).setComponent(inevow.IHand, carryoverHand)
            return carryoverHand
        return inevow.IHand(inevow.ISession(ctx), None)


class ConfigurableMixin(object):
    """
    A sane L{IConfigurable} implementation for L{Fragment} and L{Page}. 

    Methods starting with C{bind_} automatically expose corresponding method
    names.  C{bind_*} should return an L{IBinding} (L{PropertyBinding} or
    L{MethodBinding}), or, as a shortcut for L{MethodBinding}, a C{list} of
    two-C{tuples} like this::

        def bind_foo(self, ctx):
            return [('argName', String()), ('anotherArg', Integer())]

        def foo(self, argName, anotherArg):
            assert isinstance(argName, str)
            assert isinstance(anotherArg, int)
    """
    implements(iformless.IConfigurable)

    def getBindingNames(self, ctx):
        """Expose bind_* methods and attributes on this class.
        """
        for name in dir(self):
            if name.startswith('bind_'):
                yield name[len('bind_'):]

    def getBinding(self, ctx, name):
        """Massage bind_* methods and attributes into an
        IBinding. The bind_* method or attribute can either
        already implement IBinding or be a list of twoples
        which will be massaged into a MethodBinding as
        described in the ConfigurableMixin class docstring.
        """
        def _get_binding(binding):
            if callable(binding):
                binding = util.maybeDeferred(binding, ctx)
            return binding

        def _convert_list(binding):
            if isinstance(binding, list):
                binding = annotate.MethodBinding(
                    name, annotate.Method(arguments=[
                    annotate.Argument(n, v, v.id)
                    for (n, v) in binding]))
            return binding

        binding = util.maybeDeferred(getattr, self, 'bind_%s' % name)
        return binding.addCallback(_get_binding).addCallback(_convert_list)

    def getDefault(self, forBinding):
        """Get a default value for a given binding. If the
        binding is a Property, get the current value of
        that property off self. If not, simply return
        forBinding.default.
        """
        ## If it is a Property, get the value off self
        if not isinstance(forBinding, annotate.Argument):
            if hasattr(self, forBinding.name):
                return getattr(self, forBinding.name)
        return forBinding.default

    def postForm(self, ctx, bindingName, args):
        """Accept a form post to the given bindingName.
        The post arguments are given in args.

        This will invoke the IInputProcessor for the
        binding with the given name. If it succeeds, the
        property will be modified or the method will have
        been called. If it fails, a ValidateError exception
        will be raised.
        """
        def _callback(binding):
            ctx.remember(binding, iformless.IBinding)
            ctx.remember(self, iformless.IConfigurable)
            rv = iformless.IInputProcessor(binding).process(ctx, self, args)
            ctx.remember(rv, inevow.IHand)
            ctx.remember('%r success.' % bindingName, inevow.IStatusMessage)
            return rv
        return util.maybeDeferred(self.getBinding, ctx, 
                                  bindingName).addCallback(_callback)


class ConfigurableFactory:
    """Locates configurables by looking for methods that start with
    configurable_ and end with the name of the configurable. The method
    should take a single arg (other than self) - the current context.
    """
    implements(iformless.IConfigurableFactory)

    def locateConfigurable(self, context, name):
        """formless.webform.renderForms calls locateConfigurable on the IConfigurableFactory
        instance it retrieves from the context. It passes the "name" that was passed to it,
        so if renderForms() was placed in the DOM, locateConfigurable will be called with
        name = ''; if renderForms('foo') was placed in the DOM, locateConfigurable will
        be called with name = 'foo'.

        This default implementation of locateConfigurable looks for a configurable_* method
        corresponding to the name which was passed.
        """
        return util.maybeDeferred(getattr(self, 'configurable_%s'%name),
                                  context).addCallback(iformless.IConfigurable)

    def configurable_(self, context):
        """Configurable factory for use when self is a configurable;
        aka it implements IConfigurable or one or more TypedInterface
        subclasses. Usage:

        >>> class IFoo(TypedInterface):
        ...     def bar(): pass
        ...     bar = autocallable(bar)
        ...
        >>> class Foo(Page):
        ...     implements(IFoo)
        ...
        ...     def bar():
        ...         print "bar called through the web!"
        ...
        ...     def render_forms(self, ctx, data):
        ...         return renderForms() # or renderForms('')
        ...
        ...     docFactory = stan(render_forms).
        """
        if filter(lambda x: issubclass(x, annotate.TypedInterface), providedBy(self)):
            warnings.warn("[0.5] Subclassing TypedInterface to declare annotations is deprecated. Please provide bind_* methods on your Page or Fragment subclass instead.", DeprecationWarning)
            from formless import configurable
            return configurable.TypedInterfaceConfigurable(self)
        return self

    def configurable_original(self, ctx):
        """Configurable factory for use when self.original is a configurable;
        aka it implements IConfigurable or one or more TypedInterface
        subclasses. Usage:


        >>> class Foo(Page):
        ...     def __init__(self):
        ...         self.original = SomeConfigurable()
        ...     def render_forms(self, ctx, data):
        ...         return renderForms('original')
        ...     docFactory = stan(render_forms)
        """
        return self.original

_CARRYOVER = {}


def defaultsFactory(ctx):
    co = _CARRYOVER.get(
        ctx.tag.args.get('_nevow_carryover_', [None])[0], None)
    from formless import webform
    defaults = webform.FormDefaults()
    if co is not None:
        e = iformless.IFormErrors(co, {})
        for k, v in e.items():
            defaults.getAllDefaults(k).update(v.partialForm)
    return defaults


def errorsFactory(ctx):
    co = _CARRYOVER.get(
        ctx.tag.args.get('_nevow_carryover_', [None])[0], None)
    from formless import webform
    errs = webform.FormErrors()
    if co is not None:
        e = iformless.IFormErrors(co, {})
        for k, v in e.items():
            errs.updateErrors(k, v.errors)
            errs.setError(k, v.formErrorMessage)
    return errs


def handFactory(ctx):
    co = _CARRYOVER.get(
        ctx.tag.args.get('_nevow_carryover_', [None])[0], None)
    return inevow.IHand(co, None)


def statusFactory(ctx):
    co = _CARRYOVER.get(
        ctx.tag.args.get('_nevow_carryover_', [None])[0], None)
    return inevow.IStatusMessage(co, None)


def originalFactory(ctx):
    return ctx.tag


class Fragment(DataFactory, RenderFactory, MacroFactory, ConfigurableMixin):
    """
    This class is deprecated because it relies on context objects
    U{which are being removed from Nevow<http://divmod.org/trac/wiki/WitherContext>}.

    @see: L{Element}
    """
    implements(inevow.IRenderer, inevow.IGettable)

    docFactory = None
    original = None

    def __init__(self, original=None, docFactory=None):
        if original is not None:
            self.original = original
        self.toremember = []
        if docFactory is not None:
            self.docFactory = docFactory

    def get(self, context):
        return self.original

    def rend(self, context, data):
        # Create a new context so the current context is not polluted with
        # remembrances.
        context = WovenContext(parent=context)

        # Remember me as lots of things
        self.rememberStuff(context)

        preprocessors = _getPreprocessors(self)

        # This tidbit is to enable us to include Page objects inside
        # stan expressions and render_* methods and the like. But
        # because of the way objects can get intertwined, we shouldn't
        # leave the pattern changed.
        old = self.docFactory.pattern
        self.docFactory.pattern = 'content'
        self.docFactory.precompiledDoc = None
        try:
            try:
                doc = self.docFactory.load(context, preprocessors)
            finally:
                self.docFactory.pattern = old
                self.docFactory.precompiledDoc = None
        except TypeError, e:
            # Avert your eyes now! I don't want to catch anything but IQ
            # adaption exceptions here but all I get is TypeError. This whole
            # section of code is a complete hack anyway so one more won't
            # matter until it's all removed. ;-).
            if 'nevow.inevow.IQ' not in str(e):
                raise
            doc = self.docFactory.load(context, preprocessors)
        except NodeNotFound:
            doc = self.docFactory.load(context, preprocessors)
        else:
            if old == 'content':
                warnings.warn(
                    """[v0.5] Using a Page with a 'content' pattern is
                               deprecated.""",
                    DeprecationWarning,
                    stacklevel=2)

        context.tag = tags.invisible[doc]
        return context

    def remember(self, obj, inter=None):
        """Remember an object for an interface on new PageContexts which are
        constructed around this Page. Whenever this Page is involved in object
        traversal in the future, all objects will be visible to .locate() calls
        at the level of a PageContext wrapped around this Page and all contexts
        below it.

        This does not affect existing Context instances.
        """
        self.toremember.append((obj, inter))

    def rememberStuff(self, ctx):
        ctx.remember(self, inevow.IRenderer)
        ctx.remember(self, inevow.IRendererFactory)
        ctx.remember(self, inevow.IMacroFactory)
        ctx.remember(self, inevow.IData)


class ChildLookupMixin(FreeformChildMixin):
    ##
    # IResource methods
    ##

    children = None
    def locateChild(self, ctx, segments):
        """Locate a child page of this one. ctx is a
        nevow.context.PageContext representing the parent Page, and segments
        is a tuple of each element in the URI. An tuple (page, segments) should be
        returned, where page is an instance of nevow.rend.Page and segments a tuple
        representing the remaining segments of the URI. If the child is not found, return
        NotFound instead.

        locateChild is designed to be easily overridden to perform fancy lookup tricks.
        However, the default locateChild is useful, and looks for children in three places,
        in this order:

         - in a dictionary, self.children
         - a member of self named child_<childname>. This can be either an
           attribute or a method. If an attribute, it should be an object which
           can be adapted to IResource. If a method, it should take the context
           and return an object which can be adapted to IResource.
         - by calling self.childFactory(ctx, name). Name is a single string instead
           of a tuple of strings. This should return an object that can be adapted
           to IResource.
        """

        if self.children is not None:
            r = self.children.get(segments[0], None)
            if r is not None:
                return r, segments[1:]

        w = getattr(self, 'child_%s'%segments[0], None)
        if w is not None:
            if inevow.IResource(w, None) is not None:
                return w, segments[1:]
            r = w(ctx)
            if r is not None:
                return r, segments[1:]

        r = self.childFactory(ctx, segments[0])
        if r is not None:
            return r, segments[1:]

        return FreeformChildMixin.locateChild(self, ctx, segments)

    def childFactory(self, ctx, name):
        """Used by locateChild to return children which are generated
        dynamically. Note that higher level interfaces use only locateChild,
        and only nevow.rend.Page.locateChild uses this.

        segment is a string representing one element of the URI. Request is a
        nevow.appserver.NevowRequest.

        The default implementation of this always returns None; it is intended
        to be overridden."""
        return None

    def putChild(self, name, child):
        if self.children is None:
            self.children = {}
        self.children[name] = child


class Page(Fragment, ConfigurableFactory, ChildLookupMixin):
    """A page is the main Nevow resource and renders a document loaded
    via the document factory (docFactory).
    """

    implements(inevow.IResource)

    buffered = False

    beforeRender = None
    afterRender = None
    addSlash = None

    flattenFactory = lambda self, *args: flat.flattenFactory(*args)

    def renderHTTP(self, ctx):
        if self.beforeRender is not None:
            return util.maybeDeferred(self.beforeRender,ctx).addCallback(
                    lambda result,ctx: self._renderHTTP(ctx),ctx)
        return self._renderHTTP(ctx)

    def _renderHTTP(self, ctx):
        request = inevow.IRequest(ctx)
        ## XXX request is really ctx now, change the name here
        if self.addSlash and inevow.ICurrentSegments(ctx)[-1] != '':
            request.redirect(request.URLPath().child(''))
            return ''

        log.msg(http_render=None, uri=request.uri)

        self.rememberStuff(ctx)

        def finishRequest():
            carryover = request.args.get('_nevow_carryover_', [None])[0]
            if carryover is not None and _CARRYOVER.has_key(carryover):
                del _CARRYOVER[carryover]
            if self.afterRender is not None:
                return util.maybeDeferred(self.afterRender,ctx)

        if self.buffered:
            io = StringIO()
            writer = io.write
            def finisher(result):
                request.write(io.getvalue())
                return util.maybeDeferred(finishRequest).addCallback(lambda r: result)
        else:
            writer = request.write
            def finisher(result):
                return util.maybeDeferred(finishRequest).addCallback(lambda r: result)

        preprocessors = _getPreprocessors(self)
        doc = self.docFactory.load(ctx, preprocessors)
        ctx =  WovenContext(ctx, tags.invisible[doc])

        return self.flattenFactory(doc, ctx, writer, finisher)

    def rememberStuff(self, ctx):
        Fragment.rememberStuff(self, ctx)
        ctx.remember(self, inevow.IResource)

    def renderString(self, ctx=None):
        """Render this page outside of the context of a web request, returning
        a Deferred which will result in a string.

        If twisted is not installed, this method will return a string result immediately,
        and this method is equivalent to renderSynchronously.
        """
        io = StringIO()
        writer = io.write

        def finisher(result):
            return io.getvalue()

        ctx = PageContext(parent=ctx, tag=self)
        self.rememberStuff(ctx)
        doc = self.docFactory.load(ctx)
        ctx =  WovenContext(ctx, tags.invisible[doc])

        return self.flattenFactory(doc, ctx, writer, finisher)

    def renderSynchronously(self, ctx=None):
        """Render this page synchronously, returning a string result immediately.
        Raise an exception if a Deferred is required to complete the rendering
        process.
        """
        io = StringIO()

        ctx = PageContext(parent=ctx, tag=self)
        self.rememberStuff(ctx)
        doc = self.docFactory.load(ctx)
        ctx =  WovenContext(ctx, tags.invisible[doc])

        def raiseAlways(item):
            raise NotImplementedError("renderSynchronously can not support"
                " rendering: %s" % (item, ))

        list(flat.iterflatten(doc, ctx, io.write, raiseAlways))

        return io.getvalue()

    def child_(self, ctx):
        """When addSlash is True, a page rendered at a url with no
        trailing slash and a page rendered at a url with a trailing
        slash will be identical. addSlash is useful for the root
        resource of a site or directory-like resources.
        """
        # Only allow an empty child, by default, if it's on the end
        # and we're a directoryish resource (addSlash = True)
        if self.addSlash and len(inevow.IRemainingSegments(ctx)) == 1:
            return self
        return None

    def webFormPost(self, request, res, configurable, ctx, bindingName, args):
        """Accept a web form post, either redisplaying the original form (with
        errors) if validation fails, or redirecting to the appropriate location after
        the post succeeds. This hook exists specifically for formless.

        New in 0.5, _nevow_carryover_ is only used if an autocallable method
        returns a result that needs to be carried over.

        New in 0.5, autocallables may return a nevow.url.URL or URLOverlay
        instance rather than setting IRedirectAfterPost on the request.

        New in 0.5, autocallables may return a Page instance to have that Page
        instance rendered at the post target URL with no redirects at all. Useful
        for multi-step wizards.
        """
        def redirectAfterPost(aspects):
            hand = aspects.get(inevow.IHand)
            refpath = None
            if hand is not None:
                if isinstance(hand, Page):
                    refpath = url.here
                    if 'freeform_hand' not in inevow.IRequest(ctx).prepath:
                        refpath = refpath.child('freeform_hand')
                if isinstance(hand, (url.URL, url.URLOverlay)):
                    refpath, hand = hand, None

            if refpath is None:
                redirectAfterPost = request.getComponent(iformless.IRedirectAfterPost, None)
                if redirectAfterPost is None:
                    ref = request.getHeader('referer')
                    if ref:
                        refpath = url.URL.fromString(ref)
                    else:
                        refpath = url.here
                else:
                    warnings.warn("[0.5] IRedirectAfterPost is deprecated. Return a URL instance from your autocallable instead.", DeprecationWarning, 2)
                    ## Use the redirectAfterPost url
                    ref = str(redirectAfterPost)
                    refpath = url.URL.fromString(ref)

            if hand is not None or aspects.get(iformless.IFormErrors) is not None:
                magicCookie = '%s%s%s' % (now(),request.getClientIP(),random.random())
                refpath = refpath.replace('_nevow_carryover_', magicCookie)
                _CARRYOVER[magicCookie] = C = tpc.Componentized()
                for k, v in aspects.iteritems():
                    C.setComponent(k, v)

            destination = flat.flatten(refpath, ctx)
            request.redirect(destination)
            from nevow import static
            return static.Data('You posted a form to %s' % bindingName, 'text/plain'), ()

        return util.maybeDeferred(
            configurable.postForm, ctx, bindingName, args
        ).addCallback(
            self.onPostSuccess, request, ctx, bindingName, redirectAfterPost
        ).addErrback(
            self.onPostFailure, request, ctx, bindingName, redirectAfterPost
        )

    def onPostSuccess(self, result, request, ctx, bindingName, redirectAfterPost):
        if result is None:
            message = "%s success." % formless.nameToLabel(bindingName)
        else:
            message = result

        return redirectAfterPost({inevow.IHand: result, inevow.IStatusMessage: message})

    def onPostFailure(self, reason, request, ctx, bindingName, redirectAfterPost):
        reason.trap(formless.ValidateError)
        return redirectAfterPost({iformless.IFormErrors: {bindingName: reason.value}})


def sequence(context, data):
    """Renders each item in the sequence using patterns found in the
    children of the element.

    Sequence recognises the following patterns:

     - header: Rendered at the start, before the first item. If multiple
       header patterns are provided they are rendered together in the
       order they were defined.

     - footer: Just like the header only renderer at the end, after the
       last item.

     - item: Rendered once for each item in the sequence. If multiple
       item patterns are provided then the pattern is cycled in the
       order defined.

     - divider: Rendered once between each item in the sequence. Multiple
       divider patterns are cycled.

     - empty: Rendered instead of item and divider patterns when the
       sequence contains no items.

    Example::

     <table nevow:render="sequence" nevow:data="peopleSeq">
       <tr nevow:pattern="header">
         <th>name</th>
         <th>email</th>
       </tr>
       <tr nevow:pattern="item" class="odd">
         <td>name goes here</td>
         <td>email goes here</td>
       </tr>
       <tr nevow:pattern="item" class="even">
         <td>name goes here</td>
         <td>email goes here</td>
       </tr>
       <tr nevow:pattern="empty">
         <td colspan="2"><em>they've all gone!</em></td>
       </tr>
     </table>

    """
    tag = context.tag
    headers = tag.allPatterns('header')
    pattern = tag.patternGenerator('item')
    divider = tag.patternGenerator('divider', default=tags.invisible)
    content = [(pattern(data=element), divider(data=element)) for element in data]
    if not content:
        content = tag.allPatterns('empty')
    else:
        ## No divider after the last thing.
        content[-1] = content[-1][0]
    footers = tag.allPatterns('footer')

    return tag.clear()[ headers, content, footers ]


def mapping(context, data):
    """Fills any slots in the element's children with data from a
    dictionary. The dict keys are used as the slot names, the dict
    values are used as filling.

    Example::

     <tr nevow:render="mapping" nevow:data="personDict">
       <td><nevow:slot name="name"/></td>
       <td><nevow:slot name="email"/></td>
     </tr>
    """
    for k, v in data.items():
        context.fillSlots(k, v)
    return context.tag


def string(context, data):
    return context.tag.clear()[str(data)]


def data(context, data):
    """Replace the tag's content with the current data.
    """
    return context.tag.clear()[data]


class FourOhFour:
    """A simple 404 (not found) page.
    """
    implements(inevow.IResource)

    notFound = "<html><head><title>Page Not Found</title></head><body>Sorry, but I couldn't find the object you requested.</body></html>"
    original = None

    def locateChild(self, ctx, segments):
        return NotFound

    def renderHTTP(self, ctx):
        inevow.IRequest(ctx).setResponseCode(404)
        # Look for an application-remembered handler
        try:
            notFoundHandler = ctx.locate(inevow.ICanHandleNotFound)
        except KeyError, e:
            return self.notFound
        # Call the application-remembered handler but if there are any errors
        # then log it and fallback to the standard message.
        try:
            return notFoundHandler.renderHTTP_notFound(PageContext(parent=ctx, tag=notFoundHandler))
        except:
            log.err()
            return self.notFound

    def __nonzero__(self):
        return False


# Not found singleton
NotFound = None, ()
