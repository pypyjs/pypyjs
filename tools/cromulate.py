#
#  Improve compressibility of emscripten-generated javascript,
#  by moving similar functions closer together in the source.
#

import os
import sys
import zlib
import optparse
import tempfile
from collections import deque

MARKER_START_FUNCS = "// EMSCRIPTEN_START_FUNCS"
MARKER_END_FUNCS = "// EMSCRIPTEN_END_FUNCS"


def cromulate(fileobj, opts, on_progress=None):
    # Split out the code for each individual function.
    # We don't have to actually *parse* it, just chunk it up.
    # XXX TODO: read incrementally to reduce memory usage.
    data = fileobj.read()
    pre_code, data = data.split(MARKER_START_FUNCS, 1)
    data, post_code = data.split(MARKER_END_FUNCS, 1)
    functions = data.split("function ")

    def get_compressed_length(data):
        return len(zlib.compress(data, opts.compress_level))

    # Pre-calculate the compressed length of each individual function.
    # Note that functions[0] is leading whitespace, not a real function.
    compressed_lengths = [0]
    for i in xrange(1, len(functions)):
        compressed_lengths.append(get_compressed_length(functions[i]))

    # We will judge the utility of having A and B adjacent by the difference
    # between their individual compressed sizes, and their size when
    # compressed together.  Smaller values are better.
    def score_func_pair(i, j, flip=False):
        func1 = functions[i]
        func2 = functions[j]
        original = compressed_lengths[i] + compressed_lengths[j]
        if not flip:
            combined = get_compressed_length(func1 + func2)
        else:
            combined = get_compressed_length(func2 + func1)
        return combined - original

    # Use a deque so that we can add at either head or tail.
    reordered_functions = deque()

    # Keep track of the function currently at each end of the deque,
    # and a pool of candidate functions that may be written next.
    # XXX TODO: try to pick a "good" starting function?
    head = tail = 1
    if opts.window_size <= 0:
        seen = len(functions)
    else:
        seen = min(opts.window_size + 2, len(functions))
    pending = set(range(2, seen))
    reordered_functions.appendleft(functions[head])

    # While we have functions left to append, pick the one that gives
    # the best compression either at head of tail of the deque.
    # XXX TODO: consider several funcs from head/tail when choosing?
    on_progress(0, len(functions))
    while pending:
        # Find the best pending function.
        best_score = float("inf")
        best_func = iter(pending).next()
        best_is_tail = True
        for func in pending:
            score_tail = score_func_pair(tail, func)
            if score_tail < best_score:
                best_score = score_tail
                best_func = func
                best_is_tail = True
            score_head = score_func_pair(head, func, flip=True)
            if score_head < best_score:
                best_score = score_head
                best_func = func
                best_is_tail = False
        # Append it on the appropriate end of the deque.
        pending.remove(best_func)
        if best_is_tail:
            tail = best_func
            reordered_functions.append(functions[tail])
        else:
            head = best_func
            reordered_functions.appendleft(functions[head])
        # Slurp in another pending function to replace it.
        if seen < len(functions):
            pending.add(seen)
            seen += 1
        if on_progress is not None:
            on_progress(len(reordered_functions), len(functions))

    # Add the leading whitespace to ensure overall bytelength stays constant.
    reordered_functions.appendleft(functions[0])

    # Sanity-check that we haven't accidentally a function.
    assert set(functions) == set(reordered_functions)

    # That's it.  Re-assemble the full code string.
    return "".join((
        pre_code,
        MARKER_START_FUNCS,
        "function ".join(reordered_functions),
        MARKER_END_FUNCS,
        post_code,
    ))


def print_percent_complete(done, total):
    """Display simple textual progress indicator on stdout."""
    perc = 100.0 * done / total
    status = "\rCromulated {:d} of {:d} functions ({:.1f}%)"
    sys.stdout.write(status.format(done, total, perc))
    sys.stdout.flush()


def main(args=None):
    usage = "usage: %prog [options] [file ...]"
    descr = "Improve compressibility of emscripten-generated javascript"
    parser = optparse.OptionParser(usage=usage, description=descr)
    parser.add_option("-w", "--window-size", type=int, default=500,
                      metavar="SZ",
                      help="number of functions to consider per step")
    parser.add_option("-l", "--compress-level", type=int, default=9,
                      metavar="N",
                      help="zlib compress level used when comparing functions")
    parser.add_option("-c", "--stdout", action="store_true",
                      help="write output to stdout")
    parser.add_option("-q", "--quiet", action="store_true",
                      help="supress printing of progress messages")

    opts, files = parser.parse_args(args)
    if not files:
        files = [sys.stdin]
        opts.stdout = True
        opts.quiet = True
    else:
        files = [open(f, "r") for f in files]

    on_progress = None
    if not opts.quiet:
        on_progress = print_percent_complete

    for f in files:
        output = cromulate(f, opts, on_progress)
        if not opts.quiet:
            sys.stdout.write("\n")
        # XXX TODO: if we wanted to get really fancy, we could calculate
        # the expected saving of the new ordering and then pass it through
        # the cromulation again, iterating until we fail to improve the
        # existing ordering in the file.  This would also guard against
        # accidentally increasing the file size.
        if opts.stdout:
            sys.stdout.write(output)
        else:
            dirnm = os.path.dirname(f.name)
            filenm = os.path.basename(f.name)
            fd, tempnm = tempfile.mkstemp(dir=dirnm, prefix=filenm)
            try:
                os.write(fd, output)
                os.close(fd)
                os.rename(tempnm, f.name)
            finally:
                if os.path.exists(tempnm):
                    os.unlink(tempnm)

    return 0


if __name__ == "__main__":
    try:
        exitcode = main()
    except KeyboardInterrupt:
        exitcode = 1
    sys.exit(exitcode)
