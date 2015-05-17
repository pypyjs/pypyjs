#
# StringIO-based cStringIO implementation.
#

# Note that PyPy also contains a built-in module 'cStringIO' which will hide
# this one if compiled in.

from StringIO import *
from StringIO import __doc__

class StringIO(StringIO):
    def reset(self):
        """
        reset() -- Reset the file position to the beginning
        """
        self.seek(0, 0)
