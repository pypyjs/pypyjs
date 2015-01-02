#
# Makefile for building various parts of pypyjs.
#
# Note that the pypyjs build environment is very particular - emscripten
# produces 32-bit code, so pypy must be translated using a 32-bit python
# interpreter with various 32-bit support libraries.
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
all: ./build/pypy.js.tar.gz


# This runs the dockerized build commands as if they were in the current
# directory, with write access to the current directory.  For linux we
# can mount /etc/passwd and actually run as the current user.  For OSX
# we run as root, assuming the curdir is under /Users, and hence that
# boot2docker will automagically share it with appropriate permissions.

DOCKER_IMAGE = rfkelly/pypyjs-build

DOCKER_ARGS = -ti --rm -v /tmp:/tmp -v $(CURDIR):$(CURDIR) -w $(CURDIR) -e "CFLAGS=$$CFLAGS" -e "LDFLAGS=$$LDFLAGS"

ifeq ($(shell uname -s),Linux)
    # For linux, we can mount /etc/passwd and actually run as the current
    # user, making permissions work nicely on created build artifacts.
    # For other platforms we just run as the default docker user, assume
    # that the current directory is somewhere boot2docker can automagically
    # mount it, and hence build artifacts will get sensible permissions.
    DOCKER_ARGS += -v /etc/passwd:/etc/passwd -u $(USER)
endif

DOCKER = docker run $(DOCKER_ARGS) $(DOCKER_IMAGE)

# Change these variables if you want to use a custom build environment.
# They must point to the emscripten compiler, a 32-bit python executable
# and a 32-bit pypy executable.

EMCC = $(DOCKER) emcc
PYTHON = $(DOCKER) python
PYPY = $(DOCKER) pypy


# Top-level target to build a release bundle.
# This makes a tarball containing the compiled pypy interpreter, supporting
# javascript code, and the python stdlib modules and tooling.

./build/%.js.tar.gz: ./build/%.vm.js
	mkdir -p build/$*.js/lib
	# Copy the compiled VM and massage it into the expected shape.
	cp ./build/$*.vm.js ./build/$*.js/lib/pypy.vm.js
	python ./tools/extract_memory_initializer.py ./build/$*.js/lib/pypy.vm.js
	python ./tools/cromulate.py ./build/$*.js/lib/pypy.vm.js
	# Copy the supporting JS library code.
	cp ./lib/pypy.js ./lib/README.txt ./lib/Promise.min.js ./build/$*.js/lib/
	python tools/bundle_modules.py  ./build/$*.js/lib/modules/
	# Copy tools for managing the distribution.
	# XXX TODO: needs a distribution-suitable README
	mkdir -p build/$*.js/tools
	cp ./tools/bundle_modules.py ./build/$*.js/tools/
	cp ./package.json ./build/$*.js/package.json
	# Tar it up, and we're done.
	cd ./build && tar -czf $*.js.tar.gz $*.js
	rm -rf ./build/$*.js


# This is the necessary incantation to build the PyPy js backend
# in "release mode", optimized for deployment to the web.  It trades
# off some debuggability in exchange for reduced code size.

./build/pypy.vm.js:
	mkdir -p build
	$(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/pypy.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py


# This builds a debugging-friendly version that is bigger but has e.g. 
# more asserts and better traceback information.

./build/pypy-debug.vm.js:
	mkdir -p build
	export LDFLAGS="$$LDFLAGS -g2 -s ASSERTIONS=1" && $(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --inline-threshold=25 --output=./build/pypy-debug.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py


# This builds a version of pypy.js without its JIT, which is useful for
# investigating the size or performance of the core interpreter.

./build/pypy-nojit.vm.js:
	mkdir -p build
	$(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=2 --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/pypy-nojit.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py


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
