#
#  Extract inline memory initializer from emscripten-compiled file.
#
#  This script pulls out the memory initializer data from a file compiled
#  with `emcc --memory-init-file 0` and places it in a separate binary file.
#  Unlink `emcc --memory-init-file 1` it does *not* arrange for the memory
#  data to be loaded automatically at startup.  This allows for calling code
#  to have finer control over the loading process.
#

import os
import sys
import re


SOURCE_FILE = sys.argv[1]
MEMORY_FILE = SOURCE_FILE + ".mem"

MEMORY_FILEOBJ = open(MEMORY_FILE, "w")

MEMORY_REGEX = re.compile(r'allocate\(\s*\[([0-9,\s]+)\],\s*"i8",\s*ALLOC_NONE,\s*Runtime.GLOBAL_BASE(\s*\+\s*[0-9]+)?\);')


with open(SOURCE_FILE, "r") as f:
    data = f.read()

idx_start = MEMORY_REGEX.search(data).start()
for i, match in enumerate(MEMORY_REGEX.finditer(data)):
    if match.group(2) is not None:
        MEMORY_FILEOBJ.seek(int(match.group(2)))
    for byte in match.group(1).split(","):
        MEMORY_FILEOBJ.write(chr(int(byte.strip())))

print "FOUND", i, "MATCHES"

idx_end = match.end()

data = data[:idx_start] + data[idx_end:]

with open(SOURCE_FILE, "w") as f:
    f.write(data)

