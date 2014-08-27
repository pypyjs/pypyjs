#
# Makefile for building various parts of pypyjs.
#
# Note that the pypyjs build environment is very particular - emscripten
# produces 32-bit code, so pypy must be translated using a 32-bit python
# interpreter with various 32-bit support libraries.  This Makefile can
# build *some* of them automatically, but you will almost certainly want
# to run it from a 32-bit linux environment.
#
# The recommended approach is to use the pre-build docker image for the
# build environment, available at:
#
#     XXX TODO: publish the docker image
#

.PHONY: all

all: ./build/pypy.vm.js


# This is the necessary incantation to build the PyPy js backend
# in "release mode", optimized for deployment to the web.  It trades
# off some debuggability in exchange for reduced code size.

./build/pypy.vm.js: deps
	# We use a special additional include path to disable some debugging
	# info in the release build. XXX TODO: doesn't work yet...
	CC="emcc -I $(CURDIR)/deps/pypy/rpython/translator/platform/emscripten_platform/nodebug" PATH=$(CURDIR)/build/deps/bin:$(CURDIR)/deps/emscripten:$$PATH EMSCRIPTEN=$(CURDIR)/deps/emscripten LLVM=$(CURDIR)/build/deps/bin PYTHON=$(CURDIR)/deps/bin/python ./build/deps/bin/pypy ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/pypy.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py
	# XXX TODO: build separate memory initializer.
	# XXX TODO: use closure compiler on the shell code.


# This builds a debugging-friendly version that is bigger but has e.g. 
# more asserts and better traceback information.

./build/pypy-debug.vm.js: deps
	CC="emcc -g2 -s ASSERTIONS=1" PATH=$(CURDIR)/build/deps/bin:$(CURDIR)/deps/emscripten:$$PATH EMSCRIPTEN=$(CURDIR)/deps/emscripten LLVM=$(CURDIR)/build/deps/bin PYTHON=$(CURDIR)/deps/bin/python ./build/deps/bin/pypy ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --inline-threshold=25 --output=./build/pypy-debug.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py


# This builds a smaller test program.

./build/rematcher.js: deps
	CC="emcc -I $(CURDIR)/deps/pypy/rpython/translator/platform/emscripten_platform/nodebug" PATH=$(CURDIR)/build/deps/bin:$(CURDIR)/deps/emscripten:$$PATH EMSCRIPTEN=$(CURDIR)/deps/emscripten LLVM=$(CURDIR)/build/deps/bin PYTHON=$(CURDIR)/deps/bin/python ./build/deps/bin/pypy ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/rematcher.js ./tools/rematcher.py


# For convenience we build local copies of the more fiddly bits
# of our compilation toolchain.

.PHONY: deps
deps:	./build/deps/bin/pypy ./build/deps/bin/clang ./build/deps/bin/node
	# Initialize .emscripten config file.
	PATH=$(CURDIR)/build/deps/bin:$(CURDIR)/deps/emscripten:$$PATH emcc --version > /dev/null


# Build the emscripten-enabled LLVM clang toolchain.
# We need to coordinate versions of three different repos to get this working.

./build/deps/bin/clang:
	if [ -f ./deps/emscripten-fastcomp/tools/clang/README.txt ]; then true; else ln -sf ../../emscripten-fastcomp-clang ./deps/emscripten-fastcomp/tools/clang; fi
	mkdir -p ./build/tmp/emscripten
	cd ./build/tmp/emscripten ; PATH=$(CURDIR)/build/deps/bin:$$PATH ../../../deps/emscripten-fastcomp/configure --enable-optimized --disable-assertions --enable-targets=host,js --prefix=$(CURDIR)/build/deps
	cd ./build/tmp/emscripten ; make -j 2
	cd ./build/tmp/emscripten ; make install
	rm -rf ./build/tmp/emscripten

# To speed up the ultimate build process, we build a 32-bit native pypy
# interpreter with which to do the pypyjs builds.  It needs to live in the
# pypy source directory in order to locaite its library files, so we symlink
# it at the end of the build.

./build/deps/bin/pypy: ./build/deps/bin/clang
	python ./deps/pypy/rpython/bin/rpython --opt=jit --gcrootfinder=shadowstack --cc="$(CURDIR)/build/deps/bin/clang -m32" --output=./deps/pypy/pypy-c ./deps/pypy/pypy/goal/targetpypystandalone.py --translationmodules
	ln -s ../../../deps/pypy/pypy-c ./build/deps/bin/pypy

# Some distributions don't ship with nodejs by default,
# so here's a simple recipe for it.

./build/deps/bin/node:
	mkdir -p ./build/deps
	mkdir -p ./build/tmp
	# XXX TODO: verify the download
	wget -O ./build/tmp/node-v0.10.30.tar.gz http://nodejs.org/dist/v0.10.30/node-v0.10.30.tar.gz
	cd ./build/tmp ; tar -xzvf node-v0.10.30.tar.gz
	cd ./build/tmp/node-v0.10.30 ; ./configure CC=$(CURDIR)/build/deps/bin/clang --prefix=$(CURDIR)/build/deps
	cd ./build/tmp/node-v0.10.30 ; make
	cd ./build/tmp/node-v0.10.30 ; make install
	rm -rf ./build/tmp/node-v0.10.30

# Shortcuts for running the tests.

.PHONY: test-jit-backend
test-jit-backend: ./build/deps/bin/pypy
	cd ./deps/pypy/rpython/jit/backend/asmjs ; source $(CURDIR)/build/deps/bin/activate ; CC="gcc -m32" $(CURDIR)/build/deps/bin/python $(CURDIR)/deps/pypy/pytest.py -vx


# Cleanout any non-essential build cruft.
#
.PHONY: clean
clean:
	rm -rf ./build/tmp


# Blow away all built artifacts.

.PHONY: clobber
clobber:
	rm -rf ./build
