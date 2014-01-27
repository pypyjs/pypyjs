"""Reimplementation of the standard extension module '_curses' using cffi."""

import sys
from functools import wraps

from cffi import FFI

ffi = FFI()

ffi.cdef("""
typedef ... WINDOW;
typedef ... SCREEN;
typedef unsigned long mmask_t;
typedef unsigned char bool;
typedef unsigned long chtype;
typedef chtype attr_t;

typedef struct
{
    short id;           /* ID to distinguish multiple devices */
    int x, y, z;        /* event coordinates (character-cell) */
    mmask_t bstate;     /* button state bits */
}
MEVENT;

static const int ERR, OK;
static const int TRUE, FALSE;
static const int KEY_MIN, KEY_MAX;

static const int COLOR_BLACK;
static const int COLOR_RED;
static const int COLOR_GREEN;
static const int COLOR_YELLOW;
static const int COLOR_BLUE;
static const int COLOR_MAGENTA;
static const int COLOR_CYAN;
static const int COLOR_WHITE;

static const chtype A_ATTRIBUTES;
static const chtype A_NORMAL;
static const chtype A_STANDOUT;
static const chtype A_UNDERLINE;
static const chtype A_REVERSE;
static const chtype A_BLINK;
static const chtype A_DIM;
static const chtype A_BOLD;
static const chtype A_ALTCHARSET;
static const chtype A_INVIS;
static const chtype A_PROTECT;
static const chtype A_CHARTEXT;
static const chtype A_COLOR;

static const int BUTTON1_RELEASED;
static const int BUTTON1_PRESSED;
static const int BUTTON1_CLICKED;
static const int BUTTON1_DOUBLE_CLICKED;
static const int BUTTON1_TRIPLE_CLICKED;
static const int BUTTON2_RELEASED;
static const int BUTTON2_PRESSED;
static const int BUTTON2_CLICKED;
static const int BUTTON2_DOUBLE_CLICKED;
static const int BUTTON2_TRIPLE_CLICKED;
static const int BUTTON3_RELEASED;
static const int BUTTON3_PRESSED;
static const int BUTTON3_CLICKED;
static const int BUTTON3_DOUBLE_CLICKED;
static const int BUTTON3_TRIPLE_CLICKED;
static const int BUTTON4_RELEASED;
static const int BUTTON4_PRESSED;
static const int BUTTON4_CLICKED;
static const int BUTTON4_DOUBLE_CLICKED;
static const int BUTTON4_TRIPLE_CLICKED;
static const int BUTTON_SHIFT;
static const int BUTTON_CTRL;
static const int BUTTON_ALT;
static const int ALL_MOUSE_EVENTS;
static const int REPORT_MOUSE_POSITION;

int setupterm(char *, int, int *);

WINDOW *stdscr;
int COLORS;
int COLOR_PAIRS;
int COLS;
int LINES;

int baudrate(void);
int beep(void);
int box(WINDOW *, chtype, chtype);
bool can_change_color(void);
int cbreak(void);
int clearok(WINDOW *, bool);
int color_content(short, short*, short*, short*);
int copywin(const WINDOW*, WINDOW*, int, int, int, int, int, int, int);
int curs_set(int);
int def_prog_mode(void);
int def_shell_mode(void);
int delay_output(int);
int delwin(WINDOW *);
WINDOW * derwin(WINDOW *, int, int, int, int);
int doupdate(void);
int echo(void);
int endwin(void);
char erasechar(void);
void filter(void);
int flash(void);
int flushinp(void);
chtype getbkgd(WINDOW *);
WINDOW * getwin(FILE *);
int halfdelay(int);
bool has_colors(void);
bool has_ic(void);
bool has_il(void);
void idcok(WINDOW *, bool);
int idlok(WINDOW *, bool);
void immedok(WINDOW *, bool);
WINDOW * initscr(void);
int init_color(short, short, short, short);
int init_pair(short, short, short);
int intrflush(WINDOW *, bool);
bool isendwin(void);
bool is_linetouched(WINDOW *, int);
bool is_wintouched(WINDOW *);
const char * keyname(int);
int keypad(WINDOW *, bool);
char killchar(void);
int leaveok(WINDOW *, bool);
char * longname(void);
int meta(WINDOW *, bool);
int mvderwin(WINDOW *, int, int);
int mvwaddch(WINDOW *, int, int, const chtype);
int mvwaddnstr(WINDOW *, int, int, const char *, int);
int mvwaddstr(WINDOW *, int, int, const char *);
int mvwchgat(WINDOW *, int, int, int, attr_t, short, const void *);
int mvwdelch(WINDOW *, int, int);
int mvwgetch(WINDOW *, int, int);
int mvwgetnstr(WINDOW *, int, int, char *, int);
int mvwin(WINDOW *, int, int);
chtype mvwinch(WINDOW *, int, int);
int mvwinnstr(WINDOW *, int, int, char *, int);
int mvwinsch(WINDOW *, int, int, chtype);
int mvwinsnstr(WINDOW *, int, int, const char *, int);
int mvwinsstr(WINDOW *, int, int, const char *);
int napms(int);
WINDOW * newpad(int, int);
WINDOW * newwin(int, int, int, int);
int nl(void);
int nocbreak(void);
int nodelay(WINDOW *, bool);
int noecho(void);
int nonl(void);
void noqiflush(void);
int noraw(void);
int notimeout(WINDOW *, bool);
int overlay(const WINDOW*, WINDOW *);
int overwrite(const WINDOW*, WINDOW *);
int pair_content(short, short*, short*);
int pechochar(WINDOW *, const chtype);
int pnoutrefresh(WINDOW*, int, int, int, int, int, int);
int prefresh(WINDOW *, int, int, int, int, int, int);
int putwin(WINDOW *, FILE *);
void qiflush(void);
int raw(void);
int redrawwin(WINDOW *);
int resetty(void);
int reset_prog_mode(void);
int reset_shell_mode(void);
int savetty(void);
int scroll(WINDOW *);
int scrollok(WINDOW *, bool);
int start_color(void);
WINDOW * subpad(WINDOW *, int, int, int, int);
WINDOW * subwin(WINDOW *, int, int, int, int);
int syncok(WINDOW *, bool);
chtype termattrs(void);
char * termname(void);
int touchline(WINDOW *, int, int);
int touchwin(WINDOW *);
int typeahead(int);
int ungetch(int);
int untouchwin(WINDOW *);
void use_env(bool);
int waddch(WINDOW *, const chtype);
int waddnstr(WINDOW *, const char *, int);
int waddstr(WINDOW *, const char *);
int wattron(WINDOW *, int);
int wattroff(WINDOW *, int);
int wattrset(WINDOW *, int);
int wbkgd(WINDOW *, chtype);
void wbkgdset(WINDOW *, chtype);
int wborder(WINDOW *, chtype, chtype, chtype, chtype,
            chtype, chtype, chtype, chtype);
int wchgat(WINDOW *, int, attr_t, short, const void *);
int wclear(WINDOW *);
int wclrtobot(WINDOW *);
int wclrtoeol(WINDOW *);
void wcursyncup(WINDOW *);
int wdelch(WINDOW *);
int wdeleteln(WINDOW *);
int wechochar(WINDOW *, const chtype);
int werase(WINDOW *);
int wgetch(WINDOW *);
int wgetnstr(WINDOW *, char *, int);
int whline(WINDOW *, chtype, int);
chtype winch(WINDOW *);
int winnstr(WINDOW *, char *, int);
int winsch(WINDOW *, chtype);
int winsdelln(WINDOW *, int);
int winsertln(WINDOW *);
int winsnstr(WINDOW *, const char *, int);
int winsstr(WINDOW *, const char *);
int wmove(WINDOW *, int, int);
int wresize(WINDOW *, int, int);
int wnoutrefresh(WINDOW *);
int wredrawln(WINDOW *, int, int);
int wrefresh(WINDOW *);
int wscrl(WINDOW *, int);
int wsetscrreg(WINDOW *, int, int);
int wstandout(WINDOW *);
int wstandend(WINDOW *);
void wsyncdown(WINDOW *);
void wsyncup(WINDOW *);
void wtimeout(WINDOW *, int);
int wtouchln(WINDOW *, int, int, int);
int wvline(WINDOW *, chtype, int);
int tigetflag(char *);
int tigetnum(char *);
char * tigetstr(char *);
int putp(const char *);
char * tparm(const char *, ...);
int getattrs(const WINDOW *);
int getcurx(const WINDOW *);
int getcury(const WINDOW *);
int getbegx(const WINDOW *);
int getbegy(const WINDOW *);
int getmaxx(const WINDOW *);
int getmaxy(const WINDOW *);
int getparx(const WINDOW *);
int getpary(const WINDOW *);

int getmouse(MEVENT *);
int ungetmouse(MEVENT *);
mmask_t mousemask(mmask_t, mmask_t *);
bool wenclose(const WINDOW *, int, int);
int mouseinterval(int);

void setsyx(int y, int x);
const char *unctrl(chtype);
int use_default_colors(void);

int has_key(int);
bool is_term_resized(int, int);

#define _m_STRICT_SYSV_CURSES ...
#define _m_NCURSES_MOUSE_VERSION ...
#define _m_NetBSD ...
int _m_ispad(WINDOW *);

chtype acs_map[];

// For _curses_panel:

typedef ... PANEL;

WINDOW *panel_window(const PANEL *);
void update_panels(void);
int hide_panel(PANEL *);
int show_panel(PANEL *);
int del_panel(PANEL *);
int top_panel(PANEL *);
int bottom_panel(PANEL *);
PANEL *new_panel(WINDOW *);
PANEL *panel_above(const PANEL *);
PANEL *panel_below(const PANEL *);
int set_panel_userptr(PANEL *, void *);
const void *panel_userptr(const PANEL *);
int move_panel(PANEL *, int, int);
int replace_panel(PANEL *,WINDOW *);
int panel_hidden(const PANEL *);

void _m_getsyx(int *yx);
""")


lib = ffi.verify("""
#include <ncurses.h>
#include <panel.h>
#include <term.h>

#if defined STRICT_SYSV_CURSES
#define _m_STRICT_SYSV_CURSES TRUE
#else
#define _m_STRICT_SYSV_CURSES FALSE
#endif

#if defined NCURSES_MOUSE_VERSION
#define _m_NCURSES_MOUSE_VERSION TRUE
#else
#define _m_NCURSES_MOUSE_VERSION FALSE
#endif

#if defined __NetBSD__
#define _m_NetBSD TRUE
#else
#define _m_NetBSD FALSE
#endif

int _m_ispad(WINDOW *win) {
#if defined WINDOW_HAS_FLAGS
    return (win->_flags & _ISPAD);
#else
    return 0;
#endif
}

void _m_getsyx(int *yx) {
    getsyx(yx[0], yx[1]);
}
""", libraries=['ncurses', 'panel'])


def _copy_to_globals(name):
    globals()[name] = getattr(lib, name)


def _setup():
    for name in ['ERR', 'OK', 'KEY_MIN', 'KEY_MAX',
                 'A_ATTRIBUTES', 'A_NORMAL', 'A_STANDOUT', 'A_UNDERLINE',
                 'A_REVERSE', 'A_BLINK', 'A_DIM', 'A_BOLD', 'A_ALTCHARSET',
                 'A_PROTECT', 'A_CHARTEXT', 'A_COLOR',
                 'COLOR_BLACK', 'COLOR_RED', 'COLOR_GREEN', 'COLOR_YELLOW',
                 'COLOR_BLUE', 'COLOR_MAGENTA', 'COLOR_CYAN', 'COLOR_WHITE',
                 ]:
        _copy_to_globals(name)

    if not lib._m_NetBSD:
        _copy_to_globals('A_INVIS')

    for name in ['A_HORIZONTAL', 'A_LEFT', 'A_LOW', 'A_RIGHT', 'A_TOP',
                 'A_VERTICAL',
                 ]:
        if hasattr(lib, name):
            _copy_to_globals(name)

    if lib._m_NCURSES_MOUSE_VERSION:
        for name in ["BUTTON1_PRESSED", "BUTTON1_RELEASED", "BUTTON1_CLICKED",
                     "BUTTON1_DOUBLE_CLICKED", "BUTTON1_TRIPLE_CLICKED",
                     "BUTTON2_PRESSED", "BUTTON2_RELEASED", "BUTTON2_CLICKED",
                     "BUTTON2_DOUBLE_CLICKED", "BUTTON2_TRIPLE_CLICKED",
                     "BUTTON3_PRESSED", "BUTTON3_RELEASED", "BUTTON3_CLICKED",
                     "BUTTON3_DOUBLE_CLICKED", "BUTTON3_TRIPLE_CLICKED",
                     "BUTTON4_PRESSED", "BUTTON4_RELEASED", "BUTTON4_CLICKED",
                     "BUTTON4_DOUBLE_CLICKED", "BUTTON4_TRIPLE_CLICKED",
                     "BUTTON_SHIFT", "BUTTON_CTRL", "BUTTON_ALT",
                     "ALL_MOUSE_EVENTS", "REPORT_MOUSE_POSITION",
                     ]:
            _copy_to_globals(name)

    if not lib._m_NetBSD:
        for key in range(lib.KEY_MIN, lib.KEY_MAX):
            key_n = lib.keyname(key)
            if key_n == ffi.NULL:
                continue
            key_n = ffi.string(key_n)
            if key_n == b"UNKNOWN KEY":
                continue
            if not isinstance(key_n, str):   # python 3
                key_n = key_n.decode()
            key_n = key_n.replace('(', '').replace(')', '')
            globals()[key_n] = key

_setup()

# Do we want this?
# version = "2.2"
# __version__ = "2.2"


# ____________________________________________________________


_initialised_setupterm = False
_initialised = False
_initialised_color = False


def _ensure_initialised_setupterm():
    if not _initialised_setupterm:
        raise error("must call (at least) setupterm() first")


def _ensure_initialised():
    if not _initialised:
        raise error("must call initscr() first")


def _ensure_initialised_color():
    if not _initialised and _initialised_color:
        raise error("must call start_color() first")


def _check_ERR(code, fname):
    if code != lib.ERR:
        return None
    elif fname is None:
        raise error("curses function returned ERR")
    else:
        raise error("%s() returned ERR" % (fname,))


def _check_NULL(rval):
    if rval == ffi.NULL:
        raise error("curses function returned NULL")
    return rval


def _call_lib(method_name, *args):
    return getattr(lib, method_name)(*args)


def _call_lib_check_ERR(method_name, *args):
    return _check_ERR(_call_lib(method_name, *args), method_name)


def _mk_no_return(method_name):
    def _execute():
        _ensure_initialised()
        return _call_lib_check_ERR(method_name)
    _execute.__name__ = method_name
    return _execute


def _mk_flag_func(method_name):
    # This is in the CPython implementation, but not documented anywhere.
    # We have to support it, though, even if it make me sad.
    def _execute(flag=True):
        _ensure_initialised()
        if flag:
            return _call_lib_check_ERR(method_name)
        else:
            return _call_lib_check_ERR('no' + method_name)
    _execute.__name__ = method_name
    return _execute


def _mk_return_val(method_name):
    def _execute():
        return _call_lib(method_name)
    _execute.__name__ = method_name
    return _execute


def _mk_w_getyx(method_name):
    def _execute(self):
        y = _call_lib(method_name + 'y', self._win)
        x = _call_lib(method_name + 'x', self._win)
        return (y, x)
    _execute.__name__ = method_name
    return _execute


def _mk_w_no_return(method_name):
    def _execute(self, *args):
        return _call_lib_check_ERR(method_name, self._win, *args)
    _execute.__name__ = method_name
    return _execute


def _mk_w_return_val(method_name):
    def _execute(self, *args):
        return _call_lib(method_name, self._win, *args)
    _execute.__name__ = method_name
    return _execute


def _chtype(ch):
    return int(ffi.cast("chtype", ch))

def _texttype(text):
    if isinstance(text, str):
        return text
    elif isinstance(text, unicode):
        return str(text)   # default encoding
    else:
        raise TypeError("str or unicode expected, got a '%s' object"
                        % (type(text).__name__,))


def _extract_yx(args):
    if len(args) >= 2:
        return (args[0], args[1], args[2:])
    return (None, None, args)


def _process_args(funcname, args, count, optcount, frontopt=0):
    outargs = []
    if frontopt:
        if len(args) > count + optcount:
            # We have the front optional args here.
            outargs.extend(args[:frontopt])
            args = args[frontopt:]
        else:
            # No front optional args, so make them None.
            outargs.extend([None] * frontopt)
    if (len(args) < count) or (len(args) > count + optcount):
        raise error("%s requires %s to %s arguments" % (
                funcname, count, count + optcount + frontopt))
    outargs.extend(args)
    return outargs


def _argspec(count, optcount=0, frontopt=0):
    def _argspec_deco(func):
        @wraps(func)
        def _wrapped(self, *args):
            outargs = _process_args(
                func.__name__, args, count, optcount, frontopt)
            return func(self, *outargs)
        return _wrapped
    return _argspec_deco


# ____________________________________________________________


class error(Exception):
    pass


class Window(object):
    def __init__(self, window):
        self._win = window

    def __del__(self):
        if self._win != lib.stdscr:
            lib.delwin(self._win)

    untouchwin = _mk_w_no_return("untouchwin")
    touchwin = _mk_w_no_return("touchwin")
    redrawwin = _mk_w_no_return("redrawwin")
    insertln = _mk_w_no_return("winsertln")
    erase = _mk_w_no_return("werase")
    deleteln = _mk_w_no_return("wdeleteln")

    is_wintouched = _mk_w_return_val("is_wintouched")

    syncdown = _mk_w_return_val("wsyncdown")
    syncup = _mk_w_return_val("wsyncup")
    standend = _mk_w_return_val("wstandend")
    standout = _mk_w_return_val("wstandout")
    cursyncup = _mk_w_return_val("wcursyncup")
    clrtoeol = _mk_w_return_val("wclrtoeol")
    clrtobot = _mk_w_return_val("wclrtobot")
    clear = _mk_w_return_val("wclear")

    idcok = _mk_w_no_return("idcok")
    immedok = _mk_w_no_return("immedok")
    timeout = _mk_w_no_return("wtimeout")

    getyx = _mk_w_getyx("getcur")
    getbegyx = _mk_w_getyx("getbeg")
    getmaxyx = _mk_w_getyx("getmax")
    getparyx = _mk_w_getyx("getpar")

    clearok = _mk_w_no_return("clearok")
    idlok = _mk_w_no_return("idlok")
    leaveok = _mk_w_no_return("leaveok")
    notimeout = _mk_w_no_return("notimeout")
    scrollok = _mk_w_no_return("scrollok")
    insdelln = _mk_w_no_return("winsdelln")
    syncok = _mk_w_no_return("syncok")

    mvwin = _mk_w_no_return("mvwin")
    mvderwin = _mk_w_no_return("mvderwin")
    move = _mk_w_no_return("wmove")

    if not lib._m_STRICT_SYSV_CURSES:
        resize = _mk_w_no_return("wresize")

    if lib._m_NetBSD:
        keypad = _mk_w_return_val("keypad")
        nodelay = _mk_w_return_val("nodelay")
    else:
        keypad = _mk_w_no_return("keypad")
        nodelay = _mk_w_no_return("nodelay")

    @_argspec(1, 1, 2)
    def addch(self, y, x, ch, attr=None):
        if attr is None:
            attr = lib.A_NORMAL
        ch = _chtype(ch)

        if y is not None:
            code = lib.mvwaddch(self._win, y, x, ch | attr)
        else:
            code = lib.waddch(self._win, ch | attr)
        return _check_ERR(code, "addch")

    @_argspec(1, 1, 2)
    def addstr(self, y, x, text, attr=None):
        text = _texttype(text)
        if attr is not None:
            attr_old = lib.getattrs(self._win)
            lib.wattrset(self._win, attr)
        if y is not None:
            code = lib.mvwaddstr(self._win, y, x, text)
        else:
            code = lib.waddstr(self._win, text)
        if attr is not None:
            lib.wattrset(self._win, attr_old)
        return _check_ERR(code, "addstr")

    @_argspec(2, 1, 2)
    def addnstr(self, y, x, text, n, attr=None):
        text = _texttype(text)
        if attr is not None:
            attr_old = lib.getattrs(self._win)
            lib.wattrset(self._win, attr)
        if y is not None:
            code = lib.mvwaddnstr(self._win, y, x, text, n)
        else:
            code = lib.waddnstr(self._win, text, n)
        if attr is not None:
            lib.wattrset(self._win, attr_old)
        return _check_ERR(code, "addnstr")

    def bkgd(self, ch, attr=None):
        if attr is None:
            attr = lib.A_NORMAL
        return _check_ERR(lib.wbkgd(self._win, _chtype(ch) | attr), "bkgd")

    attroff = _mk_w_no_return("wattroff")
    attron = _mk_w_no_return("wattron")
    attrset = _mk_w_no_return("wattrset")

    def bkgdset(self, ch, attr=None):
        if attr is None:
            attr = lib.A_NORMAL
        lib.wbkgdset(self._win, _chtype(ch) | attr)
        return None

    def border(self, ls=0, rs=0, ts=0, bs=0, tl=0, tr=0, bl=0, br=0):
        lib.wborder(self._win,
                    _chtype(ls), _chtype(rs), _chtype(ts), _chtype(bs),
                    _chtype(tl), _chtype(tr), _chtype(bl), _chtype(br))
        return None

    def box(self, vertint=0, horint=0):
        lib.box(self._win, vertint, horint)
        return None

    @_argspec(1, 1, 2)
    def chgat(self, y, x, num, attr=None):
        # These optional args are in a weird order.
        if attr is None:
            attr = num
            num = -1

        color = ((attr >> 8) & 0xff)
        attr = attr - (color << 8)

        if y is not None:
            code = lib.mvwchgat(self._win, y, x, num, attr, color, ffi.NULL)
            lib.touchline(self._win, y, 1)
        else:
            yy, _ = self.getyx()
            code = lib.wchgat(self._win, num, attr, color, ffi.NULL)
            lib.touchline(self._win, yy, 1)
        return _check_ERR(code, "chgat")

    def delch(self, *args):
        if len(args) == 0:
            code = lib.wdelch(self._win)
        elif len(args) == 2:
            code = lib.mvwdelch(self._win, *args)
        else:
            raise error("delch requires 0 or 2 arguments")
        return _check_ERR(code, "[mv]wdelch")

    def derwin(self, *args):
        nlines = 0
        ncols = 0
        if len(args) == 2:
            begin_y, begin_x = args
        elif len(args) == 4:
            nlines, ncols, begin_y, begin_x = args
        else:
            raise error("derwin requires 2 or 4 arguments")

        win = lib.derwin(self._win, nlines, ncols, begin_y, begin_x)
        return Window(_check_NULL(win))

    def echochar(self, ch, attr=None):
        if attr is None:
            attr = lib.A_NORMAL
        ch = _chtype(ch)

        if lib._m_ispad(self._win):
            code = lib.pechochar(self._win, ch | attr)
        else:
            code = lib.wechochar(self._win, ch | attr)
        return _check_ERR(code, "echochar")

    if lib._m_NCURSES_MOUSE_VERSION:
        enclose = _mk_w_return_val("wenclose")

    getbkgd = _mk_w_return_val("getbkgd")

    def getch(self, *args):
        if len(args) == 0:
            val = lib.wgetch(self._win)
        elif len(args) == 2:
            val = lib.mvwgetch(self._win, *args)
        else:
            raise error("getch requires 0 or 2 arguments")
        return val

    def getkey(self, *args):
        if len(args) == 0:
            val = lib.wgetch(self._win)
        elif len(args) == 2:
            val = lib.mvwgetch(self._win, *args)
        else:
            raise error("getkey requires 0 or 2 arguments")

        if val == lib.ERR:
            raise error("no input")
        elif val <= 255:
            return chr(val)
        else:
            # XXX: The following line is different if `__NetBSD__` is defined.
            val = lib.keyname(val)
            if val == ffi.NULL:
                return ""
            return ffi.string(val)

    @_argspec(0, 1, 2)
    def getstr(self, y, x, n=1023):
        n = min(n, 1023)
        buf = ffi.new("char[1024]")  # /* This should be big enough.. I hope */

        if y is None:
            val = lib.wgetnstr(self._win, buf, n)
        else:
            val = lib.mvwgetnstr(self._win, y, x, buf, n)

        if val == lib.ERR:
            return ""
        return ffi.string(buf)

    @_argspec(2, 1, 2)
    def hline(self, y, x, ch, n, attr=None):
        ch = _chtype(ch)
        if attr is None:
            attr = lib.A_NORMAL
        if y is not None:
            _check_ERR(lib.wmove(self._win, y, x), "wmove")
        return _check_ERR(lib.whline(self._win, ch | attr, n), "hline")

    @_argspec(1, 1, 2)
    def insch(self, y, x, ch, attr=None):
        ch = _chtype(ch)
        if attr is None:
            attr = lib.A_NORMAL
        if y is not None:
            code = lib.mvwinsch(self._win, y, x, ch | attr)
        else:
            code = lib.winsch(self._win, ch | attr)
        return _check_ERR(code, "insch")

    def inch(self, *args):
        if len(args) == 0:
            return lib.winch(self._win)
        elif len(args) == 2:
            return lib.mvwinch(self._win, *args)
        else:
            raise error("inch requires 0 or 2 arguments")

    @_argspec(0, 1, 2)
    def instr(self, y, x, n=1023):
        n = min(n, 1023)
        buf = ffi.new("char[1024]")  # /* This should be big enough.. I hope */
        if y is None:
            code = lib.winnstr(self._win, buf, n)
        else:
            code = lib.mvwinnstr(self._win, y, x, buf, n)

        if code == lib.ERR:
            return ""
        return ffi.string(buf)

    @_argspec(1, 1, 2)
    def insstr(self, y, x, text, attr=None):
        text = _texttype(text)
        if attr is not None:
            attr_old = lib.getattrs(self._win)
            lib.wattrset(self._win, attr)
        if y is not None:
            code = lib.mvwinsstr(self._win, y, x, text)
        else:
            code = lib.winsstr(self._win, text)
        if attr is not None:
            lib.wattrset(self._win, attr_old)
        return _check_ERR(code, "insstr")

    @_argspec(2, 1, 2)
    def insnstr(self, y, x, text, n, attr=None):
        text = _texttype(text)
        if attr is not None:
            attr_old = lib.getattrs(self._win)
            lib.wattrset(self._win, attr)
        if y is not None:
            code = lib.mvwinsnstr(self._win, y, x, text, n)
        else:
            code = lib.winsnstr(self._win, text, n)
        if attr is not None:
            lib.wattrset(self._win, attr_old)
        return _check_ERR(code, "insnstr")

    def is_linetouched(self, line):
        code = lib.is_linetouched(self._win, line)
        if code == lib.ERR:
            raise error("is_linetouched: line number outside of boundaries")
        if code == lib.FALSE:
            return False
        return True

    def noutrefresh(self, *args):
        if lib._m_ispad(self._win):
            if len(args) != 6:
                raise error(
                    "noutrefresh() called for a pad requires 6 arguments")
            return _check_ERR(lib.pnoutrefresh(self._win, *args),
                              "pnoutrefresh")
        else:
            # XXX: Better args check here? We need zero args.
            return _check_ERR(lib.wnoutrefresh(self._win, *args),
                              "wnoutrefresh")

    nooutrefresh = noutrefresh  # "to be removed in 2.3", but in 2.7, 3.x.

    def _copywin(self, dstwin, overlay,
                 sminr, sminc, dminr, dminc, dmaxr, dmaxc):
        return _check_ERR(lib.copywin(self._win, dstwin._win,
                                      sminr, sminc, dminr, dminc, dmaxr, dmaxc,
                                      overlay), "copywin")

    def overlay(self, dstwin, *args):
        if len(args) == 6:
            return self._copywin(dstwin, True, *args)
        elif len(args) == 0:
            return _check_ERR(lib.overlay(self._win, dstwin._win), "overlay")
        else:
            raise error("overlay requires one or seven arguments")

    def overwrite(self, dstwin, *args):
        if len(args) == 6:
            return self._copywin(dstwin, False, *args)
        elif len(args) == 0:
            return _check_ERR(lib.overwrite(self._win, dstwin._win),
                              "overwrite")
        else:
            raise error("overwrite requires one or seven arguments")

    def putwin(self, filep):
        # filestar = ffi.new("FILE *", filep)
        return _check_ERR(lib.putwin(self._win, filep), "putwin")

    def redrawln(self, beg, num):
        return _check_ERR(lib.wredrawln(self._win, beg, num), "redrawln")

    def refresh(self, *args):
        if lib._m_ispad(self._win):
            if len(args) != 6:
                raise error(
                    "noutrefresh() called for a pad requires 6 arguments")
            return _check_ERR(lib.prefresh(self._win, *args), "prefresh")
        else:
            # XXX: Better args check here? We need zero args.
            return _check_ERR(lib.wrefresh(self._win, *args), "wrefresh")

    def setscrreg(self, y, x):
        return _check_ERR(lib.wsetscrreg(self._win, y, x), "wsetscrreg")

    def subwin(self, *args):
        nlines = 0
        ncols = 0
        if len(args) == 2:
            begin_y, begin_x = args
        elif len(args) == 4:
            nlines, ncols, begin_y, begin_x = args
        else:
            raise error("subwin requires 2 or 4 arguments")

        if lib._m_ispad(self._win):
            win = lib.subpad(self._win, nlines, ncols, begin_y, begin_x)
        else:
            win = lib.subwin(self._win, nlines, ncols, begin_y, begin_x)
        return Window(_check_NULL(win))

    def scroll(self, nlines=None):
        if nlines is None:
            return _check_ERR(lib.scroll(self._win), "scroll")
        else:
            return _check_ERR(lib.wscrl(self._win, nlines), "scroll")

    def touchline(self, st, cnt, val=None):
        if val is None:
            return _check_ERR(lib.touchline(self._win, st, cnt), "touchline")
        else:
            return _check_ERR(lib.wtouchln(self._win, st, cnt, val),
                              "touchline")

    @_argspec(2, 1, 2)
    def vline(self, y, x, ch, n, attr=None):
        ch = _chtype(ch)
        if attr is None:
            attr = lib.A_NORMAL
        if y is not None:
            _check_ERR(lib.wmove(self._win, y, x), "wmove")
        return _check_ERR(lib.wvline(self._win, ch | attr, n), "vline")


beep = _mk_no_return("beep")
def_prog_mode = _mk_no_return("def_prog_mode")
def_shell_mode = _mk_no_return("def_shell_mode")
doupdate = _mk_no_return("doupdate")
endwin = _mk_no_return("endwin")
flash = _mk_no_return("flash")
nocbreak = _mk_no_return("nocbreak")
noecho = _mk_no_return("noecho")
nonl = _mk_no_return("nonl")
noraw = _mk_no_return("noraw")
reset_prog_mode = _mk_no_return("reset_prog_mode")
reset_shell_mode = _mk_no_return("reset_shell_mode")
resetty = _mk_no_return("resetty")
savetty = _mk_no_return("savetty")

cbreak = _mk_flag_func("cbreak")
echo = _mk_flag_func("echo")
nl = _mk_flag_func("nl")
raw = _mk_flag_func("raw")

baudrate = _mk_return_val("baudrate")
termattrs = _mk_return_val("termattrs")

termname = _mk_return_val("termname")
longname = _mk_return_val("longname")

can_change_color = _mk_return_val("can_change_color")
has_colors = _mk_return_val("has_colors")
has_ic = _mk_return_val("has_ic")
has_il = _mk_return_val("has_il")
isendwin = _mk_return_val("isendwin")
flushinp = _mk_return_val("flushinp")
noqiflush = _mk_return_val("noqiflush")


def filter():
    lib.filter()
    return None


def color_content(color):
    _ensure_initialised_color()
    r, g, b = ffi.new("short *"), ffi.new("short *"), ffi.new("short *")
    if lib.color_content(color, r, g, b) == lib.ERR:
        raise error("Argument 1 was out of range. Check value of COLORS.")
    return (r, g, b)


def color_pair(n):
    _ensure_initialised_color()
    return (n << 8)


def curs_set(vis):
    _ensure_initialised()
    val = lib.curs_set(vis)
    _check_ERR(val, "curs_set")
    return val


def delay_output(ms):
    _ensure_initialised()
    return _check_ERR(lib.delay_output(ms), "delay_output")


def erasechar():
    _ensure_initialised()
    return lib.erasechar()


def getsyx():
    _ensure_initialised()
    yx = ffi.new("int[2]")
    lib._m_getsyx(yx)
    return (yx[0], yx[1])


if lib._m_NCURSES_MOUSE_VERSION:

    def getmouse():
        _ensure_initialised()
        mevent = ffi.new("MEVENT *")
        _check_ERR(lib.getmouse(mevent), "getmouse")
        return (mevent.id, mevent.x, mevent.y, mevent.z, mevent.bstate)

    def ungetmouse(id, x, y, z, bstate):
        _ensure_initialised()
        mevent = ffi.new("MEVENT *")
        mevent.id, mevent.x, mevent.y, mevent.z, mevent.bstate = (
            id, x, y, z, bstate)
        return _check_ERR(lib.ungetmouse(mevent), "ungetmouse")


def getwin(filep):
    return Window(_check_NULL(lib.getwin(filep)))


def halfdelay(tenths):
    _ensure_initialised()
    return _check_ERR(lib.halfdelay(tenths), "halfdelay")


if not lib._m_STRICT_SYSV_CURSES:
    def has_key(ch):
        _ensure_initialised()
        return lib.has_key(ch)


def init_color(color, r, g, b):
    _ensure_initialised_color()
    return _check_ERR(lib.init_color(color, r, g, b), "init_color")


def init_pair(pair, f, b):
    _ensure_initialised_color()
    return _check_ERR(lib.init_pair(pair, f, b), "init_pair")


def _mk_acs(name, ichar):
    if len(ichar) == 1:
        globals()[name] = lib.acs_map[ord(ichar)]
    else:
        globals()[name] = globals()[ichar]


def _map_acs():
    _mk_acs("ACS_ULCORNER", 'l')
    _mk_acs("ACS_LLCORNER", 'm')
    _mk_acs("ACS_URCORNER", 'k')
    _mk_acs("ACS_LRCORNER", 'j')
    _mk_acs("ACS_LTEE", 't')
    _mk_acs("ACS_RTEE", 'u')
    _mk_acs("ACS_BTEE", 'v')
    _mk_acs("ACS_TTEE", 'w')
    _mk_acs("ACS_HLINE", 'q')
    _mk_acs("ACS_VLINE", 'x')
    _mk_acs("ACS_PLUS", 'n')
    _mk_acs("ACS_S1", 'o')
    _mk_acs("ACS_S9", 's')
    _mk_acs("ACS_DIAMOND", '`')
    _mk_acs("ACS_CKBOARD", 'a')
    _mk_acs("ACS_DEGREE", 'f')
    _mk_acs("ACS_PLMINUS", 'g')
    _mk_acs("ACS_BULLET", '~')
    _mk_acs("ACS_LARROW", ',')
    _mk_acs("ACS_RARROW", '+')
    _mk_acs("ACS_DARROW", '.')
    _mk_acs("ACS_UARROW", '-')
    _mk_acs("ACS_BOARD", 'h')
    _mk_acs("ACS_LANTERN", 'i')
    _mk_acs("ACS_BLOCK", '0')
    _mk_acs("ACS_S3", 'p')
    _mk_acs("ACS_S7", 'r')
    _mk_acs("ACS_LEQUAL", 'y')
    _mk_acs("ACS_GEQUAL", 'z')
    _mk_acs("ACS_PI", '{')
    _mk_acs("ACS_NEQUAL", '|')
    _mk_acs("ACS_STERLING", '}')
    _mk_acs("ACS_BSSB", "ACS_ULCORNER")
    _mk_acs("ACS_SSBB", "ACS_LLCORNER")
    _mk_acs("ACS_BBSS", "ACS_URCORNER")
    _mk_acs("ACS_SBBS", "ACS_LRCORNER")
    _mk_acs("ACS_SBSS", "ACS_RTEE")
    _mk_acs("ACS_SSSB", "ACS_LTEE")
    _mk_acs("ACS_SSBS", "ACS_BTEE")
    _mk_acs("ACS_BSSS", "ACS_TTEE")
    _mk_acs("ACS_BSBS", "ACS_HLINE")
    _mk_acs("ACS_SBSB", "ACS_VLINE")
    _mk_acs("ACS_SSSS", "ACS_PLUS")


def initscr():
    if _initialised:
        lib.wrefresh(lib.stdscr)
        return Window(lib.stdscr)

    win = _check_NULL(lib.initscr())
    globals()['_initialised_setupterm'] = True
    globals()['_initialised'] = True

    _map_acs()

    globals()["LINES"] = lib.LINES
    globals()["COLS"] = lib.COLS

    return Window(win)


def setupterm(term=None, fd=-1):
    if fd == -1:
        # XXX: Check for missing stdout here?
        fd = sys.stdout.fileno()

    if _initialised_setupterm:
        return None

    if term is None:
        term = ffi.NULL
    err = ffi.new("int *")
    if lib.setupterm(term, fd, err) == lib.ERR:
        if err == 0:
            raise error("setupterm: could not find terminal")
        elif err == -1:
            raise error("setupterm: could not find terminfo database")
        else:
            raise error("setupterm: unknown error")

    globals()["_initialised_setupterm"] = True
    return None


def intrflush(ch):
    _ensure_initialised()
    return _check_ERR(lib.intrflush(ffi.NULL, ch), "intrflush")


# XXX: #ifdef HAVE_CURSES_IS_TERM_RESIZED
def is_term_resized(lines, columns):
    _ensure_initialised()
    return lib.is_term_resized(lines, columns)


if not lib._m_NetBSD:
    def keyname(ch):
        _ensure_initialised()
        if ch < 0:
            raise error("invalid key number")
        knp = lib.keyname(ch)
        if knp == ffi.NULL:
            return ""
        return ffi.string(knp)


def killchar():
    return lib.killchar()


def meta(ch):
    return _check_ERR(lib.meta(lib.stdscr, ch), "meta")


if lib._m_NCURSES_MOUSE_VERSION:

    def mouseinterval(interval):
        _ensure_initialised()
        return _check_ERR(lib.mouseinterval(interval), "mouseinterval")

    def mousemask(newmask):
        _ensure_initialised()
        oldmask = ffi.new("mmask_t *")
        availmask = lib.mousemask(newmask, oldmask)
        return (availmask, oldmask)


def napms(ms):
    _ensure_initialised()
    return lib.napms(ms)


def newpad(nlines, ncols):
    _ensure_initialised()
    return Window(_check_NULL(lib.newpad(nlines, ncols)))


def newwin(nlines, ncols, begin_y=None, begin_x=None):
    _ensure_initialised()
    if begin_x is None:
        if begin_y is not None:
            raise error("newwin requires 2 or 4 arguments")
        begin_y = begin_x = 0

    return Window(_check_NULL(lib.newwin(nlines, ncols, begin_y, begin_x)))


def pair_content(pair):
    _ensure_initialised_color()
    f = ffi.new("short *")
    b = ffi.new("short *")
    if lib.pair_content(pair, f, b) == lib.ERR:
        raise error("Argument 1 was out of range. (1..COLOR_PAIRS-1)")
    return (f, b)


def pair_number(pairvalue):
    _ensure_initialised_color()
    return (pairvalue & lib.A_COLOR) >> 8


def putp(text):
    text = _texttype(text)
    return _check_ERR(lib.putp(text), "putp")


def qiflush(flag=True):
    _ensure_initialised()
    if flag:
        lib.qiflush()
    else:
        lib.noqiflush()
    return None


# XXX: Do something about the following?
# /* Internal helper used for updating curses.LINES, curses.COLS, _curses.LINES
#  * and _curses.COLS */
# #if defined(HAVE_CURSES_RESIZETERM) || defined(HAVE_CURSES_RESIZE_TERM)
# static int
# update_lines_cols(void)
# {
#     PyObject *o;
#     PyObject *m = PyImport_ImportModuleNoBlock("curses");

#     if (!m)
#         return 0;

#     o = PyInt_FromLong(LINES);
#     if (!o) {
#         Py_DECREF(m);
#         return 0;
#     }
#     if (PyObject_SetAttrString(m, "LINES", o)) {
#         Py_DECREF(m);
#         Py_DECREF(o);
#         return 0;
#     }
#     if (PyDict_SetItemString(ModDict, "LINES", o)) {
#         Py_DECREF(m);
#         Py_DECREF(o);
#         return 0;
#     }
#     Py_DECREF(o);
#     o = PyInt_FromLong(COLS);
#     if (!o) {
#         Py_DECREF(m);
#         return 0;
#     }
#     if (PyObject_SetAttrString(m, "COLS", o)) {
#         Py_DECREF(m);
#         Py_DECREF(o);
#         return 0;
#     }
#     if (PyDict_SetItemString(ModDict, "COLS", o)) {
#         Py_DECREF(m);
#         Py_DECREF(o);
#         return 0;
#     }
#     Py_DECREF(o);
#     Py_DECREF(m);
#     return 1;
# }
# #endif

# #ifdef HAVE_CURSES_RESIZETERM
# static PyObject *
# PyCurses_ResizeTerm(PyObject *self, PyObject *args)
# {
#     int lines;
#     int columns;
#     PyObject *result;

#     PyCursesInitialised;

#     if (!PyArg_ParseTuple(args,"ii:resizeterm", &lines, &columns))
#         return NULL;

#     result = PyCursesCheckERR(resizeterm(lines, columns), "resizeterm");
#     if (!result)
#         return NULL;
#     if (!update_lines_cols())
#         return NULL;
#     return result;
# }

# #endif

# #ifdef HAVE_CURSES_RESIZE_TERM
# static PyObject *
# PyCurses_Resize_Term(PyObject *self, PyObject *args)
# {
#     int lines;
#     int columns;

#     PyObject *result;

#     PyCursesInitialised;

#     if (!PyArg_ParseTuple(args,"ii:resize_term", &lines, &columns))
#         return NULL;

#     result = PyCursesCheckERR(resize_term(lines, columns), "resize_term");
#     if (!result)
#         return NULL;
#     if (!update_lines_cols())
#         return NULL;
#     return result;
# }
# #endif /* HAVE_CURSES_RESIZE_TERM */


def setsyx(y, x):
    _ensure_initialised()
    lib.setsyx(y, x)
    return None


def start_color():
    _check_ERR(lib.start_color(), "start_color")
    globals()["COLORS"] = lib.COLORS
    globals()["COLOR_PAIRS"] = lib.COLOR_PAIRS
    globals()["_initialised_color"] = True
    return None


def tigetflag(capname):
    _ensure_initialised_setupterm()
    return lib.tigetflag(capname)


def tigetnum(capname):
    _ensure_initialised_setupterm()
    return lib.tigetnum(capname)


def tigetstr(capname):
    _ensure_initialised_setupterm()
    val = lib.tigetstr(capname)
    if int(ffi.cast("intptr_t", val)) in (0, -1):
        return None
    return ffi.string(val)


def tparm(fmt, i1=0, i2=0, i3=0, i4=0, i5=0, i6=0, i7=0, i8=0, i9=0):
    args = [ffi.cast("int", i) for i in (i1, i2, i3, i4, i5, i6, i7, i8, i9)]
    result = lib.tparm(fmt, *args)
    if result == ffi.NULL:
        raise error("tparm() returned NULL")
    return ffi.string(result)


def typeahead(fd):
    _ensure_initialised()
    return _check_ERR(lib.typeahead(fd), "typeahead")


def unctrl(ch):
    _ensure_initialised()
    return lib.unctrl(_chtype(ch))


def ungetch(ch):
    _ensure_initialised()
    return _check_ERR(lib.ungetch(_chtype(ch)), "ungetch")


def use_env(flag):
    lib.use_env(flag)
    return None


if not lib._m_STRICT_SYSV_CURSES:

    def use_default_colors():
        _ensure_initialised_color()
        return _check_ERR(lib.use_default_colors(), "use_default_colors")
