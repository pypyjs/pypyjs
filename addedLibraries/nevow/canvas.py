# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from zope.interface import implements

from twisted.internet import defer
from twisted.python import log

from nevow import inevow, rend, loaders, static, url, tags, util
from nevow.flat import flatten
from nevow.stan import Proto, Tag
from itertools import count

cn = count().next
cookie = lambda: str(cn())

_hookup = {}

## If we need to use Canvas through a CGI which forwards to the appserver,
## then we will need to listen with the canvas protocol on another socket
## so the canvas movie can push data to us. Here is where we will keep it.
_canvasCGIService = None

# m = method
# a = argument
# <m n="moveTo" t="canvas">
#   <a v="16" />
#   <a v="16" />
# </m>


m = Proto('m') # method call; contains arguments
a = Proto('a') # argument; has v="" attribute for simple value, or <l> or <d> child for list or dict value
l = Proto('l') # list; has <a> children; <a> children must be simple values currently
d = Proto('d') # dict; has <i> children
i = Proto('i') # dict item; has k="" for key and v="" for simple value (no nested dicts yet)


def squish(it):
    if isinstance(it, Tag):
        return a[it]
    return a(v=it)


class _Remoted(object):
    def __init__(self, cookie, canvas):
        self.cookie = cookie
        self.canvas = canvas


class Text(_Remoted):
    x = 0
    y = 0
    def change(self, text):
        self.text = text
        self.canvas.call('changeText', self.cookie, text)

    def move(self, x, y):
        self.x = x
        self.y = y
        self.canvas.call('moveText', self.cookie, x, y)

    def listFonts(self):
        if hasattr(self.canvas, '_fontList'):
            return defer.succeed(self.canvas._fontList)
        cook = cookie()
        self.canvas.deferreds[cook] = d = defer.Deferred()
        self.canvas.call('listFonts', cook)
        def _cb(l):
            L = l.split(',')
            self.canvas._fontList = L
            return L
        return d.addCallback(_cb)

    def font(self, font):
        self.canvas.call('font', self.cookie, font)

    def size(self, size):
        self.canvas.call('size', self.cookie, size)


class Image(_Remoted):
    def move(self, x, y):
        self.canvas.call('moveImage', self.cookie, x, y)

    def scale(self, x, y):
        self.canvas.call('scaleImage', self.cookie, x, y)

    def alpha(self, alpha):
        self.canvas.call('alphaImage', self.cookie, alpha)

    def rotate(self, angle):
        self.canvas.call('rotateImage', self.cookie, angle)


class Sound(_Remoted):
    def play(self, offset=0, timesLoop=0):
        """Play the sound, starting at "offset", in seconds. Loop the sound "timesLoop"
        times.
        """
        self.canvas.call('playSound', self.cookie, offset, timesLoop)


class GroupBase(object):
    def call(self, method, *args):
        """Call a client-side method with the given arguments. Arguments
        will be converted to strings. You should probably use the other higher-level
        apis instead.
        """
        flatcall = flatten(
            m(n=method, t=self.groupName)[[
                squish(x) for x in args if x is not None]])
        self.socket.write(flatcall + '\0')

    groupx = 0
    groupy = 0
    def reposition(self, x, y):
        """Reposition all the elements in this group
        """
        self.groupx = x
        self.groupy = y
        self.call('reposition', x, y)

    def rotate(self, angle):
        """Rotate all the elements of this group
        """
        self.call('rotate', angle)

    _alpha = 100
    def alpha(self, percent):
        """Set the alpha value of this group
        """
        self._alpha = percent
        self.call('alpha', percent)

    def line(self, x, y):
        """Draw a line from the current point to the given point.

        (0,0) is in the center of the canvas.
        """
        self.call('line', x, y)

    x = 0
    y = 0
    def move(self, x, y):
        """Move the pen to the given point.
    
        (0, 0) is in the center of the canvas.
        """
        self.x = x
        self.y = y
        self.call('move', x, y)

    def pen(self, width=None, rgb=None, alpha=None):
        """Change the current pen attributes. 

        width: an integer between 0 and 255; the pen thickness, in pixels.
        rgb: an integer between 0x000000 and 0xffffff
        alpha: an integer between 0 and 100; the opacity of the pen
        """
        self.call('pen', width, rgb, alpha)

    def clear(self):
        """Clear the current pen attributes.
        """
        self.call('clear')

    def fill(self, rgb, alpha=100):
        """Set the current fill. Fill will not be drawn until close is called.
        
        rgb: color of fill, integer between 0x000000 and 0xffffff
        alpha: an integer between 0 and 100; the opacity of the fill
        """
        self.call('fill', rgb, alpha)

    def close(self):
        """Close the current shape. A line will be drawn from the end point
        to the start point, and the shape will be filled with the current fill.
        """
        self.call('close')

    def curve(self, controlX, controlY, anchorX, anchorY):
        """Draw a curve
        """
        self.call('curve', controlX, controlY, anchorX, anchorY)

    def gradient(self, type, colors, alphas, ratios, matrix):
        """Draw a gradient. Currently the API for this sucks, see the flash documentation
        for info. Higher level objects for creating gradients will hopefully be developed
        eventually.
        """
        self.call('gradient', type,
            l[[a(v=x) for x in colors]],
            l[[a(v=x) for x in alphas]],
            l[[a(v=x) for x in ratios]],
            d[[i(k=k, v=v) for (k, v) in matrix.items()]])

    def text(self, text, x, y, height, width):
        """Place the given text on the canvas using the given x, y, height and width.
        The result is a Text object which can be further manipulated to affect the text.
        """
        cook = cookie()
        t = Text(cook, self)
        t.text = text
        self.call('text', cook, text, x, y, height, width)
        return t

    def image(self, where):
        """Load an image from the URL "where". The result is an Image object which
        can be further manipulated to move it or change rotation.
        """
        cook = cookie()
        I = Image(cook, self)
        self.call('image', cook, where)
        print "IMAGE", where
        return I

    def sound(self, where, stream=True):
        """Load an mp3 from the URL "where". The result is a Sound object which
        can be further manipulated.

        If stream is True, the sound will play as soon as possible. If false, 
        """
        cook = cookie()
        S = Sound(cook, self)
        self.call('sound', cook, where, stream and 1 or 0)
        return S

    def group(self):
        """Create a new group of shapes. The returned object will
        have all of the same APIs for drawing, except the grouped
        items can all be moved simultaneously, deleted, etc.
        """
        cook = cookie()
        G = Group('%s.G_%s' % (self.groupName, cook), self.socket, self)
        self.call('group', cook)
        return G


class Group(GroupBase):
    def __init__(self, groupName, socket, canvas):
        self.groupName = groupName
        self.socket = socket
        self.canvas = canvas
        self.deferreds = canvas.deferreds

    closed = property(lambda self: self.canvas.closed)

    def setMask(self, other=None):
        """Set the mask of self to the group "other". "other" must be a Group
        instance, if provided. If not provided, any previous mask will be removed
        from self.
        """
        if other is None:
            self.call('setMask', '')
        else:
            self.call('setMask', other.groupName)

    def setVisible(self, visible):
        self.call('setVisible', str(bool(visible)))

    xscale = 100
    yscale = 100
    def scale(self, x, y):
        self.call('scale', x, y)

    def swapDepth(self, intOrGroup):
        """Swap the z-order depth of this group with another.
        If an int is provided, the group will be placed at that depth,
        regardless of whether there is an existing clip there.
        If a group is provided, the z depth of self and the other group
        are swapped.
        """
        if isinstance(intOrGroup, Group):
            self.call('swapGroup', intOrGroup.groupName)
        else:
            self.call('swapInt', intOrGroup)

    def depth(self):
        """Return a deferred which will fire the depth of this group.
        XXX TODO
        """
        return 0


class CanvasSocket(GroupBase):
    """An object which represents the client-side canvas. Defines APIs for drawing
    on the canvas. An instance of this class will be passed to your onload callback.
    """
    implements(inevow.IResource)

    groupName = 'canvas'

    closed = False
    def __init__(self):
        self.canvas = self
        self.d = defer.Deferred().addErrback(log.err)

    def locateChild(self, ctx, segs):
        self.cookie = segs[0]
        return (self, ())

    def renderHTTP(self, ctx):
        try:
            self.deferreds = {}
            self.buffer = ''
            ## Don't try this at home kids! You'll blow your arm off!
            self.socket = inevow.IRequest(ctx).transport
            ## We be hijackin'
            self.socket.protocol = self
            ## This request never finishes until the user leaves the page
            self.delegate = _hookup[self.cookie]
            self.delegate.onload(self)
            del _hookup[self.cookie]
        except:
            log.err()
        return self.d

    def dataReceived(self, data):
        self.buffer += data
        while '\0' in self.buffer:
            I = self.buffer.index('\0')
            message = self.buffer[:I]
            self.buffer = self.buffer[I+1:]
            self.gotMessage(message)

    def gotMessage(self, message):
        I = message.index(' ')
        handler = getattr(self, 'handle_%s' % (message[:I], ), None)
        if handler is not None:
            handler(message[I+1:])
        else:
            self.deferreds[message[:I]].callback(message[I+1:])
            del self.deferreds[message[:I]]

    def connectionLost(self, reason):
        self.closed = True
        del self.socket

    def done(self):
        """Done drawing; close the connection with the movie
        """
        ## All done with the request object
        self.closed = True
        self.d.callback('')

    def handle_onKeyDown(self, info):
        if self.delegate.onKeyDown:
            self.delegate.onKeyDown(self, chr(int(info)))

    def handle_onKeyUp(self, info):
        if self.delegate.onKeyUp:
            self.delegate.onKeyUp(self, chr(int(info)))

    def handle_onMouseUp(self, info):
        if self.delegate.onMouseUp:
            self.delegate.onMouseUp(self, *map(int, map(float, info.split())))

    def handle_onMouseDown(self, info):
        if self.delegate.onMouseDown:
            self.delegate.onMouseDown(self, *map(int, map(float, info.split())))

    def handle_onMouseMove(self, info):
        if self.delegate.onMouseMove:
            self.delegate.onMouseMove(self, *map(int, map(float, info.split())))

    def handle_diagnostic(self, info):
        print "Trace", info

canvasServerMessage = loaders.stan(tags.html["This server dispatches for nevow canvas events."])


def canvas(width, height, delegate, useCGI=False):
    C = cookie()
    if useCGI:
        global _canvasCGIService
        if _canvasCGIService is None:
            from nevow import appserver
            # Import reactor here to avoid installing default at startup
            from twisted.internet import reactor
            _canvasCGIService = reactor.listenTCP(0, appserver.NevowSite(Canvas(docFactory=canvasServerMessage)))
            _canvasCGIService.dispatchMap = {}
        port = _canvasCGIService.getHost().port
        prefix = '/'
        movie_url = url.here.click('/').secure(False, port)
    else:
        movie_url = url.here
        port = lambda c, d: inevow.IRequest(c).transport.server.port
        def prefix(c, d):
            pre = inevow.IRequest(c).path
            if pre.endswith('/'):
                return pre
            return pre + '/'

    _hookup[C] = delegate
    handlerInfo = []
    for handlerName in ['onMouseMove', 'onMouseDown', 'onMouseUp', 'onKeyDown', 'onKeyUp']:
        if getattr(delegate, handlerName, None) is not None:
            handlerInfo.append((handlerName, 1))

    movie_url = movie_url.child('nevow_canvas_movie.swf').add('cookie', C).add('port', port).add('prefix', prefix)
    for (k, v) in handlerInfo:
        movie_url = movie_url.add(k, v)

    return tags._object(classid="clsid:d27cdb6e-ae6d-11cf-96b8-444553540000",
        codebase="http://download.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=7,0,0,0",
        width=width, height=height, id=("Canvas-", C), align="middle")[
        tags.param(name="allowScriptAccess", value="sameDomain"),
        tags.param(name="movie", value=movie_url),
        tags.param(name="quality", value="high"),
        tags.param(name="scale", value="noscale"),
        tags.param(name="bgcolor", value="#ffffff"),
        Tag('embed')(
            src=movie_url,
            quality="high",
            scale="noscale",
            bgcolor="#ffffff",
            width=width,
            height=height,
            name=("Canvas-", C),
            align="middle",
            allowScriptAccess="sameDomain",
            type="application/x-shockwave-flash",
            pluginspage="http://www.macromedia.com/go/getflashplayer")]


class Canvas(rend.Page):
    """A page which can embed canvases. Simplest usage is to subclass and
    override width, height and onload. Then, putting render_canvas in the
    template will output that canvas there.
    
    You can also embed more than one canvas in a page using the canvas
    helper function, canvas(width, height, onload). The resulting stan
    will cause a canvas of the given height and width to be embedded in
    the page at that location, and the given onload callable to be called
    with a CanvasSocket when the connection is established.
    """
    addSlash = True
    def __init__(self, original=None, width=None, height=None, onload=None, 
    onMouseMove=None, onMouseDown=None, onMouseUp=None, 
    onKeyDown=None, onKeyUp=None, **kw):
        rend.Page.__init__(self, original, **kw)
        if width: self.width = width
        if height: self.height = height
        if onload: self.onload = onload
        if onMouseMove: self.onMouseMove = onMouseMove
        if onMouseDown: self.onMouseDown = onMouseDown
        if onMouseUp: self.onMouseUp = onMouseUp
        if onKeyDown: self.onKeyDown = onKeyDown
        if onKeyUp: self.onKeyUp = onKeyUp

    def child_canvas_socket(self, ctx):
        return CanvasSocket()

    width = 1000
    height = 500

    onload = None
    onMouseDown = None
    onMouseUp = None
    onMouseMove = None
    onKeyUp = None
    onKeyDown = None

    def render_canvas(self, ctx, data):
        return canvas(
            self.width, self.height, self)

    docFactory = loaders.stan(tags.html[render_canvas])

setattr(Canvas, 'child_nevow_canvas_movie.swf', static.File(
    util.resource_filename('nevow', 'Canvas.swf'),
    'application/x-shockwave-flash'))

