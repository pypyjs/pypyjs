"""
'ctypes_configure' source for _locale.py.
Run this to rebuild _locale_cache.py.
"""

from ctypes_configure.configure import (configure, ExternalCompilationInfo,
    ConstantInteger, DefinedConstantInteger, SimpleType, check_eci)
import dumpcache

# ____________________________________________________________

_CONSTANTS = [
    'LC_CTYPE',
    'LC_TIME',
    'LC_COLLATE',
    'LC_MONETARY',
    'LC_MESSAGES',
    'LC_NUMERIC',
    'LC_ALL',
    'CHAR_MAX',
]

class LocaleConfigure:
    _compilation_info_ = ExternalCompilationInfo(includes=['limits.h',
                                                           'locale.h'])
for key in _CONSTANTS:
    setattr(LocaleConfigure, key, DefinedConstantInteger(key))

config = configure(LocaleConfigure, noerr=True)
for key, value in config.items():
    if value is None:
        del config[key]
        _CONSTANTS.remove(key)

# ____________________________________________________________

eci = ExternalCompilationInfo(includes=['locale.h', 'langinfo.h'])
HAS_LANGINFO = check_eci(eci)

if HAS_LANGINFO:
    # list of all possible names
    langinfo_names = [
        "RADIXCHAR", "THOUSEP", "CRNCYSTR",
        "D_T_FMT", "D_FMT", "T_FMT", "AM_STR", "PM_STR",
        "CODESET", "T_FMT_AMPM", "ERA", "ERA_D_FMT", "ERA_D_T_FMT",
        "ERA_T_FMT", "ALT_DIGITS", "YESEXPR", "NOEXPR", "_DATE_FMT",
        ]
    for i in range(1, 8):
        langinfo_names.append("DAY_%d" % i)
        langinfo_names.append("ABDAY_%d" % i)
    for i in range(1, 13):
        langinfo_names.append("MON_%d" % i)
        langinfo_names.append("ABMON_%d" % i)
    
    class LanginfoConfigure:
        _compilation_info_ = eci
        nl_item = SimpleType('nl_item')
    for key in langinfo_names:
        setattr(LanginfoConfigure, key, DefinedConstantInteger(key))

    langinfo_config = configure(LanginfoConfigure)
    for key, value in langinfo_config.items():
        if value is None:
            del langinfo_config[key]
            langinfo_names.remove(key)
    config.update(langinfo_config)
    _CONSTANTS += langinfo_names

# ____________________________________________________________

config['ALL_CONSTANTS'] = tuple(_CONSTANTS)
config['HAS_LANGINFO'] = HAS_LANGINFO
dumpcache.dumpcache2('locale', config)
