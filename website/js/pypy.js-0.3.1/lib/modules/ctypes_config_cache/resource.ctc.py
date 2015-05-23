"""
'ctypes_configure' source for resource.py.
Run this to rebuild _resource_cache.py.
"""


from ctypes import sizeof
import dumpcache
from ctypes_configure.configure import (configure,
    ExternalCompilationInfo, ConstantInteger, DefinedConstantInteger,
    SimpleType)


_CONSTANTS = (
    'RLIM_INFINITY',
    'RLIM_NLIMITS',
)
_OPTIONAL_CONSTANTS = (
    'RLIMIT_CPU',
    'RLIMIT_FSIZE',
    'RLIMIT_DATA',
    'RLIMIT_STACK',
    'RLIMIT_CORE',
    'RLIMIT_RSS',
    'RLIMIT_NPROC',
    'RLIMIT_NOFILE',
    'RLIMIT_OFILE',
    'RLIMIT_MEMLOCK',
    'RLIMIT_AS',
    'RLIMIT_LOCKS',
    'RLIMIT_SIGPENDING',
    'RLIMIT_MSGQUEUE',
    'RLIMIT_NICE',
    'RLIMIT_RTPRIO',
    'RLIMIT_VMEM',

    'RUSAGE_BOTH',
    'RUSAGE_SELF',
    'RUSAGE_CHILDREN',
)

# Setup our configure
class ResourceConfigure:
    _compilation_info_ = ExternalCompilationInfo(includes=['sys/resource.h'])
    rlim_t = SimpleType('rlim_t')
for key in _CONSTANTS:
    setattr(ResourceConfigure, key, ConstantInteger(key))
for key in _OPTIONAL_CONSTANTS:
    setattr(ResourceConfigure, key, DefinedConstantInteger(key))

# Configure constants and types
config = configure(ResourceConfigure)
config['rlim_t_max'] = (1<<(sizeof(config['rlim_t']) * 8)) - 1
optional_constants = []
for key in _OPTIONAL_CONSTANTS:
    if config[key] is not None:
        optional_constants.append(key)
    else:
        del config[key]

config['ALL_CONSTANTS'] = _CONSTANTS + tuple(optional_constants)
dumpcache.dumpcache2('resource', config)
