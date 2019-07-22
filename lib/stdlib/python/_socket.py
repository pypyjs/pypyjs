from __future__ import unicode_literals
AF_APPLETALK = AF_ASH = AF_ATMPVC = AF_ATMSVC = AF_AX25 = AF_BLUETOOTH = AF_BRIDGE = AF_ECONET = AF_INET = AF_INET6 = AF_IPX = AF_IRDA = AF_KEY = AF_LLC = AF_NETBEUI = AF_NETLINK = AF_NETROM = AF_PACKET = AF_PPPOX = AF_ROSE = AF_ROUTE = AF_SECURITY = AF_SNA = AF_UNIX = AF_UNSPEC = AF_WANPIPE = AF_X25 = AI_ADDRCONFIG = AI_ALL = AI_CANONNAME = AI_NUMERICHOST = AI_NUMERICSERV = AI_PASSIVE = AI_V4MAPPED = BDADDR_ANY = BDADDR_LOCAL = EAI_ADDRFAMILY = EAI_AGAIN = EAI_BADFLAGS = EAI_FAIL = EAI_FAMILY = EAI_MEMORY = EAI_NODATA = EAI_NONAME = EAI_OVERFLOW = EAI_SERVICE = EAI_SOCKTYPE = EAI_SYSTEM = FD_SETSIZE = INADDR_ALLHOSTS_GROUP = INADDR_ANY = INADDR_BROADCAST = INADDR_LOOPBACK = INADDR_MAX_LOCAL_GROUP = INADDR_NONE = INADDR_UNSPEC_GROUP = IPPORT_RESERVED = IPPORT_USERRESERVED = IPPROTO_AH = IPPROTO_DSTOPTS = IPPROTO_EGP = IPPROTO_ESP = IPPROTO_FRAGMENT = IPPROTO_GRE = IPPROTO_HOPOPTS = IPPROTO_ICMP = IPPROTO_ICMPV6 = IPPROTO_IDP = IPPROTO_IGMP = IPPROTO_IP = IPPROTO_IPIP = IPPROTO_IPV6 = IPPROTO_NONE = IPPROTO_PIM = IPPROTO_PUP = IPPROTO_RAW = IPPROTO_ROUTING = IPPROTO_RSVP = IPPROTO_TCP = IPPROTO_TP = IPPROTO_UDP = IPV6_CHECKSUM = IPV6_DSTOPTS = IPV6_HOPLIMIT = IPV6_HOPOPTS = IPV6_JOIN_GROUP = IPV6_LEAVE_GROUP = IPV6_MULTICAST_HOPS = IPV6_MULTICAST_IF = IPV6_MULTICAST_LOOP = IPV6_NEXTHOP = IPV6_PKTINFO = IPV6_RECVDSTOPTS = IPV6_RECVHOPLIMIT = IPV6_RECVHOPOPTS = IPV6_RECVPKTINFO = IPV6_RECVRTHDR = IPV6_RECVTCLASS = IPV6_RTHDR = IPV6_RTHDRDSTOPTS = IPV6_RTHDR_TYPE_0 = IPV6_TCLASS = IPV6_UNICAST_HOPS = IPV6_V6ONLY = IP_ADD_MEMBERSHIP = IP_DEFAULT_MULTICAST_LOOP = IP_DEFAULT_MULTICAST_TTL = IP_DROP_MEMBERSHIP = IP_HDRINCL = IP_MAX_MEMBERSHIPS = IP_MULTICAST_IF = IP_MULTICAST_LOOP = IP_MULTICAST_TTL = IP_OPTIONS = IP_RECVOPTS = IP_RECVRETOPTS = IP_RETOPTS = IP_TOS = IP_TTL = MSG_CTRUNC = MSG_DONTROUTE = MSG_DONTWAIT = MSG_EOR = MSG_OOB = MSG_PEEK = MSG_TRUNC = MSG_WAITALL = NETLINK_DNRTMSG = NETLINK_FIREWALL = NETLINK_IP6_FW = NETLINK_NFLOG = NETLINK_ROUTE = NETLINK_USERSOCK = NETLINK_XFRM = NI_DGRAM = NI_MAXHOST = NI_MAXSERV = NI_NAMEREQD = NI_NOFQDN = NI_NUMERICHOST = NI_NUMERICSERV = PACKET_BROADCAST = PACKET_FASTROUTE = PACKET_HOST = PACKET_LOOPBACK = PACKET_MULTICAST = PACKET_OTHERHOST = PACKET_OUTGOING = POLLERR = POLLHUP = POLLIN = POLLMSG = POLLNVAL = POLLOUT = POLLPRI = POLLRDBAND = POLLRDNORM = POLLWRNORM = SHUT_RD = SHUT_RDWR = SHUT_WR = SIOCGIFINDEX = SIOCGIFNAME = SOCK_DGRAM = SOCK_RAW = SOCK_RDM = SOCK_SEQPACKET = SOCK_STREAM = SOL_IP = SOL_SOCKET = SOL_TCP = SOL_UDP = SOMAXCONN = SO_ACCEPTCONN = SO_BROADCAST = SO_DEBUG = SO_DONTROUTE = SO_ERROR = SO_KEEPALIVE = SO_LINGER = SO_OOBINLINE = SO_RCVBUF = SO_RCVLOWAT = SO_RCVTIMEO = SO_REUSEADDR = SO_REUSEPORT = SO_SNDBUF = SO_SNDLOWAT = SO_SNDTIMEO = SO_TYPE = 1

SocketType = TCP_CORK = TCP_DEFER_ACCEPT = TCP_INFO = TCP_KEEPCNT = TCP_KEEPIDLE = TCP_KEEPINTVL = TCP_LINGER2 = TCP_MAXSEG = TCP_NODELAY = TCP_QUICKACK = TCP_SYNCNT = TCP_WINDOW_CLAMP = error = fromfd = gaierror = getaddrinfo = getdefaulttimeout = gethostbyaddr = gethostbyname = gethostbyname_ex = gethostname = getnameinfo = getprotobyname = getservbyname = getservbyport = has_ipv6 = herror = htonl = htons = inet_aton = inet_ntoa = inet_ntop = inet_pton = ntohl = ntohs = setdefaulttimeout = socket = socketpair = timeout = None

import js
import os
import StringIO
import time



sockets=os.fileNumbers
class error(Exception): pass


class _fileobject(file):
    def __init__(self, sock):
        self._sock=sock
    def read(self, length):
        return self._sock.recv(length)
    def write(self, msg):
        return self._sock.send(msg)
    def pullFromJS(self):
        return self._sock.pullFromJS()

class _socket(object):
    '''socket implementation using websockets'''
    def __init__(self, *_):
        self._fileno=len(sockets)
        os.fileNumbers.append(self.makefile())
        self.timeout=None
        self.closed=False
    @property
    def ready(self):
        return hasattr(self, '_sock') and self._sock.ready
    def fileno(self):
        return self._fileno
    def accept(self):
        raise Exception("sockets in server mode not yet implemented")
    def bind(self, (address, port)):
        raise Exception("Bind not supported")
    def listen(self):
        raise Exception("Listen not supported")
    def close(self, *_):
        self._sock.close()
        self.closed=True
    def connect(self, arg):
        self._stringIO = StringIO.StringIO()
        if isinstance(arg, (str, unicode)):
            self.connection_info=arg.split(':')
            self._sock = js.globals['socketConnect'](arg)
        else:
            address,port=arg
            self.connection_info=address,port
            self._sock = js.globals['socketConnect']("ws://" + address + ':' + str(port))
        def onmsg(msg):
            self._stringIO.write(msg)
        self.onmsgHandler=js.Function(onmsg),onmsg
        self._sock.onrecv=self.onmsgHandler[0]
    def settimeout(self, t):
        self.timeout=t
    def setsockopt(self, *a):
        pass
    def getsockopt(self, *a):
        return 0
    def gettimeout(self):
        return self.timeout
    def makefile(self):
        return _fileobject(self)
    proto=0
    def pullFromJS(self):
        #while self._sock.queue.length:
        #    self._stringIO.write(self._sock.queue.shift());
        return len(self._stringIO.getvalue())
    def recv(self, length, *_):
        self.pullFromJS()
        if self.timeout is None:
            while True:
                r = self._stringIO.getvalue()
                self._stringIO.buf=r[length:]
                r=r[:length]
                if r:
                    return r
                time.sleep(0.1)
        else:
            r = self._stringIO.getvalue()
            self._stringIO.buf=r[length:]
            r=r[:length]
            if r:
                return r
            time.sleep(self.timeout)
            r = self._stringIO.getvalue()
            self._stringIO.buf=r[length:]
            r=r[:length]
            if r:
                return r
        raise error('Timed out')
    def send(self, msg, *a):
        self._sock.send(str(msg))
        return len(msg)
    def recv_into(self, buff):
        buff.write(self.recv(1024))
    def recvfrom(self, num):
        return self.recv(num), 'server'
    def recvfrom_into(self, buff):
        return self.recv_into(num), 'server'
    def sendto(self, data, flags, address):
        raise Exception("not implemented")
    def connect_ex(self, addr):
        return self.connect(addr)
    def getpeername(self):
        return self.connection_info
    def getsockname(self):
        return '127.0.0.1',0
    def sendall(self, data):
        self.send(data)
    def setblocking(self, v):
        self.blocking=v
    def shutdown(self, side):
        self.close()
    def _drop(self, *_):
        self.close()

def getservbyname(a,b):
    return a

socket=_socket
