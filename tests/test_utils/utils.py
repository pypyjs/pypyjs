import difflib
import os
import posixpath


def make_diff(block1, block2):
    d = difflib.Differ()

    block1 = block1.replace("\\n", "\\n\n").split("\n")
    block2 = block2.replace("\\n", "\\n\n").split("\n")

    diff = d.compare(block1, block2)

    result = ["%2s %s\n" % (line, i) for line, i in enumerate(diff)]
    return "".join(result)


def website_url_path(sub_path):
    """
    used to build the local url like:
        file:///path/to/pypyjs/website/index.html
    """
    url = posixpath.abspath(posixpath.join(os.path.dirname(__file__), "..", "..", "website", sub_path))
    assert os.path.exists(os.path.normpath(url)), "path %r doesn't exists!" % url
    return url