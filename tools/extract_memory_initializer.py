#
#  Extract inline memory initializer from emscripten-compiled file.
#
#  This script pulls out the memory initializer data from a file compiled
#  with `emcc --memory-init-file 0` and places it in a separate binary file.
#  It's convenient to do this as a separate step because it makes it easier
#  to use a virtualized build environment, and gives us more fine-grained
#  control over the loading of the memory data.
#
#  In a future iteration of this script, we will provide calling code with
#  the opportunity to control loading of the memory initializer rather than
#  have the compiled code load it automatically.  This could be helpful for
#  e.g. downloading the initializer concurrently with compiling the script.
#

import os
import sys
import re
import contextlib


SOURCE_FILE = sys.argv[1]
OUTPUT_FILE = SOURCE_FILE + ".new"
MEMORY_FILE = SOURCE_FILE + ".mem"

OUTPUT_FILEOBJ = open(OUTPUT_FILE, "w")
MEMORY_FILEOBJ = open(MEMORY_FILE, "w")

try:
  with contextlib.nested(OUTPUT_FILEOBJ, MEMORY_FILEOBJ):

    # Slurp in all of the input file.  Whatevz, memory usage...

    with open(SOURCE_FILE, "r") as f:
        data = f.read()

    # Find the point where the memoryInitializer variable is declared.
    # This lets us sanity-check whether there is actually inline memory data,
    # and re-write it to point to our output file if so.

    MEMORY_VAR_REGEX = re.compile(r"var\s+memoryInitializer\s*=\s*")
    match = MEMORY_VAR_REGEX.search(data)
    if match is None:
        raise ValueError("no memoryInitializer variable found")

    memory_var_end = match.end() + 4
    if data[match.end():memory_var_end] != "null":
        raise ValueError("non-null memoryInitializer variable found")
    if data.find("var memoryInitializer", memory_var_end) >= 0:
        raise ValueError("non-null memoryInitializer variable found")

    OUTPUT_FILEOBJ.write(data[:match.end()])
    OUTPUT_FILEOBJ.write('"')
    OUTPUT_FILEOBJ.write(os.path.basename(MEMORY_FILE))
    OUTPUT_FILEOBJ.write('"')
    

    # This regex locates memory allocations relative to Runtime.GLOBAL_BASE,
    # which AFAICT uniquely indicates inline memory-initializer data.  It 
    # matches up to two sub-groups:
    #
    #  Group 1: the array of integers representing the allocated bytes
    #  Group 2: the offset of this allocation from GLOBAL_BASE

    MEMORY_ALLOC_REGEX = re.compile(r'allocate\(\s*\[([0-9,\s]+)\],\s*"i8",\s*ALLOC_NONE,\s*Runtime.GLOBAL_BASE(\s*\+\s*[0-9e]+)?\);')

    # Find the first memory allocation, so we can write out any code between
    # memory_var_end and the actual memory data.

    match = MEMORY_ALLOC_REGEX.search(data)
    if match is not None:
        OUTPUT_FILEOBJ.write(data[memory_var_end:match.start()])

    # Iterate over all memory allocations, writing each byte into the separate
    # memory file.  The are ommitted from the source file.

    for i, match in enumerate(MEMORY_ALLOC_REGEX.finditer(data)):
        # Ensure we write at the correct offset.  The memory initializer
        # data can have gaps if there are chunks of zeros in it.
        # Note that offset may be encoded like 123e4
        offset = match.group(2)
        if offset is not None:
            idx = offset.find("e")
            if idx == -1:
                offset = int(offset)
            else:
                offset = int(offset[:idx]) * (10 ** int(offset[idx+1:]))
            MEMORY_FILEOBJ.seek(offset)
        for byte in match.group(1).split(","):
            MEMORY_FILEOBJ.write(chr(int(byte.strip())))

    # Write out the remainder of the source file unchanged.

    if match is None:
        OUTPUT_FILEOBJ.write(data[memory_var_end:])
    else:
        OUTPUT_FILEOBJ.write(data[match.end():])

except BaseException:
    os.unlink(OUTPUT_FILE)
    os.unlink(MEMORY_FILE)
    raise
else:
    os.rename(OUTPUT_FILE, SOURCE_FILE)

