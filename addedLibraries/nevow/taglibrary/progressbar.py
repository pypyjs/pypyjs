from nevow import static, tags as t, util
from nevow.taglibrary.livetags import component


class progressBarGlue:
    
    _css = util.resource_filename('nevow.taglibrary', "progressBar.css")
    _js = util.resource_filename('nevow.taglibrary', "progressBar.js")
    
    fileCSS = static.Data(_css, 'text/css')
    fileJS = static.Data(_js, 'text/javascript')
    fileGlue = (
        t.link(rel='stylesheet', type_='text/css', href='/progressBar.css'),
        t.script(type_='text/javascript', src='/progressBar.js')
        )
    
    inlineCSS = t.style(type_='text/css')[ t.xml(file(_css).read()) ]
    inlineJS = t.inlineJS(file(_js).read())
    inlineGlue = inlineJS, inlineCSS


class ProgressBarComponent(object):
    """
    Data
    ====
    
      name    : name for this component (default 'theProgressBar')
      percent : progress status as integer between 0 and 100 (default 0)

    Live component interface
    ========================
    
      component.setPercent(percent)
      -----------------------------

        Update the progress status to 'percent' (between 0 and 100).
    """
    
    def progressBar(self, ctx, data):
        name = data.get('name', 'theProgressBar')
        percent = data.get('percent', 0)
        yield t.div(class_='progressBar', id_=str(name))[
            t.div(class_ ='progressBarDiv', style='width: %i%%'%percent) ]
        yield t.script(type='text/javascript')[
            component[name].init('new ProgressBar(%r)'%name),
            #component[name].setPercent(percent)
        ]

progressBar = ProgressBarComponent().progressBar


__all__ = [ "progressBar", "progressBarGlue" ]
