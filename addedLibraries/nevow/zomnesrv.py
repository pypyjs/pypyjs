
import warnings
warnings.warn("nevow.zomnesrv is deprecated.", category=DeprecationWarning)

import time

from nevow import wsgi

from twisted.internet import protocol
from twisted.protocols import basic
from twisted.python import log


IN_KEY = 'STDIN_FILENAME='
IN_KEY_LEN = len(IN_KEY)


class ZomneProtocol(basic.NetstringReceiver):
    def connectionMade(self):
        self.environ = {}

    def stringReceived(self, data):
        key, value = data.split('=', 1)
        self.environ[key] = value
        if data.startswith(IN_KEY):
            filenm = data[IN_KEY_LEN:]
            self.stdin = open(filenm).read()

            # WSGI variables
            self.environ['wsgi.version']      = (1,0)
            self.environ['wsgi.multithread']  = False
            self.environ['wsgi.multiprocess'] = False
            if self.environ.get('HTTPS','off') in ('on','1'):
                self.environ['wsgi.url_scheme'] = 'https'
            else:
                self.environ['wsgi.url_scheme'] = 'http'

            # print "ENV", self.environ
            result = self.factory.application(self.environ, self.start_response)
            for data in result:
                if data:
                    self.write(data)
            ## We got everything, let's render the request
            self.transport.loseConnection()

            self.factory.log('%s - - %s "%s" %d %s "%s" "%s"' % (
                self.environ['REMOTE_ADDR'],
                time.strftime("[%d/%b/%Y:%H:%M:%S +0000]", time.gmtime()),
                '%s %s %s' % (
                    self.environ['REQUEST_METHOD'],
                    self.environ['REQUEST_URI'],
                    self.environ['SERVER_PROTOCOL']),
                self.responseCode,
                self.sentLength or "-",
                self.environ.get('HTTP_REFERER', ''),
                self.environ.get('HTTP_USER_AGENT', '')))

    sentLength = 0
    def write(self, what):
        self.sentLength += len(what)
        self.transport.write(what)

    def start_response(self, status, headers, exc_info=None):
        self.responseCode = int(status.split()[0])
        self.transport.write("Status: %s\r\n" % (status, ))
        for key, value in headers:
            self.transport.write("%s: %s\r\n" % (key, value))
        self.transport.write("\r\n")
        return self.write


class NotificationProtocol(protocol.Protocol):
    def connectionMade(self):
        self.transport.loseConnection()


class NotificationFactory(protocol.ClientFactory):
    protocol = NotificationProtocol


class ZomneFactory(protocol.Factory):
    def __init__(self, root, logfile=None, prefixURL=None):
        """`prefixURL` is used by WSGI apps. wsgi.py stores it in appRootURL.
        It is the HTTP url for the nevow.cgi script"""
        if logfile is not None:
            self.log = open(logfile, 'a')
        if prefixURL:
            self.application = wsgi.createWSGIApplication(root, prefixURL)
        else:
            self.application = wsgi.createWSGIApplication(root)

    protocol = ZomneProtocol

    def startFactory(self):
        """Tell the other end that we are done starting up.
        """
        # Import reactor here to avoid installing default at startup
        from twisted.internet import reactor
        reactor.connectUNIX('zomne_startup_complete.socket', NotificationFactory())

    def log(self, msg):
        log.msg(msg)
