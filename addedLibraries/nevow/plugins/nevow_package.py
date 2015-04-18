from twisted.python import util

from nevow import athena

import nevow

nevowCSSPkg = athena.AutoCSSPackage(util.sibpath(nevow.__file__, 'css'))
nevowPkg = athena.AutoJSPackage(util.sibpath(nevow.__file__, 'js'))
