__all__ = ['average']

from ..core.numeric import array

def average(a):
    # This implements a weighted average, for now we don't implement the
    # weighting, just the average part!
    if not hasattr(a, "mean"):
        a = array(a)
    return a.mean()
