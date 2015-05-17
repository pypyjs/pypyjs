# The content of this file is redirected from
# sysconfig_cpython or sysconfig_pypy.
# All underscore names are imported too, because
# people like to use undocumented sysconfig._xxx
# directly.

import sys
if '__pypy__' in sys.builtin_module_names:
    from distutils import sysconfig_pypy as _sysconfig_module
else:
    from distutils import sysconfig_cpython as _sysconfig_module
globals().update(_sysconfig_module.__dict__)
