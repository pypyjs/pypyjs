from twisted.trial import unittest
import os
from nevow import static, util, context, testutil


def deferredRender(res, req):
    d = util.maybeDeferred(res.renderHTTP,
        context.PageContext(
            tag=res, parent=context.RequestContext(
                tag=req)))

    def done(result):
        if isinstance(result, str):
            req.write(result)
        return req
    d.addCallback(done)
    return d

class Range(unittest.TestCase):
    def setUp(self):
        self.tmpdir = self.mktemp()
        os.mkdir(self.tmpdir)
        name = os.path.join(self.tmpdir, 'junk')
        f = file(name, 'w')
        f.write(800 * '0123456789')
        f.close()
        self.file = static.File(name)
        self.request = testutil.FakeRequest()

    def testBodyLength(self):
        self.request.received_headers['range'] = 'bytes=0-1999'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(len(r.v), 2000))

    def testBodyContent(self):
        self.request.received_headers['range'] = 'bytes=0-1999'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.v, 200 * '0123456789'))

    def testContentLength(self):
        """Content-Length of a request is correct."""
        self.request.received_headers['range'] = 'bytes=0-1999'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers['content-length'], '2000'))

    def testContentRange(self):
        """Content-Range of a request is correct."""
        self.request.received_headers['range'] = 'bytes=0-1999'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers.get('content-range'),
                                        'bytes 0-1999/8000'))

    def testBodyLength_offset(self):
        self.request.received_headers['range'] = 'bytes=3-10'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(len(r.v), 8))

    def testBodyContent_offset(self):
        self.request.received_headers['range'] = 'bytes=3-10'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.v, '34567890'))

    def testContentLength_offset(self):
        """Content-Length of a request is correct."""
        self.request.received_headers['range'] = 'bytes=3-10'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers['content-length'], '8'))

    def testContentRange_offset(self):
        """Content-Range of a request is correct."""
        self.request.received_headers['range'] = 'bytes=3-10'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers.get('content-range'),
                                        'bytes 3-10/8000'))

    def testBodyLength_end(self):
        self.request.received_headers['range'] = 'bytes=7991-7999'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(len(r.v), 9))

    def testBodyContent_end(self):
        self.request.received_headers['range'] = 'bytes=7991-7999'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.v, '123456789'))

    def testContentLength_end(self):
        self.request.received_headers['range'] = 'bytes=7991-7999'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers['content-length'], '9'))

    def testContentRange_end(self):
        self.request.received_headers['range'] = 'bytes=7991-7999'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers.get('content-range'),
                                        'bytes 7991-7999/8000'))

    def testBodyLength_openEnd(self):
        self.request.received_headers['range'] = 'bytes=7991-'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(len(r.v), 9))

    def testBodyContent_openEnd(self):
        self.request.received_headers['range'] = 'bytes=7991-'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.v, '123456789'))

    def testContentLength_openEnd(self):
        self.request.received_headers['range'] = 'bytes=7991-'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers['content-length'], '9'))

    def testContentRange_openEnd(self):
        self.request.received_headers['range'] = 'bytes=7991-'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers.get('content-range'),
                                        'bytes 7991-7999/8000'))

    def testBodyLength_fullRange(self):
        self.request.received_headers['range'] = 'bytes=0-'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(len(r.v), 8000))

    def testBodyContent_fullRange(self):
        self.request.received_headers['range'] = 'bytes=0-'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.v, 800 * '0123456789'))

    def testContentLength_fullRange(self):
        self.request.received_headers['range'] = 'bytes=0-'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers['content-length'], '8000'))

    def testContentRange_fullRange(self):
        self.request.received_headers['range'] = 'bytes=0-'
        return deferredRender(self.file, self.request).addCallback(
            lambda r: self.assertEquals(r.headers.get('content-range'),
                                        'bytes 0-7999/8000'))
