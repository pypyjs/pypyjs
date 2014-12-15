#
# Makefile for building various parts of pypyjs.
#
# Note that the pypyjs build environment is very particular - emscripten
# produces 32-bit code, so pypy must be translated using a 32-bit python
# interpreter with various 32-bit support libraries.  This Makefile can
# build *some* of them automatically, but you will almost certainly want
# to run it from a 32-bit linux environment.
#
# The recommended approach is to use the pre-built docker image for the
# build environment, available via:
#
#     docker pull rfkelly/pypyjs-build
#
# If you'd like to use your own versions of these dependencies you
# will need to install:
#
#   * a working emscripten build environment
#   * a 32-bit pypy interpreter, for running the build
#   * a 32-bit cpython intereter, for running the tests
#   * 32-bit development libraries for "libffi" and "libgc"
#
# You can tweak the makefile variables below to point to such an environment.
#

.PHONY: all
all: ./build/pypy.vm.js

# This runs the dockerized build commands as if they were in the current
# directory, with write access to the current directory.  For linux we
# can mount /etc/passwd and actually run as the current user.  For OSX
# we run as root, assuming the curdir is under /Users, and hence that
# boot2docker will automagically share it with appropriate permissions.
#
# Change these variables if you want to use a custom build environment.

ifeq ($(shell uname -s),Linux)
    # For linux, we can mount /etc/passwd and actually run as the current
    # user, making permissions work nicely on created build artifacts.
    # For other platforms we just run as the default docker user, assume
    # that the current directory is somewhere boot2docker can automagically
    # mount it, and hence build artifacts will get sensible permissions.
    DOCKER_EXTRA_ARGS = -v /etc/passwd:/etc/passwd -u $(USER)
endif

DOCKER = docker run -ti --rm -v /tmp:/tmp -v $(CURDIR):$(CURDIR) -w $(CURDIR) -e "CFLAGS=$$CFLAGS" -e "LDFLAGS=$$LDFLAGS" $(DOCKER_EXTRA_ARGS) rfkelly/pypyjs-build

EMCC = $(DOCKER) emcc
PYTHON = $(DOCKER) python
PYPY = $(DOCKER) pypy


# This is the necessary incantation to build the PyPy js backend
# in "release mode", optimized for deployment to the web.  It trades
# off some debuggability in exchange for reduced code size.

./build/pypy.vm.js:
	mkdir -p build
	$(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/pypy.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py
	# XXX TODO: build separate memory initializer.
	# XXX TODO: use closure compiler on the shell code.


# This builds a similarly-configured native pypy executable.
# It's useful for doing performance comparisons etc.

./build/pypy:
	mkdir -p build
	$(PYPY) ./deps/pypy/rpython/bin/rpython --backend=c --cc="clang -m32" --opt=jit --gcrootfinder=shadowstack --translation-backendopt-remove_asserts --output=./build/pypy ./deps/pypy/pypy/goal/targetpypystandalone.py --withoutmod-bz2


# This builds a debugging-friendly version that is bigger but has e.g. 
# more asserts and better traceback information.

./build/pypy-debug.vm.js:
	mkdir -p build
	export LDFLAGS="$$LDFLAGS -g2 -s ASSERTIONS=1" && $(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --inline-threshold=25 --output=./build/pypy-debug.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py


# This builds a smaller test program.

./build/rematcher.js:
	mkdir -p build
	$(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/rematcher.js ./tools/rematcher.py


# Convenience target to launch a shell in the dockerized build environment.

shell:
	$(DOCKER) /bin/bash


# Convenience targets for running the tests.

.PHONY: test-jit-backend
test-jit-backend:
	$(PYTHON) $(CURDIR)/deps/pypy/pytest.py -vx ./deps/pypy/rpython/jit/backend/asmjs

.PHONY: test-js-module
test-js-module:
	$(PYTHON) $(CURDIR)/deps/pypy/pytest.py -vx ./deps/pypy/pypy/module/js
