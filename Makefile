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


# This runs the dockerized build commands as if they were in the current
# directory, with write access to the current directory.  We try to do
# the most useful thing we can for the following platforms:
#
# * For linux, we can mount /etc/passwd and actually run as the current
#   user, ensuring that the built artifacts get sensible file permissions
#   by default.
#
# * For docker-on-macOS, we run as root inside the docker container
#   and assume the curdir is under /Users, meaning that docker will
#   automagically share it with appropriate permissions.
#
# * For docker-on-windows-under-WSL, we run as root inside the docker
#   container and assume the curdir somewhere under /c/, meaning that
#   docker can automagically share it with appropriate permissions.

DOCKER_IMAGE = rfkelly/pypyjs-build

DOCKER_ARGS = -ti --rm -v $(CURDIR):$(CURDIR) -w $(CURDIR) -e "CFLAGS=$$CFLAGS" -e "LDFLAGS=$$LDFLAGS" -e "EMCFLAGS=$$EMCFLAGS" -e "EMLDFLAGS=$$EMLDFLAGS" -e "IN_DOCKER=1" -e "PYTHONPATH=$$PYTHONPATH"

ifeq ($(shell uname -s),Linux)
    ifeq (,$(findstring Microsoft,$(shell uname -r)))
        DOCKER_ARGS += -v /etc/passwd:/etc/passwd -u $(USER)
    endif
endif

ifeq ($(IN_DOCKER), 1)
    DOCKER =
else
    DOCKER = docker run $(DOCKER_ARGS) $(DOCKER_IMAGE)
endif


# Enable this to assist in debugging failed builds.
# It causes PyPy to store its temp build state under ./build/
# but has the potential to slow down builds due to file sharing overhead.
#DOCKER_ARGS += -e "PYPY_USESSION_DIR=$(CURDIR)/build/tmp"

# Change these variables if you want to use a custom build environment.
# They must point to the emscripten compiler, a 32-bit python executable
# and a 32-bit pypy executable.

EMCC = $(DOCKER) emcc
PYTHON = $(DOCKER) python
PYPY = $(DOCKER) pypy


# The default target puts a built interpreter locally in ./lib.

.PHONY: lib
lib: ./lib/pypyjs.js

./lib/pypyjs.js: ./src/pypyjs.js ./src/tests/tests.js ./lib/pypyjs.vm.js ./node_modules/gulp/bin/gulp.js
	node ./node_modules/gulp/bin/gulp.js

./lib/pypyjs.vm.js: ./build/pypyjs.vm.js
	cp ./build/pypyjs.vm.js ./lib/
	python ./tools/extract_memory_initializer.py ./lib/pypyjs.vm.js
	#python ./tools/compress_memory_initializer.py ./lib/pypyjs.vm.js
	rm -rf ./lib/modules/
	python tools/module_bundler.py init ./lib/modules/


# This makes a releasable tarball containing the compiled pypy interpreter,
# supporting javascript code, and the python stdlib modules and tooling.

VERSION = 0.4.1

.PHONY: release
release: ./build/pypyjs-$(VERSION).tar.gz

.PHONY: release-nojit
release-nojit: ./build/pypyjs-nojit-$(VERSION).tar.gz

.PHONY: release-debug
release-debug: ./build/pypyjs-debug-$(VERSION).tar.gz

./build/%-$(VERSION).tar.gz: RELNAME = $*-$(VERSION)
./build/%-$(VERSION).tar.gz: RELDIR = ./build/$(RELNAME)
./build/%-$(VERSION).tar.gz: ./build/%.vm.js ./lib/pypyjs.js
	mkdir -p $(RELDIR)/lib
	# Copy the compiled VM and massage it into the expected shape.
	cp ./build/$*.vm.js $(RELDIR)/lib/pypyjs.vm.js
	python ./tools/extract_memory_initializer.py $(RELDIR)/lib/pypyjs.vm.js
	python ./tools/compress_memory_initializer.py $(RELDIR)/lib/pypyjs.vm.js
	# Cromulate for better compressibility, unless it's a debug build.
	if [ `echo $< | grep -- -debug` ]; then true ; else python ./tools/cromulate.py -w 1000 $(RELDIR)/lib/pypyjs.vm.js ; fi
	# Copy the supporting JS library code.
	cp ./lib/pypyjs.js ./lib/README.txt ./lib/*Promise*.js $(RELDIR)/lib/
	cp -r ./lib/tests $(RELDIR)/lib/tests
	# Create an indexed stdlib distribution.
	# Note that we must run this with matching major python version,
	# to signal that we want the corresponding libs.
	if [` echo $< | grep pypyjs3` ]; then python3 tools/module_bundler.py init $(RELDIR)/lib/modules/ ; else python ./tools/module_bundler.py init $(RELDIR)/lib/modules/; fi
	# Copy tools for managing the distribution.
	mkdir -p $(RELDIR)/tools
	cp ./tools/module_bundler.py $(RELDIR)/tools/
	# Copy release distribution metadata.
	cp ./package.json $(RELDIR)/package.json
	cp ./README.dist.rst $(RELDIR)/README.rst
	# Tar it up, and we're done.
	cd ./build && tar -czf $(RELNAME).tar.gz $(RELNAME)
	rm -rf $(RELDIR)


# This is the necessary incantation to build the PyPy js backend
# in "release mode", optimized for deployment to the web.  It trades
# off some debuggability in exchange for reduced code size.

./build/pypyjs.vm.js: ./build/tmp
	$(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/pypyjs.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py


# This builds a debugging-friendly version that is bigger but has e.g.
# more asserts and better traceback information.

./build/pypyjs-debug.vm.js: ./build/tmp
	export EMLDFLAGS="$$EMLDFLAGS -g2 -s ASSERTIONS=1" && $(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --inline-threshold=25 --output=./build/pypyjs-debug.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py


# This builds a version of pypy.js without its JIT, which is useful for
# investigating the size or performance of the core interpreter.

./build/pypyjs-nojit.vm.js: ./build/tmp
	$(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=2 --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/pypyjs-nojit.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py


# Experimental targets for building python3 interpreter.
#
# To avoid the overhead of porting our rpython toolchain modifications
# across branches, we build a python3 interpreter by using the toolchain
# from our default branch and feeding it the interpreter from the py3k
# branch.  Not pretty, but it works andit *saves* us work.

.PHONY: release3
release3: ./build/pypyjs3-$(VERSION).tar.gz

.PHONY: release3-nojit
release3-nojit: ./build/pypyjs3-nojit-$(VERSION).tar.gz

.PHONY: release3-debug
release3-debug: ./build/pypyjs3-debug-$(VERSION).tar.gz

./build/pypy3-builder/NONEXISTENT:
	# This gets rsynced every time we try to build something
	# python3-related, but rsync is pretty fast so no big deal.
	# We just have to make sure it's an order-only prereq of the
	# *.vm.js targets, otherwise those will also be rebuilt every time.
	mkdir -p ./build/pypy3-builder
	rsync -ad --exclude=/rpython ./deps/pypy3/ ./build/pypy3-builder/
	rsync -ad ./deps/pypy/rpython/ ./build/pypy3-builder/rpython/

./build/pypyjs3.vm.js: ./build/tmp | ./build/pypy3-builder/NONEXISTENT
	$(PYPY) ./build/pypy3-builder/rpython/bin/rpython --backend=js --opt=jit --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/pypyjs3.vm.js ./build/pypy3-builder/pypy/goal/targetpypystandalone.py

./build/pypyjs3-debug.vm.js: ./build/tmp | ./build/pypy3-builder/NONEXISTENT
	export EMLDFLAGS="$$EMLDFLAGS -g2 -s ASSERTIONS=1" && $(PYPY) ./build/pypy3-builder/rpython/bin/rpython --backend=js --opt=jit --inline-threshold=25 --output=./build/pypyjs3-debug.vm.js ./build/pypy3-builder/pypy/goal/targetpypystandalone.py

./build/pypyjs3-nojit.vm.js: ./build/tmp | ./build/pypy3-builder/NONEXISTENT
	$(PYPY) ./build/pypy3-builder/rpython/bin/rpython --backend=js --opt=2 --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/pypyjs3-nojit.vm.js ./build/pypy3-builder/pypy/goal/targetpypystandalone.py

# This builds a smaller test program.

./build/rematcher.js: ./build/tmp
	$(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/rematcher.js ./tools/rematcher.py

./build/rematcher-nojit.js: ./build/tmp
	$(PYPY) ./deps/pypy/rpython/bin/rpython --backend=js --opt=2 --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/rematcher-nojit.js ./tools/rematcher.py

./build/tmp:
	mkdir -p ./build/tmp

./node_modules/gulp/bin/gulp.js: package.json
	npm install
	touch ./node_modules/gulp/bin/gulp.js

# Convenience target to launch a shell in the dockerized build environment.

shell:
	$(DOCKER) /bin/bash


# Convenience targets for running the tests.

.PHONY: test
test: test-js-module test-jit-backend

.PHONY: test-jit-backend
test-jit-backend:
	$(PYTHON) $(CURDIR)/deps/pypy/pytest.py --platform=emscripten -vx ./deps/pypy/rpython/jit/backend/asmjs

.PHONY: test-js-module
test-js-module:
	$(PYTHON) $(CURDIR)/deps/pypy/pytest.py -vx ./deps/pypy/pypy/module/js

