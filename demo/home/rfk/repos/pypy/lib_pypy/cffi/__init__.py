__all__ = ['FFI', 'VerificationError', 'VerificationMissing', 'CDefError',
           'FFIError']

from .api import FFI, CDefError, FFIError
from .ffiplatform import VerificationError, VerificationMissing

__version__ = "0.7"
__version_info__ = (0, 7)
