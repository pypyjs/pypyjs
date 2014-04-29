"""Imported by app_main.py when PyPy needs to fire up the interactive console.
"""
import sys
import os


def interactive_console(mainmodule=None, quiet=False):
    # set sys.{ps1,ps2} just before invoking the interactive interpreter. This
    # mimics what CPython does in pythonrun.c
    if not hasattr(sys, 'ps1'):
        sys.ps1 = '>>>> '
    if not hasattr(sys, 'ps2'):
        sys.ps2 = '.... '
    #
    if not quiet:
        try:
            from _pypy_irc_topic import some_topic
            text = "And now for something completely different: ``%s''" % (
                some_topic(),)
            while len(text) >= 80:
                i = text[:80].rfind(' ')
                print(text[:i])
                text = text[i+1:]
            print(text)
        except ImportError:
            pass
    #
    try:
        if not os.isatty(sys.stdin.fileno()):
            # Bail out if stdin is not tty-like, as pyrepl wouldn't be happy
            # For example, with:
            # subprocess.Popen(['pypy', '-i'], stdin=subprocess.PIPE)
            raise ImportError
        from pyrepl.simple_interact import check
        if not check():
            raise ImportError
        from pyrepl.simple_interact import run_multiline_interactive_console
    except ImportError:
        run_simple_interactive_console(mainmodule)
    else:
        run_multiline_interactive_console(mainmodule)

def run_simple_interactive_console(mainmodule):
    import code
    if mainmodule is None:
        import __main__ as mainmodule
    console = code.InteractiveConsole(mainmodule.__dict__, filename='<stdin>')
    # some parts of code.py are copied here because it seems to be impossible
    # to start an interactive console without printing at least one line
    # of banner
    more = 0
    while 1:
        try:
            if more:
                prompt = getattr(sys, 'ps2', '... ')
            else:
                prompt = getattr(sys, 'ps1', '>>> ')
            try:
                line = raw_input(prompt)
                # Can be None if sys.stdin was redefined
                encoding = getattr(sys.stdin, 'encoding', None)
                if encoding and not isinstance(line, unicode):
                    line = line.decode(encoding)
            except EOFError:
                console.write("\n")
                break
            else:
                more = console.push(line)
        except KeyboardInterrupt:
            console.write("\nKeyboardInterrupt\n")
            console.resetbuffer()
            more = 0

# ____________________________________________________________

if __name__ == '__main__':    # for testing
    if os.getenv('PYTHONSTARTUP'):
        execfile(os.getenv('PYTHONSTARTUP'))
    interactive_console()
