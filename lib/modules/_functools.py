""" Supplies the internal functions for functools.py in the standard library """

# reduce() has moved to _functools in Python 2.6+.
reduce = reduce

class partial(object):
    """
    partial(func, *args, **keywords) - new function with partial application
    of the given arguments and keywords.
    """

    def __init__(self, func, *args, **keywords):
        if not callable(func):
            raise TypeError("the first argument must be callable")
        self.func = func
        self.args = args
        self.keywords = keywords or None

    def __call__(self, *fargs, **fkeywords):
        if self.keywords is not None:
            fkeywords = dict(self.keywords, **fkeywords)
        return self.func(*(self.args + fargs), **fkeywords)

    def __reduce__(self):
        d = dict((k, v) for k, v in self.__dict__.iteritems() if k not in
                ('func', 'args', 'keywords'))
        if len(d) == 0:
            d = None
        return (type(self), (self.func,),
                (self.func, self.args, self.keywords, d))

    def __setstate__(self, state):
        self.func, self.args, self.keywords, d = state
        if d is not None:
            self.__dict__.update(d)
