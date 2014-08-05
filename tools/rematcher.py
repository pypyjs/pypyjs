
import os
import sys

from time import time as clock

from rpython.rlib import jit
from rpython.rlib import rrandom
from rpython.jit.codewriter.policy import JitPolicy


# The regex is built up from a combination individual Regex objects.
# Each is responsiblef for implementing a specific operator.

class Regex(object):

    _immutable_fields_ = ["empty"]

    def __init__(self, empty):
        self.empty = empty
        self.marked = 0

    def reset(self):
        self.marked = 0

    def shift(self, c, mark):
        marked = self._shift(c, mark)
        self.marked = marked
        return marked


class Char(Regex):

    _immutable_fields_ = ["c"]

    def __init__(self, c):
        Regex.__init__(self, 0)
        self.c = c

    def _shift(self, c, mark):
        return mark & (c == self.c)


class Epsilon(Regex):

    def __init__(self):
        Regex.__init__(self, empty=1)

    def _shift(self, c, mark):
        return 0


class Binary(Regex):

    _immutable_fields_ = ["left", "right"]

    def __init__(self, left, right, empty):
        Regex.__init__(self, empty)
        self.left = left
        self.right = right

    def reset(self):
        self.left.reset()
        self.right.reset()
        Regex.reset(self)


class Alternative(Binary):

    def __init__(self, left, right):
        empty = left.empty | right.empty
        Binary.__init__(self, left, right, empty)

    def _shift(self, c, mark):
        marked_left  = self.left.shift(c, mark)
        marked_right = self.right.shift(c, mark)
        return marked_left | marked_right


class Repetition(Regex):

    _immutable_fields_ = ["re"]

    def __init__(self, re):
        Regex.__init__(self, 1)
        self.re = re

    def _shift(self, c, mark):
        return self.re.shift(c, mark | self.marked)

    def reset(self):
        self.re.reset()
        Regex.reset(self)


class Sequence(Binary):

    def __init__(self, left, right):
        empty = left.empty & right.empty
        Binary.__init__(self, left, right, empty)

    def _shift(self, c, mark):
        old_marked_left = self.left.marked
        marked_left = self.left.shift(c, mark)
        marked_right = self.right.shift(
            c, old_marked_left | (mark & self.left.empty))
        return (marked_left & self.right.empty) | marked_right


# The matching loop just shifts each characer from the input string
# into the regex object.  If it's "marked" by the time we hit the
# end of the string, then it matches.

jitdriver = jit.JitDriver(reds="auto", greens=["re"])

def match(re, s):
    if not s:
        return re.empty
    result = re.shift(s[0], 1)
    i = 1
    while i < len(s):
        jitdriver.jit_merge_point(re=re)
        result = re.shift(s[i], 0)
        i += 1
    re.reset()
    return result


def entry_point(argv):
    # Adjust the amount of work we do based on command-line arguments.
    # NUM_INPUTS increases the number of loop iterations.
    # INPUT_LENGTH increases the amount of work done per loop iteration.
    NUM_INPUTS = 1000
    INPUT_LENGTH = 50
    if len(argv) > 1:
        NUM_INPUTS = int(argv[1])
    if len(argv) > 2:
        INPUT_LENGTH = int(argv[2])
    if len(argv) > 3:
        raise RuntimeError("too many arguments")

    # Build up the regex pattern.
    # Target pattern: (a|b)*a(a|b){20}a(a|b)*
    # For now we use the same pattern every time, but it must be
    # dynamically constructed or it gets eliminated at compile-time.
    prefix = Sequence(Repetition(Alternative(Char("a"), Char("b"))), Char("a"))
    suffix = Sequence(Char("a"), Repetition(Alternative(Char("a"), Char("b"))))
    pattern = prefix
    for _ in xrange(20):
        pattern = Sequence(pattern,  Alternative(Char("a"), Char("b")))
    pattern = Sequence(pattern, suffix)

    # Generate "random input" to match against the pattern.
    # Ideally this would come from the outside world, but stdio
    # on pypy.js doesn't seem to work just yet.
    print "Generating", NUM_INPUTS, "strings of length", INPUT_LENGTH, "..."
    inputs = [None] * NUM_INPUTS
    r = rrandom.Random(42)
    for i in xrange(len(inputs)):
        s = []
        for _ in xrange(INPUT_LENGTH):
            if r.random() > 0.5:
                s.append("a")
            else:
                s.append("b")
        inputs[i] = "".join(s)

    # Run each input string through the regex.
    # Time how long it takes for the total run.
    print "Matching all strings against the regex..."
    ts = clock()
    for i in xrange(len(inputs)):
        # No output, we just want to exercise the loop.
        matched = match(pattern, inputs[i])
    tdiff = clock() - ts
    print "Done!"
    print "Matching time for %d strings: %f" % (len(inputs), tdiff)
    print "Performed %f matches per second." % (len(inputs) / tdiff,)
    return 0


def jitpolicy(driver):
    return JitPolicy()


def target(*args):
    return entry_point, None


if __name__ == "__main__":
    sys.exit(entry_point(sys.argv))
