#!/bin/bash
#
# Script to build a docker image encapsulating the pypyjs build environment.
#
# The pypyjs build environment is very particular - it requires a 32-bit
# linux system with several pre-installed libraries and header files.
# This script starts from a 32-bit base environment, installs the necessary
# build and test tools, and stores the result as a docker image.
#
# Pre-requisites:
#
#    * docker, and a running docker daemon
#    * a built "rfkelly/linux32" base image
#

set -e
set -u

BUILD_DIR=`mktemp -d -t pypyjs-docker-build-XXXXXX`
trap "rm -rf $BUILD_DIR" EXIT

# Ensure that docker is actually running.

docker ps >/dev/null

# Write out a Makefile for building all the things.
# This makes it easy to do them in one hit, rather than having each
# build step add another layer to the final dockerfile.

cat > $BUILD_DIR/Makefile << END_MAKEFILE

.PHONY: all
all: /usr/local/lib/python2.7/dist-packages/PyV8-1.0_dev-py2.7-linux-x86_64.egg /usr/bin/emcc /usr/bin/pypy


/usr/bin/pypy:
	apt-get install -y git-core python-dev libffi-dev libgc-dev libncurses-dev libz-dev pkg-config
	mkdir -p /build
	# Ensure we have the repo checked out.
	if [ -d /build/pypy ]; then true; else git clone https://github.com/pypyjs/pypy /build/pypy; fi;
	# Ensure we're using up-to-date code.
	cd /build/pypy; git pull; git gc --aggressive
	# Build it, and link it into system path.
	python /build/pypy/rpython/bin/rpython --opt=jit --gcrootfinder=shadowstack --cc="gcc -m32" --thread --no-shared --output=/build/pypy/pypy-c /build/pypy/pypy/goal/targetpypystandalone.py --translationmodules
	ln -s /build/pypy/pypy-c /usr/bin/pypy
	# Remove any build and vc files that we don't need at runtime.
	rm -rf /tmp/usession-* /tmp/ctypes_configure-*
	rm -rf /build/pypy/.git


/usr/bin/emcc: /usr/bin/node /usr/bin/cmake
	apt-get install -y git-core libffi-dev libgc-dev libncurses-dev libz-dev pkg-config
	mkdir -p /build
	wget -O /tmp/emscripten-portable.tar.gz https://s3.amazonaws.com/mozilla-games/emscripten/releases/emsdk-portable.tar.gz
	cd /build; tar -zxvf /tmp/emscripten-portable.tar.gz ; rm /tmp/emscripten-portable.tar.gz
	cd /build/emsdk-portable; ./emsdk update
	# We're on a 32-bit system, so clang builds with 32-bit filesystem structures.
	# But docker-for-windows mounts volumes via CIFS, which has 64-bit inodes.
	# So we have to do a little hackery to force clang to build with large-file support,
	# otherwise it will ignore include files mounted into the docker image via CIFS. Bleh.
	mkdir -p /build/emsdk-portable/clang/fastcomp
	git clone https://github.com/kripken/emscripten-fastcomp /build/emsdk-portable/clang/fastcomp/src
	echo 'add_definitions("-D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64")' > /build/emsdk-portable/clang/fastcomp/src/CMakeLists.txt.new
	cat /build/emsdk-portable/clang/fastcomp/src/CMakeLists.txt >> /build/emsdk-portable/clang/fastcomp/src/CMakeLists.txt.new
	mv /build/emsdk-portable/clang/fastcomp/src/CMakeLists.txt.new /build/emsdk-portable/clang/fastcomp/src/CMakeLists.txt
	# OK now we can let the SDK build it.
	cd /build/emsdk-portable; ./emsdk install sdk-master-32bit
	cd /build/emsdk-portable; ./emsdk activate sdk-master-32bit --global
	ln -s /build/emsdk-portable/emscripten/master/emcc /usr/bin/emcc
	# Hack around problem with missing netlink.h include.
	grep -v "AF_NETLINK" /build/emsdk-portable/emscripten/master/system/include/libc/sys/socket.h > /tmp/socket.h.new
	mv /tmp/socket.h.new /build/emsdk-portable/emscripten/master/system/include/libc/sys/socket.h
	# Use system node, rather than the one bundled with emscripten.
	rm -rf /build/emsdk-portable/node
	cat /root/.emscripten | grep -v NODE_JS= > /root/.emscripten.new
	echo "NODE_JS='/usr/bin/node'" | cat - /root/.emscripten.new > /root/.emscripten
	rm -rf /root/.emscripten.new
	# Pre-compile common emscripten utilities
	cd /build/emsdk-portable ; . ./emsdk_env.sh ; emcc --version > /dev/null
	cd /build/emsdk-portable ; . ./emsdk_env.sh ; emcc --clear-cache > /dev/null
	cd /build/emsdk-portable ; . ./emsdk_env.sh ; python ./emscripten/master/embuilder.py build libc


/usr/local/lib/python2.7/dist-packages/PyV8-1.0_dev-py2.7-linux-x86_64.egg:
	apt-get install -y git-core pkg-config python-dev python-setuptools libboost-system-dev libboost-thread-dev libboost-python-dev
	git clone http://github.com/buffer/pyv8.git /build/pyv8
	cd /build/pyv8; git submodule init; git submodule update
	cd /build/pyv8; cat setup.py | sed "s/if os.uname/if False and os.uname/g" > setup.py.new; mv setup.py.new setup.py
	# For unknown reasons setup.py does not find the tools in depot_tools
	cd /build/pyv8; PATH="/build/pyv8/depot_tools/:\${PATH}" python setup.py build
	cd /build/pyv8; python setup.py install
	rm -rf /build/pyv8


/usr/bin/node:
	apt-get install -y python-dev
	wget -O /tmp/node-v6.10.3.tar.gz https://nodejs.org/dist/v6.10.3/node-v6.10.3.tar.gz
	cd /tmp ; tar -xzvf node-v6.10.3.tar.gz
	cd /tmp/node-v6.10.3 ; ./configure  --prefix=/usr
	cd /tmp/node-v6.10.3 ; make
	cd /tmp/node-v6.10.3 ; make install
	rm -rf /tmp/node-v6.10.3*


/usr/bin/cmake:
	wget -O /tmp/cmake-3.8.0-rc4.tar.gz https://cmake.org/files/v3.8/cmake-3.8.0-rc4.tar.gz
	cd /tmp ; tar -xzvf cmake-3.8.0-rc4.tar.gz
	cd /tmp/cmake-3.8.0-rc4 ; ./configure --prefix=/usr && make && make install
	rm -rf /tmp/cmake-*

END_MAKEFILE

# Use docker to chroot into it and complete the setup.

cat > $BUILD_DIR/Dockerfile << END_DOCKERFILE

FROM rfkelly/linux32

MAINTAINER Ryan Kelly <ryan@rfk.id.au>

ENV LANG C.UTF-8

ADD Makefile /build/Makefile

RUN make -C /build all

ENV PATH /build/emsdk-portable:/build/emsdk-portable/clang/fastcomp/build_master_32/bin:/build/emsdk-portable/emscripten/master:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV EMSDK /build/emsdk-portable
ENV EM_CONFIG /root/.emscripten
ENV BINARYEN_ROOT /build/emsdk-portable/clang/bin/binaryen
ENV EMSCRIPTEN /build/emsdk-portable/emscripten/bin

END_DOCKERFILE

docker build --no-cache --tag="rfkelly/pypyjs-build" $BUILD_DIR

