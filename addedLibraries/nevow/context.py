# -*- test-case-name: nevow.test.test_context -*-
# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from __future__ import generators

import warnings

from nevow import stan
from nevow.inevow import IData, IRequest
from nevow.stan import Unset
from nevow.util import qual

from zope.interface import providedBy
# TTT: Move to web2.context

def megaGetInterfaces(adapter):
    return [qual(x) for x in providedBy(adapter)]

dataqual = qual(IData)

class WebContext(object):
    _remembrances = None
    tag = None
    _slotData = None
    parent = None
    locateHook = None

    # XXX: can we get rid of these somehow?
    isAttrib = property(lambda self: False)
    inURL = property(lambda self: False)
    inJS = property(lambda self: False)
    inJSSingleQuoteString = property(lambda self: False)

    precompile = property(lambda self: False)

    def arg(self, get, default=None):
        """Placeholder until I can find Jerub's implementation of this

        Return a single named argument from the request arguments
        """
        req = self.locate(IRequest)
        return req.args.get(get, [default])[0]

    def __init__(self, parent=None, tag=None, remembrances=None):
        self.tag = tag
        sd = getattr(tag, 'slotData', None)
        if sd is not None:
            self._slotData = sd
        self.parent = parent
        self._remembrances = remembrances

    def remember(self, adapter, interface=None):
        """Remember an object that implements some interfaces.
        Later, calls to .locate which are passed an interface implemented
        by this object will return this object.

        If the 'interface' argument is supplied, this object will only
        be remembered for this interface, and not any of
        the other interfaces it implements.
        """
        if interface is None:
            interfaceList = megaGetInterfaces(adapter)
            if not interfaceList:
                interfaceList = [dataqual]
        else:
            interfaceList = [qual(interface)]
        if self._remembrances is None:
            self._remembrances = {}
        for interface in interfaceList:
            self._remembrances[interface] = adapter
        return self

    def locate(self, interface, depth=1, _default=object()):
        """Locate an object which implements a given interface.
        Objects will be searched through the context stack top
        down.
        """
        key = qual(interface)
        currentContext = self
        while True:
            if depth < 0:
                full = []
                while True:
                    try:
                        full.append(self.locate(interface, len(full)+1))
                    except KeyError:
                        break
                #print "full", full, depth
                if full:
                    return full[depth]
                return None

            _remembrances = currentContext._remembrances
            if _remembrances is not None:
                rememberedValue = _remembrances.get(key, _default)
                if rememberedValue is not _default:
                    depth -= 1
                    if not depth:
                        return rememberedValue

            # Hook for FactoryContext and other implementations of complex locating
            locateHook = currentContext.locateHook
            if locateHook is not None:
                result = locateHook(interface)
                if result is not None:
                    currentContext.remember(result, interface)
                    return result

            contextParent = currentContext.parent
            if contextParent is None:
                raise KeyError, "Interface %s was not remembered." % key

            currentContext = contextParent

    def chain(self, context):
        """For nevow machinery use only.

        Go to the top of this context's context chain, and make
        the given context the parent, thus continuing the chain
        into the given context's chain.
        """
        top = self
        while top.parent is not None:
            if top.parent.tag is None:
                ## If top.parent.tag is None, that means this context (top)
                ## is just a marker. We want to insert the current context
                ## (context) as the parent of this context (top) to chain properly.
                break
            top = top.parent
            if top is context: # this context is already in the chain; don't create a cycle
                return
        top.parent = context

    def fillSlots(self, name, stan):
        """Set 'stan' as the stan tree to replace all slots with name 'name'.
        """
        if self._slotData is None:
            self._slotData = {}
        self._slotData[name] = stan

    def locateSlotData(self, name):
        """For use by nevow machinery only, or for some fancy cases.

        Find previously remembered slot filler data.
        For use by flatstan.SlotRenderer"""
        currentContext = self
        while True:
            if currentContext._slotData:
                data = currentContext._slotData.get(name, Unset)
                if data is not Unset:
                    return data
            if currentContext.parent is None:
                raise KeyError, "Slot named '%s' was not filled." % name
            currentContext = currentContext.parent

    def clone(self, deep=True, cloneTags=True):
        ## don't clone the tags of parent contexts. I *hope* code won't be
        ## trying to modify parent tags so this should not be necessary.  We
        ## used to also clone parent contexts, but that is insanely expensive.
        ## The only code that actually required that behavior is
        ## ContextSerializer, which is the only caller of context.chain.  So
        ## instead of doing the clone here, now we do it there.

        if self.parent is not None:
            if deep:
                parent = self.parent.clone(cloneTags=False)
            else:
                parent = self.parent
        else:
            parent = None

        if cloneTags:
            tag = self.tag.clone(deep=deep)
        else:
            tag = self.tag

        if self._remembrances is not None:
            remembrances = self._remembrances.copy()
        else:
            remembrances = None

        return type(self)(
            parent=parent,
            tag=tag,
            remembrances=remembrances,
        )

    def __conform__(self, interface):
        """Support IFoo(ctx) syntax.
        """
        try:
            return self.locate(interface)
        except KeyError:
            return None

    def __repr__(self):
        rstr = ''
        if self._remembrances:
            rstr = ', remembrances=%r' % self._remembrances
        return "%s(tag=%r%s)" % (self.__class__.__name__, self.tag, rstr)


class FactoryContext(WebContext):
    """A context which allows adapters to be registered against it so that an object
    can be lazily created and returned at render time. When ctx.locate is called
    with an interface for which an adapter is registered, that adapter will be used
    and the result returned.
    """
    inLocate = 0
    
    def locateHook(self, interface):

        ## Prevent infinite recursion from interface(self) calling self.getComponent calling self.locate
        self.inLocate += 1
        adapter = interface(self, None)
        self.inLocate -= 1
        
        return adapter

    def __conform__(self, interface):
        if self.inLocate:
            return None
        return WebContext.__conform__(self, interface)

class SiteContext(FactoryContext):
    """A SiteContext is created and installed on a NevowSite upon initialization.
    It will always be used as the root context, and can be used as a place to remember
    things sitewide.
    """
    pass


class RequestContext(FactoryContext):
    """A RequestContext has adapters for the following interfaces:

    ISession
    IFormDefaults
    IFormErrors
    IHand
    IStatusMessage
    """
    pass

def getRequestContext(self):
    top = self.parent
    while not isinstance(top, RequestContext):
        top = top.parent
    return top

class PageContext(FactoryContext):
    """A PageContext has adapters for the following interfaces:

    IRenderer
    IRendererFactory
    IData
    """

    def __init__(self, *args, **kw):
        FactoryContext.__init__(self, *args, **kw)
        if self.tag is not None and hasattr(self.tag, 'toremember'):
            for i in self.tag.toremember:
                self.remember(*i)

# TTT: To stay here.
NodeNotFound = stan.NodeNotFound # XXX: DeprecationWarning?
TooManyNodes = stan.TooManyNodes # XXX: DeprecationWarning?

class WovenContext(WebContext):
    key = None
    isAttrib = False
    inURL = False
    precompile = False
    inJS = False
    inJSSingleQuoteString = False

    def __init__(self, parent=None, tag=None, precompile=None, remembrances=None, key=None, isAttrib=None, inURL=None, inJS=None, inJSSingleQuoteString=None):
        WebContext.__init__(self, parent, tag, remembrances)
        if self.parent:
            self.precompile = parent.precompile
            self.isAttrib = parent.isAttrib
            self.inURL = parent.inURL
            self.inJS = parent.inJS
            self.inJSSingleQuoteString = parent.inJSSingleQuoteString

        if self.tag is not None:
            if self.tag.remember is not Unset:
                self.remember(tag.remember)
            if key is None:
                key = self.tag.key

        if key is not None and key is not Unset:
            if self.parent is not None and getattr(self.parent, 'key', None):
                self.key = '.'.join((self.parent.key, key))
            else:
                self.key = key
            #print "KEY", `self.key`
        else:
            ## Bubble the value down to the bottom so it's always immediately accessible
            if self.parent is not None:
                self.key = getattr(self.parent, 'key', '')

        if precompile is not None: self.precompile = precompile
        if isAttrib is not None: self.isAttrib = isAttrib
        if inURL is not None: self.inURL = inURL
        if inJS is not None: self.inJS = inJS
        if inJSSingleQuoteString is not None: self.inJSSingleQuoteString = inJSSingleQuoteString

    def __repr__(self):
        rstr = ''
        if self._remembrances:
            rstr = ', remembrances=%r' % self._remembrances
        attribstr=''
        if self.isAttrib:
            attribstr=", isAttrib=True"
        urlStr = ''
        if self.inURL:
            urlStr = ', inURL=True'
        return "%s(tag=%r%s%s%s)" % (self.__class__.__name__, self.tag, rstr,attribstr,urlStr)

    def patternGenerator(self, pattern, default=None):
        warnings.warn("use Tag.patternGenerator instead", DeprecationWarning, stacklevel=2)
        return self.tag.patternGenerator(pattern, default)

    def allPatterns(self, pattern):
        warnings.warn("use Tag.allPatterns instead", DeprecationWarning, stacklevel=2)
        return self.tag.allPatterns(pattern)

    def onePattern(self, pattern):
        warnings.warn("use Tag.onePattern instead", DeprecationWarning, stacklevel=2)
        return self.tag.onePattern(pattern)

    def clone(self, deep=True, cloneTags=True):
        cloned = WebContext.clone(self, deep, cloneTags)
        cloned.isAttrib = self.isAttrib
        cloned.inURL = self.inURL
        return cloned
        
