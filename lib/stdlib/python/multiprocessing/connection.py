#
# A higher level module for using sockets (or Windows named pipes)
#
# multiprocessing/connection.py
#
# Copyright (c) 2006-2008, R Oudkerk
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of author nor the names of any contributors may be
#    used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#

__all__ = [ 'Client', 'Listener', 'Pipe' ]

import os
import sys
import socket
import errno
import time
import tempfile
import itertools


from multiprocessing import current_process, AuthenticationError
from multiprocessing.util import get_temp_dir, Finalize, sub_debug, debug
from multiprocessing.forking import duplicate, close

class ConnectionException(Exception):
    pass
#
#
#

BUFSIZE = 8192
# A very generous timeout when it comes to local connections...
CONNECTION_TIMEOUT = 20.

_mmap_counter = itertools.count()

default_family = 'AF_INET'
families = ['AF_INET']

if hasattr(socket, 'AF_UNIX'):
    default_family = 'AF_UNIX'
    families += ['AF_UNIX']



def _init_timeout(timeout=CONNECTION_TIMEOUT):
    return time.time() + timeout

def _check_timeout(t):
    return time.time() > t

#
#
#

def arbitrary_address(family):
    '''
    Return an arbitrary free address for the given family
    '''
    if family == 'AF_INET':
        return ('localhost', 0)
    elif family == 'AF_UNIX':
        return tempfile.mktemp(prefix='listener-', dir=get_temp_dir())
    elif family == 'AF_PIPE':
        return tempfile.mktemp(prefix=r'\\.\pipe\pyc-%d-%d-' %
                               (os.getpid(), _mmap_counter.next()), dir="")
    else:
        raise ValueError('unrecognized family')


def address_type(address):
    '''
    Return the types of the address

    This can be 'AF_INET', 'AF_UNIX', or 'AF_PIPE'
    '''
    if type(address) == tuple:
        return 'AF_INET'
    elif type(address) is str and address.startswith('\\\\'):
        return 'AF_PIPE'
    elif type(address) is str:
        return 'AF_UNIX'
    else:
        raise ValueError('address type of %r unrecognized' % address)

#
# Public functions
#

class Listener(object):
    '''
    Returns a listener object.

    This is a wrapper for a bound socket which is 'listening' for
    connections, or for a Windows named pipe.
    '''
    def __init__(self, address=None, family=None, backlog=1, authkey=None):
        family = family or (address and address_type(address)) \
                 or default_family
        address = address or arbitrary_address(family)

        if family == 'AF_PIPE':
            self._listener = PipeListener(address, backlog)
        else:
            self._listener = SocketListener(address, family, backlog)

        if authkey is not None and not isinstance(authkey, bytes):
            raise TypeError, 'authkey should be a byte string'

        self._authkey = authkey

    def accept(self):
        '''
        Accept a connection on the bound socket or named pipe of `self`.

        Returns a `Connection` object.
        '''
        c = self._listener.accept()
        if self._authkey:
            deliver_challenge(c, self._authkey)
            answer_challenge(c, self._authkey)
        return c

    def close(self):
        '''
        Close the bound socket or named pipe of `self`.
        '''
        return self._listener.close()

    address = property(lambda self: self._listener._address)
    last_accepted = property(lambda self: self._listener._last_accepted)


def Client(address, family=None, authkey=None):
    '''
    Returns a connection to the address of a `Listener`
    '''
    family = family or address_type(address)
    if family == 'AF_PIPE':
        c = PipeClient(address)
    else:
        c = SocketClient(address)

    if authkey is not None and not isinstance(authkey, bytes):
        raise TypeError, 'authkey should be a byte string'

    if authkey is not None:
        answer_challenge(c, authkey)
        deliver_challenge(c, authkey)

    return c





if sys.platform != 'win32':

    def Pipe(duplex=True, buffer_id=None):
        import _multiprocessing
        '''
        Returns pair of connection objects at either end of a pipe
        '''
        if duplex:
            raise ConnectionException('can\'t do duplex')
        fd1, fd2 = os.pipe(buffer_id)
        c1 = _multiprocessing.Connection(fd1, writeable=False)
        c2 = _multiprocessing.Connection(fd2, readable=False)

        return c1, c2


#
# Definitions for connections based on sockets
#

class SocketListener(object):
    '''
    Representation of a socket which is bound to an address and listening
    '''
    def __init__(self, address, family, backlog=1):
        self._socket = socket.socket(getattr(socket, family))
        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setblocking(True)
            self._socket.bind(address)
            self._socket.listen(backlog)
            self._address = self._socket.getsockname()
        except socket.error:
            self._socket.close()
            raise
        self._family = family
        self._last_accepted = None

        if family == 'AF_UNIX':
            self._unlink = Finalize(
                self, os.unlink, args=(address,), exitpriority=0
                )
        else:
            self._unlink = None

    def accept(self):
        import _multiprocessing
        while True:
            try:
                s, self._last_accepted = self._socket.accept()
            except socket.error as e:
                if e.args[0] != errno.EINTR:
                    raise
            else:
                break
        s.setblocking(True)
        fd = duplicate(s.fileno())
        conn = _multiprocessing.Connection(fd)
        s.close()
        return conn

    def close(self):
        self._socket.close()
        if self._unlink is not None:
            self._unlink()


def SocketClient(address):
    '''
    Return a connection object connected to the socket given by `address`
    '''
    import _multiprocessing
    family = getattr(socket, address_type(address))
    t = _init_timeout()

    while 1:
        s = socket.socket(family)
        s.setblocking(True)
        try:
            s.connect(address)
        except socket.error, e:
            s.close()
            if e.args[0] != errno.ECONNREFUSED or _check_timeout(t):
                debug('failed to connect to address %s', address)
                raise
            time.sleep(0.01)
        else:
            break
    else:
        raise

    fd = duplicate(s.fileno())
    conn = _multiprocessing.Connection(fd)
    s.close()
    return conn

#
# Definitions for connections based on named pipes
#
#
# Authentication stuff
#

MESSAGE_LENGTH = 20

CHALLENGE = b'#CHALLENGE#'
WELCOME = b'#WELCOME#'
FAILURE = b'#FAILURE#'

def deliver_challenge(connection, authkey):
    import hmac
    assert isinstance(authkey, bytes)
    message = os.urandom(MESSAGE_LENGTH)
    connection.send_bytes(CHALLENGE + message)
    digest = hmac.new(authkey, message).digest()
    response = connection.recv_bytes(256)        # reject large message
    if response == digest:
        connection.send_bytes(WELCOME)
    else:
        connection.send_bytes(FAILURE)
        raise AuthenticationError('digest received was wrong')

def answer_challenge(connection, authkey):
    import hmac
    assert isinstance(authkey, bytes)
    message = connection.recv_bytes(256)         # reject large message
    assert message[:len(CHALLENGE)] == CHALLENGE, 'message = %r' % message
    message = message[len(CHALLENGE):]
    digest = hmac.new(authkey, message).digest()
    connection.send_bytes(digest)
    response = connection.recv_bytes(256)        # reject large message
    if response != WELCOME:
        raise AuthenticationError('digest sent was rejected')

#
# Support for using xmlrpclib for serialization
#

class ConnectionWrapper(object):
    def __init__(self, conn, dumps, loads):
        self._conn = conn
        self._dumps = dumps
        self._loads = loads
        for attr in ('fileno', 'close', 'poll', 'recv_bytes', 'send_bytes'):
            obj = getattr(conn, attr)
            setattr(self, attr, obj)
    def send(self, obj):
        s = self._dumps(obj)
        self._conn.send_bytes(s)
    def recv(self):
        s = self._conn.recv_bytes()
        return self._loads(s)

def _xml_dumps(obj):
    return xmlrpclib.dumps((obj,), None, None, None, 1).encode('utf8')

def _xml_loads(s):
    (obj,), method = xmlrpclib.loads(s.decode('utf8'))
    return obj

class XmlListener(Listener):
    def accept(self):
        global xmlrpclib
        import xmlrpclib
        obj = Listener.accept(self)
        return ConnectionWrapper(obj, _xml_dumps, _xml_loads)

def XmlClient(*args, **kwds):
    global xmlrpclib
    import xmlrpclib
    return ConnectionWrapper(Client(*args, **kwds), _xml_dumps, _xml_loads)
