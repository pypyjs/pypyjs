##########################################################
#                  /!\ WARNING /!\                       #
# This is completely experimental. Use at your own risk. #
#             Also, learn you some docker:               #
#           http://docker.io/gettingstarted              #
##########################################################

FROM debian:7.4
MAINTAINER Ryan Kelly <ryan@rfk.id.au>

ENV LANG C.UTF-8

RUN dpkg --add-architecture i386

RUN DEBIAN_FRONTEND=noninteractive apt-get update -y

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    curl \
    build-essential \
    git-core \
    vim \
    wget \
    multiarch-support

RUN dpkg --add-architecture i386

RUN DEBIAN_FRONTEND=noninteractive apt-get update -y

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
    gcc-multilib \
    g++-multilib \
    libc6-dev-i386 \
    libffi-dev:i386 \
    libgc-dev:i386

RUN DEBIAN_FRONTEND=noninteractive apt-get clean

ADD ./ ./pypyjs

WORKDIR ./pypyjs

RUN git submodule init
RUN git submodule update

RUN make deps

