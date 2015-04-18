# Copyright (c) 2004 Divmod.
# See LICENSE for details.

"""Builtin template loaders that supply a Page or renderer with a
document to render.

Nevow provides the following DocFactory loaders by default:

  - B{stan} - turn a stan tag tree into a DocFactory
  - B{xmlfile} - load a well formed XML document from file
  - B{htmlfile} - load a HTML file from disk
  - B{xmlstr} - load a well formed XML document from a string
  - B{htmlstr} - load a HTML document from a string

Unless absolutely necessary you should use either the stan loader or
one of the xml loaders. The html loaders should only be used for badly
formed HTML documents, i.e. if your HTML developer hasn't heard of
XHTML yet. Even then, you should probably try to educate the HTML
developer first ;-).
"""

import warnings

import os.path
from zope.interface import implements

from twisted.python.reflect import getClass
from twisted.web import microdom

from nevow import inevow
from nevow import flat
from nevow.flat import flatsax
from nevow.util import CachedFile


class stan(object):
    """A stan tags document factory"""

    implements(inevow.IDocFactory)

    stan = None
    pattern = None
    _cache = None

    def __init__(self, stan=None, pattern=None):
        if stan is not None:
            self.stan = stan
        if pattern is not None:
            self.pattern = pattern


    def load(self, ctx=None, preprocessors=()):
        if self._cache is None:
            stan = [self.stan]
            for proc in preprocessors:
                stan = proc(stan)
            stan = flat.precompile(stan, ctx)
            if self.pattern is not None:
                stan = inevow.IQ(stan).onePattern(self.pattern)
            self._cache = stan
        return self._cache



class htmlstr(object):
    """A document factory for HTML contained in a string"""

    implements(inevow.IDocFactory)

    template = None
    pattern = None
    beExtremelyLenient = True
    _cache = None

    def __init__(self, template=None, pattern=None, beExtremelyLenient=None):
        warnings.warn(
            "[v0.8] htmlstr is deprecated because it's buggy. Please start using xmlfile and/or xmlstr.",
            DeprecationWarning,
            stacklevel=2)
        if template is not None:
            self.template = template
        if pattern is not None:
            self.pattern = pattern
        if beExtremelyLenient is not None:
            self.beExtremelyLenient = beExtremelyLenient

    def load(self, ctx=None, preprocessors=()):
        assert not preprocessors, "preprocessors not supported by htmlstr"
        if self._cache is None:
            doc = microdom.parseString(self.template, beExtremelyLenient=self.beExtremelyLenient)
            doc = flat.precompile(doc, ctx)
            if self.pattern is not None:
                doc = inevow.IQ(doc).onePattern(self.pattern)
            self._cache = doc
        return self._cache

class htmlfile(object):
    """A document factory for an HTML disk template"""

    implements(inevow.IDocFactory)

    template = None
    pattern = None
    templateDir = ''
    beExtremelyLenient = True

    def __init__(self, template=None, pattern=None, templateDir=None, beExtremelyLenient=None):
        warnings.warn(
            "[v0.8] htmlfile is deprecated because it's buggy. Please start using xmlfile and/or xmlstr.",
            DeprecationWarning,
            stacklevel=2)
        if template is not None:
            self.template = template
        if pattern is not None:
            self.pattern = pattern
        if templateDir is not None:
            self.templateDir = templateDir
        if beExtremelyLenient is not None:
            self.beExtremelyLenient = beExtremelyLenient
        _filename = os.path.join(self.templateDir, self.template)
        self._cache = CachedFile(_filename, self._reallyLoad)

    def _reallyLoad(self, path, ctx):
        doc = microdom.parse(path, beExtremelyLenient=self.beExtremelyLenient)
        doc = flat.precompile(doc, ctx)
        if self.pattern is not None:
            doc = inevow.IQ(doc).onePattern(self.pattern)
        return doc

    def load(self, ctx=None, preprocessors=()):
        assert not preprocessors, "preprocessors not supported by htmlfile"
        return self._cache.load(ctx)

class xmlstr(object):

    implements(inevow.IDocFactory)

    template = None
    pattern = None
    ignoreDocType = None
    ignoreComment = None
    _cache = None

    def __init__(self, template=None, pattern=None, ignoreDocType=False, ignoreComment=False):
        if template is not None:
            self.template = template
        if pattern is not None:
            self.pattern = pattern
        if ignoreDocType is not None:
            self.ignoreDocType = ignoreDocType
        if ignoreComment is not None:
            self.ignoreComment = ignoreComment

    def load(self, ctx=None, preprocessors=()):
        """
        Get an instance, possibly cached from a previous call, of this document
        """
        if self._cache is None:
            doc = flatsax.parseString(self.template, self.ignoreDocType, self.ignoreComment)
            for proc in preprocessors:
                doc = proc(doc)
            doc = flat.precompile(doc, ctx)
            if self.pattern is not None:
                doc = inevow.IQ(doc).onePattern(self.pattern)
            self._cache = doc
        return self._cache


class xmlfile(object):

    implements(inevow.IDocFactory)

    template = None
    templateDir = None
    pattern = None
    ignoreDocType = False
    ignoreComment = False

    def __init__(self, template=None, pattern=None, templateDir=None, ignoreDocType=None, ignoreComment=None):
        self._cache = {}
        if template is not None:
            self.template = template
        if pattern is not None:
            self.pattern = pattern
        if templateDir is not None:
            self.templateDir = templateDir
        if ignoreDocType is not None:
            self.ignoreDocType = ignoreDocType
        if ignoreComment is not None:
            self.ignoreComment = ignoreComment
        if self.templateDir is not None:
            self._filename = os.path.join(self.templateDir, self.template)
        else:
            self._filename = self.template

        self._cache = {}

    def load(self, ctx=None, preprocessors=()):
        rendererFactoryClass = None
        if ctx is not None:
            r = inevow.IRendererFactory(ctx, None)
            if r is not None:
                rendererFactoryClass = getClass(r)

        cacheKey = (self._filename, self.pattern, rendererFactoryClass)
        cachedFile = self._cache.get(cacheKey)
        if cachedFile is None:
            cachedFile = self._cache[cacheKey] = CachedFile(self._filename, self._reallyLoad)

        return cachedFile.load(ctx, preprocessors)

    def _reallyLoad(self, path, ctx, preprocessors):
        doc = flatsax.parse(open(self._filename), self.ignoreDocType, self.ignoreComment)
        for proc in preprocessors:
            doc = proc(doc)
        doc = flat.precompile(doc, ctx)

        if self.pattern is not None:
            doc = inevow.IQ(doc).onePattern(self.pattern)

        return doc
