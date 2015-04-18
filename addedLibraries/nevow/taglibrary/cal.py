import calendar
import datetime

from nevow import tags as t, url, itaglibrary, rend, static

_calendar_css = """
.calendar tbody td.today { background-color: #aaaaaa; }
"""

calendarCSS = t.style(type_="text/css")[_calendar_css]
calendarCSSFile = static.File(_calendar_css, "text/css")

class CalendarComponent(object):
    current_date = None
    def days(self, year, month):
        def _(ctx, data):
            return [[day and datetime.date(year, month, day) or None
                     for day in row]
                         for row in calendar.monthcalendar(year, month)]
        return _

    def render_calendarDay(self, ctx, data):
        options = itaglibrary.ICalendarOptions(ctx, {})
        today_class = options.get('today_class', 'today')
        if data is None:
            return ctx.tag['']
        if self.current_date.day == data.day and \
           self.current_date.month == data.month and \
           self.current_date.year == data.year:
            return ctx.tag(class_=today_class)[data.day] 
        return ctx.tag[data.day]

    def calendar(self, ctx, data):
        now = datetime.datetime.now()
        self.current_date = now
        month_delta = datetime.timedelta(31)
        options = itaglibrary.ICalendarOptions(ctx, {})
        strftime = options.get('strftime', '%b %d, %Y @ %I:%M %p')
        width = options.get('width', 2)
        prev = options.get('prev', None)
        next = options.get('next', None)
        base = options.get('base_url', None)
        calendar_class = options.get('calendar_class', 'calendar')
        if data is None:
            d = now
            current = d.year, d.month
        elif isinstance(data, tuple):
            year, month = data
            d = datetime.date(year, month, 4)
            current = data
        elif isinstance(data, (datetime.date, datetime.datetime)):
            d = data
            current = d.year, d.month

        if prev is None or next is None:
            p = d - month_delta
            n = d + month_delta
            prev = p.year, p.month
            next = n.year, n.month
            if base is None:
                u = url.URL.fromContext(ctx)
                segments = u.pathList()
                if segments[-1] == '':
                    u = u.up()
                    segments = segments[:-1]
                if segments[-1].isdigit() and segments[-2].isdigit():
                    u = u.up().up()
                prev_url = u
                next_url = u
            else:
                prev_url = base
                next_url = base

            add_query_params = False
            def buildUrl(u, el):
                if add_query_params:
                    param_name, param_value = el
                    u = u.add(param_name, str(param_value))
                else:
                    u = u.child(str(el))
                return u

            for el in prev:
                if el == '?':
                    add_query_params = True
                    continue
                prev_url = buildUrl(prev_url, el)
            add_query_params = False
            for el in next:
                if el == '?':
                    add_query_params = True
                    continue
                next_url = buildUrl(next_url, el)
        else:
            if isinstance(prev, (url.URL, url.URLOverlay)) and \
               isinstance(next, (url.URL, url.URLOverlay)):
                next_url = next
                prev_url = prev

        return t.table(class_=calendar_class)[
            t.thead[
              t.tr[
                t.th(colspan="7")[
                   t.a(href=prev_url)[t.xml("&larr;")],
                   t.xml(" "),
                   t.xml('-'.join([str(el) for el in current])),
                   t.xml(" "),
                   t.a(href=next_url)[t.xml("&rarr;")]
                ]
              ],
              [
                t.tr[[t.td[dayname] for dayname in calendar.weekheader(width).split()]]
              ]
            ],
            t.tbody[
              t.invisible(data=self.days(*current), render=rend.sequence)[
                 t.tr(pattern='item', render=rend.sequence)[
                     t.td(pattern='item', render=self.render_calendarDay)
                 ]
              ]
            ],
            t.tfoot[
               t.tr[
                  t.td(colspan="7")[
                      now.strftime(strftime)
                  ]
               ]
            ]
        ]


c = CalendarComponent()
cal = c.calendar
__all__ = ["cal", "CalendarComponent", "calendarCSS", "calendarCSSFile"]
