# -*- test-case-name: nevow.test.test_newflat -*-
# Copyright (c) 2008 Divmod.
# See LICENSE for details.

"""
Context-free flattener/serializer for rendering Python objects, possibly
complex or arbitrarily nested, as strings.

Immediate future plans:

  - Deprecate IRenderer and getFlattener cases in _flatten
  - Write a precompiler which is more friendly towards _flatten
  - Write a pretty "render stack" formatter for the information in
    FlattenerError._roots

"""

from sys import exc_info
from types import GeneratorType
from traceback import extract_tb, format_list

from twisted.internet.defer import Deferred

from nevow.inevow import IRenderable, IRenderer, IRendererFactory, IData
from nevow.inevow import IRequest
from nevow.url import URL
from nevow.stan import _PrecompiledSlot, Unset, Proto, Tag, Entity, slot, xml
from nevow.stan import directive
from nevow.context import WovenContext
from nevow.flat.flatstan import allowSingleton
from nevow.flat import flattenFactory
from nevow.flat.ten import getFlattener
from nevow.tags import raw


class FlattenerError(Exception):
    """
    An error occurred while flattening an object.

    @ivar _roots: A list of the objects on the flattener's stack at the time
        the unflattenable object was encountered.  The first element is least
        deeply nested object and the last element is the most deeply nested.
    """
    def __init__(self, exception, roots, traceback):
        self._exception = exception
        self._roots = roots
        self._traceback = traceback
        Exception.__init__(self, exception, roots, traceback)


    def _formatRoot(self, obj):
        """
        Convert an object from C{self._roots} to a string suitable for
        inclusion in a render-traceback (like a normal Python traceback, but
        can include "frame" source locations which are not in Python source
        files).

        @param obj: Any object which can be a render step I{root}.
            Typically, L{Tag}s, strings, and other simple Python types.

        @return: A string representation of C{obj}.
        @rtype: L{str}
        """
        if isinstance(obj, (str, unicode)):
            # It's somewhat unlikely that there will ever be a str in the roots
            # list.  However, something like a MemoryError during a str.replace
            # call (eg, replacing " with &quot;) could possibly cause this.
            # Likewise, UTF-8 encoding a unicode string to a byte string might
            # fail like this.
            if len(obj) > 40:
                if isinstance(obj, str):
                    prefix = 1
                else:
                    prefix = 2
                return repr(obj[:20])[:-1] + '<...>' + repr(obj[-20:])[prefix:]
            else:
                return repr(obj)
        elif isinstance(obj, Tag):
            if obj.filename is None:
                return 'Tag <' + obj.tagName + '>'
            else:
                return "File \"%s\", line %d, column %d, in \"%s\"" % (
                    obj.filename, obj.lineNumber,
                    obj.columnNumber, obj.tagName)
        else:
            return repr(obj)


    def __repr__(self):
        if self._roots:
            roots = '  ' + '\n  '.join([
                    self._formatRoot(r) for r in self._roots]) + '\n'
        else:
            roots = ''
        if self._traceback:
            traceback = '\n'.join([
                    line
                    for entry in format_list(self._traceback)
                    for line in entry.splitlines()]) + '\n'
        else:
            traceback = ''
        return (
            'Exception while flattening:\n' +
            roots + traceback +
            self._exception.__class__.__name__ + ': ' +
            str(self._exception) + '\n')


    def __str__(self):
        return repr(self)



class UnfilledSlot(Exception):
    """
    During flattening, a slot with no associated data was encountered.
    """
    def __str__(self):
        return 'UnfilledSlot(%r)' % self.args



class UnsupportedType(Exception):
    """
    During flattening, an object of a type which cannot be flattened was
    encountered.
    """
    def __str__(self):
        return "UnsupportedType(%r)" % self.args



def escapedData(data, inAttribute, inXML):
    """
    Escape a string for inclusion in a document.

    @type data: C{str}
    @param data: The string to escape.

    @type inAttribute: C{bool}
    @param inAttribute: A flag which, if set, indicates that the string should
        be quoted for use as the value of an XML tag value.

    @type inXML: C{bool}
    @param inXML: A flag which, if set, indicates that the string should be
        quoted for use as an XML text node or as the value of an XML tag value.

    @rtype: C{str}
    @return: The quoted form of C{data}.
    """
    if inXML or inAttribute:
        data = data.replace('&', '&amp;'
            ).replace('<', '&lt;'
            ).replace('>', '&gt;')
    if inAttribute:
        data = data.replace('"', '&quot;')
    return data



def _ctxForRequest(request, slotData, renderFactory, inAttribute):
    """
    Create a L{WovenContext} which can be used to by the
    backwards-compatibility support of L{IRenderer} and L{getFlattener} to
    continue rendering a response for the given request.
    """
    ctx = WovenContext()
    ctx.isAttrib = inAttribute
    ctx.remember(None, IData) # Even though IData(ctx) can never return None,
                              # remembering None here is somehow very important
                              # for preventing a TypeError from happening when
                              # ctx.locate(IData) is invoked, since it is
                              # sometimes invoked from a codepath other than
                              # __conform__. -exarkun
    ctx.remember(request, IRequest)
    for slotGroup in slotData:
        if slotGroup is not None:
            for k, v in slotGroup.items():
                ctx.fillSlots(k, v)
    if renderFactory is not None:
        ctx.remember(_OldRendererFactory(renderFactory), IRendererFactory)
    return ctx



def _getSlotValue(name, slotData):
    """
    Find the value of the named slot in the given stack of slot data.
    """
    for slotFrame in slotData[::-1]:
        if slotFrame is not None and name in slotFrame:
            return slotFrame[name]
    else:
        raise UnfilledSlot(name)



def _flatten(request, root, slotData, renderFactory, inAttribute, inXML):
    """
    Make C{root} slightly more flat by yielding all or part of it as strings or
    generators.

    @param request: A request object which will be passed to
        L{IRenderable.render}.

    @param root: An object to be made flatter.  This may be of type C{unicode},
        C{str}, L{raw}, L{Proto}, L{xml}, L{slot}, L{_PrecompiledSlot}, L{Tag},
        L{URL}, L{tuple}, L{list}, L{GeneratorType}, L{Entity}, L{Deferred}, or
        it may be an object which is adaptable to L{IRenderable}.  Deprecated
        backwards-compatibility support is also present for objects adaptable
        to L{IRenderer} or for which a flattener has been registered via
        L{registerFlattener}.

    @param slotData: A C{list} of C{dict} mapping C{str} slot names to data
        with which those slots will be replaced.

    @param inAttribute: A flag which, if set, indicates that C{str} and
        C{unicode} instances encountered must be quoted as for XML tag
        attribute values.

    @param inXML: A flag which, if set, indicates that C{str} and C{unicode}
        instances encountered must be quoted as for XML text node data.

    @return: An iterator which yields C{str}, L{Deferred}, and more iterators
        of the same type.
    """
    if isinstance(root, unicode):
        root = root.encode('utf-8')
    elif isinstance(root, WovenContext):
        # WovenContext is supported via the getFlattener case, but that is a
        # very slow case.  Checking here is an optimization.  It also lets us
        # avoid the deprecation warning which would be emitted whenever a
        # precompiled document was flattened, since those contain WovenContexts
        # for tags with render directives. -exarkun
        inAttribute = root.isAttrib
        inXML = True
        root = root.tag

    if isinstance(root, raw):
        root = str(root)
        if inAttribute:
            root = root.replace('"', '&quot;')
        yield root
    elif isinstance(root, Proto):
        root = str(root)
        if root:
            if root in allowSingleton:
                yield '<' + root + ' />'
            else:
                yield '<' + root + '></' + root + '>'
    elif isinstance(root, str):
        yield escapedData(root, inAttribute, inXML)
    elif isinstance(root, slot):
        slotValue = _getSlotValue(root.name, slotData)
        yield _flatten(request, slotValue, slotData, renderFactory,
                       inAttribute, inXML)
    elif isinstance(root, _PrecompiledSlot):
        slotValue = _getSlotValue(root.name, slotData)
        yield _flatten(request, slotValue, slotData, renderFactory,
                       root.isAttrib, inXML)
    elif isinstance(root, Tag):
        if root.pattern is Unset or root.pattern is None:
            slotData.append(root.slotData)
            if root.render is Unset:
                if not root.tagName:
                    for element in _flatten(request, root.children,
                                            slotData, renderFactory,
                                            False, True):
                        yield element
                else:
                    yield '<'
                    if isinstance(root.tagName, unicode):
                        tagName = root.tagName.encode('ascii')
                    else:
                        tagName = str(root.tagName)
                    yield tagName
                    for k, v in root.attributes.iteritems():
                        if isinstance(k, unicode):
                            k = k.encode('ascii')
                        yield " " + k + "=\""
                        for element in _flatten(request, v, slotData,
                                                renderFactory, True, True):
                            yield element
                        yield "\""
                    if root.children or tagName not in allowSingleton:
                        yield '>'
                        for element in _flatten(request, root.children,
                                                slotData, renderFactory,
                                                False, True):
                            yield element
                        yield '</' + tagName + '>'
                    else:
                        yield ' />'
            else:
                if isinstance(root.render, directive):
                    rendererName = root.render.name
                else:
                    rendererName = root.render
                root = root.clone(False)
                del root._specials['render']
                result = renderFactory.renderer(rendererName)(request, root)
                yield _flatten(request, result, slotData, renderFactory, None,
                               inXML)
            slotData.pop()
    elif isinstance(root, URL):
        yield escapedData(str(root), inAttribute, inXML)
    elif isinstance(root, (tuple, list, GeneratorType)):
        for element in root:
            yield _flatten(request, element, slotData, renderFactory,
                           inAttribute, inXML)
    elif isinstance(root, Entity):
        yield '&#'
        yield root.num
        yield ';'
    elif isinstance(root, xml):
        if isinstance(root.content, unicode):
            yield root.content.encode('utf-8')
        else:
            yield root.content
    elif isinstance(root, Deferred):
        yield root.addCallback(
            lambda result: (result, _flatten(request, result, slotData,
                                             renderFactory, inAttribute,
                                             inXML)))
    else:
        renderable = IRenderable(root, None)
        if renderable is not None:
            # [] for the slotData parameter of this call to _flatten means
            # slots returned by this renderable's render method won't be filled
            # with data which has so far accumulated in the slotData stack.
            # This seems like a reasonable thing to me, since a renderable is a
            # piece of Python code.  It should be isolated from this other
            # stuff, which is primarily data. -exarkun
            yield _flatten(request, renderable.render(request), [], renderable,
                           inAttribute, inXML)
        else:
            renderer = IRenderer(root, None)
            if renderer is not None:
                ctx = _ctxForRequest(request, slotData, None, inAttribute)
                results = []
                synchronous = []
                flattened = flattenFactory(renderer, ctx, results.append,
                                           lambda ign: None)
                def cbFlattened(result):
                    synchronous.append(None)
                    return (result, (str(s) for s in results))
                flattened.addCallback(cbFlattened)
                if synchronous:
                    yield ''.join(map(str, results))
                else:
                    yield flattened
            else:
                flattener = getFlattener(root)
                if flattener is not None:
                    ctx = _ctxForRequest(request, slotData, renderFactory,
                                         inAttribute)
                    yield _flatten(request, flattener(root, ctx), slotData,
                                   renderFactory, False, False)
                else:
                    raise UnsupportedType(root)



class _OldRendererFactory(object):
    """
    Adapter from L{IRenderable} to L{IRenderFactory}, used to provide support
    for using the old flattener on new kinds of view objects.
    """
    def __init__(self, newRendererFactory):
        self.newRendererFactory = newRendererFactory


    def renderer(self, context, name):
        f = self.newRendererFactory.renderer(name)
        def render(ctx, data):
            return f(
                IRequest(ctx, None),
                ctx.tag,
                )
        return render



def flatten(request, root, inAttribute, inXML):
    """
    Make C{root} into an iterable of C{str} and L{Deferred}.

    @param request: A request object which will be passed to
        L{IRenderable.render}.

    @param root: An object to be made flatter.  This may be of type C{unicode},
        C{str}, L{Proto}, L{slot}, L{Tag}, L{URL}, L{tuple}, L{list},
        L{Entity}, L{Deferred}, or it may be an object which is adaptable to
        L{IRenderable}.

    @type inAttribute: C{bool}
    @param inAttribute: A flag which, if set, indicates that the string should
        be quoted for use as the value of an XML tag value.

    @type inXML: C{bool}
    @param inXML: A flag which, if set, indicates that the string should be
        quoted for use as an XML text node or as the value of an XML tag value.

    @return: An iterator which yields objects of type C{str} and L{Deferred}.
        A L{Deferred} is only yielded when one is encountered in the process of
        flattening C{root}.  The returned iterator must not be iterated again
        until the L{Deferred} is called back.
    """
    stack = [_flatten(request, root, [], None, inAttribute, inXML)]
    while stack:
        try:
            # In Python 2.5, after an exception, a generator's gi_frame is
            # None.
            frame = stack[-1].gi_frame
            element = stack[-1].next()
        except StopIteration:
            stack.pop()
        except Exception, e:
            stack.pop()
            roots = []
            for generator in stack:
                roots.append(generator.gi_frame.f_locals['root'])
            roots.append(frame.f_locals['root'])
            raise FlattenerError(e, roots, extract_tb(exc_info()[2]))
        else:
            if type(element) is str:
                yield element
            elif isinstance(element, Deferred):
                def cbx((original, toFlatten)):
                    stack.append(toFlatten)
                    return original
                yield element.addCallback(cbx)
            else:
                stack.append(element)



def _flattensome(state, write, schedule, result):
    """
    Take strings from an iterator and pass them to a writer function.

    @param state: An iterator of C{str} and L{Deferred}.  C{str} instances will
        be passed to C{write}.  L{Deferred} instances will be waited on before
        resuming iteration of C{state}.

    @param write: A callable which will be invoked with each C{str}
        produced by iterating C{state}.

    @param schedule: A callable which will arrange for a function to be called
        with some positional arguments I{later}.  This is used to avoid
        unbounded call stack depth due to already-fired L{Deferred}s produced
        by C{state}.

    @param result: A L{Deferred} which will be called back when C{state} has
        been completely flattened into C{write} or which will be errbacked if
        an unexpected exception occurs.

    @return: C{None}
    """
    while True:
        try:
            element = state.next()
        except StopIteration:
            result.callback(None)
        except:
            result.errback()
        else:
            if type(element) is str:
                write(element)
                continue
            else:
                def cby(original):
                    schedule(_flattensome, state, write, schedule, result)
                    return original
                element.addCallbacks(cby, result.errback)
        break



def _schedule(f, *a):
    """
    Scheduler for use with L{_flattensome} which uses L{IReactorTime.callLater}
    to schedule calls.  This works around the fact that L{Deferred} can exceed
    the stack limit in certain cases.
    """
    # XXX SUCKY
    from twisted.internet import reactor
    reactor.callLater(0, f, *a)



def deferflatten(request, root, inAttribute, inXML, write):
    """
    Incrementally write out a string representation of C{root} using C{write}.

    In order to create a string representation, C{root} will be decomposed into
    simpler objects which will themselves be decomposed and so on until strings
    or objects which can easily be converted to strings are encountered.

    @param request: A request object which will be passed to the C{render}
        method of any L{IRenderable} provider which is encountered.

    @param root: An object to be made flatter.  This may be of type C{unicode},
        C{str}, L{raw}, L{Proto}, L{xml}, L{slot}, L{_PrecompiledSlot}, L{Tag},
        L{URL}, L{tuple}, L{list}, L{GeneratorType}, L{Entity}, L{Deferred}, or
        it may be an object which is adaptable to L{IRenderable}.  Deprecated
        backwards-compatibility support is also present for objects adaptable
        to L{IRenderer} or for which a flattener has been registered via
        L{registerFlattener}.

    @type inAttribute: C{bool}
    @param inAttribute: A flag which, if set, indicates that the string should
        be quoted for use as the value of an XML tag value.

    @type inXML: C{bool}
    @param inXML: A flag which, if set, indicates that the string should be
        quoted for use as an XML text node or as the value of an XML tag value.

    @param write: A callable which will be invoked with each C{str}
        produced by flattening C{root}.

    @return: A L{Deferred} which will be called back when C{root} has
        been completely flattened into C{write} or which will be errbacked if
        an unexpected exception occurs.
    """
    result = Deferred()
    state = flatten(request, root, inAttribute, inXML)
    _flattensome(state, write, _schedule, result)
    return result
