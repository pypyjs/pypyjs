"""
This is just enough of a "signal" module for PyPy.js that things won't usually crash.
"""


ITIMER_PROF = ITIMER_REAL = ITIMER_VIRTUAL = ItimerError = NSIG = SIGABRT = SIGALRM = SIGBUS = None
SIGCHLD = SIGCLD = SIGCONT = SIGFPE = SIGHUP = SIGILL = SIGINT = SIGIO = SIGIOT = SIGKILL = None
SIGPIPE = SIGPOLL = SIGPROF = SIGPWR = SIGQUIT = SIGRTMAX = SIGRTMIN = SIGSEGV = SIGSTOP = None
SIGSYS = SIGTERM = SIGTRAP = SIGTSTP = SIGTTIN = SIGTTOU = SIGURG = SIGUSR1 = SIGUSR2 = None
SIGVTALRM = SIGWINCH = SIGXCPU = SIGXFSZ = SIG_DFL = SIG_IGN = None


def default_int_handler(*args):
    return None


def getsignal(*args):
    return None


def signal(*args):
    return None


def siginterrupt(*args):
    return None
