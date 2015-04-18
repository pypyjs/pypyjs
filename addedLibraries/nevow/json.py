# -*- test-case-name: nevow.test.test_json -*-
# Copyright (c) 2004-2007 Divmod.
# See LICENSE for details.

"""
JavaScript Object Notation.

This is not (nor does it intend to be) a faithful JSON implementation, but it
is kind of close.
"""

import re, types

from nevow.inevow import IAthenaTransportable
from nevow import rend, page, _flat, tags

class ParseError(ValueError):
    pass

whitespace = re.compile(
            r'('
            r'[\r\n\t\ ]+'
            r'|/\*.*?\*/'
            r'|//[^\n]*[\n]'
            r')'
            , re.VERBOSE + re.DOTALL)
openBrace = re.compile(r'{')
closeBrace = re.compile(r'}')
openSquare = re.compile(r'\[')
closeSquare = re.compile(r'\]')

class StringTokenizer(object):
    """
    because r'(?<!\\)"([^"]+|\\")*(?<!\\)"'
    """

    def match(self, s):
        if not s.startswith('"'):
            return None

        bits = []

        SLASH = "\\"

        IT = iter(s)
        bits = [IT.next()]
        for char in IT:
            bits.append(char)
            if char == SLASH:
                try:
                    bits.append(IT.next())
                except StopIteration:
                    return None
            if char == '"':
                self.matched = ''.join(bits)
                return self

        return None

    def group(self, num):
        return self.matched

string = StringTokenizer()
identifier = re.compile(r'[A-Za-z_][A-Za-z_0-9]*')
colon = re.compile(r':')
comma = re.compile(r',')
true = re.compile(r'true')
false = re.compile(r'false')
null = re.compile(r'null')
floatNumber = re.compile(r'-?([1-9][0-9]*|0)(\.[0-9]+)([eE][-+]?[0-9]+)?')
longNumber = re.compile(r'-?([1-9][0-9]*|0)([eE][-+]?[0-9]+)?')

class StringToken(str):
    pass

class IdentifierToken(str):
    pass

class WhitespaceToken(object):
    pass

def jsonlong(s):
    if 'e' in s:
        m, e = map(long, s.split('e', 1))
    else:
        m, e = long(s), 0
    return m * 10 ** e

# list of tuples, the first element is a compiled regular expression the second
# element returns a token and the original string.
actions = [
    (whitespace, lambda s: (WhitespaceToken, s)),
    (openBrace, lambda s: ('{',s)),
    (closeBrace, lambda s: ('}',s)),
    (openSquare, lambda s: ('[',s)),
    (closeSquare, lambda s: (']',s)),
    (string, lambda s: (StringToken(s), s)),
    (colon, lambda s: (':', s)),
    (comma, lambda s: (',', s)),
    (true, lambda s: (True, s)),
    (false, lambda s: (False, s)),
    (null, lambda s: (None, s)),
    (identifier, lambda s: (IdentifierToken(s), s)),
    (floatNumber, lambda s: (float(s), s)),
    (longNumber, lambda s: (jsonlong(s), s)),
]
def tokenise(s):
    tokens = []
    while s:
        for regexp, action in actions:
            m = regexp.match(s)
            if m:
                tok, tokstr = action(m.group(0))
                break
        else:
            raise ValueError, "Invalid Input, %r" % (s[:10],)

        if tok is not WhitespaceToken:
            tokens.append(tok)
        s = s[len(tokstr):]

    return tokens

def accept(want, tokens):
    t = tokens.pop(0)
    if want != t:
        raise ParseError, "Unexpected %r, %s expected" % (t , want)

def parseValue(tokens):
    if tokens[0] == '{':
        return parseObject(tokens)

    if tokens[0] == '[':
        return parseList(tokens)

    if tokens[0] in (True, False, None):
        return tokens.pop(0), tokens

    if type(tokens[0]) == StringToken:
        return parseString(tokens)

    if type(tokens[0]) in (int, float, long):
        return tokens.pop(0), tokens

    raise ParseError, "Unexpected %r" % tokens[0]


_stringExpr = re.compile(
    ur'(?:\\x(?P<unicode>[a-fA-F0-9]{2})) # Match hex-escaped unicode' u'\n'
    ur'|' u'\n'
    ur'(?:\\u(?P<unicode2>[a-fA-F0-9]{4})) # Match hex-escaped high unicode' u'\n'
    ur'|' u'\n'
    ur'(?P<control>\\[fbntr\\"]) # Match escaped control characters' u'\n',
    re.VERBOSE)

_controlMap = {
    u'\\f': u'\f',
    u'\\b': u'\b',
    u'\\n': u'\n',
    u'\\t': u'\t',
    u'\\r': u'\r',
    u'\\"': u'"',
    u'\\\\': u'\\',
    }

def _stringSub(m):
    u = m.group('unicode')
    if u is None:
        u = m.group('unicode2')
    if u is not None:
        return unichr(int(u, 16))
    c = m.group('control')
    return _controlMap[c]


def parseString(tokens):
    if type(tokens[0]) is not StringToken:
        raise ParseError, "Unexpected %r" % tokens[0]
    s = _stringExpr.sub(_stringSub, tokens.pop(0)[1:-1].decode('utf-8'))
    return s, tokens


def parseIdentifier(tokens):
    if type(tokens[0]) is not IdentifierToken:
        raise ParseError("Unexpected %r" % (tokens[0],))
    return tokens.pop(0), tokens


def parseList(tokens):
    l = []
    tokens.pop(0)
    first = True
    while tokens[0] != ']':
        if not first:
            accept(',', tokens)
        first = False

        value, tokens = parseValue(tokens)
        l.append(value)

    accept(']', tokens)
    return l, tokens


def parseObject(tokens):
    o = {}
    tokens.pop(0)
    first = True
    while tokens[0] != '}':
        if not first:
            accept(',', tokens)
        first = False

        name, tokens = parseString(tokens)
        accept(':', tokens)
        value, tokens = parseValue(tokens)
        o[name] = value

    accept('}', tokens)
    return o, tokens


def parse(s):
    """
    Return the object represented by the JSON-encoded string C{s}.
    """
    tokens = tokenise(s)
    value, tokens = parseValue(tokens)
    if tokens:
        raise ParseError, "Unexpected %r" % tokens[0]
    return value

class CycleError(Exception):
    pass

_translation = dict([(o, u'\\x%02x' % (o,)) for o in range(0x20)])

# Characters which cannot appear as literals in the output
_translation.update({
    ord(u'\\'): u'\\\\',
    ord(u'"'): ur'\"',
    ord(u'\f'): ur'\f',
    ord(u'\b'): ur'\b',
    ord(u'\n'): ur'\n',
    ord(u'\t'): ur'\t',
    ord(u'\r'): ur'\r',
    # The next two are sneaky, see
    # http://timelessrepo.com/json-isnt-a-javascript-subset
    ord(u'\u2028'): u'\\u2028',
    ord(u'\u2029'): u'\\u2029',
    })

def stringEncode(s):
    return s.translate(_translation).encode('utf-8')


def _serialize(obj, w, seen):
    from nevow import athena

    if isinstance(obj, types.BooleanType):
        if obj:
            w('true')
        else:
            w('false')
    elif isinstance(obj, (int, long, float)):
        w(str(obj))
    elif isinstance(obj, unicode):
        w('"')
        w(stringEncode(obj))
        w('"')
    elif isinstance(obj, types.NoneType):
        w('null')
    elif id(obj) in seen:
        raise CycleError(type(obj))
    elif isinstance(obj, (tuple, list)):
        w('[')
        for n, e in enumerate(obj):
            _serialize(e, w, seen)
            if n != len(obj) - 1:
                w(',')
        w(']')
    elif isinstance(obj, dict):
        w('{')
        for n, (k, v) in enumerate(obj.iteritems()):
            _serialize(k, w, seen)
            w(':')
            _serialize(v, w, seen)
            if n != len(obj) - 1:
                w(',')
        w('}')
    elif isinstance(obj, (athena.LiveFragment, athena.LiveElement)):
        _serialize(obj._structured(), w, seen)
    elif isinstance(obj, (rend.Fragment, page.Element)):
        wrapper = tags.div(xmlns="http://www.w3.org/1999/xhtml")
        w('"')
        w(stringEncode(
                "".join(_flat.flatten(None, wrapper[obj],
                                      False, False)).decode('utf-8')))
        w('"')
    else:
        transportable = IAthenaTransportable(obj, None)
        if transportable is not None:
            w('(new ' + transportable.jsClass.encode('ascii') + '(')
            arguments = transportable.getInitialArguments()
            for n, e in enumerate(arguments):
                _serialize(e, w, seen)
                if n != len(arguments) - 1:
                    w(',')
            w('))')
        else:
            raise TypeError("Unsupported type %r: %r" % (type(obj), obj))



_undefined = object()
def serialize(obj=_undefined, **kw):
    """
    JSON-encode an object.

    @param obj: None, True, False, an int, long, float, unicode string,
    list, tuple, or dictionary the JSON-encoded form of which will be
    returned.
    """
    if obj is _undefined:
        obj = kw
    L = []
    _serialize(obj, L.append, {})
    return ''.join(L)

__all__ = ['parse', 'serialize']
