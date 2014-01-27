import numeric
from numeric import *
import fromnumeric
from fromnumeric import *
import shape_base
from shape_base import *

from fromnumeric import amax as max, amin as min
from numeric import absolute as abs

__all__ = []
__all__ += numeric.__all__
__all__ += fromnumeric.__all__
__all__ += shape_base.__all__
