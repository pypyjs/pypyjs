# Copyright (c) 2004 Divmod.
# See LICENSE for details.

#  failure.py

import types
import linecache
import re

from nevow import tags as t
from twisted.python import failure


stylesheet = """
p.error {
  color: black;
  font-family: Verdana, Arial, helvetica, sans-serif;
  font-weight: bold;
  font-size: large;
  margin: 0.25em;
}

div {
  font-family: Verdana, Arial, helvetica, sans-serif;
}

strong.variableClass {
  font-size: small;
}

div.stackTrace {
}

div.frame {
  padding: 0.25em;
  background: white;
  border-bottom: thin black dotted;
}

div.firstFrame {
  padding: 0.25em;
  background: white;
  border-top: thin black dotted;
  border-bottom: thin black dotted;
}

div.location {
    font-size: small;
}

div.snippet {
  background: #FFFFDD;
  padding: 0.25em;
}

div.snippetHighlightLine {
  color: red;
}

span.lineno {
    font-size: small;
}

pre.code {
  margin: 0px;
  padding: 0px;
  display: inline;
  font-size: small;
  font-family: "Courier New", courier, monotype;
}

span.function {
  font-weight: bold;
  font-family: "Courier New", courier, monotype;
}

table.variables {
  border-collapse: collapse;
  width: 100%;
}

td.varName {
  width: 1in;
  vertical-align: top;
  font-style: italic;
  font-size: small;
  padding-right: 0.25em;
}

td.varValue {
  padding-left: 0.25em;
  padding-right: 0.25em;
  font-size: small;
}

div.variables {
  margin-top: 0.5em;
}

div.dict {
  background: #cccc99;
  padding: 2px;
  float: left;
}

td.dictKey {
  background: #ffff99;
  font-weight: bold;
}

td.dictValue {
  background: #ffff99;
}

div.list {
  background: #7777cc;
  padding: 2px;
  float: left;
}

div.listItem {
  background: #9999ff;
}

div.instance {
  width: 100%;
  background: #efefef;
  padding: 2px;
  float: left;
}

span.instanceName {
  font-size: small;
  display: block;
}

span.instanceRepr {
  font-family: "Courier New", courier, monotype;
}

div.function {
  background: orange;
  font-weight: bold;
  float: left;
}
"""


def saferepr(x):
    try:
        rx = repr(x)
    except:
        rx = "repr failed! %s instance at 0x%x" % (x.__class__, id(x))
    return rx


def htmlDict(d):
    return t.div(_class="dict")[
        t.span(_class="heading")[
            "Dictionary instance @ 0x%x" % id(d)
        ],
        t.table(_class="dict")[[
            t.tr[
                t.td(_class="dictKey")[ k == '__builtins__' and 'builtin dictionary' or htmlrepr(k) ],
                t.td(_class="dictValue")[ htmlrepr(v) ]
            ]
            for k, v in d.items()
        ]]
    ]
                

def htmlList(l):
    return t.div(_class="list")[
        t.span(_class="heading")[ "List instance @ 0x%x" % id(l) ],
        [t.div(_class="listItem")[ htmlrepr(i) ] for i in l]
    ]


def htmlInst(i):
    return t.div(_class="instance")[
        t.span(_class="instanceName")[ "%s instance at 0x%x" % (i.__class__, id(i)) ],
        t.span(_class="instanceRepr")[ saferepr(i) ]
    ]


def htmlString(s):
    return s


def htmlFunc(f):
    return t.div(_class="function")[
        "Function %s in file %s at line %s" % (f.__name__, f.func_code.co_filename, f.func_code.co_firstlineno)
    ]


def htmlMeth(m):
    return t.div(_class="method")[
        "Method %s in file %s at line %s" % (m.im_func.__name__, m.im_func.func_code.co_filename, m.im_func.func_code.co_firstlineno)
    ]

def htmlUnknown(u):
    return t.pre[
        saferepr(u)
    ]


htmlReprTypes = {
    types.DictType: htmlDict,
    types.ListType: htmlList,
    types.InstanceType: htmlInst,
    types.StringType: htmlString,
    types.FunctionType: htmlFunc,
    types.MethodType: htmlMeth,
}


def htmlrepr(x):
    return htmlReprTypes.get(type(x), htmlUnknown)(x)


def varTable(usedVars):
    return t.table(_class="variables")[[
        t.tr(_class="varRow")[
            t.td(_class="varName")[ key ],
            t.td(_class="varValue")[ htmlrepr(value) ]
        ]
        for (key, value) in usedVars
    ]]


def formatFailure(myFailure):
    if not isinstance(myFailure, failure.Failure):
        return t.pre[ str(myFailure) ]

    stackTrace = t.div(_class="stackTrace")
    failureOverview = t.p(_class="error")[ str(myFailure.type), ": ", str(myFailure.value) ]

    result = [
        t.style(type="text/css")[
            stylesheet,
        ],
        t.a(href="#tracebackEnd")[ failureOverview ],
        stackTrace,
        t.a(name="tracebackEnd")[ failureOverview ]
    ]

    first = 1
    for method, filename, lineno, localVars, globalVars in myFailure.frames:
        # It's better to have a line number than nothing at all.
        #if filename == '<string>':
        #    continue
        if first:
            frame = t.div(_class="firstFrame")
            first = 0
        else:
            frame = t.div(_class="frame")
        stackTrace[ frame ]

        snippet = t.div(_class="snippet")
        frame[
            t.div(_class="location")[
                filename, ", line ", lineno, " in ", t.span(_class="function")[ method ]
            ],
            snippet,
        ]

        textSnippet = ''
        for snipLineNo in range(lineno-2, lineno+2):
            snipLine = linecache.getline(filename, snipLineNo)
            textSnippet += snipLine
            if snipLineNo == lineno:
                snippetClass = "snippetHighlightLine"
            else:
                snippetClass = "snippetLine"
            snippet[
                t.div(_class=snippetClass)[
                    t.span(_class="lineno")[ snipLineNo ],
                    t.pre(_class="code")[ snipLine ]
                ]
            ]

        # Instance variables
        for name, var in localVars:
            if name == 'self' and hasattr(var, '__dict__'):
                usedVars = [ (key, value) for (key, value) in var.__dict__.items()
                             if re.search(r'\Wself.%s\W' % (re.escape(key),), textSnippet) ]
                if usedVars:
                    frame[
                        t.div(_class="variables")[
                            t.strong(_class="variableClass")[ "Self" ],
                            varTable(usedVars)
                        ]
                    ]
                    break

        # Local and global vars
        for nm, varList in ('Locals', localVars), ('Globals', globalVars):
            usedVars = [ (name, var) for (name, var) in varList
                         if re.search(r'\W%s\W' % (re.escape(name),), textSnippet) ]
            if usedVars:
                frame[
                    t.div(_class="variables")[ t.strong(_class="variableClass")[ nm ] ],
                    varTable(usedVars)
                ]

    return result
