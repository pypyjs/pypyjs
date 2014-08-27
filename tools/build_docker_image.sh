#!/bin/bash
#
# Script to build a docker image encapsulating pypyjs build environment.
#
# The pypyjs build environment is very particular - it requires a 32bit
# linux system with several pre-installed libraries and header files.
# This script boostraps a 32-bit debian chroot, installs the necessary
# dependencies, and stores the result as a docker image.
#
# Pre-requisites:
#
#    * docker, and a running docker daemon
#    * deboostrap, and run as root so it will work correctly
#

BUILD_DIR=`mktemp -d -t pypyjs-docker-build-XXXXXX`
trap "rm -rf $BUILD_DIR" EXIT

# Ensure that docker is actually running.
docker ps >/dev/null || exit 1;

# Create a bare-bones 32-bit debian chroot.
CHROOT_DIR="$BUILD_DIR/chroot"
debootstrap --arch i386 wheezy $CHROOT_DIR http://http.debian.net/debian/

# It needs a couple of 64-bit libs in it to allow docker to work correctly.
mkdir $CHROOT_DIR/lib64
cp /usr/lib/libpthread.so.0 $CHROOT_DIR/lib64
cp /lib/libc.so.6 $CHROOT_DIR/lib64
cp /lib64/ld-linux-x86-64.so.2 $CHROOT_DIR/lib64

cp -r /home/rfk/repos/pypyjs $CHROOT_DIR/pypyjs

# Import it into a base docker image
BASE_IMAGE_ID=`tar -cf - -C $CHROOT_DIR . | docker import -`
rm -rf $CHROOT_DIR
#BASE_IMAGE_ID="5986cdabf41eb90373f3d43cca0cc5c90264b6d274d5f3ed9741ddc7c2668d32"

# Use docker to chroot into it and complete the setup.
docker build --no-cache - << END_DOCKERFILE

FROM $BASE_IMAGE_ID
MAINTAINER Ryan Kelly <ryan@rfk.id.au>

ENV LANG C.UTF-8

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update -y

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        build-essential \
        subversion \
        git-core \
        git-svn \
        vim \
        python-dev \
        libffi-dev \
        libgc-dev \
        libncurses-dev \
        libz-dev

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get clean

#RUN git clone https://github.com/rfk/pypyjs

WORKDIR ./pypyjs

#RUN git submodule init
#RUN git submodule update

RUN make deps

END_DOCKERFILE

# The resulting image should be the most recently-built one.
IMAGE_ID=`docker images -q | head -n 1`

# Flatten it into a standalone image for distribution.
# XXX TODO: this seems to throw away overlays etc, but is it really necessary?
echo "IMAGE: $IMAGE_ID"
