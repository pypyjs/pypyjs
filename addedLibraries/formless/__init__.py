# Copyright (c) 2004 Divmod.
# See LICENSE for details.

# FIXME: remove next two lines after fixing compyCompat to have lazy importing.
#        or else moving formless' adapter registration here.
import nevow
del nevow

from formless.annotate import *
from formless.processors import process
