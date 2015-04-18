# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from __future__ import generators

import urllib, warnings

from twisted.python import log, failure

from nevow import util
from nevow.stan import directive, Unset, invisible, _PrecompiledSlot
from nevow.inevow import ICanHandleException, IData, IMacroFactory, IRenderer, IRendererFactory
from nevow.flat import precompile, serialize
from nevow.accessors import convertToData
from nevow.context import WovenContext

allowSingleton = ('img', 'br', 'hr', 'base', 'meta', 'link', 'param', 'area',
                  'input', 'col', 'basefont', 'isindex', 'frame')


def ProtoSerializer(original, context):
    return '<%s />' % original


def _datacallback(result, context):
    context.remember(result, IData)
    return ''


def TagSerializer(original, context, contextIsMine=False):
    """
    Original is the tag.
    Context is either:
      - the context of someone up the chain (if contextIsMine is False)
      - this tag's context (if contextIsMine is True)
    """
#    print "TagSerializer:",original, "ContextIsMine",contextIsMine, "Context:",context
    visible = bool(original.tagName)
    
    if visible and context.isAttrib:
        raise RuntimeError, "Tried to render tag '%s' in an tag attribute context." % (original.tagName)

    if context.precompile and original.macro:
        toBeRenderedBy = original.macro
        ## Special case for directive; perhaps this could be handled some other way with an interface?
        if isinstance(toBeRenderedBy, directive):
            toBeRenderedBy = IMacroFactory(context).macro(context, toBeRenderedBy.name)
        original.macro = Unset
        newContext = WovenContext(context, original)
        yield serialize(toBeRenderedBy(newContext), newContext)
        return

    ## TODO: Do we really need to bypass precompiling for *all* specials?
    ## Perhaps just render?
    if context.precompile and (
        [x for x in original._specials.values() 
        if x is not None and x is not Unset]
        or original.slotData):
        ## The tags inside this one get a "fresh" parent chain, because
        ## when the context yielded here is serialized, the parent
        ## chain gets reconnected to the actual parents at that
        ## point, since the render function here could change
        ## the actual parentage hierarchy.
        nestedcontext = WovenContext(precompile=context.precompile, isAttrib=context.isAttrib)
        
        # If necessary, remember the MacroFactory onto the new context chain.
        macroFactory = IMacroFactory(context, None)
        if macroFactory is not None:
            nestedcontext.remember(macroFactory, IMacroFactory)

        original = original.clone(deep=False)
        if not contextIsMine:
            context = WovenContext(context, original)
        context.tag.children = precompile(context.tag.children, nestedcontext)

        yield context
        return

    ## Don't render patterns
    if original.pattern is not Unset and original.pattern is not None:
        return

    if not contextIsMine:
        if original.render:
            ### We must clone our tag before passing to a render function
            original = original.clone(deep=False)
        context = WovenContext(context, original)
        
    if original.data is not Unset:
        newdata = convertToData(original.data, context)
        if isinstance(newdata, util.Deferred):
            yield newdata.addCallback(lambda newdata: _datacallback(newdata, context))
        else:
            _datacallback(newdata, context)
            
    if original.render:
        ## If we have a render function we want to render what it returns,
        ## not our tag
        toBeRenderedBy = original.render
        # erase special attribs so if the renderer returns the tag,
        # the specials won't be on the context twice.
        original._clearSpecials()
        yield serialize(toBeRenderedBy, context)
        return

    if not visible:
        for child in original.children:
            yield serialize(child, context)
        return

    yield '<%s' % original.tagName
    if original.attributes:
        attribContext = WovenContext(parent=context, precompile=context.precompile, isAttrib=True)
        for (k, v) in original.attributes.iteritems():
            if v is None:
                continue
            yield ' %s="' % k
            yield serialize(v, attribContext)
            yield '"'
    if not original.children:
        if original.tagName in allowSingleton:
            yield ' />'
        else:
            yield '></%s>' % original.tagName
    else:
        yield '>'
        for child in original.children:
            yield serialize(child, context)        
        yield '</%s>' % original.tagName


def EntitySerializer(original, context):
    if original.name in ['amp', 'gt', 'lt', 'quot']:
        return '&%s;' % original.name
    return '&#%s;' % original.num

def _jsSingleQuoteQuote(quotable):
    return quotable.replace(
        "\\", "\\\\").replace(
        "'", r"\'").replace(
        "\n", "\\n").replace(
        "\r", "\\r")

def RawSerializer(original, context):
    if context.inJSSingleQuoteString:
        return _jsSingleQuoteQuote(original)
    return original


def StringSerializer(original, context):
    # Quote the string as necessary. URLs need special quoting - only
    # alphanumeric and a few punctation characters are valid.
    # Otherwise we use normal XML escaping rules but also replacing "
    # in an attribute because Nevow always uses "..." for values.
    if context.inURL:
        # The magic string "-_.!*'()" also appears in url.py.  Thinking about
        # changing this?  Change that, too.
        return urllib.quote(original, safe="-_.!*'()")
    ## quote it
    if context.inJS:
        original = _jsSingleQuoteQuote(original)
        if not context.inJSSingleQuoteString:
            original = "'%s'" % (original, )
    if context.isAttrib:
        return original.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    elif context.inJS:
        return original
    else:
        return original.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def NoneWarningSerializer(original, context):
    if context.isAttrib:
        ## We don't want the big red None warning inside a html attribute. Just leave it blank.
        return ''
    elif context.inURL:
        return ''
    elif context.inJS:
        return ''
    return '<span style="font-size: xx-large; font-weight: bold; color: red; border: thick solid red;">None</span>'


def StringCastSerializer(original, context):
    if context.inJS:
        return str(original)
    return StringSerializer(str(original), context)



def BooleanSerializer(original, context):
    if context.inJS:
        if original:
            return 'true'
        return 'false'
    return str(original)


def ListSerializer(original, context):
    for item in original:
        yield serialize(item, context)


def XmlSerializer(original, context):
    return original.content


PASS_SELF = object()


def FunctionSerializer_nocontext(original):
    code = getattr(original, 'func_code', None)
    if code is None:
        return True
    argcount = code.co_argcount
    if argcount == 1:
        return True
    if argcount == 3:
        return PASS_SELF
    return False


def FunctionSerializer(original, context, nocontextfun=FunctionSerializer_nocontext):
    if context.precompile:
        return WovenContext(tag=invisible(render=original))
    else:
        data = convertToData(context.locate(IData), context)
        try:
            nocontext = nocontextfun(original)
            if nocontext is True:
                result = original(data)
            else:
                if nocontext is PASS_SELF:
                    renderer = context.locate(IRenderer)
                    result = original(renderer, context, data)
                else:
                    result = original(context, data)
        except StopIteration:
            raise RuntimeError, "User function %r raised StopIteration." % original
        return serialize(result, context)


def MethodSerializer(original, context):
    def nocontext(original):
        func = getattr(original, 'im_func', None)
        code = getattr(func, 'func_code', None)
        return code is None or code.co_argcount == 2
    return FunctionSerializer(original, context, nocontext)


def RendererSerializer(original, context):
    def nocontext(original):
        func = getattr(original, 'im_func', None)
        code = getattr(func, 'func_code', None)
        return code is None or code.co_argcount == 2
    return FunctionSerializer(original.rend, context, nocontext)


def DirectiveSerializer(original, context):
    if context.precompile:
        return original

    rendererFactory = context.locate(IRendererFactory)
    renderer = rendererFactory.renderer(context, original.name)
    return serialize(renderer, context)


def SlotSerializer(original, context):
    """
    Serialize a slot.

    If the value is already available in the given context, serialize and
    return it.  Otherwise, if this is a precompilation pass, return a new
    kind of slot which captures the current render context, so that any
    necessary quoting may be performed.  Otherwise, raise an exception
    indicating that the slot cannot be serialized.
    """
    if context.precompile:
        try:
            data = context.locateSlotData(original.name)
        except KeyError:
            return _PrecompiledSlot(
                original.name,
                precompile(original.children, context),
                original.default,
                context.isAttrib,
                context.inURL,
                context.inJS,
                context.inJSSingleQuoteString,
                original.filename,
                original.lineNumber,
                original.columnNumber)
        else:
            return serialize(data, context)
    try:
        data = context.locateSlotData(original.name)
    except KeyError:
        if original.default is None:
            raise
        data = original.default
    return serialize(data, context)


def PrecompiledSlotSerializer(original, context):
    """
    Serialize a pre-compiled slot.

    Return the serialized value of the slot or raise a KeyError if it has no
    value.
    """
    # Precompilation should _not_ be happening at this point, but Nevow is very
    # sloppy about precompiling multiple times, so sometimes we are in a
    # precompilation context.  In this case, there is nothing to do, just
    # return the original object.  The case which seems to exercise this most
    # often is the use of a pattern as the stan document given to the stan
    # loader.  The pattern has already been precompiled, but the stan loader
    # precompiles it again.  This case should be eliminated by adding a loader
    # for precompiled documents.
    if context.precompile:
        warnings.warn(
            "[v0.9.9] Support for multiple precompilation passes is deprecated.",
            PendingDeprecationWarning)
        return original

    try:
        data = context.locateSlotData(original.name)
    except KeyError:
        if original.default is None:
            raise
        data = original.default
    originalContext = context.clone(deep=False)
    originalContext.isAttrib = original.isAttrib
    originalContext.inURL = original.inURL
    originalContext.inJS = original.inJS
    originalContext.inJSSingleQuoteString = original.inJSSingleQuoteString
    return serialize(data, originalContext)


def ContextSerializer(original, context):
    """
    Serialize the given context's tag in that context.
    """
    originalContext = original.clone(deep=False)
    originalContext.precompile = context and context.precompile or False
    if originalContext.parent is not None:
        originalContext.parent = originalContext.parent.clone(cloneTags=False)
    originalContext.chain(context)
    try:
        return TagSerializer(originalContext.tag, originalContext, contextIsMine=True)
    except:
        f = failure.Failure()
        handler = context.locate(ICanHandleException)
        if handler:
            return handler.renderInlineError(context, f)
        else:
            log.err(f)
            return """<div style="border: 1px dashed red; color: red; clear: both">[[ERROR]]</div>"""


def CommentSerializer(original, context):
    yield "<!--"
    for x in original.children:
        yield serialize(x, context)
    yield "-->"


def DocFactorySerializer(original, ctx):
    """Serializer for document factories.
    """
    return serialize(original.load(ctx), ctx)


def FailureSerializer(original, ctx):
    from nevow import failure
    return serialize(failure.formatFailure(original), ctx)


def inlineJSSerializer(original, ctx):
    from nevow import livepage
    from nevow.tags import script, xml
    theJS = livepage.js(original.children)
    new = livepage.JavascriptContext(ctx, invisible[theJS])
    return serialize(script(type="text/javascript")[
        xml('\n//<![CDATA[\n'),
        serialize(theJS, new),
        xml('\n//]]>\n')], ctx)

