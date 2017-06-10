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
#    * a basic linux-like environment shell environment
#

set -e
set -u

BUILD_DIR=`mktemp -d -t pypyjs-docker-build-XXXXXX`
trap "rm -rf $BUILD_DIR" EXIT

# Ensure that docker is actually running.

docker ps >/dev/null

# Use the default debian docker image, to create a bare-bones 32-bit debian chroot.
# It needs a couple of 64-bit libs in it to allow docker to work correctly.

echo "Building 32-bit chroot..."

docker run --privileged -i --rm -v /tmp:/tmp debian:stable-slim > $BUILD_DIR/chroot.tar.gz sh << END_BUILD_SCRIPT

apt-get update >&2 && \
apt-get install -y debootstrap >&2 && \
debootstrap --arch i386 stable /my-chroot http://deb.debian.org/debian/ >&2 && \
mkdir /my-chroot/lib64 && \
cp /lib/x86_64-linux-gnu/libpthread.so.0 /my-chroot/lib64 && \
cp /lib/x86_64-linux-gnu/libc.so.6 /my-chroot/lib64 && \
cp /lib64/ld-linux-x86-64.so.2 /my-chroot/lib64 && \
tar -cz -C /my-chroot . | cat

END_BUILD_SCRIPT

# Import the chroot into a base docker image

echo "Convering to docker image..."

BASE_IMAGE_ID=`gunzip -c $BUILD_DIR/chroot.tar.gz | docker import -`
rm -rf $BUILD_DIR/chroot.tar.gz

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
        vim \
        wget \
    && apt-get clean

END_DOCKERFILE
