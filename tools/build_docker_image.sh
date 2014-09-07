#!/bin/bash
#
# Script to build a docker image encapsulating the pypyjs build environment.
#
# The pypyjs build environment is very particular - it requires a 32-bit
# linux system with several pre-installed libraries and header files.
# This script boostraps a 32-bit debian chroot, installs the necessary
# dependencies, and stores the result as a docker image.
#
# Pre-requisites:
#
#    * docker, and a running docker daemon
#    * deboostrap, and running as root so it will work correctly
#

set -e
set -u

BUILD_DIR=`mktemp -d -t pypyjs-docker-build-XXXXXX`
trap "rm -rf $BUILD_DIR" EXIT

# Ensure that docker is actually running.

docker ps >/dev/null

# Create a bare-bones 32-bit debian chroot.

CHROOT_DIR="$BUILD_DIR/chroot"
debootstrap --arch i386 wheezy $CHROOT_DIR http://http.debian.net/debian/

# It needs a couple of 64-bit libs in it to allow docker to work correctly.
# XXX TODO: will they always be in these locations?

mkdir $CHROOT_DIR/lib64
cp /usr/lib/libpthread.so.0 $CHROOT_DIR/lib64
cp /lib/libc.so.6 $CHROOT_DIR/lib64
cp /lib64/ld-linux-x86-64.so.2 $CHROOT_DIR/lib64

# Write out a Makefile for building custom parts of the environment

cat > $CHROOT_DIR/Makefile << END_MAKEFILE

.PHONY: all
all: /usr/local/lib/python2.7/dist-packages/PyV8-1.0_dev-py2.7-linux-x86_64.egg /usr/bin/node /usr/bin/emcc /usr/bin/pypy


/usr/bin/node:
	# XXX TODO: verify the download
	wget -O tmp/node-v0.10.30.tar.gz http://nodejs.org/dist/v0.10.30/node-v0.10.30.tar.gz
	cd /tmp ; tar -xzvf node-v0.10.30.tar.gz
	cd /tmp/node-v0.10.30 ; ./configure  --prefix=/usr
	cd /tmp/node-v0.10.30 ; make
	cd /tmp/node-v0.10.30 ; make install
	rm -rf /tmp/node-v0.10.30*


/usr/bin/pypy:
	mkdir -p /build
	# Ensure we have the repo checked out.
	if [ -d /build/pypy ]; then true; else git clone https://github.com/rfk/pypy /build/pypy; fi;
	# Ensure we're using up-to-date code.
	cd /build/pypy; git pull; git gc --aggressive
	# Build it, and link it into system path.
	python /build/pypy/rpython/bin/rpython --opt=jit --gcrootfinder=shadowstack --cc="gcc -m32" --output=/build/pypy/pypy-c ./build/pypy/pypy/goal/targetpypystandalone.py --translationmodules
	ln -s /build/pypy/pypy-c /usr/bin/pypy
	# Remove any build and vc files that we don't need at runtime.
	rm -rf /tmp/usession-* /tmp/ctypes_configure-*
	rm -rf /build/pypy/.git


/usr/bin/emcc: /usr/bin/node
	mkdir -p /build
	# Fetch all the necessary repos.
	git clone https://github.com/kripken/emscripten /build/emscripten;
	git clone https://github.com/kripken/emscripten-fastcomp /build/emscripten-fastcomp
	git clone https://github.com/kripken/emscripten-fastcomp-clang /build/emscripten-fastcomp/tools/clang
	cd /build/emscripten ; git checkout -t origin/incoming
	cd /build/emscripten-fastcomp ; git checkout -t origin/incoming
	cd /build/emscripten-fastcomp/tools/clang ; git checkout -t origin/incoming
	# Build the emscripten-enabled clang toolchain.
	mkdir -p /tmp/emscripten
	cd /tmp/emscripten ; /build/emscripten-fastcomp/configure --enable-optimized --disable-assertions --enable-targets=host,js --prefix=/usr
	cd /tmp/emscripten ; make -j 4
	cd /tmp/emscripten ; make install
	# Workaround for https://github.com/kripken/emscripten/issues/2734
	cd /build/emscripten/src; grep -v "console.log(' ')" postamble.js > postamble.js.new; mv postamble.js.new postamble.js
	cd /build/emscripten/src; grep -v "console.log(' ')" compiler.js > compiler.js.new; mv compiler.js.new compiler.js
	# Symlink emcc into system path.
	ln -s /build/emscripten/emcc /usr/bin/emcc
	# Initialize .emscripten config file.
	emcc --version > /dev/null
	# Remove any of the build and vc data that we no longer need.
	rm -rf /tmp/emscripten
	rm -rf /build/emscripten-fastcomp
	rm -rf /build/emscripten/.git


/usr/local/lib/python2.7/dist-packages/PyV8-1.0_dev-py2.7-linux-x86_64.egg:
	svn checkout http://pyv8.googlecode.com/svn/trunk/ /build/pyv8
	cd /build/pyv8; cat setup.py | sed "s/if os.uname/if False and os.uname/g" > setup.py.new; mv setup.py.new setup.py
	cd /build/pyv8; python setup.py build
	cd /build/pyv8; python setup.py install
	rm -rf /build/pyv8


END_MAKEFILE

# Import it into a base docker image

BASE_IMAGE_ID=`tar -cf - -C $CHROOT_DIR . | docker import -`
rm -rf $CHROOT_DIR

# Use docker to chroot into it and complete the setup.

docker build --no-cache --tag="rfkelly/pypyjs-build" - << END_DOCKERFILE

FROM $BASE_IMAGE_ID

MAINTAINER Ryan Kelly <ryan@rfk.id.au>

ENV LANG C.UTF-8
ENV EM_CACHE /tmp

# Install various (32-bit) build dependencies.

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update -y \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        subversion \
        git-core \
        vim \
        wget \
        libffi-dev \
        libgc-dev \
        libncurses-dev \
        libz-dev \
        python-dev \
        python-setuptools \
        libboost-system-dev \
        libboost-thread-dev \
        libboost-python-dev \
    && apt-get clean

# Build the custom dependencies.

RUN make all

END_DOCKERFILE
