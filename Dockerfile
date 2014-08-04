##########################################################
#                  /!\ WARNING /!\                       #
# This is completely experimental. Use at your own risk. #
#             Also, learn you some docker:               #
#           http://docker.io/gettingstarted              #
##########################################################

FROM debian:7.4
MAINTAINER Ryan Kelly <ryan@rfk.id.au>

ENV LANG C.UTF-8

RUN DEBIAN_FRONTEND=noninteractive apt-get update -y

RUN DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    ca-certificates \
    curl \
    build-essential \
    git-core \
    vim

RUN DEBIAN_FRONTEND=noninteractive apt-get clean

ADD ./ ./pypyjs

WORKDIR ./pypyjs

RUN git submodule update

