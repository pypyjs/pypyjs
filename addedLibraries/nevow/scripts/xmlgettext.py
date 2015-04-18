from xml.dom import pulldom
from cStringIO import StringIO
from twisted.python import usage
import nevow

class LineBasedStream(object):
    """
    Allow pulldom to read at most one line at a time, to get accurate
    line number reporting. Otherwise it always reports everything is
    on the last line read in a single chunk.

    Delay reporting newlines to next read, to avoid line numbers
    always being off by one.

    Not the prettiest code I've written :-(
    """
    def __init__(self, stream):
        self.stream = stream
        self.buffer = ''

    def read(self, bufsize):
        if not self.buffer:
            self.buffer = self.stream.readline(bufsize)

        if not self.buffer:
            # eof
            return ''

        data, self.buffer = self.buffer, ''
        while data.endswith('\n'):
            self.buffer = self.buffer + data[-1]
            data = data[:-1]
        if not data:
            # data was nothing but newlines, undo above or it would
            # look like EOF and we'd never make progress
            data, self.buffer = self.buffer, ''
        return data

def getMsgID(node):
    out = StringIO()
    print >>out, 'msgid ""'
    for child in node.childNodes:
        s = child.toxml('utf-8')
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', '\\n')
        print >>out, '"%s"' % s
    print >>out, 'msgstr ""'
    return out.getvalue()

def process(filename, messages):
    f = open(filename, 'rU')
    stream = LineBasedStream(f)
    events = pulldom.parse(stream)

    for (event, node) in events:
        if event == pulldom.START_ELEMENT:
            get = getattr(node, 'getAttributeNS', None)
            if get is not None:
                value = get('http://nevow.com/ns/nevow/0.1', 'render')
                if value == 'i18n':
                    events.expandNode(node)

                    msgid = getMsgID(node)
                    l = messages.setdefault(msgid, [])
                    l.append('#: %s:%d' % (filename, events.parser.getLineNumber()))


def report(messages):
    for msgid, locations in messages.items():
        for line in locations:
            print line
        print msgid

class GettextOptions(usage.Options):
    def opt_version(self):
        print 'Nevow version:', nevow.__version__
        usage.Options.opt_version(self)

    def parseArgs(self, *files):
        self['files'] = files

def runApp(config):
    messages = {}

    for filename in config['files']:
        process(filename, messages)

    report(messages)

def run():
    from twisted.application import app
    app.run(runApp, GettextOptions)
