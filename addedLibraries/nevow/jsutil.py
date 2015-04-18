# -*- test-case-name: nevow.test.test_consolejstest -*-
# Copyright (c) 2004-2007 Divmod.
# See LICENSE for details.

from twisted.python.procutils import which
from twisted.python.util import sibpath

import nevow
from nevow.athena import (LivePage, allJavascriptPackages, AthenaModule,
    jsModuleDeclaration)

_TEST_BOOTSTRAP = LivePage.BOOTSTRAP_MODULES[:]
_TEST_BOOTSTRAP.insert(_TEST_BOOTSTRAP.index('Divmod.Runtime'),
                       'Divmod.MockBrowser')

_DUMMY_MODULE_NAME = 'ConsoleJSTest'

def getDependencies(fname, ignore=[],
                    bootstrap=_TEST_BOOTSTRAP,
                    packages=None):
    """
    Get the javascript modules that the code in the file with name C{fname}
    depends on, recursively

    @param fname: javascript source file name
    @type fname: C{str}

    @param ignore: names of javascript modules to exclude from dependency list
    @type ignore: sequence

    @param bootstrap: names of javascript modules to always include, regardless
    of explicit dependencies (defaults to L{LivePage}'s list of bootstrap
    modules, plus the mock browser implementation.)
    @type boostrap: sequence

    @param packages: all javascript packages we know about.  defaults to the
    result of L{allJavascriptPackages}
    @type packages: C{dict}

    @return: modules included by javascript in file named C{fname}
    @rtype: dependency-ordered list of L{AthenaModule} instances
    """
    if packages is None:
        packages = allJavascriptPackages()

    # TODO if a module is ignored, we should ignore its dependencies
    bootstrapModules = [AthenaModule.getOrCreate(m, packages)
                        for m in bootstrap if m not in ignore]

    packages[_DUMMY_MODULE_NAME] = fname
    module = AthenaModule(_DUMMY_MODULE_NAME, packages)

    return (bootstrapModules +
            [dep for dep in module.allDependencies()
             if (dep.name not in bootstrap
                 and dep.name != _DUMMY_MODULE_NAME
                 and dep.name not in ignore)])



def findJavascriptInterpreter():
    """
    Return a string path to a JavaScript interpreter if one can be found in
    the executable path. If not, return None.
    """
    for script in ['smjs', 'js']:
        _jsInterps = which(script)
        if _jsInterps:
            return _jsInterps[0]
    return None



def generateTestScript(fname, after={}, dependencies=None):
    """
    Turn the contents of the Athena-style javascript test module in the file
    named C{fname} into a plain javascript script.  Recursively includes any
    modules that are depended on, as well as the utility module
    nevow/test/testsupport.js.

    @param fname: javascript source file name
    @type fname: C{str}

    @param after: mapping of javascript module names to sequences of lines of
    javascript source that should be injected into the output immediately
    after the source of the named module is included
    @type after: C{dict}

    @param dependencies: the modules the script depends on.  Defaults to the
    result of L{getDependencies}
    @type dependencies: dependency-ordered list of L{AthenaModule} instances

    @return: converted javascript source text
    @rtype: C{str}
    """
    if dependencies is None:
        dependencies = getDependencies(fname)

    load = lambda fname: 'load(%r);' % (fname,)
    initialized = {}
    js = [load(sibpath(nevow.__file__, 'test/testsupport.js'))]
    for m in dependencies:
        segments = m.name.split('.')
        if segments[-1] == '__init__':
            segments = segments[:-1]
        initname = '.'.join(segments)
        if initname not in initialized:
            initialized[initname] = 1
            js.append(jsModuleDeclaration(initname))
        js.append(load(m.mapping[m.name]))
        if m.name in after:
            js.extend(after[m.name])

    js.append(file(fname).read())

    return '\n'.join(js)
