
.PHONY: all

all: ./build/pypy.vm.js


# This is the necessary incantation to build the PyPy js backend
# in "release mode", optimized for deployment to the web.  It trades
# off some debuggability in exchange for reduced code size.
./build/pypy.vm.js: deps
	# We use a special additional include path to disable some debugging
	# info in the release build.
	CC="emcc -I $(CURDIR)/deps/pypy/rpython/translator/platform/emscripten_platform/nodebug" PATH=$(CURDIR)/build/deps/bin:$(CURDIR)/deps/emscripten:$$PATH EMSCRIPTEN=$(CURDIR)/deps/emscripten LLVM=$(CURDIR)/build/deps/bin PYTHON=$(CURDIR)/deps/bin/python ./build/deps/bin/pypy ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --translation-backendopt-remove_asserts --inline-threshold=25 --output=./build/pypy.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py
	# XXX TODO: build separate memory initializer.
	# XXX TODO: use closure compiler on the shell code.


# This builds a debugging-friendly version that is bigger but has e.g. 
# more asserts and better traceback information.
./build/pypy-debug.vm.js: deps
	CC="emcc -g2 -s ASSERTIONS=1" PATH=$(CURDIR)/build/deps/bin:$(CURDIR)/deps/emscripten:$$PATH EMSCRIPTEN=$(CURDIR)/deps/emscripten LLVM=$(CURDIR)/build/deps/bin PYTHON=$(CURDIR)/deps/bin/python ./build/deps/bin/pypy ./deps/pypy/rpython/bin/rpython --backend=js --opt=jit --inline-threshold=25 --output=./build/pypy-debug.vm.js ./deps/pypy/pypy/goal/targetpypystandalone.py


# This builds a bundle of the stdlib filesystem for easy inclusion.
./build/stdlib.js:
	python ./deps/emscripten/tools/file_packager.py ./build/stdlib.data --js-output=./build/stdlib.js --preload ./deps/pypy/lib-python@lib/pypyjs/lib-python --preload ./deps/pypy/lib_pypy/@lib/pypyjs/lib_pypy --no-heap-copy --exclude *.wav --exclude *.pyc



# For convenience we build local copies of the more fiddly bits
# of our compilation toolchain.
.PHONY: deps
deps:	./build/deps/bin/pypy ./build/deps/bin/clang
	# Check that nodejs is available.
	node --version > /dev/null
	# Initialize .emscripten config file.
	PATH=$(CURDIR)/build/deps/bin:$(CURDIR)/deps/emscripten:$$PATH emcc --version > /dev/null


# Running the tests requires a local install of "libffi".
./build/deps/lib/libffi-3.1/include/ffi.h:
	mkdir -p ./build/deps
	mkdir -p ./build/tmp
	# XXX TODO: https or digest verification on this file...
	wget -O ./build/tmp/libffi-3.1.gz ftp://sourceware.org/pub/libffi/libffi-3.1.tar.gz
	cd ./build/tmp ; tar -xzvf libffi-3.1.gz
	cd ./build/tmp/libffi-3.1 ; ./configure --prefix=$(CURDIR)/build/deps --includedir=$(CURDIR)/build/deps/include CC="gcc -m32"
	cd ./build/tmp/libffi-3.1 ; make
	cd ./build/tmp/libffi-3.1 ; make install


# Running the tests requires a local install of "libgc".
./build/deps/include/gc.h:
	mkdir -p ./build/deps
	mkdir -p ./build/tmp
	# XXX TODO: https or digest verification on this file...
	wget -O ./build/tmp/gc-7.2f.tar.gz http://www.hboehm.info/gc/gc_source/gc-7.2f.tar.gz
	cd ./build/tmp ; tar -xzvf gc-7.2f.tar.gz
	cd ./build/tmp/gc-7.2 ; ./configure --prefix=$(CURDIR)/build/deps CC="gcc -m32"
	cd ./build/tmp/gc-7.2 ; make
	cd ./build/tmp/gc-7.2 ; make install


# Since emscripten is a 32-bit target platform, we have to build pypy
# using a 32-bit python or it gets very confused.  This fetches and 
# builds an appropriate version from source.
./build/deps/bin/python:
	mkdir -p ./build/deps
	mkdir -p ./build/tmp
	wget -O ./build/tmp/Python-2.7.8.tgz https://www.python.org/ftp/python/2.7.8/Python-2.7.8.tgz
	cd ./build/tmp ; tar -xzvf Python-2.7.8.tgz
	cd ./build/tmp/Python-2.7.8 ; ./configure --prefix=$(CURDIR)/build/deps CC="gcc -m32"
	cd ./build/tmp/Python-2.7.8 ; make
	cd ./build/tmp/Python-2.7.8 ; make install
	rm -rf ./build/tmp/Python-2.7.8*


# To speed up the ultimate build process, we now use the above 32-bit
# cpython to build a 32-bit native pypy executable.  This is what we'll
# run do to the actual pypy.js builds.  It needs to live in the pypy
# directory to properly find its library files, so we symlink it at
# the end of the build.
./build/deps/bin/pypy: ./build/deps/bin/python
	./build/deps/bin/python ./deps/pypy/rpython/bin/rpython --opt=jit --gcrootfinder=shadowstack --cc="gcc -m32" --output=./deps/pypy/pypy-c ./deps/pypy/pypy/goal/targetpypystandalone.py --translationmodules
	ln -s ../../../deps/pypy/pypy-c ./build/deps/bin/pypy


# Build the emscripten-enabled LLVM clang toolchain.
# We need to coordinate versions of three different repos to get
# this working, so we might as well simplify it for people.
./build/deps/bin/clang:
	if [ -f ./deps/emscripten-fastcomp/tools/clang/README.txt ]; then true; else ln -sf ../../emscripten-fastcomp-clang ./deps/emscripten-fastcomp/tools/clang; fi
	mkdir -p ./build/tmp/emscripten
	cd ./build/tmp/emscripten ; ../../../deps/emscripten-fastcomp/configure --enable-optimized --disable-assertions --enable-targets=host,js --prefix=$(CURDIR)/build/deps
	cd ./build/tmp/emscripten ; make -j 2
	cd ./build/tmp/emscripten ; make install
	rm -rf ./build/tmp/emscripten

.PHONY: test-jit-backend
test-jit-backend: ./build/deps/bin/python ./build/deps/include/gc.h ./build/deps/lib/libffi-3.1/include/ffi.h
	cd ./deps/pypy/rpython/jit/backend/asmjs ; LD_LIBRARY_PATH="../../../../../../build/deps/lib" CC="gcc -m32 -I$(CURDIR)/deps/pypy/rpython/translator/platform/emscripten_platform -I$(CURDIR)/build/deps/include -L$(CURDIR)/build/deps/lib" ../../../../../../build/deps/bin/python ../../../../pytest.py -vx


# Cleanout any non-essential build cruft.
.PHONY: clean
clean:
	rm -rf ./build/tmp


# Blow away all built artifacts.
.PHONY: clobber
clobber:
	rm -rf ./build
