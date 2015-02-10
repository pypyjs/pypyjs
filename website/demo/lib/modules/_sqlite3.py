#-*- coding: utf-8 -*-
# pysqlite2/dbapi.py: pysqlite DB-API module
#
# Copyright (C) 2007-2008 Gerhard Häring <gh@ghaering.de>
#
# This file is part of pysqlite.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.
#
# Note: This software has been modified for use in PyPy.

from collections import OrderedDict
from functools import wraps
import datetime
import string
import sys
import weakref
from threading import _get_ident as _thread_get_ident
try:
    from __pypy__ import newlist_hint
except ImportError:
    assert '__pypy__' not in sys.builtin_module_names
    newlist_hint = lambda sizehint: []

if sys.version_info[0] >= 3:
    StandardError = Exception
    cmp = lambda x, y: (x > y) - (x < y)
    long = int
    xrange = range
    basestring = unicode = str
    buffer = memoryview
    _BLOB_TYPE = bytes
else:
    _BLOB_TYPE = buffer

from cffi import FFI as _FFI

_ffi = _FFI()

_ffi.cdef("""
#define SQLITE_OK ...
#define SQLITE_ERROR ...
#define SQLITE_INTERNAL ...
#define SQLITE_PERM ...
#define SQLITE_ABORT ...
#define SQLITE_BUSY ...
#define SQLITE_LOCKED ...
#define SQLITE_NOMEM ...
#define SQLITE_READONLY ...
#define SQLITE_INTERRUPT ...
#define SQLITE_IOERR ...
#define SQLITE_CORRUPT ...
#define SQLITE_NOTFOUND ...
#define SQLITE_FULL ...
#define SQLITE_CANTOPEN ...
#define SQLITE_PROTOCOL ...
#define SQLITE_EMPTY ...
#define SQLITE_SCHEMA ...
#define SQLITE_TOOBIG ...
#define SQLITE_CONSTRAINT ...
#define SQLITE_MISMATCH ...
#define SQLITE_MISUSE ...
#define SQLITE_NOLFS ...
#define SQLITE_AUTH ...
#define SQLITE_FORMAT ...
#define SQLITE_RANGE ...
#define SQLITE_NOTADB ...
#define SQLITE_ROW ...
#define SQLITE_DONE ...
#define SQLITE_INTEGER ...
#define SQLITE_FLOAT ...
#define SQLITE_BLOB ...
#define SQLITE_NULL ...
#define SQLITE_TEXT ...
#define SQLITE3_TEXT ...

#define SQLITE_TRANSIENT ...
#define SQLITE_UTF8 ...

#define SQLITE_DENY ...
#define SQLITE_IGNORE ...

#define SQLITE_CREATE_INDEX ...
#define SQLITE_CREATE_TABLE ...
#define SQLITE_CREATE_TEMP_INDEX ...
#define SQLITE_CREATE_TEMP_TABLE ...
#define SQLITE_CREATE_TEMP_TRIGGER ...
#define SQLITE_CREATE_TEMP_VIEW ...
#define SQLITE_CREATE_TRIGGER ...
#define SQLITE_CREATE_VIEW ...
#define SQLITE_DELETE ...
#define SQLITE_DROP_INDEX ...
#define SQLITE_DROP_TABLE ...
#define SQLITE_DROP_TEMP_INDEX ...
#define SQLITE_DROP_TEMP_TABLE ...
#define SQLITE_DROP_TEMP_TRIGGER ...
#define SQLITE_DROP_TEMP_VIEW ...
#define SQLITE_DROP_TRIGGER ...
#define SQLITE_DROP_VIEW ...
#define SQLITE_INSERT ...
#define SQLITE_PRAGMA ...
#define SQLITE_READ ...
#define SQLITE_SELECT ...
#define SQLITE_TRANSACTION ...
#define SQLITE_UPDATE ...
#define SQLITE_ATTACH ...
#define SQLITE_DETACH ...
#define SQLITE_ALTER_TABLE ...
#define SQLITE_REINDEX ...
#define SQLITE_ANALYZE ...
#define SQLITE_CREATE_VTABLE ...
#define SQLITE_DROP_VTABLE ...
#define SQLITE_FUNCTION ...

const char *sqlite3_libversion(void);

typedef ... sqlite3;
typedef ... sqlite3_stmt;
typedef ... sqlite3_context;
typedef ... sqlite3_value;
typedef int64_t sqlite3_int64;
typedef uint64_t sqlite3_uint64;

int sqlite3_open(
    const char *filename,   /* Database filename (UTF-8) */
    sqlite3 **ppDb          /* OUT: SQLite db handle */
);

int sqlite3_close(sqlite3 *);

int sqlite3_busy_timeout(sqlite3*, int ms);
int sqlite3_prepare_v2(
    sqlite3 *db,            /* Database handle */
    const char *zSql,       /* SQL statement, UTF-8 encoded */
    int nByte,              /* Maximum length of zSql in bytes. */
    sqlite3_stmt **ppStmt,  /* OUT: Statement handle */
    const char **pzTail     /* OUT: Pointer to unused portion of zSql */
);
int sqlite3_finalize(sqlite3_stmt *pStmt);
int sqlite3_data_count(sqlite3_stmt *pStmt);
int sqlite3_column_count(sqlite3_stmt *pStmt);
const char *sqlite3_column_name(sqlite3_stmt*, int N);
int sqlite3_get_autocommit(sqlite3*);
int sqlite3_reset(sqlite3_stmt *pStmt);
int sqlite3_step(sqlite3_stmt*);
int sqlite3_errcode(sqlite3 *db);
const char *sqlite3_errmsg(sqlite3*);
int sqlite3_changes(sqlite3*);

int sqlite3_bind_blob(sqlite3_stmt*, int, const void*, int n, void(*)(void*));
int sqlite3_bind_double(sqlite3_stmt*, int, double);
int sqlite3_bind_int(sqlite3_stmt*, int, int);
int sqlite3_bind_int64(sqlite3_stmt*, int, sqlite3_int64);
int sqlite3_bind_null(sqlite3_stmt*, int);
int sqlite3_bind_text(sqlite3_stmt*, int, const char*, int n, void(*)(void*));
int sqlite3_bind_text16(sqlite3_stmt*, int, const void*, int, void(*)(void*));
int sqlite3_bind_value(sqlite3_stmt*, int, const sqlite3_value*);
int sqlite3_bind_zeroblob(sqlite3_stmt*, int, int n);

const void *sqlite3_column_blob(sqlite3_stmt*, int iCol);
int sqlite3_column_bytes(sqlite3_stmt*, int iCol);
double sqlite3_column_double(sqlite3_stmt*, int iCol);
int sqlite3_column_int(sqlite3_stmt*, int iCol);
sqlite3_int64 sqlite3_column_int64(sqlite3_stmt*, int iCol);
const unsigned char *sqlite3_column_text(sqlite3_stmt*, int iCol);
const void *sqlite3_column_text16(sqlite3_stmt*, int iCol);
int sqlite3_column_type(sqlite3_stmt*, int iCol);
const char *sqlite3_column_decltype(sqlite3_stmt*,int);

void sqlite3_progress_handler(sqlite3*, int, int(*)(void*), void*);
int sqlite3_create_collation(
    sqlite3*,
    const char *zName,
    int eTextRep,
    void*,
    int(*xCompare)(void*,int,const void*,int,const void*)
);
int sqlite3_set_authorizer(
    sqlite3*,
    int (*xAuth)(void*,int,const char*,const char*,const char*,const char*),
    void *pUserData
);
int sqlite3_create_function(
    sqlite3 *db,
    const char *zFunctionName,
    int nArg,
    int eTextRep,
    void *pApp,
    void (*xFunc)(sqlite3_context*,int,sqlite3_value**),
    void (*xStep)(sqlite3_context*,int,sqlite3_value**),
    void (*xFinal)(sqlite3_context*)
);
void *sqlite3_aggregate_context(sqlite3_context*, int nBytes);

sqlite3_int64 sqlite3_last_insert_rowid(sqlite3*);
int sqlite3_bind_parameter_count(sqlite3_stmt*);
const char *sqlite3_bind_parameter_name(sqlite3_stmt*, int);
int sqlite3_total_changes(sqlite3*);

int sqlite3_prepare(
    sqlite3 *db,            /* Database handle */
    const char *zSql,       /* SQL statement, UTF-8 encoded */
    int nByte,              /* Maximum length of zSql in bytes. */
    sqlite3_stmt **ppStmt,  /* OUT: Statement handle */
    const char **pzTail     /* OUT: Pointer to unused portion of zSql */
);

void sqlite3_result_blob(sqlite3_context*, const void*, int, void(*)(void*));
void sqlite3_result_double(sqlite3_context*, double);
void sqlite3_result_error(sqlite3_context*, const char*, int);
void sqlite3_result_error16(sqlite3_context*, const void*, int);
void sqlite3_result_error_toobig(sqlite3_context*);
void sqlite3_result_error_nomem(sqlite3_context*);
void sqlite3_result_error_code(sqlite3_context*, int);
void sqlite3_result_int(sqlite3_context*, int);
void sqlite3_result_int64(sqlite3_context*, sqlite3_int64);
void sqlite3_result_null(sqlite3_context*);
void sqlite3_result_text(sqlite3_context*, const char*, int, void(*)(void*));
void sqlite3_result_text16(sqlite3_context*, const void*, int, void(*)(void*));
void sqlite3_result_text16le(sqlite3_context*,const void*, int,void(*)(void*));
void sqlite3_result_text16be(sqlite3_context*,const void*, int,void(*)(void*));
void sqlite3_result_value(sqlite3_context*, sqlite3_value*);
void sqlite3_result_zeroblob(sqlite3_context*, int n);

const void *sqlite3_value_blob(sqlite3_value*);
int sqlite3_value_bytes(sqlite3_value*);
int sqlite3_value_bytes16(sqlite3_value*);
double sqlite3_value_double(sqlite3_value*);
int sqlite3_value_int(sqlite3_value*);
sqlite3_int64 sqlite3_value_int64(sqlite3_value*);
const unsigned char *sqlite3_value_text(sqlite3_value*);
const void *sqlite3_value_text16(sqlite3_value*);
const void *sqlite3_value_text16le(sqlite3_value*);
const void *sqlite3_value_text16be(sqlite3_value*);
int sqlite3_value_type(sqlite3_value*);
int sqlite3_value_numeric_type(sqlite3_value*);
""")

def _has_load_extension():
    """Only available since 3.3.6"""
    unverified_ffi = _FFI()
    unverified_ffi.cdef("""
    typedef ... sqlite3;
    int sqlite3_enable_load_extension(sqlite3 *db, int onoff);
    """)
    libname = 'sqlite3'
    if sys.platform == 'win32':
        import os
        _libname = os.path.join(os.path.dirname(sys.executable), libname)
        if os.path.exists(_libname + '.dll'):
            libname = _libname
    unverified_lib = unverified_ffi.dlopen(libname)
    return hasattr(unverified_lib, 'sqlite3_enable_load_extension')

if _has_load_extension():
    _ffi.cdef("int sqlite3_enable_load_extension(sqlite3 *db, int onoff);")

if sys.platform.startswith('freebsd'):
    _lib = _ffi.verify("""
    #include <sqlite3.h>
    """, libraries=['sqlite3'],
         include_dirs=['/usr/local/include'],
         library_dirs=['/usr/local/lib']
    )
else:
    _lib = _ffi.verify("""
    #include <sqlite3.h>
    """, libraries=['sqlite3']
    )

exported_sqlite_symbols = [
    'SQLITE_ALTER_TABLE',
    'SQLITE_ANALYZE',
    'SQLITE_ATTACH',
    'SQLITE_CREATE_INDEX',
    'SQLITE_CREATE_TABLE',
    'SQLITE_CREATE_TEMP_INDEX',
    'SQLITE_CREATE_TEMP_TABLE',
    'SQLITE_CREATE_TEMP_TRIGGER',
    'SQLITE_CREATE_TEMP_VIEW',
    'SQLITE_CREATE_TRIGGER',
    'SQLITE_CREATE_VIEW',
    'SQLITE_DELETE',
    'SQLITE_DENY',
    'SQLITE_DETACH',
    'SQLITE_DROP_INDEX',
    'SQLITE_DROP_TABLE',
    'SQLITE_DROP_TEMP_INDEX',
    'SQLITE_DROP_TEMP_TABLE',
    'SQLITE_DROP_TEMP_TRIGGER',
    'SQLITE_DROP_TEMP_VIEW',
    'SQLITE_DROP_TRIGGER',
    'SQLITE_DROP_VIEW',
    'SQLITE_IGNORE',
    'SQLITE_INSERT',
    'SQLITE_OK',
    'SQLITE_PRAGMA',
    'SQLITE_READ',
    'SQLITE_REINDEX',
    'SQLITE_SELECT',
    'SQLITE_TRANSACTION',
    'SQLITE_UPDATE',
]

for symbol in exported_sqlite_symbols:
    globals()[symbol] = getattr(_lib, symbol)

_SQLITE_TRANSIENT = _ffi.cast('void *', _lib.SQLITE_TRANSIENT)

# pysqlite version information
version = "2.6.0"

# pysqlite constants
PARSE_COLNAMES = 1
PARSE_DECLTYPES = 2

# SQLite version information
sqlite_version = str(_ffi.string(_lib.sqlite3_libversion()).decode('ascii'))

_STMT_TYPE_UPDATE = 0
_STMT_TYPE_DELETE = 1
_STMT_TYPE_INSERT = 2
_STMT_TYPE_REPLACE = 3
_STMT_TYPE_OTHER = 4
_STMT_TYPE_SELECT = 5
_STMT_TYPE_INVALID = 6


class Error(StandardError):
    pass


class Warning(StandardError):
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class InternalError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class DataError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


def connect(database, timeout=5.0, detect_types=0, isolation_level="",
                 check_same_thread=True, factory=None, cached_statements=100):
    factory = Connection if not factory else factory
    return factory(database, timeout, detect_types, isolation_level,
                    check_same_thread, factory, cached_statements)


def _unicode_text_factory(x):
    return unicode(x, 'utf-8')

if sys.version_info[0] < 3:
    def OptimizedUnicode(s):
        try:
            val = unicode(s, "ascii").encode("ascii")
        except UnicodeDecodeError:
            val = unicode(s, "utf-8")
        return val
else:
    OptimizedUnicode = _unicode_text_factory


class _StatementCache(object):
    def __init__(self, connection, maxcount):
        self.connection = connection
        self.maxcount = maxcount
        self.cache = OrderedDict()

    def get(self, sql):
        try:
            stat = self.cache[sql]
        except KeyError:
            stat = Statement(self.connection, sql)
            self.cache[sql] = stat
            if len(self.cache) > self.maxcount:
                self.cache.popitem(0)
        else:
            if stat._in_use:
                stat = Statement(self.connection, sql)
                self.cache[sql] = stat
        return stat


class Connection(object):
    __initialized = False
    _db = None

    def __init__(self, database, timeout=5.0, detect_types=0, isolation_level="",
                 check_same_thread=True, factory=None, cached_statements=100):
        self.__initialized = True
        db_star = _ffi.new('sqlite3 **')

        if isinstance(database, unicode):
            database = database.encode('utf-8')
        if _lib.sqlite3_open(database, db_star) != _lib.SQLITE_OK:
            raise OperationalError("Could not open database")
        self._db = db_star[0]
        if timeout is not None:
            timeout = int(timeout * 1000)  # pysqlite2 uses timeout in seconds
            _lib.sqlite3_busy_timeout(self._db, timeout)

        self.row_factory = None
        self.text_factory = _unicode_text_factory

        self._detect_types = detect_types
        self._in_transaction = False
        self.isolation_level = isolation_level

        self.__cursors = []
        self.__cursors_counter = 0
        self.__statements = []
        self.__statements_counter = 0
        self._statement_cache = _StatementCache(self, cached_statements)

        self.__func_cache = {}
        self.__aggregates = {}
        self.__aggregate_instances = {}
        self.__collations = {}
        if check_same_thread:
            self.__thread_ident = _thread_get_ident()

        self.Error = Error
        self.Warning = Warning
        self.InterfaceError = InterfaceError
        self.DatabaseError = DatabaseError
        self.InternalError = InternalError
        self.OperationalError = OperationalError
        self.ProgrammingError = ProgrammingError
        self.IntegrityError = IntegrityError
        self.DataError = DataError
        self.NotSupportedError = NotSupportedError

    def __del__(self):
        if self._db:
            _lib.sqlite3_close(self._db)

    def close(self):
        self._check_thread()

        self.__do_all_statements(Statement._finalize, True)

        if self._db:
            ret = _lib.sqlite3_close(self._db)
            if ret != _lib.SQLITE_OK:
                raise self._get_exception(ret)
            self._db = None

    def _check_closed(self):
        if not self.__initialized:
            raise ProgrammingError("Base Connection.__init__ not called.")
        if not self._db:
            raise ProgrammingError("Cannot operate on a closed database.")

    def _check_closed_wrap(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._check_closed()
            return func(self, *args, **kwargs)
        return wrapper

    def _check_thread(self):
        try:
            if self.__thread_ident == _thread_get_ident():
                return
        except AttributeError:
            pass
        else:
            raise ProgrammingError(
                "SQLite objects created in a thread can only be used in that "
                "same thread. The object was created in thread id %d and this "
                "is thread id %d", self.__thread_ident, _thread_get_ident())

    def _check_thread_wrap(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._check_thread()
            return func(self, *args, **kwargs)
        return wrapper

    def _get_exception(self, error_code=None):
        if error_code is None:
            error_code = _lib.sqlite3_errcode(self._db)
        error_message = _ffi.string(_lib.sqlite3_errmsg(self._db)).decode('utf-8')

        if error_code == _lib.SQLITE_OK:
            raise ValueError("error signalled but got SQLITE_OK")
        elif error_code in (_lib.SQLITE_INTERNAL, _lib.SQLITE_NOTFOUND):
            exc = InternalError
        elif error_code == _lib.SQLITE_NOMEM:
            exc = MemoryError
        elif error_code in (
                _lib.SQLITE_ERROR, _lib.SQLITE_PERM, _lib.SQLITE_ABORT,
                _lib.SQLITE_BUSY, _lib.SQLITE_LOCKED, _lib.SQLITE_READONLY,
                _lib.SQLITE_INTERRUPT, _lib.SQLITE_IOERR, _lib.SQLITE_FULL,
                _lib.SQLITE_CANTOPEN, _lib.SQLITE_PROTOCOL, _lib.SQLITE_EMPTY,
                _lib.SQLITE_SCHEMA):
            exc = OperationalError
        elif error_code == _lib.SQLITE_CORRUPT:
            exc = DatabaseError
        elif error_code == _lib.SQLITE_TOOBIG:
            exc = DataError
        elif error_code in (_lib.SQLITE_CONSTRAINT, _lib.SQLITE_MISMATCH):
            exc = IntegrityError
        elif error_code == _lib.SQLITE_MISUSE:
            exc = ProgrammingError
        else:
            exc = DatabaseError
        exc = exc(error_message)
        exc.error_code = error_code
        return exc

    def _remember_cursor(self, cursor):
        self.__cursors.append(weakref.ref(cursor))
        self.__cursors_counter += 1
        if self.__cursors_counter < 200:
            return
        self.__cursors_counter = 0
        self.__cursors = [r for r in self.__cursors if r() is not None]

    def _remember_statement(self, statement):
        self.__statements.append(weakref.ref(statement))
        self.__statements_counter += 1
        if self.__statements_counter < 200:
            return
        self.__statements_counter = 0
        self.__statements = [r for r in self.__statements if r() is not None]

    def __do_all_statements(self, action, reset_cursors):
        for weakref in self.__statements:
            statement = weakref()
            if statement is not None:
                action(statement)

        if reset_cursors:
            for weakref in self.__cursors:
                cursor = weakref()
                if cursor is not None:
                    cursor._reset = True

    @_check_thread_wrap
    @_check_closed_wrap
    def __call__(self, sql):
        return self._statement_cache.get(sql)

    def cursor(self, factory=None):
        self._check_thread()
        self._check_closed()
        if factory is None:
            factory = Cursor
        cur = factory(self)
        if self.row_factory is not None:
            cur.row_factory = self.row_factory
        return cur

    def execute(self, *args):
        cur = self.cursor()
        return cur.execute(*args)

    def executemany(self, *args):
        cur = self.cursor()
        return cur.executemany(*args)

    def executescript(self, *args):
        cur = self.cursor()
        return cur.executescript(*args)

    def iterdump(self):
        from sqlite3.dump import _iterdump
        return _iterdump(self)

    def _begin(self):
        statement_star = _ffi.new('sqlite3_stmt **')
        ret = _lib.sqlite3_prepare_v2(self._db, self.__begin_statement, -1,
                                      statement_star, _ffi.NULL)
        try:
            if ret != _lib.SQLITE_OK:
                raise self._get_exception(ret)
            ret = _lib.sqlite3_step(statement_star[0])
            if ret != _lib.SQLITE_DONE:
                raise self._get_exception(ret)
            self._in_transaction = True
        finally:
            _lib.sqlite3_finalize(statement_star[0])

    def commit(self):
        self._check_thread()
        self._check_closed()
        if not self._in_transaction:
            return

        self.__do_all_statements(Statement._reset, False)

        statement_star = _ffi.new('sqlite3_stmt **')
        ret = _lib.sqlite3_prepare_v2(self._db, b"COMMIT", -1,
                                      statement_star, _ffi.NULL)
        try:
            if ret != _lib.SQLITE_OK:
                raise self._get_exception(ret)
            ret = _lib.sqlite3_step(statement_star[0])
            if ret != _lib.SQLITE_DONE:
                raise self._get_exception(ret)
            self._in_transaction = False
        finally:
            _lib.sqlite3_finalize(statement_star[0])

    def rollback(self):
        self._check_thread()
        self._check_closed()
        if not self._in_transaction:
            return

        self.__do_all_statements(Statement._reset, True)

        statement_star = _ffi.new('sqlite3_stmt **')
        ret = _lib.sqlite3_prepare_v2(self._db, b"ROLLBACK", -1,
                                      statement_star, _ffi.NULL)
        try:
            if ret != _lib.SQLITE_OK:
                raise self._get_exception(ret)
            ret = _lib.sqlite3_step(statement_star[0])
            if ret != _lib.SQLITE_DONE:
                raise self._get_exception(ret)
            self._in_transaction = False
        finally:
            _lib.sqlite3_finalize(statement_star[0])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None and exc_value is None and exc_tb is None:
            self.commit()
        else:
            self.rollback()

    @_check_thread_wrap
    @_check_closed_wrap
    def create_function(self, name, num_args, callback):
        try:
            closure = self.__func_cache[callback]
        except KeyError:
            @_ffi.callback("void(sqlite3_context*, int, sqlite3_value**)")
            def closure(context, nargs, c_params):
                _function_callback(callback, context, nargs, c_params)
            self.__func_cache[callback] = closure

        if isinstance(name, unicode):
            name = name.encode('utf-8')
        ret = _lib.sqlite3_create_function(self._db, name, num_args,
                                           _lib.SQLITE_UTF8, _ffi.NULL,
                                           closure, _ffi.NULL, _ffi.NULL)
        if ret != _lib.SQLITE_OK:
            raise self.OperationalError("Error creating function")

    @_check_thread_wrap
    @_check_closed_wrap
    def create_aggregate(self, name, num_args, cls):
        try:
            step_callback, final_callback = self.__aggregates[cls]
        except KeyError:
            @_ffi.callback("void(sqlite3_context*, int, sqlite3_value**)")
            def step_callback(context, argc, c_params):
                res = _lib.sqlite3_aggregate_context(context,
                                                     _ffi.sizeof("size_t"))
                aggregate_ptr = _ffi.cast("size_t[1]", res)

                if not aggregate_ptr[0]:
                    try:
                        aggregate = cls()
                    except Exception:
                        msg = (b"user-defined aggregate's '__init__' "
                               b"method raised error")
                        _lib.sqlite3_result_error(context, msg, len(msg))
                        return
                    aggregate_id = id(aggregate)
                    self.__aggregate_instances[aggregate_id] = aggregate
                    aggregate_ptr[0] = aggregate_id
                else:
                    aggregate = self.__aggregate_instances[aggregate_ptr[0]]

                params = _convert_params(context, argc, c_params)
                try:
                    aggregate.step(*params)
                except Exception:
                    msg = (b"user-defined aggregate's 'step' "
                           b"method raised error")
                    _lib.sqlite3_result_error(context, msg, len(msg))

            @_ffi.callback("void(sqlite3_context*)")
            def final_callback(context):
                res = _lib.sqlite3_aggregate_context(context,
                                                     _ffi.sizeof("size_t"))
                aggregate_ptr = _ffi.cast("size_t[1]", res)

                if aggregate_ptr[0]:
                    aggregate = self.__aggregate_instances[aggregate_ptr[0]]
                    try:
                        val = aggregate.finalize()
                    except Exception:
                        msg = (b"user-defined aggregate's 'finalize' "
                               b"method raised error")
                        _lib.sqlite3_result_error(context, msg, len(msg))
                    else:
                        _convert_result(context, val)
                    finally:
                        del self.__aggregate_instances[aggregate_ptr[0]]

            self.__aggregates[cls] = (step_callback, final_callback)

        if isinstance(name, unicode):
            name = name.encode('utf-8')
        ret = _lib.sqlite3_create_function(self._db, name, num_args,
                                           _lib.SQLITE_UTF8, _ffi.NULL,
                                           _ffi.NULL,
                                           step_callback,
                                           final_callback)
        if ret != _lib.SQLITE_OK:
            raise self._get_exception(ret)

    @_check_thread_wrap
    @_check_closed_wrap
    def create_collation(self, name, callback):
        name = name.upper()
        if not all(c in string.ascii_uppercase + string.digits + '_' for c in name):
            raise ProgrammingError("invalid character in collation name")

        if callback is None:
            del self.__collations[name]
            collation_callback = _ffi.NULL
        else:
            if not callable(callback):
                raise TypeError("parameter must be callable")

            @_ffi.callback("int(void*, int, const void*, int, const void*)")
            def collation_callback(context, len1, str1, len2, str2):
                text1 = _ffi.buffer(str1, len1)[:]
                text2 = _ffi.buffer(str2, len2)[:]
                try:
                    ret = callback(text1, text2)
                    assert isinstance(ret, (int, long))
                    return cmp(ret, 0)
                except Exception:
                    return 0

            self.__collations[name] = collation_callback

        if isinstance(name, unicode):
            name = name.encode('utf-8')
        ret = _lib.sqlite3_create_collation(self._db, name,
                                            _lib.SQLITE_UTF8,
                                            _ffi.NULL,
                                            collation_callback)
        if ret != _lib.SQLITE_OK:
            raise self._get_exception(ret)

    @_check_thread_wrap
    @_check_closed_wrap
    def set_authorizer(self, callback):
        try:
            authorizer = self.__func_cache[callback]
        except KeyError:
            @_ffi.callback("int(void*, int, const char*, const char*, "
                           "const char*, const char*)")
            def authorizer(userdata, action, arg1, arg2, dbname, source):
                try:
                    ret = callback(action, arg1, arg2, dbname, source)
                    assert isinstance(ret, int)
                    # try to detect cases in which cffi would swallow
                    # OverflowError when casting the return value
                    assert int(_ffi.cast('int', ret)) == ret
                    return ret
                except Exception:
                    return _lib.SQLITE_DENY
            self.__func_cache[callback] = authorizer

        ret = _lib.sqlite3_set_authorizer(self._db, authorizer, _ffi.NULL)
        if ret != _lib.SQLITE_OK:
            raise self._get_exception(ret)

    @_check_thread_wrap
    @_check_closed_wrap
    def set_progress_handler(self, callable, nsteps):
        if callable is None:
            progress_handler = _ffi.NULL
        else:
            try:
                progress_handler = self.__func_cache[callable]
            except KeyError:
                @_ffi.callback("int(void*)")
                def progress_handler(userdata):
                    try:
                        return bool(callable())
                    except Exception:
                        # abort query if error occurred
                        return 1
                self.__func_cache[callable] = progress_handler
        _lib.sqlite3_progress_handler(self._db, nsteps, progress_handler,
                                      _ffi.NULL)

    if sys.version_info[0] >= 3:
        def __get_in_transaction(self):
            return self._in_transaction
        in_transaction = property(__get_in_transaction)

    def __get_total_changes(self):
        self._check_closed()
        return _lib.sqlite3_total_changes(self._db)
    total_changes = property(__get_total_changes)

    def __get_isolation_level(self):
        return self._isolation_level

    def __set_isolation_level(self, val):
        if val is None:
            self.commit()
        else:
            self.__begin_statement = str("BEGIN " + val).encode('utf-8')
        self._isolation_level = val
    isolation_level = property(__get_isolation_level, __set_isolation_level)

    if hasattr(_lib, 'sqlite3_enable_load_extension'):
        @_check_thread_wrap
        @_check_closed_wrap
        def enable_load_extension(self, enabled):
            rc = _lib.sqlite3_enable_load_extension(self._db, int(enabled))
            if rc != _lib.SQLITE_OK:
                raise OperationalError("Error enabling load extension")


class Cursor(object):
    __initialized = False
    __statement = None

    def __init__(self, con):
        if not isinstance(con, Connection):
            raise TypeError
        self.__connection = con

        self.arraysize = 1
        self.row_factory = None
        self._reset = False
        self.__locked = False
        self.__closed = False
        self.__lastrowid = None
        self.__rowcount = -1

        con._check_thread()
        con._remember_cursor(self)

        self.__initialized = True

    def close(self):
        self.__connection._check_thread()
        self.__connection._check_closed()
        if self.__statement:
            self.__statement._reset()
            self.__statement = None
        self.__closed = True

    def __check_cursor(self):
        if not self.__initialized:
            raise ProgrammingError("Base Cursor.__init__ not called.")
        if self.__closed:
            raise ProgrammingError("Cannot operate on a closed cursor.")
        if self.__locked:
            raise ProgrammingError("Recursive use of cursors not allowed.")
        self.__connection._check_thread()
        self.__connection._check_closed()

    def __check_cursor_wrap(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.__check_cursor()
            return func(self, *args, **kwargs)
        return wrapper

    def __check_reset(self):
        if self._reset:
            raise InterfaceError(
                "Cursor needed to be reset because of commit/rollback "
                "and can no longer be fetched from.")

    def __build_row_cast_map(self):
        if not self.__connection._detect_types:
            return
        self.__row_cast_map = []
        for i in xrange(_lib.sqlite3_column_count(self.__statement._statement)):
            converter = None

            if self.__connection._detect_types & PARSE_COLNAMES:
                colname = _lib.sqlite3_column_name(self.__statement._statement, i)
                if colname:
                    colname = _ffi.string(colname).decode('utf-8')
                    type_start = -1
                    key = None
                    for pos in range(len(colname)):
                        if colname[pos] == '[':
                            type_start = pos + 1
                        elif colname[pos] == ']' and type_start != -1:
                            key = colname[type_start:pos]
                            converter = converters[key.upper()]

            if converter is None and self.__connection._detect_types & PARSE_DECLTYPES:
                decltype = _lib.sqlite3_column_decltype(self.__statement._statement, i)
                if decltype:
                    decltype = _ffi.string(decltype).decode('utf-8')
                    # if multiple words, use first, eg.
                    # "INTEGER NOT NULL" => "INTEGER"
                    decltype = decltype.split()[0]
                    if '(' in decltype:
                        decltype = decltype[:decltype.index('(')]
                    converter = converters.get(decltype.upper(), None)

            self.__row_cast_map.append(converter)

    def __fetch_one_row(self):
        num_cols = _lib.sqlite3_data_count(self.__statement._statement)
        row = newlist_hint(num_cols)
        for i in xrange(num_cols):
            if self.__connection._detect_types:
                converter = self.__row_cast_map[i]
            else:
                converter = None

            if converter is not None:
                blob = _lib.sqlite3_column_blob(self.__statement._statement, i)
                if not blob:
                    val = None
                else:
                    blob_len = _lib.sqlite3_column_bytes(self.__statement._statement, i)
                    val = _ffi.buffer(blob, blob_len)[:]
                    val = converter(val)
            else:
                typ = _lib.sqlite3_column_type(self.__statement._statement, i)
                if typ == _lib.SQLITE_NULL:
                    val = None
                elif typ == _lib.SQLITE_INTEGER:
                    val = _lib.sqlite3_column_int64(self.__statement._statement, i)
                    val = int(val)
                elif typ == _lib.SQLITE_FLOAT:
                    val = _lib.sqlite3_column_double(self.__statement._statement, i)
                elif typ == _lib.SQLITE_TEXT:
                    text = _lib.sqlite3_column_text(self.__statement._statement, i)
                    text_len = _lib.sqlite3_column_bytes(self.__statement._statement, i)
                    val = _ffi.buffer(text, text_len)[:]
                    val = self.__connection.text_factory(val)
                elif typ == _lib.SQLITE_BLOB:
                    blob = _lib.sqlite3_column_blob(self.__statement._statement, i)
                    blob_len = _lib.sqlite3_column_bytes(self.__statement._statement, i)
                    val = _BLOB_TYPE(_ffi.buffer(blob, blob_len)[:])
            row.append(val)
        return tuple(row)

    def __execute(self, multiple, sql, many_params):
        self.__locked = True
        self._reset = False
        try:
            del self.__next_row
        except AttributeError:
            pass
        try:
            if not isinstance(sql, basestring):
                raise ValueError("operation parameter must be str or unicode")
            try:
                del self.__description
            except AttributeError:
                pass
            self.__rowcount = -1
            self.__statement = self.__connection._statement_cache.get(sql)

            if self.__connection._isolation_level is not None:
                if self.__statement._type in (
                    _STMT_TYPE_UPDATE,
                    _STMT_TYPE_DELETE,
                    _STMT_TYPE_INSERT,
                    _STMT_TYPE_REPLACE
                ):
                    if not self.__connection._in_transaction:
                        self.__connection._begin()
                elif self.__statement._type == _STMT_TYPE_OTHER:
                    if self.__connection._in_transaction:
                        self.__connection.commit()
                elif self.__statement._type == _STMT_TYPE_SELECT:
                    if multiple:
                        raise ProgrammingError("You cannot execute SELECT "
                                               "statements in executemany().")

            for params in many_params:
                self.__statement._set_params(params)

                # Actually execute the SQL statement
                ret = _lib.sqlite3_step(self.__statement._statement)

                if ret == _lib.SQLITE_ROW:
                    if multiple:
                        raise ProgrammingError("executemany() can only execute DML statements.")
                    self.__build_row_cast_map()
                    self.__next_row = self.__fetch_one_row()
                elif ret == _lib.SQLITE_DONE:
                    if not multiple:
                        self.__statement._reset()
                else:
                    self.__statement._reset()
                    raise self.__connection._get_exception(ret)

                if self.__statement._type in (
                    _STMT_TYPE_UPDATE,
                    _STMT_TYPE_DELETE,
                    _STMT_TYPE_INSERT,
                    _STMT_TYPE_REPLACE
                ):
                    if self.__rowcount == -1:
                        self.__rowcount = 0
                    self.__rowcount += _lib.sqlite3_changes(self.__connection._db)

                if not multiple and self.__statement._type == _STMT_TYPE_INSERT:
                    self.__lastrowid = _lib.sqlite3_last_insert_rowid(self.__connection._db)
                else:
                    self.__lastrowid = None

                if multiple:
                    self.__statement._reset()
        finally:
            self.__connection._in_transaction = \
                not _lib.sqlite3_get_autocommit(self.__connection._db)
            self.__locked = False
        return self

    @__check_cursor_wrap
    def execute(self, sql, params=[]):
        return self.__execute(False, sql, [params])

    @__check_cursor_wrap
    def executemany(self, sql, many_params):
        return self.__execute(True, sql, many_params)

    def executescript(self, sql):
        self.__check_cursor()
        self._reset = False
        if isinstance(sql, unicode):
            sql = sql.encode('utf-8')
        elif not isinstance(sql, str):
            raise ValueError("script argument must be unicode or string.")
        statement_star = _ffi.new('sqlite3_stmt **')
        next_char = _ffi.new('char **')

        self.__connection.commit()
        while True:
            c_sql = _ffi.new("char[]", sql)
            rc = _lib.sqlite3_prepare(self.__connection._db, c_sql, -1,
                                      statement_star, next_char)
            if rc != _lib.SQLITE_OK:
                raise self.__connection._get_exception(rc)

            rc = _lib.SQLITE_ROW
            while rc == _lib.SQLITE_ROW:
                if not statement_star[0]:
                    rc = _lib.SQLITE_OK
                else:
                    rc = _lib.sqlite3_step(statement_star[0])

            if rc != _lib.SQLITE_DONE:
                _lib.sqlite3_finalize(statement_star[0])
                if rc == _lib.SQLITE_OK:
                    break
                else:
                    raise self.__connection._get_exception(rc)

            rc = _lib.sqlite3_finalize(statement_star[0])
            if rc != _lib.SQLITE_OK:
                raise self.__connection._get_exception(rc)

            sql = _ffi.string(next_char[0])
            if not sql:
                break
        return self

    def __iter__(self):
        return self

    def __next__(self):
        self.__check_cursor()
        self.__check_reset()
        if not self.__statement:
            raise StopIteration

        try:
            next_row = self.__next_row
        except AttributeError:
            raise StopIteration
        del self.__next_row

        if self.row_factory is not None:
            next_row = self.row_factory(self, next_row)

        ret = _lib.sqlite3_step(self.__statement._statement)
        if ret == _lib.SQLITE_ROW:
            self.__next_row = self.__fetch_one_row()
        else:
            self.__statement._reset()
            if ret != _lib.SQLITE_DONE:
                raise self.__connection._get_exception(ret)
        return next_row

    if sys.version_info[0] < 3:
        next = __next__
        del __next__

    def fetchone(self):
        return next(self, None)

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize
        lst = []
        for row in self:
            lst.append(row)
            if len(lst) == size:
                break
        return lst

    def fetchall(self):
        return list(self)

    def __get_connection(self):
        return self.__connection
    connection = property(__get_connection)

    def __get_rowcount(self):
        return self.__rowcount
    rowcount = property(__get_rowcount)

    def __get_description(self):
        try:
            return self.__description
        except AttributeError:
            self.__description = self.__statement._get_description()
            return self.__description
    description = property(__get_description)

    def __get_lastrowid(self):
        return self.__lastrowid
    lastrowid = property(__get_lastrowid)

    def setinputsizes(self, *args):
        pass

    def setoutputsize(self, *args):
        pass


class Statement(object):
    _statement = None

    def __init__(self, connection, sql):
        self.__con = connection
        self.__con._remember_statement(self)

        self._in_use = False

        if not isinstance(sql, basestring):
            raise Warning("SQL is of wrong type. Must be string or unicode.")

        first_word = sql.lstrip().split(" ")[0].upper()
        if first_word == "":
            self._type = _STMT_TYPE_INVALID
        elif first_word == "SELECT":
            self._type = _STMT_TYPE_SELECT
        elif first_word == "INSERT":
            self._type = _STMT_TYPE_INSERT
        elif first_word == "UPDATE":
            self._type = _STMT_TYPE_UPDATE
        elif first_word == "DELETE":
            self._type = _STMT_TYPE_DELETE
        elif first_word == "REPLACE":
            self._type = _STMT_TYPE_REPLACE
        else:
            self._type = _STMT_TYPE_OTHER

        if isinstance(sql, unicode):
            sql = sql.encode('utf-8')
        statement_star = _ffi.new('sqlite3_stmt **')
        next_char = _ffi.new('char **')
        c_sql = _ffi.new("char[]", sql)
        ret = _lib.sqlite3_prepare_v2(self.__con._db, c_sql, -1,
                                      statement_star, next_char)
        self._statement = statement_star[0]

        if ret == _lib.SQLITE_OK and not self._statement:
            # an empty statement, work around that, as it's the least trouble
            self._type = _STMT_TYPE_SELECT
            c_sql = _ffi.new("char[]", b"select 42")
            ret = _lib.sqlite3_prepare_v2(self.__con._db, c_sql, -1,
                                          statement_star, next_char)
            self._statement = statement_star[0]

        if ret != _lib.SQLITE_OK:
            raise self.__con._get_exception(ret)

        tail = _ffi.string(next_char[0]).decode('utf-8')
        if _check_remaining_sql(tail):
            raise Warning("You can only execute one statement at a time.")

    def __del__(self):
        if self._statement:
            _lib.sqlite3_finalize(self._statement)

    def _finalize(self):
        if self._statement:
            _lib.sqlite3_finalize(self._statement)
            self._statement = None
        self._in_use = False

    def _reset(self):
        if self._in_use and self._statement:
            _lib.sqlite3_reset(self._statement)
            self._in_use = False

    if sys.version_info[0] < 3:
        def __check_decodable(self, param):
            if self.__con.text_factory in (unicode, OptimizedUnicode,
                                           _unicode_text_factory):
                for c in param:
                    if ord(c) & 0x80 != 0:
                        raise self.__con.ProgrammingError(
                            "You must not use 8-bit bytestrings unless "
                            "you use a text_factory that can interpret "
                            "8-bit bytestrings (like text_factory = str). "
                            "It is highly recommended that you instead "
                            "just switch your application to Unicode strings.")

    def __set_param(self, idx, param):
        cvt = converters.get(type(param))
        if cvt is not None:
            param = cvt(param)

        try:
            param = adapt(param)
        except:
            pass  # And use previous value

        if param is None:
            rc = _lib.sqlite3_bind_null(self._statement, idx)
        elif isinstance(param, (bool, int, long)):
            if -2147483648 <= param <= 2147483647:
                rc = _lib.sqlite3_bind_int(self._statement, idx, param)
            else:
                rc = _lib.sqlite3_bind_int64(self._statement, idx, param)
        elif isinstance(param, float):
            rc = _lib.sqlite3_bind_double(self._statement, idx, param)
        elif isinstance(param, unicode):
            param = param.encode("utf-8")
            rc = _lib.sqlite3_bind_text(self._statement, idx, param,
                                        len(param), _SQLITE_TRANSIENT)
        elif isinstance(param, str):
            self.__check_decodable(param)
            rc = _lib.sqlite3_bind_text(self._statement, idx, param,
                                        len(param), _SQLITE_TRANSIENT)
        elif isinstance(param, (buffer, bytes)):
            param = bytes(param)
            rc = _lib.sqlite3_bind_blob(self._statement, idx, param,
                                        len(param), _SQLITE_TRANSIENT)
        else:
            rc = -1
        return rc

    def _set_params(self, params):
        self._in_use = True

        num_params_needed = _lib.sqlite3_bind_parameter_count(self._statement)
        if isinstance(params, (tuple, list)) or \
                not isinstance(params, dict) and \
                hasattr(params, '__getitem__'):
            try:
                num_params = len(params)
            except TypeError:
                num_params = -1
            if num_params != num_params_needed:
                raise ProgrammingError("Incorrect number of bindings supplied. "
                                       "The current statement uses %d, and "
                                       "there are %d supplied." %
                                       (num_params_needed, num_params))
            for i in range(num_params):
                rc = self.__set_param(i + 1, params[i])
                if rc != _lib.SQLITE_OK:
                    raise InterfaceError("Error binding parameter %d - "
                                         "probably unsupported type." % i)
        elif isinstance(params, dict):
            for i in range(1, num_params_needed + 1):
                param_name = _lib.sqlite3_bind_parameter_name(self._statement, i)
                if not param_name:
                    raise ProgrammingError("Binding %d has no name, but you "
                                           "supplied a dictionary (which has "
                                           "only names)." % i)
                param_name = _ffi.string(param_name).decode('utf-8')[1:]
                try:
                    param = params[param_name]
                except KeyError:
                    raise ProgrammingError("You did not supply a value for "
                                           "binding %d." % i)
                rc = self.__set_param(i, param)
                if rc != _lib.SQLITE_OK:
                    raise InterfaceError("Error binding parameter :%s - "
                                         "probably unsupported type." %
                                         param_name)
        else:
            raise ValueError("parameters are of unsupported type")

    def _get_description(self):
        if self._type in (
            _STMT_TYPE_INSERT,
            _STMT_TYPE_UPDATE,
            _STMT_TYPE_DELETE,
            _STMT_TYPE_REPLACE
        ):
            return None
        desc = []
        for i in xrange(_lib.sqlite3_column_count(self._statement)):
            name = _lib.sqlite3_column_name(self._statement, i)
            if name:
                name = _ffi.string(name).split("[")[0].strip()
            desc.append((name, None, None, None, None, None, None))
        return desc


class Row(object):
    def __init__(self, cursor, values):
        self.description = cursor.description
        self.values = values

    def __getitem__(self, item):
        if type(item) is int:
            return self.values[item]
        else:
            item = item.lower()
            for idx, desc in enumerate(self.description):
                if desc[0].lower() == item:
                    return self.values[idx]
            raise KeyError

    def keys(self):
        return [desc[0] for desc in self.description]

    def __eq__(self, other):
        if not isinstance(other, Row):
            return NotImplemented
        if self.description != other.description:
            return False
        if self.values != other.values:
            return False
        return True

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(self.description)) ^ hash(tuple(self.values))


def _check_remaining_sql(s):
    state = "NORMAL"
    for char in s:
        if char == chr(0):
            return 0
        elif char == '-':
            if state == "NORMAL":
                state = "LINECOMMENT_1"
            elif state == "LINECOMMENT_1":
                state = "IN_LINECOMMENT"
        elif char in (' ', '\t'):
            pass
        elif char == '\n':
            if state == "IN_LINECOMMENT":
                state = "NORMAL"
        elif char == '/':
            if state == "NORMAL":
                state = "COMMENTSTART_1"
            elif state == "COMMENTEND_1":
                state = "NORMAL"
            elif state == "COMMENTSTART_1":
                return 1
        elif char == '*':
            if state == "NORMAL":
                return 1
            elif state == "LINECOMMENT_1":
                return 1
            elif state == "COMMENTSTART_1":
                state = "IN_COMMENT"
            elif state == "IN_COMMENT":
                state = "COMMENTEND_1"
        else:
            if state == "COMMENTEND_1":
                state = "IN_COMMENT"
            elif state == "IN_LINECOMMENT":
                pass
            elif state == "IN_COMMENT":
                pass
            else:
                return 1
    return 0


def _convert_params(con, nargs, params):
    _params = []
    for i in range(nargs):
        typ = _lib.sqlite3_value_type(params[i])
        if typ == _lib.SQLITE_NULL:
            val = None
        elif typ == _lib.SQLITE_INTEGER:
            val = _lib.sqlite3_value_int64(params[i])
            val = int(val)
        elif typ == _lib.SQLITE_FLOAT:
            val = _lib.sqlite3_value_double(params[i])
        elif typ == _lib.SQLITE_TEXT:
            val = _lib.sqlite3_value_text(params[i])
            val = _ffi.string(val).decode('utf-8')
        elif typ == _lib.SQLITE_BLOB:
            blob = _lib.sqlite3_value_blob(params[i])
            blob_len = _lib.sqlite3_value_bytes(params[i])
            val = _BLOB_TYPE(_ffi.buffer(blob, blob_len)[:])
        else:
            raise NotImplementedError
        _params.append(val)
    return _params


def _convert_result(con, val):
    if val is None:
        _lib.sqlite3_result_null(con)
    elif isinstance(val, (bool, int, long)):
        _lib.sqlite3_result_int64(con, int(val))
    elif isinstance(val, float):
        _lib.sqlite3_result_double(con, val)
    elif isinstance(val, unicode):
        val = val.encode('utf-8')
        _lib.sqlite3_result_text(con, val, len(val), _SQLITE_TRANSIENT)
    elif isinstance(val, str):
        _lib.sqlite3_result_text(con, val, len(val), _SQLITE_TRANSIENT)
    elif isinstance(val, (buffer, bytes)):
        _lib.sqlite3_result_blob(con, bytes(val), len(val), _SQLITE_TRANSIENT)
    else:
        raise NotImplementedError


def _function_callback(real_cb, context, nargs, c_params):
    params = _convert_params(context, nargs, c_params)
    try:
        val = real_cb(*params)
    except Exception:
        msg = b"user-defined function raised exception"
        _lib.sqlite3_result_error(context, msg, len(msg))
    else:
        _convert_result(context, val)

converters = {}
adapters = {}


class PrepareProtocol(object):
    pass


def register_adapter(typ, callable):
    adapters[typ, PrepareProtocol] = callable


def register_converter(name, callable):
    converters[name.upper()] = callable


def register_adapters_and_converters():
    def adapt_date(val):
        return val.isoformat()

    def adapt_datetime(val):
        return val.isoformat(" ")

    def convert_date(val):
        return datetime.date(*map(int, val.split("-")))

    def convert_timestamp(val):
        datepart, timepart = val.split(" ")
        year, month, day = map(int, datepart.split("-"))
        timepart_full = timepart.split(".")
        hours, minutes, seconds = map(int, timepart_full[0].split(":"))
        if len(timepart_full) == 2:
            microseconds = int(timepart_full[1])
        else:
            microseconds = 0
        return datetime.datetime(year, month, day, hours, minutes, seconds,
                                 microseconds)

    register_adapter(datetime.date, adapt_date)
    register_adapter(datetime.datetime, adapt_datetime)
    register_converter("date", convert_date)
    register_converter("timestamp", convert_timestamp)


def adapt(val, proto=PrepareProtocol):
    # look for an adapter in the registry
    adapter = adapters.get((type(val), proto), None)
    if adapter is not None:
        return adapter(val)

    # try to have the protocol adapt this object
    if hasattr(proto, '__adapt__'):
        try:
            adapted = proto.__adapt__(val)
        except TypeError:
            pass
        else:
            if adapted is not None:
                return adapted

    # and finally try to have the object adapt itself
    if hasattr(val, '__conform__'):
        try:
            adapted = val.__conform__(proto)
        except TypeError:
            pass
        else:
            if adapted is not None:
                return adapted

    return val

register_adapters_and_converters()
