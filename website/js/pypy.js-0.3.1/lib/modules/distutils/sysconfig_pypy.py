"""Provide access to Python's configuration information.
This is actually PyPy's minimal configuration information.

The specific configuration variables available depend heavily on the
platform and configuration.  The values may be retrieved using
get_config_var(name), and the list of variables is available via
get_config_vars().keys().  Additional convenience functions are also
available.
"""

__revision__ = "$Id: sysconfig.py 85358 2010-10-10 09:54:59Z antoine.pitrou $"

import sys
import os
import shlex

from distutils.errors import DistutilsPlatformError


PREFIX = os.path.normpath(sys.prefix)
EXEC_PREFIX = os.path.normpath(sys.exec_prefix)
project_base = os.path.dirname(os.path.abspath(sys.executable))
python_build = False


def get_python_inc(plat_specific=0, prefix=None):
    from os.path import join as j
    return j(sys.prefix, 'include')

def get_python_version():
    """Return a string containing the major and minor Python version,
    leaving off the patchlevel.  Sample return values could be '1.5'
    or '2.2'.
    """
    return sys.version[:3]


def get_python_lib(plat_specific=0, standard_lib=0, prefix=None):
    """Return the directory containing the Python library (standard or
    site additions).

    If 'plat_specific' is true, return the directory containing
    platform-specific modules, i.e. any module from a non-pure-Python
    module distribution; otherwise, return the platform-shared library
    directory.  If 'standard_lib' is true, return the directory
    containing standard Python library modules; otherwise, return the
    directory for site-specific modules.

    If 'prefix' is supplied, use it instead of sys.prefix or
    sys.exec_prefix -- i.e., ignore 'plat_specific'.
    """
    if prefix is None:
        prefix = PREFIX
    if standard_lib:
        return os.path.join(prefix, "lib-python", get_python_version())
    return os.path.join(prefix, 'site-packages')


_config_vars = None

def _init_posix():
    """Initialize the module as appropriate for POSIX systems."""
    g = {}
    g['EXE'] = ""
    g['SO'] = ".so"
    g['SOABI'] = g['SO'].rsplit('.')[0]
    g['LIBDIR'] = os.path.join(sys.prefix, 'lib')
    g['CC'] = "gcc -pthread" # -pthread might not be valid on OS/X, check

    global _config_vars
    _config_vars = g


def _init_nt():
    """Initialize the module as appropriate for NT"""
    g = {}
    g['EXE'] = ".exe"
    g['SO'] = ".pyd"
    g['SOABI'] = g['SO'].rsplit('.')[0]

    global _config_vars
    _config_vars = g


def get_config_vars(*args):
    """With no arguments, return a dictionary of all configuration
    variables relevant for the current platform.  Generally this includes
    everything needed to build extensions and install both pure modules and
    extensions.  On Unix, this means every variable defined in Python's
    installed Makefile; on Windows and Mac OS it's a much smaller set.

    With arguments, return a list of values that result from looking up
    each argument in the configuration variable dictionary.
    """
    global _config_vars
    if _config_vars is None:
        func = globals().get("_init_" + os.name)
        if func:
            func()
        else:
            _config_vars = {}

        _config_vars['prefix'] = PREFIX
        _config_vars['exec_prefix'] = EXEC_PREFIX

    if args:
        vals = []
        for name in args:
            vals.append(_config_vars.get(name))
        return vals
    else:
        return _config_vars

def get_config_var(name):
    """Return the value of a single variable using the dictionary
    returned by 'get_config_vars()'.  Equivalent to
    get_config_vars().get(name)
    """
    return get_config_vars().get(name)

def customize_compiler(compiler):
    """Dummy method to let some easy_install packages that have
    optional C speedup components.
    """
    if compiler.compiler_type == "unix":
        compiler.compiler_so.extend(['-O2', '-fPIC', '-Wimplicit'])
        compiler.shared_lib_extension = get_config_var('SO')
        if "CPPFLAGS" in os.environ:
            cppflags = shlex.split(os.environ["CPPFLAGS"])
            compiler.compiler.extend(cppflags)
            compiler.compiler_so.extend(cppflags)
            compiler.linker_so.extend(cppflags)
        if "CFLAGS" in os.environ:
            cflags = shlex.split(os.environ["CFLAGS"])
            compiler.compiler.extend(cflags)
            compiler.compiler_so.extend(cflags)
            compiler.linker_so.extend(cflags)
        if "LDFLAGS" in os.environ:
            ldflags = shlex.split(os.environ["LDFLAGS"])
            compiler.linker_so.extend(ldflags)


from sysconfig_cpython import (
    parse_makefile, _variable_rx, expand_makefile_vars)

