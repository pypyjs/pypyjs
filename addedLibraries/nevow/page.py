# -*- test-case-name: nevow.test.test_element -*-

"""
Basic rendering classes for Nevow applications.

API Stability: Completely unstable.
"""

from zope.interface import implements

from nevow.inevow import IRequest, IRenderable, IRendererFactory
from nevow.errors import MissingRenderMethod, MissingDocumentFactory

from nevow.util import Expose
from nevow.rend import _getPreprocessors

from nevow.flat.ten import registerFlattener
from nevow._flat import FlattenerError, _OldRendererFactory, _ctxForRequest
from nevow._flat import deferflatten


renderer = Expose(
    """
    Allow one or more methods to be used to satisfy template render
    directives::

    | class Foo(Element):
    |     def twiddle(self, request, tag):
    |         return tag['Hello, world.']
    |     renderer(twiddle)

    | <div xmlns:nevow="http://nevow.com/ns/nevow/0.1">
    |     <span nevow:render="twiddle" />
    | </div>

    Will result in this final output:

    | <div>
    |     <span>Hello, world.</span>
    | </div>
    """)



class Element(object):
    """
    Base for classes which can render part of a page.

    An Element is a renderer that can be embedded in a stan document and can
    hook its template (from the docFactory) up to render methods.

    An Element might be used to encapsulate the rendering of a complex piece of
    data which is to be displayed in multiple different contexts.  The Element
    allows the rendering logic to be easily re-used in different ways.

    Element implements L{IRenderable.renderer} to return render methods which
    are registered using L{nevow.page.renderer}.  For example::

        class Menu(Element):
            def items(self, request, tag):
                ....
            renderer(items)

    Render methods are invoked with two arguments: first, the
    L{nevow.inevow.IRequest} being served and second, the tag object which
    "invoked" the render method.

    Element implements L{IRenderable.render} to load C{docFactory} and return
    the result.

    @type docFactory: L{IDocFactory} provider
    @ivar docFactory: The factory which will be used to load documents to
        return from C{render}.
    """
    implements(IRenderable)

    docFactory = None
    preprocessors = ()

    def __init__(self, docFactory=None):
        if docFactory is not None:
            self.docFactory = docFactory


    def renderer(self, name):
        """
        Get the named render method using C{nevow.page.renderer}.
        """
        method = renderer.get(self, name, None)
        if method is None:
            raise MissingRenderMethod(self, name)
        return method


    def render(self, request):
        """
        Load and return C{self.docFactory}.
        """
        rend = self.rend
        if rend.im_func is not Element.__dict__['rend']:
            context = _ctxForRequest(request, [], self, False)
            return rend(context, None)

        docFactory = self.docFactory
        if docFactory is None:
            raise MissingDocumentFactory(self)
        return docFactory.load(None, _getPreprocessors(self))


    def rend(self, context, data):
        """
        Backwards compatibility stub.  This is only here so that derived
        classes can upcall to it.  It is not otherwise used in the rendering
        process.
        """
        context.remember(_OldRendererFactory(self), IRendererFactory)
        docFactory = self.docFactory
        if docFactory is None:
            raise MissingDocumentFactory(self)
        return docFactory.load(None, _getPreprocessors(self))



def _flattenElement(element, ctx):
    """
    Use the new flattener implementation to flatten the given L{IRenderable} in
    a manner appropriate for the specified context.
    """
    if ctx.precompile:
        return element

    synchronous = []
    accumulator = []
    request = IRequest(ctx, None) # XXX None case is DEPRECATED
    finished = deferflatten(request, element, ctx.isAttrib, True, accumulator.append)
    def cbFinished(ignored):
        if synchronous is not None:
            synchronous.append(None)
        return accumulator
    def ebFinished(err):
        if synchronous is not None:
            synchronous.append(err)
        else:
            return err
    finished.addCallbacks(cbFinished, ebFinished)
    if synchronous:
        if synchronous[0] is None:
            return accumulator
        synchronous[0].raiseException()
    synchronous = None
    return finished

registerFlattener(_flattenElement, Element)


__all__ = [
    'FlattenerError',

    'Element',

    'renderer', 'deferflatten',
    ]
