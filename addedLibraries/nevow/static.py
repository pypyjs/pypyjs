# -*- test-case-name: twisted.test.test_web -*-
# Copyright (c) 2004 Divmod.
# See LICENSE for details.

"""I deal with static resources.
"""

# System Imports
import os, string, time
import cStringIO
import traceback
import warnings
StringIO = cStringIO
del cStringIO
from zope.interface import implements

try:
    from twisted.web.resource import NoResource, ForbiddenResource
except ImportError:
    from twisted.web.error import NoResource, ForbiddenResource
from twisted.web.util import redirectTo

try:
    from twisted.web import http
except ImportError:
    from twisted.protocols import http
from twisted.python import threadable, log, components, filepath
from twisted.internet import abstract
from twisted.spread import pb
from twisted.python.util import InsensitiveDict
from twisted.python.runtime import platformType

from nevow import appserver, dirlist, inevow, rend


dangerousPathError = NoResource("Invalid request URL.")

def isDangerous(path):
    return path == '..' or '/' in path or os.sep in path

class Data:
    """
    This is a static, in-memory resource.
    """
    implements(inevow.IResource)

    def __init__(self, data, type, expires=None):
        self.data = data
        self.type = type
        self.expires = expires


    def time(self):
        """
        Return the current time as a float.

        The default implementation simply uses L{time.time}.  This is mainly
        provided as a hook for tests to override.
        """
        return time.time()


    def locateChild(self, ctx, segments):
        return appserver.NotFound


    def renderHTTP(self, ctx):
        request = inevow.IRequest(ctx)
        request.setHeader("content-type", self.type)
        request.setHeader("content-length", str(len(self.data)))
        if self.expires is not None:
            request.setHeader("expires",
                              http.datetimeToString(self.time() + self.expires))
        if request.method == "HEAD":
            return ''
        return self.data

def staticHTML(someString):
    return Data(someString, 'text/html')


def addSlash(request):
    return "http%s://%s%s/" % (
        request.isSecure() and 's' or '',
        request.getHeader("host"),
        (string.split(request.uri,'?')[0]))

class Registry(components.Componentized):
    """
    I am a Componentized object that will be made available to internal Twisted
    file-based dynamic web content such as .rpy and .epy scripts.
    """

    def __init__(self):
        components.Componentized.__init__(self)
        self._pathCache = {}

    def cachePath(self, path, rsrc):
        self._pathCache[path] = rsrc

    def getCachedPath(self, path):
        return self._pathCache.get(path)


def loadMimeTypes(mimetype_locations=['/etc/mime.types']):
    """
    Multiple file locations containing mime-types can be passed as a list.
    The files will be sourced in that order, overriding mime-types from the
    files sourced beforehand, but only if a new entry explicitly overrides
    the current entry.
    """
    import mimetypes
    # Grab Python's built-in mimetypes dictionary.
    contentTypes = mimetypes.types_map
    # Update Python's semi-erroneous dictionary with a few of the
    # usual suspects.
    contentTypes.update(
        {
            '.conf':  'text/plain',
            '.diff':  'text/plain',
            '.exe':   'application/x-executable',
            '.flac':  'audio/x-flac',
            '.java':  'text/plain',
            '.ogg':   'application/ogg',
            '.oz':    'text/x-oz',
            '.swf':   'application/x-shockwave-flash',
            '.tgz':   'application/x-gtar',
            '.wml':   'text/vnd.wap.wml',
            '.xul':   'application/vnd.mozilla.xul+xml',
            '.py':    'text/plain',
            '.patch': 'text/plain',
            '.pjpeg': 'image/pjpeg',
            '.tac':   'text/x-python',
        }
    )
    # Users can override these mime-types by loading them out configuration
    # files (this defaults to ['/etc/mime.types']).
    for location in mimetype_locations:
        if os.path.exists(location):
            contentTypes.update(mimetypes.read_mime_types(location))
            
    return contentTypes

def getTypeAndEncoding(filename, types, encodings, defaultType):
    p, ext = os.path.splitext(filename)
    ext = ext.lower()
    if encodings.has_key(ext):
        enc = encodings[ext]
        ext = os.path.splitext(p)[1].lower()
    else:
        enc = None
    type = types.get(ext, defaultType)
    return type, enc

class File:
    """
    File is a resource that represents a plain non-interpreted file
    (although it can look for an extension like .rpy or .cgi and hand the
    file to a processor for interpretation if you wish). Its constructor
    takes a file path.

    Alternatively, you can give a directory path to the constructor. In this
    case the resource will represent that directory, and its children will
    be files underneath that directory. This provides access to an entire
    filesystem tree with a single Resource.

    If you map the URL 'http://server/FILE' to a resource created as
    File('/tmp'), then http://server/FILE/ will return an HTML-formatted
    listing of the /tmp/ directory, and http://server/FILE/foo/bar.html will
    return the contents of /tmp/foo/bar.html .
    """

    implements(inevow.IResource)

    contentTypes = loadMimeTypes()

    contentEncodings = {
        ".gz" : "application/x-gzip",
        ".bz2": "application/x-bzip2"
        }

    processors = {}

    indexNames = ["index", "index.html", "index.htm", "index.trp", "index.rpy"]

    type = None

    def __init__(self, path, defaultType="text/html", ignoredExts=(), registry=None, allowExt=0):
        """Create a file with the given path.
        """
        self.fp = filepath.FilePath(path)
        # Remove the dots from the path to split
        self.defaultType = defaultType
        if ignoredExts in (0, 1) or allowExt:
            warnings.warn("ignoredExts should receive a list, not a boolean")
            if ignoredExts or allowExt:
                self.ignoredExts = ['*']
            else:
                self.ignoredExts = []
        else:
            self.ignoredExts = list(ignoredExts)
        self.registry = registry or Registry()
        self.children = {}

    def ignoreExt(self, ext):
        """Ignore the given extension.

        Serve file.ext if file is requested
        """
        self.ignoredExts.append(ext)

    def directoryListing(self):
        return dirlist.DirectoryLister(self.fp.path,
                                       self.listNames(),
                                       self.contentTypes,
                                       self.contentEncodings,
                                       self.defaultType)

    def putChild(self, name, child):
        self.children[name] = child
        
    def locateChild(self, ctx, segments):
        r = self.children.get(segments[0], None)
        if r:
            return r, segments[1:]
        
        path=segments[0]
        
        self.fp.restat()
        
        if not self.fp.isdir():
            return rend.NotFound

        if path:
            fpath = self.fp.child(path)
        else:
            fpath = self.fp.childSearchPreauth(*self.indexNames)
            if fpath is None:
                return self.directoryListing(), segments[1:]

        if not fpath.exists():
            fpath = fpath.siblingExtensionSearch(*self.ignoredExts)
            if fpath is None:
                return rend.NotFound

        # Don't run processors on directories - if someone wants their own
        # customized directory rendering, subclass File instead.
        if fpath.isfile():
            if platformType == "win32":
                # don't want .RPY to be different than .rpy, since that
                # would allow source disclosure.
                processor = InsensitiveDict(self.processors).get(fpath.splitext()[1])
            else:
                processor = self.processors.get(fpath.splitext()[1])
            if processor:
                return (
                    inevow.IResource(processor(fpath.path, self.registry)),
                    segments[1:])

        return self.createSimilarFile(fpath.path), segments[1:]

    # methods to allow subclasses to e.g. decrypt files on the fly:
    def openForReading(self):
        """Open a file and return it."""
        return self.fp.open()

    def getFileSize(self):
        """Return file size."""
        return self.fp.getsize()


    def renderHTTP(self, ctx):
        """You know what you doing."""
        self.fp.restat()

        if self.type is None:
            self.type, self.encoding = getTypeAndEncoding(self.fp.basename(),
                                                          self.contentTypes,
                                                          self.contentEncodings,
                                                          self.defaultType)

        if not self.fp.exists():
            return rend.FourOhFour()

        request = inevow.IRequest(ctx)

        if self.fp.isdir():
            return self.redirect(request)

        # fsize is the full file size
        # size is the length of the part actually transmitted
        fsize = size = self.getFileSize()

        request.setHeader('accept-ranges','bytes')

        if self.type:
            request.setHeader('content-type', self.type)
        if self.encoding:
            request.setHeader('content-encoding', self.encoding)

        try:
            f = self.openForReading()
        except IOError, e:
            import errno
            if e[0] == errno.EACCES:
                return ForbiddenResource().render(request)
            else:
                raise

        if request.setLastModified(self.fp.getmtime()) is http.CACHED:
            return ''

        try:
            range = request.getHeader('range')

            if range is not None:
                # This is a request for partial data...
                bytesrange = string.split(range, '=')
                assert bytesrange[0] == 'bytes',\
                       "Syntactically invalid http range header!"
                start, end = string.split(bytesrange[1],'-')
                if start:
                    f.seek(int(start))
                if end:
                    end = int(end)
                else:
                    end = fsize-1
                request.setResponseCode(http.PARTIAL_CONTENT)
                request.setHeader('content-range',"bytes %s-%s/%s" % (
                    str(start), str(end), str(fsize)))
                #content-length should be the actual size of the stuff we're
                #sending, not the full size of the on-server entity.
                size = 1 + end - int(start)

            request.setHeader('content-length', str(size))
        except:
            traceback.print_exc(file=log.logfile)

        if request.method == 'HEAD':
            return ''

        # return data
        FileTransfer(f, size, request)
        # and make sure the connection doesn't get closed
        return request.deferred

    def redirect(self, request):
        return redirectTo(addSlash(request), request)

    def listNames(self):
        if not self.fp.isdir():
            return []
        directory = self.fp.listdir()
        directory.sort()
        return directory

    def createSimilarFile(self, path):
        f = self.__class__(path, self.defaultType, self.ignoredExts, self.registry)
        # refactoring by steps, here - constructor should almost certainly take these
        f.processors = self.processors
        f.indexNames = self.indexNames[:]
        return f


class FileTransfer(pb.Viewable):
    """
    A class to represent the transfer of a file over the network.
    """
    request = None
    def __init__(self, file, size, request):
        self.file = file
        self.size = size
        self.request = request
        request.registerProducer(self, 0)

    def resumeProducing(self):
        if not self.request:
            return
        data = self.file.read(min(abstract.FileDescriptor.bufferSize, self.size))
        if data:
            self.request.write(data)
            self.size -= len(data)
        if self.size <= 0:
            self.request.unregisterProducer()
            self.request.finish()
            self.request = None

    def pauseProducing(self):
        pass

    def stopProducing(self):
        self.file.close()
        self.request = None

    # Remotely relay producer interface.

    def view_resumeProducing(self, issuer):
        self.resumeProducing()

    def view_pauseProducing(self, issuer):
        self.pauseProducing()

    def view_stopProducing(self, issuer):
        self.stopProducing()


    synchronized = ['resumeProducing', 'stopProducing']

threadable.synchronize(FileTransfer)

"""I contain AsIsProcessor, which serves files 'As Is'
   Inspired by Apache's mod_asis
"""

class ASISProcessor:
    implements(inevow.IResource)
    
    def __init__(self, path, registry=None):
        self.path = path
        self.registry = registry or Registry()

    def renderHTTP(self, ctx):
        request = inevow.IRequest(ctx)
        request.startedWriting = 1
        return File(self.path, registry=self.registry)

    def locateChild(self, ctx, segments):
        return appserver.NotFound
