# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from zope.interface import implements, providedBy

from formless.iformless import IConfigurable, IActionableType, IBinding
from formless.annotate import Argument, ElementBinding, GroupBinding, Object, TypedInterface

from nevow import inevow
from nevow.context import WovenContext

class Configurable(object):
    implements(IConfigurable)

    bindingDict = None

    def __init__(self, original):
        self.original = original
        self.boundTo = self

    def getBindingNames(self, context):
        ## Todo: remove this getattr
        ifs = providedBy(getattr(self, 'boundTo', self))
        ifs = [
            x for x in ifs if x is not IConfigurable and x is not TypedInterface
        ]
        bindingNames = []
        self.bindingDict = bindingDict = {}
        for interface in ifs:
            ## TypedInterfaces have a __spec__ attribute which is a list of all Typed properties and
            ## autocallable methods
            for binding in getattr(interface, '__spec__', []):
                bindingDict[binding.name] = binding
                if binding.name not in bindingNames:
                    bindingNames.append(binding.name)
                if IActionableType.providedBy(binding.typedValue):
                    acts = binding.typedValue.actions
                    if acts is None:
                        acts = []
                    for action in acts:
                        bindingDict[action.name] = action
        return bindingNames

    def getDefault(self, forBinding):
        ## TODO: Clean this up, it's a mess
        if not isinstance(forBinding, Argument):
            name = forBinding.name
            if hasattr(self, name):
                return getattr(self, name)
            ## Todo: Only do this in ConfigurableAdapter instead of Configurable
            if hasattr(self.boundTo, name):
                return getattr(self.boundTo, name)
            if self.original is not self.boundTo and hasattr(self.original, name):
                return getattr(self.original, name)
        return forBinding.default

    def getBinding(self, context, name):
        if self.bindingDict is None:
            self.getBindingNames(context)
        if self.bindingDict is None:
            self.bindingDict = {}
        binding = getattr(self, 'bind_%s' % name, getattr(self.boundTo, 'bind_%s' % name, None))
        if binding is not None:
            binding = binding(context)
        else:
            try:
                binding = self.bindingDict[name]
            except KeyError:
                raise RuntimeError, "%s is not an exposed binding on object %s." % (name, self.boundTo)
        binding.boundTo = self.boundTo
        return binding

    def postForm(self, ctx, bindingName, args):
        """Accept a form post to the given bindingName. The bindingName
        can be dotted to indicate an attribute of this Configurable, eg
        addresses.0.changeEmail. The post arguments are given in args.
        Return a Resource which will be rendered in response.
        """
        from formless import iformless
        from nevow.tags import invisible
        request = ctx.locate(inevow.IRequest)
        pathSegs = bindingName.split('.')
        configurable = self

        cf = ctx.locate(iformless.IConfigurableFactory)
        ## Get the first binding
        firstSeg = pathSegs.pop(0)
        binding = configurable.getBinding(ctx, firstSeg)
        ctx.remember(binding, IBinding)
        ctx.remember(configurable, IConfigurable)
        ## I don't think this works right now, it needs to be fixed.
        ## Most cases it won't be triggered, because we're just traversing a
        ## single binding name
        for seg in pathSegs:
            assert 1 == 0, "Sorry, this doesn't work right now"
            binding = configurable.getBinding(ctx, seg)
            child = self.boundTo
            if not isinstance(binding, GroupBinding):
                accessor = inevow.IContainer(configurable.boundTo, None)
                if accessor is None:
                    child = getattr(configurable.boundTo, binding.name)
                else:
                    child = accessor.child(ctx, binding.name)
            ## If it's a groupbinding, we don't do anything at all for this path segment
            
            ## This won't work right now. We need to push the previous configurable
            ## as the configurableFactory somehow and ask that for hte next binding
            ## we also need to support deferreds coming back from locateConfigurable
            assert 'black' is 'white', "Deferred support is pending"
            configurable = cf.locateConfigurable(ctx, child)
            ctx = WovenContext(ctx, invisible(key=seg))
            ctx.remember(binding, IBinding)
            ctx.remember(configurable, IConfigurable)

        bindingProcessor = iformless.IInputProcessor(binding)
        rv = bindingProcessor.process(ctx, binding.boundTo, args)
        ctx.remember(rv, inevow.IHand)
        ctx.remember('%r success.' % bindingName, inevow.IStatusMessage)
        return rv

    def summary(self):
        return "An instance of %s" % self.__class__.__name__

    postLocation = None

class NotFoundConfigurable(Configurable):
    def getBinding(self, context, name):
        raise RuntimeError, self.original


class TypedInterfaceConfigurable(Configurable):
    def __init__(self, original):
        self.original = original
        self.boundTo = original

    def summary(self):
        return "An instance of %s" % self.original.__class__.__name__

    def __repr__(self):
        return "TypedInterfaceConfigurable(%r)" % self.original


class ListConfigurable(TypedInterfaceConfigurable):
    def getBinding(self, context, name):
        eb = ElementBinding(name, Object())
        eb.boundTo = self.original
        return eb


class GroupConfigurable(TypedInterfaceConfigurable):
    def __init__(self, original, groupInterface):
        TypedInterfaceConfigurable.__init__(self, original)
        self.groupInterface = groupInterface

    bindingDict = None

    def getBindingNames(self, context):
        bindingNames = []
        self.bindingDict = bindingDict = {}
        interface = self.groupInterface
        for binding in getattr(interface, '__spec__', []):
            bindingDict[binding.name] = binding
            if binding.name not in bindingNames:
                bindingNames.append(binding.name)
            if IActionableType.providedBy(binding.typedValue):
                acts = binding.typedValue.actions
                if acts is None:
                    acts = []
                for action in acts:
                    bindingDict[action.name] = action
        return bindingNames


