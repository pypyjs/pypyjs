#!/usr/bin/env python

try:
    # python 3
    from http.server import SimpleHTTPRequestHandler
    import socketserver
except ImportError:
    # python 2
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    import SocketServer as socketserver


ADDR = "127.0.0.1"
PORT = 8000

httpd = socketserver.TCPServer(
    (ADDR, PORT),
    SimpleHTTPRequestHandler
)

print("\nserving at http://%s:%s" % (ADDR, PORT))
print("(Abort with Ctrl-C)")
httpd.serve_forever()

