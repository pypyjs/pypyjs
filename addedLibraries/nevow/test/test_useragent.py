
"""
Tests for L{nevow.useragent}.
"""

from twisted.trial.unittest import TestCase

from nevow.useragent import UserAgent, browsers


class UserAgentTests(TestCase):
    """
    Tests for L{UserAgent}.
    """
    def test_parseNetscape71(self):
        """
        L{UserAgent.parse_GECKO} should return a UserAgent instance for a
        Netscape 7.1 User-Agent string.
        """
        agent = UserAgent.parse_GECKO(
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; ja-JP; rv:1.4) '
            'Gecko/20030624 Netscape/7.1 (ax)')
        self.assertEqual(agent.browser, browsers.GECKO)
        self.assertEqual(agent.version, (20030624,))


    def test_parseFirefox15(self):
        """
        L{UserAgent.parse_GECKO} should return a UserAgent instance for a
        Firefox 1.5 User-Agent string.
        """
        agent = UserAgent.parse_GECKO(
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; en; rv:1.8.0.3) '
            'Gecko/20060426 Firefox/1.5.0.3')
        self.assertEqual(agent.browser, browsers.GECKO)
        self.assertEqual(agent.version, (20060426,))


    def test_parseBonEcho(self):
        """
        L{UserAgent.parse_GECKO} should return a UserAgent instance for a
        BonEcho Firefox 2.0 alpha User-Agent string.
        """
        agent = UserAgent.parse_GECKO(
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1a2) '
            'Gecko/20060512 BonEcho/2.0a2')
        self.assertEqual(agent.browser, browsers.GECKO)
        self.assertEqual(agent.version, (20060512,))


    def test_parseFirefox20(self):
        """
        L{UserAgent.parse_GECKO} should return a UserAgent instance for a
        Firefox 2.0 User-Agent string.
        """
        agent = UserAgent.parse_GECKO(
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.4) '
            'Gecko/20070515 Firefox/2.0.0.4')
        self.assertEqual(agent.browser, browsers.GECKO)
        self.assertEqual(agent.version, (20070515,))


    def test_parseExplorer45(self):
        """
        L{UserAgent.parse_MSIE} should return a UserAgent instance for an
        Internet Explorer 4.5 User-Agent string.
        """
        agent = UserAgent.parse_MSIE(
            'Mozilla/4.0 (compatible; MSIE 4.5; Windows 98; Win 9x 4.8410008)')
        self.assertEqual(agent.browser, browsers.INTERNET_EXPLORER)
        self.assertEqual(agent.version, (4, 5))


    def test_parseExplorer55(self):
        """
        L{UserAgent.parse_MSIE} should return a UserAgent instance for an
        Internet Explorer 5.5 User-Agent string.
        """
        agent = UserAgent.parse_MSIE(
            'Mozilla/5.0 (compatible; MSIE 5.5; Windows 98; Win 9x 4.1704896)')
        self.assertEqual(agent.browser, browsers.INTERNET_EXPLORER)
        self.assertEqual(agent.version, (5, 5))


    def test_parseExplorer65(self):
        """
        L{UserAgent.parse_MSIE} should return a UserAgent instance for an
        Internet Explorer 6.5 User-Agent string.
        """
        agent = UserAgent.parse_MSIE(
            'Mozilla/5.0 (compatible; MSIE 6.5; Windows 98; Win 9x 4.7654712)')
        self.assertEqual(agent.browser, browsers.INTERNET_EXPLORER)
        self.assertEqual(agent.version, (6, 5))


    def test_parseOmniWeb607(self):
        """
        L{UserAgent.parse_WEBKIT} should return a UserAgent instance for an
        OmniWeb User-Agent string.
        """
        agent = UserAgent.parse_WEBKIT(
            'Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en-US) AppleWebKit/420+ '
            '(KHTML, like Gecko, Safari/420) OmniWeb/v607.17')
        self.assertEqual(agent.browser, browsers.WEBKIT)
        self.assertEqual(agent.version, (420,))


    def test_parseSafari20(self):
        """
        L{UserAgent.parse_WEBKIT} should return a UserAgent instance for a
        Safari 2.0 User-Agent string.
        """
        agent = UserAgent.parse_WEBKIT(
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X; en) AppleWebKit/'
            '418.9.1 (KHTML, like Gecko) Safari/419.3')
        self.assertEqual(agent.browser, browsers.WEBKIT)
        self.assertEqual(agent.version, (418, 9, 1))


    def test_parseOpera9(self):
        """
        L{UserAgent.parse_OPERA} should return a UserAgent instance for an
        Opera 9 User-Agent string.
        """
        agent = UserAgent.parse_OPERA('Opera/9.20 (Windows NT 6.0; U; en)')
        self.assertEqual(agent.browser, browsers.OPERA)
        self.assertEqual(agent.version, (9, 20))


    def test_geckoParser(self):
        """
        It should be possible to invoke the Gecko parser via L{UserAgent.parse}
        with an appropriate string.
        """
        agent = UserAgent.fromHeaderValue(
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; ja-JP; rv:1.4) '
            'Gecko/20030624 Netscape/7.1 (ax)')
        self.assertEqual(agent.browser, browsers.GECKO)


    def test_webkitParser(self):
        """
        It should be possible to invoke the WebKit parser via
        L{UserAgent.parse} with an appropriate string.
        """
        agent = UserAgent.fromHeaderValue(
            'Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en-US) AppleWebKit/420+ '
            '(KHTML, like Gecko, Safari/420) OmniWeb/v607.17')
        self.assertEqual(agent.browser, browsers.WEBKIT)


    def test_msieParser(self):
        """
        It should be possible to invoke the MSIE parser via L{UserAgent.parse}
        with an appropriate string.
        """
        agent = UserAgent.fromHeaderValue(
            'Mozilla/4.0 (compatible; MSIE 4.5; Windows 98; Win 9x 4.8410008)')
        self.assertEqual(agent.browser, browsers.INTERNET_EXPLORER)


    def test_operaParser(self):
        """
        It should be possible to invoke the Opera parser via L{UserAgent.parse}
        with an appropriate string.
        """
        agent = UserAgent.fromHeaderValue('Opera/9.20 (Windows NT 6.0; U; en)')
        self.assertEqual(agent.browser, browsers.OPERA)
