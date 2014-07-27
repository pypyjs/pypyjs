import unittest

from ctypes import *
import _ctypes_test

lib = CDLL(_ctypes_test.__file__)

class LibTest(unittest.TestCase):
    def test_sqrt(self):
        lib.my_sqrt.argtypes = c_double,
        lib.my_sqrt.restype = c_double
        self.assertEqual(lib.my_sqrt(4.0), 2.0)
        import math
        self.assertEqual(lib.my_sqrt(2.0), math.sqrt(2.0))

    def test_qsort(self):
        comparefunc = CFUNCTYPE(c_int, POINTER(c_char), POINTER(c_char))
        lib.my_qsort.argtypes = c_void_p, c_size_t, c_size_t, comparefunc
        lib.my_qsort.restype = None

        def sort(a, b):
            return cmp(a[0], b[0])

        chars = create_string_buffer("spam, spam, and spam")
        lib.my_qsort(chars, len(chars)-1, sizeof(c_char), comparefunc(sort))
        self.assertEqual(chars.raw, "   ,,aaaadmmmnpppsss\x00")

    def SKIPPED_test_no_more_xfail(self):
        # We decided to not explicitly support the whole ctypes-2.7
        # and instead go for a case-by-case, demand-driven approach.
        # So this test is skipped instead of failing.
        import socket
        import ctypes.test
        self.assertTrue(not hasattr(ctypes.test, 'xfail'),
                        "You should incrementally grep for '@xfail' and remove them, they are real failures")

if __name__ == "__main__":
    unittest.main()
