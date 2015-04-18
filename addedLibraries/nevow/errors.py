# -*- test-case-name: nevow.test -*-


"""
Exception classes raised by Nevow.
"""

class RenderError(Exception):
    """
    Base exception class for all errors which can occur during rendering.
    """


class MissingRenderMethod(RenderError):
    """
    Tried to use a render method which does not exist.

    @ivar element: The element which did not have the render method.
    @ivar renderName: The name of the renderer which could not be found.
    """
    def __init__(self, element, renderName):
        RenderError.__init__(self, element, renderName)
        self.element = element
        self.renderName = renderName


    def __repr__(self):
        return '%r: %r had no renderer named %r' % (self.__class__.__name__,
                                                    self.element,
                                                    self.renderName)



class MissingDocumentFactory(RenderError):
    """
    Tried to render an Element without a docFactory.

    @ivar element: The Element which did not have a document factory.
    """
    def __init__(self, element):
        RenderError.__init__(self, element)
        self.element = element


    def __repr__(self):
        return '%r: %r had no docFactory' % (self.__class__.__name__,
                                             self.element)

