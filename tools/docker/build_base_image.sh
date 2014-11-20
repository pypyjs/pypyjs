#!/bin/bash
#
# Script to build a base 32-bit docker image.
#
# The pypyjs build environment is very particular - it requires a 32-bit
# linux system with several pre-installed libraries and header files.
# This script boostraps a 32-bit debian chroot, and stores it into a docker
# image, to serve as a base for building toolchain images.
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

# Import it into a base docker image

BASE_IMAGE_ID=`tar -cf - -C $CHROOT_DIR . | docker import -`
rm -rf $CHROOT_DIR

# Use docker to chroot into it and do updates etc.

docker build --no-cache --tag="rfkelly/linux32" - << END_DOCKERFILE

FROM $BASE_IMAGE_ID

MAINTAINER Ryan Kelly <ryan@rfk.id.au>

ENV LANG C.UTF-8

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

END_DOCKERFILE
