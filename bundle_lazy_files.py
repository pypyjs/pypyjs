
import os
import sys


CREATE_DIR = "Module['FS_createFolder'](%r, %r, true, true);"
CREATE_FILE = "Module['FS_createLazyFile'](%r, %r, %r true, true);"

created_paths = set()


def create_parents(pathname):
    parent, _ = os.path.split(pathname[1:])
    if parent and parent not in created_paths:
        create_parents(parent)
        gparent, parentnm = os.path.split(parent)
        print CREATE_DIR % (gparent, parentnm)
        created_paths.add(parent)


def create_children(rootdir):
    if rootdir[1:] not in created_paths:
        create_parents(rootdir)
        if os.path.isfile(rootdir):
            dirpath, filename = os.path.split(rootdir)
            print CREATE_FILE % (dirpath[1:], filename, rootdir)
            created_paths.add(rootdir[1:])
        else:
            for (dirpath, dirnames, filenames) in os.walk(rootdir):
                print CREATE_DIR % os.path.split(dirpath[1:])
                created_paths.add(dirpath[1:])
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    print CREATE_FILE % (dirpath[1:], filename, filepath)
                    created_paths.add(filepath[1:])

if __name__ == "__main__":
    for rootdir in sys.argv[1:]:
        create_children(os.path.abspath(rootdir))
