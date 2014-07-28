#
#  Bundle and index python module files for use in PyPy.js.
#
#  This script copies over the stdlib .py files from pypy and places them
#  under a single directoy, along with an "index.json" file that gives
#  some metadata about their contents and dependencies.  This ensures that
#  they can be loaded on-demand into the PyPy.js virtual filesystem, without
#  have to load all the files even if they won't be needed.
#

import os
import sys
import ast
import json
import base64
import shutil


PYPY_ROOT = os.path.join(
    os.path.dirname(__file__),
    "../deps/pypy",
)


OUTPUT_DIR = sys.argv[1]


# Module that are not going to work, so don't bother including them.
EXCLUDE = [
    "readline",
    "ntpath",
    "os2emxpath",
    "ctypes",
    "ctypes_support",
    "_ctypes",
    "cffi",
    "subprocess",
    "_subprocess",
    "threading",
    "thread",
]


EAGER_MODULES = [
    "os",
    "code",
]


if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR)


# Walk the pypy stdlib dirs to find all available module files and
# copy them into the output directory.  This is also a good chance to
# build up the big index of available modules.

all_modules = {}


def is_excluded(name):
    for excl in EXCLUDE:
        if name == excl:
            return True
        if name.startswith(excl + "."):
            return True
    return False


def gather_module(package, rootdir, relpath):
    modname = os.path.basename(relpath)[:-3]
    if package:
        modname = package + "." + modname
    if not is_excluded(modname):
        moddata = { "file": relpath }
        all_modules[modname] = moddata
        shutil.copyfile(os.path.join(rootdir, relpath),
                        os.path.join(OUTPUT_DIR, relpath))


def gather_package(package, rootdir, relpath):
    fullpath = os.path.join(rootdir, relpath)
    subpackage = os.path.basename(fullpath)
    if package:
        subpackage = package + "." + subpackage
    if not is_excluded(subpackage):
        all_modules[subpackage] = { "dir": relpath }
        os.makedirs(os.path.join(OUTPUT_DIR, relpath))
        for nm in os.listdir(fullpath):
            if nm.startswith("."):
                continue
            subrelpath = os.path.join(relpath, nm)
            subfullpath = os.path.join(fullpath, nm)
            if os.path.isdir(subfullpath):
                if os.path.exists(os.path.join(subfullpath, "__init__.py")):
                    gather_package(subpackage, rootdir, subrelpath)
            elif nm.endswith(".py"):
                gather_module(subpackage, rootdir, subrelpath)


for modroot in ("lib-python/2.7", "lib_pypy"):
    rootdir = os.path.join(PYPY_ROOT, modroot)
    for nm in os.listdir(rootdir):
        if nm.startswith("."):
            continue
        fullpath = os.path.join(rootdir, nm)
        if os.path.isdir(fullpath):
            if os.path.exists(os.path.join(fullpath, "__init__.py")):
                gather_package("", rootdir, nm)
        elif nm.endswith(".py"):
            gather_module("", rootdir, nm)


# Copy each file across, and examine it for imports.
# List all other modules imported by a module as part of its metadata.


class ImportFinder(ast.NodeVisitor):

    def __init__(self, module, filepath):
        super(ImportFinder, self).__init__()
        self.module = module
        if "." in module:
            self.package = module.rsplit(".", 1)[0]
        else:
            self.package = ""
        self.filepath = filepath
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
        # Dereferences explicit relative imports indicated by leading dots.
        if name[0] == ".":
            name = name[1:]
            pkgbits = self.package.split(".")
            while name[0] == ".":
                name = name[1:]
                pkgbits = pkgbits[:-1]
            name = ".".join(pkgbits) + "." + name 
        # Resolve implicit relative imports within the containing package.
        elif not self.uses_absolute_import and self.package:
            pkgname = self.package
            relname = name.rsplit(".", 1)[0]
            while True:
                absname = pkgname + "." + relname
                if absname in all_modules:
                    name = pkgname + "." + name
                    break
                if "." not in pkgname:
                    break
                pkgname = pkgname.rsplit(".", 1)[0]
        # Strip trailing components until we find a valid module name.
        while name not in all_modules and "." in name:
            name = name.rsplit(".", 1)[0]
        if name in all_modules:
            self.imported_names.add(name)


for modname, moddata in all_modules.iteritems():
    if "file" in moddata:
        impf = ImportFinder(modname, os.path.join(OUTPUT_DIR, moddata["file"]))
        moddata["imports"] = impf.find_imported_modules()


def find_transitive_dependencies(name, seen=None):
    if seen is None:
        seen = set()
    moddata = all_modules.get(name)
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
                find_transitive_dependencies(dep, seen)
    return seen


eager_modules = {}

for name in EAGER_MODULES:
    for depname in find_transitive_dependencies(name):
        if depname in eager_modules:
            continue
        moddata = all_modules[depname]
        if "file" in moddata:
            filepath = os.path.join(OUTPUT_DIR, moddata["file"])
            with open(filepath, "r") as f:
                eager_modules[depname] = f.read()
            os.unlink(filepath)


index_data = {
    "modules": all_modules,
    "eager": eager_modules,
}
with open(os.path.join(OUTPUT_DIR, "index.json"), "w") as f:
    f.write(json.dumps(index_data, indent=2, sort_keys=True))
