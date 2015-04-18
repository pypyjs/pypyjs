# Copyright (c) 2004 Divmod.
# See LICENSE for details.

"""Directory listing."""

# system imports
import os
import urllib
import stat

# twisted imports
from nevow import inevow
from nevow import rend
from nevow import loaders
from nevow import tags

def formatFileSize(size):
    if size < 1024:
        return '%ib' % size
    elif size < (1024**2):
        return '%iK' % (size / 1024)
    elif size < (1024**3):
        return '%iM' % (size / (1024**2))
    else:
        return '%iG' % (size / (1024**3))

class DirectoryLister(rend.Page):
    def __init__(self, pathname, dirs=None,
                 contentTypes={},
                 contentEncodings={},
                 defaultType='text/html'):
        self.contentTypes = contentTypes
        self.contentEncodings = contentEncodings
        self.defaultType = defaultType
        # dirs allows usage of the File to specify what gets listed
        self.dirs = dirs
        self.path = pathname
        rend.Page.__init__(self)

    def data_listing(self, context, data):
        from nevow.static import getTypeAndEncoding

        if self.dirs is None:
            directory = os.listdir(self.path)
            directory.sort()
        else:
            directory = self.dirs

        files = []; dirs = []

        for path in directory:
            url = urllib.quote(path, '/')
            if os.path.isdir(os.path.join(self.path, path)):
                url = url + '/'
                dirs.append({
                    'link': url,
                    'linktext': path + "/",
                    'type': '[Directory]',
                    'filesize': '',
                    'encoding': '',
                    })
            else:
                mimetype, encoding = getTypeAndEncoding(
                    path,
                    self.contentTypes, self.contentEncodings, self.defaultType)
                try:
                    filesize = os.stat(os.path.join(self.path, path))[stat.ST_SIZE]
                except OSError, x:
                    if x.errno != 2 and x.errno != 13:
                        raise x
                else:
                    files.append({
                        'link': url,
                        'linktext': path,
                        'type': '[%s]' % mimetype,
                        'filesize': formatFileSize(filesize),
                        'encoding': (encoding and '[%s]' % encoding or '')})

        return dirs + files

    def data_header(self, context, data):
        request = context.locate(inevow.IRequest)
        return "Directory listing for %s" % urllib.unquote(request.uri)

    def render_tableLink(self, context, data):
        return tags.a(href=data['link'])[data['linktext']]

    def __repr__(self):  
        return '<DirectoryLister of %r>' % self.path
        
    __str__ = __repr__


    docFactory = loaders.stan(tags.html[
      tags.head[
        tags.title(data=tags.directive('header'))[str],
        tags.style['''
          th, .even td, .odd td { padding-right: 0.5em; }
          .even-dir { background-color: #efe0ef }
          .even { background-color: #eee }
          .odd-dir {background-color: #f0d0ef }
          .odd { background-color: #dedede }
          .icon { text-align: center }
          .listing {
              margin-left: auto;
              margin-right: auto;
              width: 50%;
              padding: 0.1em;
              }

          body { border: 0; padding: 0; margin: 0; background-color: #efefef;}
          h1 {padding: 0.1em; background-color: #777; color: white; border-bottom: thin white dashed;}
          ''']
      ],
      tags.body[tags.div(_class='directory-listing')[
        tags.h1(data=tags.directive('header'))[str],
        tags.table(render=rend.sequence, data=tags.directive('listing'))[
          tags.tr(pattern="header")[
            tags.th["Filename"],
            tags.th["Size"],
            tags.th["Content type"],
            tags.th["Content encoding"],
          ],
          tags.tr(_class="even", pattern="item")[
            tags.td[tags.a(render=tags.directive("tableLink"))],
            tags.td(data=tags.directive("filesize"))[str],
            tags.td(data=tags.directive("type"))[str],
            tags.td(data=tags.directive("encoding"))[str],
          ],
          tags.tr(_class="odd", pattern="item")[
            tags.td[tags.a(render=tags.directive("tableLink"))],
            tags.td(data=tags.directive("filesize"))[str],
            tags.td(data=tags.directive("type"))[str],
            tags.td(data=tags.directive("encoding"))[str],
          ]
        ]
      ]]
    ])
