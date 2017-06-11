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
        data = f.read().strip()

    # This regex locates memory allocations relative to Runtime.GLOBAL_BASE,
    # which AFAICT uniquely indicates inline memory-initializer data.  It 
    # matches up to two sub-groups:
    #
    #  Group 1: the array of integers representing the allocated bytes
    #  Group 2: the offset of this allocation from GLOBAL_BASE

    MEMORY_ALLOC_REGEX = re.compile(r'allocate\(\s*\[([0-9,\s]+)\],\s*"i8",\s*ALLOC_NONE,\s*Runtime.GLOBAL_BASE(\s*\+\s*[0-9e]+)?\);')

    # Find the first memory allocation.
    # We're going to replace it with the definition of the
    # async memory-initializer loader.

    match = MEMORY_ALLOC_REGEX.search(data)
    if match is None:
        raise ValueError("no global memory initialization found")

    OUTPUT_FILEOBJ.write(data[:match.start()])
    OUTPUT_FILEOBJ.write("var memoryInitializer=\"")
    OUTPUT_FILEOBJ.write(os.path.basename(MEMORY_FILE))
    OUTPUT_FILEOBJ.write("\";")

    # Iterate over all memory allocations, writing each byte into the separate
    # memory file.  They are ommitted from the source file.

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

    # Emscripten doesn't output the memory-initializer-loading code if
    # there's no memory initializer, so we'll have to put it back.
    # It goes right before the final call to run().

    FINAL_POSTAMBLE = "run()"
    if data.endswith(";"):
        FINAL_POSTAMBLE = "\n" + FINAL_POSTAMBLE + ";"
    assert data.endswith("}" + FINAL_POSTAMBLE)

    OUTPUT_FILEOBJ.write(data[match.end():-len(FINAL_POSTAMBLE)])
    OUTPUT_FILEOBJ.write("""
        memoryInitializer = Module['memoryInitializerPrefixURL'] + memoryInitializer;
        if (ENVIRONMENT_IS_NODE || ENVIRONMENT_IS_SHELL) {
          var data = Module['readBinary'](memoryInitializer);
          HEAPU8.set(data, Runtime.GLOBAL_BASE);
        } else {
          addRunDependency('memory initializer');
          var applyMemoryInitializer = function(data) {
            if (data.byteLength) data = new Uint8Array(data);
            HEAPU8.set(data, Runtime.GLOBAL_BASE);
            removeRunDependency('memory initializer');
          }
          Browser.asyncLoad(memoryInitializer, applyMemoryInitializer, function() {
            throw 'could not load memory initializer ' + memoryInitializer;
          });
        }
    """)
    OUTPUT_FILEOBJ.write(FINAL_POSTAMBLE)

except BaseException:
    os.unlink(OUTPUT_FILE)
    os.unlink(MEMORY_FILE)
    raise
else:
    os.rename(OUTPUT_FILE, SOURCE_FILE)
