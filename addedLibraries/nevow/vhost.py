# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from twisted.python import log
from zope.interface import implements
from nevow import loaders, rend, inevow
from nevow.stan import directive
from nevow import tags

class VirtualHostList(rend.Page):
    def __init__(self, nvh):
        rend.Page.__init__(self)
        self.nvh = nvh

    stylesheet = """
    body { border: 0; padding: 0; margin: 0; background-color: #efefef; }
    h1 {padding: 0.1em; background-color: #777; color: white; border-bottom: thin white dashed;}
"""

    def getStyleSheet(self):
        return self.stylesheet
 
    def data_hostlist(self, context, data):
        return self.nvh.hosts.keys()

    def render_hostlist(self, context, data):
        host=data
        req = context.locate(inevow.IRequest)
        proto = req.clientproto.split('/')[0].lower()
        port = req.getHeader('host').split(':')[1]

        link = "%s://%s" % (proto, host)

        if port != 80:
            link += ":%s" % port

        link += req.path

        return context.tag[tags.a(href=link)[ host ]]
 
    def render_title(self, context, data):
        req = context.locate(inevow.IRequest)
        proto = req.clientproto.split('/')[0].lower()
        host = req.getHeader('host')
        return context.tag[ "Virtual Host Listing for %s://%s" % (proto, host) ]

    def render_stylesheet(self, context, data):
        return tags.style(type="text/css")[self.getStyleSheet()]
        
    docFactory = loaders.stan(
        tags.html[
            tags.head[
                tags.title(render=render_title),
                tags.directive('stylesheet'),
            ],
            tags.body[
                tags.h1(render=render_title),
                tags.ul(data=directive("hostlist"), render=directive("sequence"))[
                    tags.li(pattern="item", render=render_hostlist)]]])
 
class NameVirtualHost(rend.Page):
    """I am a resource which represents named virtual hosts. 
       And these are my obligatory comments
    """
    
    supportNested = True

    def __init__(self, default=None, listHosts=True):
        """Initialize. - Do you really need me to tell you that?
        """
        log.msg("Initializing %r" % self)

        rend.Page.__init__(self)
        self.hosts = {}
       
        self.default = default
        self.listHosts = listHosts
        
        if self.listHosts and self.default == None:
            self.default = VirtualHostList(self)
            
    def addHost(self, name, resrc):
        """Add a host to this virtual host. - The Fun Stuff(TM)
            
        This associates a host named 'name' with a resource 'resrc'

            >>> nvh.addHost('nevow.com', nevowDirectory)
            >>> nvh.addHost('divmod.org', divmodDirectory)
            >>> nvh.addHost('twistedmatrix.com', twistedMatrixDirectory)

        I told you that was fun.
        """
        
        self.hosts[name] = resrc

    def removeHost(self, name):
        """Remove a host. :(
        """
        del self.hosts[name]

    def _getResourceForRequest(self, request):
        """(Internal) Get the appropriate resource for the request
        """
        
        hostHeader = request.getHeader('host')
        
        if hostHeader == None:
            return self.default or rend.NotFound[0]
        else:
            host = hostHeader.split(':')[0].lower()
            
            if self.supportNested:
                """ If supportNested is True domain prefixes (the stuff up to the first '.')
                    will be chopped off until it's reduced to the tld or a valid domain is 
                    found.
                """

                while not self.hosts.has_key(host) and len(host.split('.')) > 1:
                    host = '.'.join(host.split('.')[1:])

        return (self.hosts.get(host, self.default) or rend.NotFound[0])

    def locateChild(self, ctx, segments):
        """It's a NameVirtualHost, do you know where your children are?
        
        This uses locateChild magic so you don't have to mutate the request.
        """
        resrc = self._getResourceForRequest(inevow.IRequest(ctx))
        return resrc, segments

class _VHostMonsterResourcePrepathCleaner:
    """VHostMonsterResource cannot modify request.prepath because the
    segments it needs to remove are not appended to prepath until
    *after* it returns the (resource,segments) tuple.
    """
    implements(inevow.IResource)
    def locateChild(self, ctx, segments):
        request = inevow.IRequest(ctx)
        request.prepath = request.prepath[3:]
        return request.site.resource, segments

_prepathCleaner = _VHostMonsterResourcePrepathCleaner()

class VHostMonsterResource:
    """VHostMonster resource that helps to deploy a Nevow site behind a proxy.
    
    The main problem when deploying behind a proxy is that the scheme, host name
    and port the user typed into their browser are lost because the proxying web
    server forwards the request to something like http://localhost:8080/.
    
    A vhost resource consumes the next 2 segments of the URL to rewrite the
    scheme, host and port in the request object. It then "forwards" the request
    to the site's root resource.
    
    To install the resource use something like:
    
    >>> root = MyRootPage()
    >>> root.putChild('vhost', VHostMonsterResource())
    >>> site = NevowSite(root)
        
    An appropriate Apache configuration using mod_proxy would be::
        
        ProxyPass / http://localhost:8080/vhost/http/real.domainname.com/

    If you only want to proxy a part of the url tree, try::

        ProxyPass /foo/bar http://localhost:8080/vhost/http/real.domainname.com/foo/bar

    Note how the path is equal on both the public and the private server.
    Where as the /vhost/http/real.domainname.com part tells the private
    server the scheme, hostname, and possibly port, the /foo/bar is needed
    at the end to let the private know the path also.

    This also means your private server should serve the real content at
    /foo/bar, and not at the root of the tree.

    Warning: anyone who can access a VHostMonsterResource can fake the
    host name they are contacting. This can lead to cookie stealing or
    cross site scripting attacks. Never expose /vhost to the Internet.
    """
    implements(inevow.IResource)

    def locateChild(self, ctx, segments):

        request = inevow.IRequest(ctx)

        if len(segments) < 2:
            return rend.NotFound
        else:
            if segments[0] == 'http':
                request.isSecure = lambda: 0
            elif segments[0] == 'https':
                request.isSecure = lambda: 1

            if ':' in segments[1]:
                host, port = segments[1].split(':', 1)
                port = int(port)
            else:
                host, port = segments[1], 80
           
            request.setHost(host, port)

            prefixLen = len('/'+'/'.join(request.prepath)+'/'+'/'.join(segments[:2]))
            request.path = '/'+'/'.join(segments[2:])
            request.uri = request.uri[prefixLen:]

            return _prepathCleaner, segments[2:]

