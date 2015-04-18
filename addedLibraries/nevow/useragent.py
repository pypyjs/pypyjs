# -*- test-case-name: nevow.test.test_useragent -*-

"""
Parsers for browser User-Agent strings.

http://en.wikipedia.org/wiki/User_agent
http://www.user-agents.org/
"""

# Internet Explorer 1.0
# Microsoft Internet Explorer/Version (Platform)

# Internet Explorer, and browsers cloaking as Internet Explorer
# Mozilla/MozVer (compatible; MSIE IEVer[; Provider]; Platform[; Extension]*) [Addition]
# MozVer

# Netscape < 6.0
# Mozilla/Version[Gold] [[Language]][Provider] (Platform; Security[; SubPlatform][StandAlone])

# Mozilla
# Mozilla/MozVer (Platform; Security; SubPlatform; Language; rv:Revision[; Extension]*) Gecko/GeckVer [Product/ProdVer]

# Opera
# Opera/Version (Platform; U) [Language]


class browsers(object):
    """
    Namespace class for Browser identifiers.
    """
    GECKO = u'gecko'
    INTERNET_EXPLORER = u'internet explorer'
    WEBKIT = u'webkit'
    OPERA = u'opera'


class UserAgent(object):
    """
    Structured representation of a version identifier of a web browser.

    This presents only minimal structured information about the agent
    currently.  It could be expanded to include much more information, such a
    security properties, platform, and native language.

    @type browser: C{unicode}
    @ivar browser: The broad category of the browser.  Can only take on values
        from L{browsers}.

    @type version: C{str}
    @ivar version: The version claimed by the browser.
    """
    def __init__(self, browser, version):
        """
        Initialize a new UserAgent.

        The positions of the arguments to this initializer are not stable.
        Only pass arguments by keyword.
        """
        self.browser = browser
        self.version = version


    def parse_GECKO(cls, agentString):
        """
        Attempt to parse the given User-Agent string as a Gecko-based browser's
        user-agent.
        """
        identifier = 'Gecko/'
        start = agentString.find(identifier)
        if start != -1:
            end = agentString.find(' ', start)
            if end == -1:
                end = None
            version = agentString[start + len(identifier):end]
            try:
                version = int(version)
            except ValueError:
                pass
            else:
                return cls(browsers.GECKO, (version,))
    parse_GECKO = classmethod(parse_GECKO)


    def parse_WEBKIT(cls, agentString):
        """
        Attempt to parse the given User-Agent string as a WebKit-based
        browser's user-agent.
        """
        identifier = 'WebKit/'
        start = agentString.find(identifier)
        if start != -1:
            end = start + len(identifier)
            while (
                end < len(agentString) and
                agentString[end].isdigit() or
                agentString[end] == '.'):
                end += 1
            version = agentString[start + len(identifier):end]
            try:
                version = map(int, version.split('.'))
            except ValueError:
                pass
            else:
                return cls(browsers.WEBKIT, tuple(version))
    parse_WEBKIT = classmethod(parse_WEBKIT)


    def parse_OPERA(cls, agentString):
        """
        Attempt to parse an Opera user-agent.
        """
        prefix = 'Opera/'
        if agentString.startswith(prefix):
            version = agentString[len(prefix):].split(None, 1)[0]
            try:
                version = map(int, version.split('.'))
            except ValueError:
                pass
            else:
                return cls(browsers.OPERA, tuple(version))
    parse_OPERA = classmethod(parse_OPERA)


    def parse_MSIE(cls, agentString):
        """
        Attempt to parse an Internet Explorer user-agent.
        """
        oldPrefix = 'Mozilla/4.0 (compatible; MSIE '
        newPrefix = 'Mozilla/5.0 (compatible; MSIE '
        for prefix in oldPrefix, newPrefix:
            if agentString.startswith(prefix):
                end = agentString.find(';', len(prefix))
                if end == -1:
                    end = None
                version = agentString[len(prefix):end]
                try:
                    version = map(int, version.split('.'))
                except ValueError:
                    pass
                else:
                    return cls(browsers.INTERNET_EXPLORER, tuple(version))
    parse_MSIE = classmethod(parse_MSIE)


    def fromHeaderValue(cls, agentString):
        """
        Attempt to parse an arbitrary user-agent.

        @rtype: C{cls} or C{NoneType}
        @return: A user agent object, or C{None} if parsing fails.
        """
        # Order matters here - MSIE parser will match a ton of browsers.
        for parser in ['GECKO', 'WEBKIT', 'MSIE', 'OPERA']:
            agent = getattr(cls, 'parse_' + parser)(agentString)
            if agent is not None:
                return agent
        return None
    fromHeaderValue = classmethod(fromHeaderValue)
