#!/usr/bin/env python
#
#  Manage bundled python module files for use in PyPy.js.
#
#  This script is used to manage an indexed bundle of python module files in
#  a format that makes them easy to use for PyPy.js.  In particular it lets
#  us hack around the fact that we can't use an async XMLHttpRequest from
#  inside the compiled PyPy.js VM.
#
#  When PyPy.js goes to import a module, the contents of the module file
#  and all of its dependencies must already be loaded into the virtual
#  filesystem.  But loading the entire stdlib at startup would waste time,
#  bandwidth, and memory.
#
#  Instead, we can load just the bundle's index file at startup, which gives
#  metadata about the available modules and their dependencies.  This data
#  can be used to load the module files on demand before passing 'import'
#  statements through to the VM for execution.
#

import os
import re
import sys
import ast
import json
import codecs
import argparse
import shutil


# The root of our pypy source checkout, if it exists.
PYPY_ROOT = os.path.join(
    os.path.dirname(__file__),
    "../deps/pypy",
)

# Modules that are builtin, so we shouldn't expect them in the bundle.
BUILTIN_MODULES = [
    "__builtin__",
    "__pypy__",
    "_ast",
    "_codecs",
    "_collections",
    "_csv",
    "_file",
    "_hashlib",
    "_io",
    "_locale",
    "_md5",
    "_minimal_curses",
    "_multibytecodec",
    "_pickle_support",
    "_pypyjson",
    "_random",
    "_sha",
    "_socket",
    "_sre",
    "_struct",
    "_testing",
    "_warnings",
    "_weakref",
    "array",
    "binascii",
    "cStringIO",
    "cmath",
    "errno",
    "exceptions",
    "gc",
    "imp",
    "itertools",
    "js",
    "marshal",
    "math",
    "operator",
    "parser",
    "posix",
    "pypyjit",
    "symbol",
    "sys",
    "time",
    "token",
    "unicodedata",
]

# Modules that are not going to work, so don't bother including them.
EXCLUDE_MODULES = [
    "readline",
    "ntpath",
    "macpath",
    "os2emxpath",
    "ctypes",
    "ctypes_support",
    "ctypes_configure",
    "ctypes_configure_cache",
    "_ctypes",
    "cffi",
    "_ffi",
    "_rawffi",
    "subprocess",
    "_subprocess",
    "threading",
    "thread",
    "multiprocessing",
    "_multiprocessing",
    "audiodev",
    "audioop",
    "Carbon",
    "MacOS",
    "_osx_support"
    "smtpd",
    "idlelib",
    "Tkinter",
    "Tkconstants",
    "_tkinter",
    "ttk",
    "__main__",
    "bsddb",
    "ssl",
    "_ssl",
    "_winreg",
    "cpyext",
    "symtable",
    "java",
    "msilib",
    "dos",
    "nt",
    "os2",
    "org.python",
    "riscos",
    "riscosenviron",
    "vmslib",
    "win32api",
    "win32con",
    "win32pipe",
    "win32wnet",
    "win32evtlog",
    "msvcrt",
    "hotshot",
    "sunau",
    "sunaudio",
    "wave",
]

# Modules that are pretty much always needed, and so should be loaded eagerly.
PRELOAD_MODULES = [
    "os",
    "code",
    # Python has some magic to auto-load encodings when they're needed,
    # which doesn't work right if they're not preloaded.
    "encodings.ascii",
    "encodings.hex_codec",
    "encodings.base64_codec",
    "encodings.latin_1",
    "encodings.utf_8",
    "encodings.utf_16",
    "encodings.unicode_internal",
    "encodings.unicode_escape",
    "encodings.raw_unicode_escape",
]


def main(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")

    parser_init = subparsers.add_parser("init")
    parser_init.add_argument("bundle_dir")
    parser_init.add_argument("--exclude", action="append",
                             help="exclude these modules from the bundle")
    parser_init.add_argument("--preload", action="append",
                             help="preload these modules in the bundle")

    parser_add = subparsers.add_parser("add")
    parser_add.add_argument("bundle_dir")
    parser_add.add_argument("modules", nargs="+", metavar="module")
    parser_add.add_argument("--exclude", action="append",
                            help="exclude these modules from the bundle")
    parser_add.add_argument("--preload", action="append",
                            help="preload these modules in the bundle")

    parser_preload = subparsers.add_parser("preload")
    parser_preload.add_argument("bundle_dir")
    parser_preload.add_argument("modules", nargs="+", metavar="module")

    opts = parser.parse_args(argv[1:])
    bundler = ModuleBundle(opts.bundle_dir)
    if opts.subcommand == "init":
        cmd_init(bundler, opts)
    elif opts.subcommand == "add":
        cmd_add(bundler, opts)
    elif opts.subcommand == "preload":
        cmd_preload(bundler, opts)
    else:
        assert False, "unknown subcommand {}".format(opts.subcommand)
    return 0


def cmd_init(bundler, opts):
    # Update the bundler's exclusion list.
    if opts.exclude:
        for name in opts.exclude:
            if not bundler.is_excluded(name):
                bundler.exclude.append(name)
    # Walk the pypy stdlib dirs to find all available module files and
    # copy them into the bundle.
    for modroot in ("lib-python/2.7", "lib_pypy"):
        rootdir = os.path.join(PYPY_ROOT, modroot)
        bundler.bundle_directory(rootdir)
    # Preload the default set of preloaded modules.
    for name in PRELOAD_MODULES:
        bundler.preload_module(name)
    # Along with any that were explicitly requested.
    if opts.preload:
        for name in opts.preload:
            bundler.preload_module(name)
    bundler.flush_index()


def cmd_add(bundler, opts):
    # Update the exclude list if necessary.
    if opts.exclude:
        for name in opts.exclude:
            if not bundler.is_excluded(name):
                bundler.exclude.append(name)
    # Find and bundle each module/package.
    for name in opts.modules:
        if os.path.exists(name):
            bundler.bundle_path(name)
        else:
            # XXX TODO: try to find it by importing it?
            raise ValueError("non-existent module: {}".format(name))
    # Preload any additional modules that were specified.
    if opts.preload:
        for name in opts.preload:
            bundler.preload_module(name)
    bundler.flush_index()


def cmd_preload(bundler, opts):
    for name in opts.modules:
        bundler.preload_module(name)
    bundler.flush_index()


class ModuleBundle(object):
    """Class managing a directory of bundled modules.

    This class builds up a directory containing python module files along
    with an "index.json" file giving metadata about their contents and
    dependencies.  Loading the index gives enough information to determine
    what files should be loaded in order to handle importing of any available
    module.

    The structure of index.json is as follows:

      {
        "modules":  {          # maps dotted module name to metadata
          "a.b": {
            "file": "<a.py>"   # for modules, relative path to .py file
            "dir": "<A>"       # for packages, relative path to package dir
            "imports": []      # list of module names imported by this module
          }
        },
        "preload": {         # maps dotted module name to raw file contents
          "x.y": "<code>",
        }
      }

    There is also an ancilliary file "meta.json" which tracks information
    useful when building up the bundle, not unnecessary when loading modules
    from it.  This helps avoid paying the overhead of loading the extra
    information when using the bundle.

    The structure of meta.json is as follows:

      {
        "exclude": [      # list of modules excluded from the bundle
          "some.module"
        ]
        "missing": {      # maps dotted module names that are not found in the
          "a.b.c.d": []   # bundle to the modules that would import them.
        }
      }

    """

    def __init__(self, bundle_dir):
        self.bundle_dir = os.path.abspath(bundle_dir)
        self.index_file = os.path.join(self.bundle_dir, "index.json")
        self.meta_file = os.path.join(self.bundle_dir, "meta.json")
        self.modules = {}
        self.preload = {}
        self.exclude = list(EXCLUDE_MODULES)
        self.missing = {}
        self._modules_pending_import_analysis = []
        if not os.path.isdir(self.bundle_dir):
            os.makedirs(self.bundle_dir)
        if not os.path.exists(self.index_file):
            self.flush_index()
        self.load_index()

    def flush_index(self):
        """Write out the index file based on in-memory state."""
        # Atomically update the index file.
        with open(self.index_file + ".new", "w") as f:
            json.dump({
                "modules": self.modules,
                "preload": self.preload,
            }, f, indent=2, sort_keys=True)
        if sys.platform.startswith("win32"):
            shutil.copy(self.index_file + ".new", self.index_file)
            os.remove(self.index_file + ".new")
        else:
            os.rename(self.index_file + ".new", self.index_file)
        # Atomically update the meta file.
        with open(self.meta_file + ".new", "w") as f:
            json.dump({
                "exclude": self.exclude,
                "missing": self.missing,
            }, f, indent=2, sort_keys=True)
        if sys.platform.startswith("win32"):
            shutil.copy(self.meta_file + ".new", self.meta_file)
            os.remove(self.meta_file + ".new")
        else:
            os.rename(self.meta_file + ".new", self.meta_file)
        # Remove preloaded module files from disk, now that their contents
        # are safely flushed to the index file.
        for name in self.preload:
            moddata = self.modules[name]
            if "file" in moddata:
                filepath = os.path.join(self.bundle_dir, moddata["file"])
                if os.path.exists(filepath):
                    os.unlink(filepath)

    def load_index(self):
        """Load in-memory state from the index file."""
        with open(self.index_file) as f:
            index = json.load(f)
        self.modules = index["modules"]
        self.preload = index["preload"]
        with open(self.meta_file) as f:
            meta = json.load(f)
        self.exclude = meta["exclude"]
        self.missing = meta["missing"]

    def is_dotted_prefix(self, prefix, name):
        """Check whether a dotted name is a prefix of another."""
        if name == prefix:
            return True
        if name.startswith(prefix):
            if name[len(prefix)] == ".":
                return True
        return False

    def is_builtin(self, name):
        """Check whether the named module is a builtin."""
        for builtin in BUILTIN_MODULES:
            if self.is_dotted_prefix(builtin, name):
                return True
        return False

    def is_excluded(self, name):
        """Check whether the named module should be excluded."""
        for excl in self.exclude:
            if self.is_dotted_prefix(excl, name):
                return True
        return False

    def bundle_module(self, filepath):
        """Bundle the given file as a python module."""
        filepath = os.path.abspath(filepath)
        rootdir, relpath = os.path.split(filepath)
        self._gather_module("", rootdir, relpath)
        self._perform_pending_import_analysis()

    def bundle_package(self, dirpath):
        """Bundle the given directory as a python package."""
        dirpath = os.path.abspath(dirpath)
        rootdir, relpath = os.path.split(dirpath)
        self._gather_package("", rootdir, relpath)
        self._perform_pending_import_analysis()

    def bundle_directory(self, dirpath):
        """Bundle all modules/packages in the given directory."""
        dirpath = os.path.abspath(dirpath)
        for nm in os.listdir(dirpath):
            if nm.startswith("."):
                continue
            itempath = os.path.join(dirpath, nm)
            if os.path.isdir(itempath):
                if os.path.exists(os.path.join(itempath, "__init__.py")):
                    self.bundle_package(itempath)
            elif nm.endswith(".py"):
                self.bundle_module(itempath)

    def bundle_path(self, path):
        """Bundle whatever exists at the given path.

        The path could specify a module, a package, or a directory of modules
        and packages.  Its type is intuited based on the contents of the path.
        """
        if os.path.isfile(path):
            self.bundle_module(path)
        elif os.path.isfile(os.path.join(path, "__init__.py")):
            self.bundle_package(path)
        else:
            self.bundle_directory(path)

    def _gather_module(self, package, rootdir, relpath):
        """Gather a python module file into the bundle.

        Given the name of a python module, the root import directory under
        which it was found, and the relative path from that root to the
        module file, this method copies the file into the bundle and adds it
        to the list of all available modules.
        """
        modname = os.path.basename(relpath)[:-3]
        if package:
            modname = package + "." + modname
        if not self.is_excluded(modname):
            # Add it to the list of available modules.
            moddata = {"file": relpath.replace("\\", "/")}
            self.modules[modname] = moddata
            # Copy its source file across.
            self._copy_py_file(os.path.join(rootdir, relpath),
                               os.path.join(self.bundle_dir, relpath))
            # We'll need to analyse its imports once all siblings are gathered.
            self._modules_pending_import_analysis.append(modname)

    def _gather_package(self, package, rootdir, relpath):
        """Recursively gather a python package directory into the bundle.

        Given the name of the python package, the root import directory under
        which it was found, and the relative path from that root to the
        package directory, this method copies the package and all its contents
        into the bundle and adds them to the list of available modules.
        """
        abspath = os.path.join(rootdir, relpath)
        subpackage = os.path.basename(abspath)
        if package:
            subpackage = package + "." + subpackage
        if not self.is_excluded(subpackage):
            # Note it as an available package.
            self.modules[subpackage] = {"dir": relpath.replace("\\", "/")}
            if not os.path.isdir(os.path.join(self.bundle_dir, relpath)):
                os.makedirs(os.path.join(self.bundle_dir, relpath))
            # Include it in post-gathering analysis.
            self._modules_pending_import_analysis.append(subpackage)
            # Recursively gather all its contents.
            for nm in os.listdir(abspath):
                if nm.startswith("."):
                    continue
                subrelpath = os.path.join(relpath, nm)
                subabspath = os.path.join(abspath, nm)
                if os.path.isdir(subabspath):
                    if os.path.exists(os.path.join(subabspath, "__init__.py")):
                        self._gather_package(subpackage, rootdir, subrelpath)
                elif nm.endswith(".py"):
                    self._gather_module(subpackage, rootdir, subrelpath)

    def _copy_py_file(self, srcpath, dstpath):
        """Copy a python source file into the bundle.

        This method copes the contents of a python source file into the bundle.
        Since browsers usually expect strings in utf-8 format, it will try to
        detect source files in other encodings and transparently convert them
        to utf-8.
        """
        # XXX TODO: copy in chunks, like shutil would do?
        with open(srcpath, "rb") as f_src:
            data = f_src.read()
        # Look for the encoding marker in the first two lines of the file.
        lines = data.split("\n", 2)
        encoding = None
        for i in xrange(2):
            if i >= len(lines):
                break
            if lines[i].startswith("#"):
                match = re.search(r"coding[:=]\s*([-\w.]+)", lines[i])
                if match is not None:
                    encoding = match.group(1)
                    try:
                        codecs.lookup(encoding)
                    except LookupError:
                        encoding = None
                    break
        # Write normalized data to output file.
        with open(dstpath, "wb") as f_dst:
            if encoding is None:
                f_dst.write(data)
            else:
                for j in xrange(i):
                    f_dst.write(lines[j])
                    f_dst.write("\n")
                f_dst.write(lines[i].replace(encoding, "utf-8"))
                f_dst.write("\n")
                for j in xrange(i + 1, len(lines)):
                    f_dst.write(lines[j].decode(encoding).encode("utf8"))
                    if j < len(lines) - 1:
                        f_dst.write("\n")

    def _perform_pending_import_analysis(self):
        """Perform import analysis on any pending modules.

        To make it easier to resolve intra-package relative imports, we
        delay doing any import analsyis until all the contents of a package
        have been gathered into the bundle.  This method is called after
        the gathering in order to perform the pending analyses.
        """
        while self._modules_pending_import_analysis:
            modname = self._modules_pending_import_analysis.pop()
            # Check if this new module resolves previously-missing imports.
            # XXX TODO: this is pretty ugly and inefficient...
            for depname in self.missing.keys():
                if self.is_dotted_prefix(modname, depname):
                    revdeps = self.missing.pop(depname)
                    for revdepname in revdeps:
                        revdepdata = self.modules[revdepname]
                        revdepdata["imports"].remove(depname)
                        if modname not in revdepdata["imports"]:
                            revdepdata["imports"].append(modname)
            # Find all the names that it imports.
            moddata = self.modules[modname]
            if "file" not in moddata:
                continue
            modpath = os.path.join(self.bundle_dir, moddata["file"])
            impf = ImportFinder(modname, modpath, self.modules)
            moddata["imports"] = impf.find_imported_modules()
            # Check for any imports that are missing from the bundle.
            for depname in moddata["imports"]:
                if depname not in self.modules:
                    if not self.is_excluded(depname):
                        if not self.is_builtin(depname):
                            if depname not in self.missing:
                                self.missing[depname] = []
                            self.missing[depname].append(modname)

    def preload_module(self, name):
        """Preload a module's file data into the index itself.

        This is a little trick to speed up loading of commonly-used modules.
        Rather than having the module's file data as a separate file on disk,
        we store it as a string directly in the index file, and avoid doing
        a separate network access to load it at VM startup time.
        """
        for depname in self._find_transitive_dependencies(name):
            if depname in self.preload:
                continue
            moddata = self.modules[depname]
            if "file" in moddata:
                filepath = os.path.join(self.bundle_dir, moddata["file"])
                with open(filepath, "r") as f:
                    self.preload[depname] = f.read()

    def _find_transitive_dependencies(self, name, seen=None):
        """Transitively find all dependencies of a module."""
        if seen is None:
            seen = set((name,))
        moddata = self.modules.get(name)
        if moddata is not None:
            deps = set()
            imports = moddata.get("imports")
            if imports is not None:
                deps.update(imports)
            if "dir" in moddata:
                deps.add(name + ".__init__")
            if "." in name:
                deps.add(name.rsplit(".", 1)[0])
            seen.add(name)
            for dep in deps:
                if dep not in seen:
                    self._find_transitive_dependencies(dep, seen)
        return seen


class ImportFinder(ast.NodeVisitor):
    """An AST NodeVisitor for finding all names imported in a python file."""

    def __init__(self, module, filepath, known_modules):
        super(ImportFinder, self).__init__()
        self.module = module
        if "." in module:
            self.package = module.rsplit(".", 1)[0]
        else:
            self.package = ""
        self.filepath = filepath
        self.known_modules = known_modules
        self.imported_names = set()
        self.uses_absolute_import = False

    def find_imported_modules(self):
        with open(self.filepath, "r") as f:
            code = f.read()
        try:
            n = ast.parse(code)
        except SyntaxError:
            return []
        self.visit(n)
        return sorted(list(self.imported_names))

    def visit_Import(self, node):
        for alias in node.names:
            self.record_imported_name(alias.name)

    def visit_ImportFrom(self, node):
        if node.module == "__future__":
            for alias in node.names:
                if alias.name == "absolute_import":
                    self.uses_absolute_import = True
        prefix = "." * node.level
        if node.module is not None:
            prefix += node.module + "."
        for alias in node.names:
            self.record_imported_name(prefix + alias.name)

    def record_imported_name(self, name):
        # Dereference explicit relative imports indicated by leading dots.
        if name[0] == ".":
            name = name[1:]
            pkgbits = self.package.split(".")
            while name[0] == ".":
                name = name[1:]
                pkgbits = pkgbits[:-1]
            name = ".".join(pkgbits) + "." + name
        # Resolve implicit relative imports within the containing package.
        # This depends on self.known_modules having all sibling modules.
        elif not self.uses_absolute_import and self.package:
            pkgname = self.package
            relname = name.rsplit(".", 1)[0]
            while True:
                absname = pkgname + "." + relname
                if absname in self.known_modules:
                    name = pkgname + "." + name
                    break
                if "." not in pkgname:
                    break
                pkgname = pkgname.rsplit(".", 1)[0]
        # Strip trailing components to try to  find a known module name.
        orig_name = name
        while name not in self.known_modules and "." in name:
            name = name.rsplit(".", 1)[0]
        if name in self.known_modules:
            self.imported_names.add(name)
        else:
            self.imported_names.add(orig_name)


if __name__ == "__main__":
    res = main(sys.argv)
    sys.exit(res)
