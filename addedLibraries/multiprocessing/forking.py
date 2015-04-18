#
# Module for starting a process object using os.fork() or CreateProcess()
#
# multiprocessing/forking.py
#
# Copyright (c) 2006-2008, R Oudkerk
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of author nor the names of any contributors may be
#    used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#

import os
import sys
import signal
import errno

from multiprocessing import util, process

__all__ = ['Popen', 'assert_spawning', 'exit', 'duplicate', 'close', 'ForkingPickler']

#
# Check that the current thread is spawning a child process
#

def assert_spawning(self):
    if not Popen.thread_is_spawning():
        raise RuntimeError(
            '%s objects should only be shared between processes'
            ' through inheritance' % type(self).__name__
            )

#
# Try making some callable types picklable
#

from pickle import Pickler
class ForkingPickler(Pickler):
    dispatch = Pickler.dispatch.copy()

    @classmethod
    def register(cls, type, reduce):
        def dispatcher(self, obj):
            rv = reduce(obj)
            self.save_reduce(obj=obj, *rv)
        cls.dispatch[type] = dispatcher

def _reduce_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)
ForkingPickler.register(type(ForkingPickler.save), _reduce_method)

if type(list.append) is not type(ForkingPickler.save):
    # Some python implementations have unbound methods even for builtin types
    def _reduce_method_descriptor(m):
        return getattr, (m.__objclass__, m.__name__)
    ForkingPickler.register(type(list.append), _reduce_method_descriptor)
    ForkingPickler.register(type(int.__add__), _reduce_method_descriptor)

try:
    from functools import partial
except ImportError:
    pass
else:
    def _reduce_partial(p):
        return _rebuild_partial, (p.func, p.args, p.keywords or {})
    def _rebuild_partial(func, args, keywords):
        return partial(func, *args, **keywords)
    ForkingPickler.register(partial, _reduce_partial)

#
# Unix
#

o=[]

if sys.platform != 'win32':
    import time
    import js
    def fork(obj):
        import pickle
        dta = pickle.dumps(obj)
        return js.globals['fork'](dta)
    js.fork=fork
    exit = os._exit
    duplicate = os.dup
    close = os.close

    #
    # We define a Popen class similar to the one from subprocess, but
    # whose constructor takes a process object as its argument.
    #

    class Popen(object):

        def __init__(self, process_obj, isChild=False):
            sys.stdout.flush()
            sys.stderr.flush()
            self.returncode = None
            
            if isChild:
                if 'random' in sys.modules:
                    import random
                    random.seed()
                code = process_obj._bootstrap()
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(code)
            else:
                self.pid = js.fork(process_obj)
        def poll(self, flag=os.WNOHANG):
            if self.returncode is None:
                while True:
                    try:
                        pid, sts = os.waitpid(self.pid, flag)
                    except os.error as e:
                        if e.errno == errno.EINTR:
                            continue
                        # Child process not yet created. See #1731717
                        # e.errno == errno.ECHILD == 10
                        return None
                    else:
                        break
                if pid == self.pid:
                    if os.WIFSIGNALED(sts):
                        self.returncode = -os.WTERMSIG(sts)
                    else:
                        assert os.WIFEXITED(sts)
                        self.returncode = os.WEXITSTATUS(sts)
            return self.returncode

        def wait(self, timeout=None):
            if timeout is None:
                return self.poll(0)
            deadline = time.time() + timeout
            delay = 0.0005
            while 1:
                res = self.poll()
                if res is not None:
                    break
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                delay = min(delay * 2, remaining, 0.05)
                time.sleep(delay)
            return res

        def terminate(self):
            if self.returncode is None:
                try:
                    os.kill(self.pid, signal.SIGTERM)
                except OSError, e:
                    if self.wait(timeout=0.1) is None:
                        raise

        @staticmethod
        def thread_is_spawning():
            return False

#
# Prepare current process
#

old_main_modules = []

def prepare(data):
    '''
    Try to get current process ready to unpickle process object
    '''
    old_main_modules.append(sys.modules['__main__'])

    if 'name' in data:
        process.current_process().name = data['name']

    if 'authkey' in data:
        process.current_process()._authkey = data['authkey']

    if 'log_to_stderr' in data and data['log_to_stderr']:
        util.log_to_stderr()

    if 'log_level' in data:
        util.get_logger().setLevel(data['log_level'])

    if 'sys_path' in data:
        sys.path = data['sys_path']

    if 'sys_argv' in data:
        sys.argv = data['sys_argv']

    if 'dir' in data:
        os.chdir(data['dir'])

    if 'orig_dir' in data:
        process.ORIGINAL_DIR = data['orig_dir']

    if 'main_path' in data:
        main_path = data['main_path']
        main_name = os.path.splitext(os.path.basename(main_path))[0]
        if main_name == '__init__':
            main_name = os.path.basename(os.path.dirname(main_path))

        if main_name != 'ipython':
            import imp

            if main_path is None:
                dirs = None
            elif os.path.basename(main_path).startswith('__init__.py'):
                dirs = [os.path.dirname(os.path.dirname(main_path))]
            else:
                dirs = [os.path.dirname(main_path)]

            assert main_name not in sys.modules, main_name
            file, path_name, etc = imp.find_module(main_name, dirs)
            try:
                # We would like to do "imp.load_module('__main__', ...)"
                # here.  However, that would cause 'if __name__ ==
                # "__main__"' clauses to be executed.
                main_module = imp.load_module(
                    '__parents_main__', file, path_name, etc
                    )
            finally:
                if file:
                    file.close()

            sys.modules['__main__'] = main_module
            main_module.__name__ = '__main__'

            # Try to make the potentially picklable objects in
            # sys.modules['__main__'] realize they are in the main
            # module -- somewhat ugly.
            for obj in main_module.__dict__.values():
                try:
                    if obj.__module__ == '__parents_main__':
                        obj.__module__ = '__main__'
                except Exception:
                    pass
