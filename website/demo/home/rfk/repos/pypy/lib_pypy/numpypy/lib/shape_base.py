__all__ = ['dstack']

from ..core import numeric as _nx
from ..core import atleast_3d

def dstack(tup):
    """
    Stack arrays in sequence depth wise (along third axis).

    Takes a sequence of arrays and stack them along the third axis
    to make a single array. Rebuilds arrays divided by `dsplit`.
    This is a simple way to stack 2D arrays (images) into a single
    3D array for processing.

    Parameters
    ----------
    tup : sequence of arrays
        Arrays to stack. All of them must have the same shape along all
        but the third axis.

    Returns
    -------
    stacked : ndarray
        The array formed by stacking the given arrays.

    See Also
    --------
    vstack : Stack along first axis.
    hstack : Stack along second axis.
    concatenate : Join arrays.
    dsplit : Split array along third axis.

    Notes
    -----
    Equivalent to ``np.concatenate(tup, axis=2)``.

    Examples
    --------
    >>> a = np.array((1,2,3))
    >>> b = np.array((2,3,4))
    >>> np.dstack((a,b))
    array([[[1, 2],
            [2, 3],
            [3, 4]]])

    >>> a = np.array([[1],[2],[3]])
    >>> b = np.array([[2],[3],[4]])
    >>> np.dstack((a,b))
    array([[[1, 2]],
           [[2, 3]],
           [[3, 4]]])

    """
    return _nx.concatenate(map(atleast_3d,tup),2)
