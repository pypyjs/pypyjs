#! /usr/bin/env python
# Run this script to rebuild all caches from the *.ctc.py files.

import os, sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..')))

import py

_dirpath = os.path.dirname(__file__) or os.curdir

from rpython.tool.ansi_print import ansi_log
log = py.log.Producer("ctypes_config_cache")
py.log.setconsumer("ctypes_config_cache", ansi_log)


def rebuild_one(name):
    filename = os.path.join(_dirpath, name)
    d = {'__file__': filename}
    path = sys.path[:]
    try:
        sys.path.insert(0, _dirpath)
        execfile(filename, d)
    finally:
        sys.path[:] = path

def try_rebuild():
    size = 32 if sys.maxint <= 2**32 else 64
    # remove the files '_*_size_.py'
    left = {}
    for p in os.listdir(_dirpath):
        if p.startswith('_') and (p.endswith('_%s_.py' % size) or
                                  p.endswith('_%s_.pyc' % size)):
            os.unlink(os.path.join(_dirpath, p))
        elif p.startswith('_') and (p.endswith('_.py') or
                                    p.endswith('_.pyc')):
            for i in range(2, len(p)-4):
                left[p[:i]] = True
    # remove the files '_*_cache.py' if there is no '_*_*_.py' left around
    for p in os.listdir(_dirpath):
        if p.startswith('_') and (p.endswith('_cache.py') or
                                  p.endswith('_cache.pyc')):
            if p[:-9] not in left:
                os.unlink(os.path.join(_dirpath, p))
    #
    for p in os.listdir(_dirpath):
        if p.endswith('.ctc.py'):
            try:
                rebuild_one(p)
            except Exception, e:
                log.ERROR("Running %s:\n  %s: %s" % (
                    os.path.join(_dirpath, p),
                    e.__class__.__name__, e))


if __name__ == '__main__':
    try_rebuild()
