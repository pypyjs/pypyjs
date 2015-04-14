
import os
import re
import sys
import optparse

MARKER_START_FUNCS = "// EMSCRIPTEN_START_FUNCS"
MARKER_END_FUNCS = "// EMSCRIPTEN_END_FUNCS"

FUNCTION_CODE_RE = re.compile(
  r"function (?P<name>[a-zA-Z0-9_]+)(?P<defn>.*?)((?=function)|(?=$))"
)


def analyze_code_size(fileobj, opts):
    funcs = {}
    name_re = None
    if opts.grep is not None:
      name_re = re.compile(opts.grep, re.I)
    # Split out and analyze the code for each individual function.
    # XXX TODO: read incrementally to reduce memory usage.
    data = fileobj.read()
    pre_code, data = data.split(MARKER_START_FUNCS, 1)
    data, post_code = data.split(MARKER_END_FUNCS, 1)
    for match in FUNCTION_CODE_RE.finditer(data):
        name = match.group("name")
        defn = match.group("defn")
        if name_re and not name_re.search(name):
            continue
        funcs[name] = FunctionMetrics(name, defn)
    # Print summary metrics.
    total = 0
    funcs_by_size = ((f.size, f.name) for f in funcs.itervalues())
    for (size, name) in sorted(funcs_by_size, reverse=True):
        print size, name, human_readable(size)
        total += size
    print "Total size:", total, human_readable(total)


class FunctionMetrics(object):

    def __init__(self, name, defn):
        self.name = name
        self.defn = defn
        self.size = len(defn)


def human_readable(size):
    units = ((1024*1024, "M"), (1024, "k"))
    for (scale, unit) in units:
        scale = float(scale)
        if size / scale > 0.1:
            return "(%.2f%s)" % (size / scale, unit)
    return ""
    


def main(args=None):
    usage = "usage: %prog [options] file"
    descr = "Analyze code size and complexity for emscripten-compiled output"
    parser = optparse.OptionParser(usage=usage, description=descr)
    parser.add_option("-g", "--grep", metavar="REGEXP",
                      help="only analyze functions matching this regexp")

    opts, args = parser.parse_args(args)
    with open(args[0], "r") as infile:
        analyze_code_size(infile, opts)
    return 0


if __name__ == "__main__":
    try:
        exitcode = main()
    except KeyboardInterrupt:
        exitcode = 1
    sys.exit(exitcode)
