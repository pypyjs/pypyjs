#
#  Compress memory initializer for emscripten-compiled file.
#
#  Given an emscripten-compiled .js file with corresponding .js.mem file
#  for its memory initializer, this script will replace the memory initializer
#  with a compressed version in .js.zmem, and will modify the javascript to
#  transparently decompress it at startup.
#
#  The compression scheme used is a based on the deflate format described in:
#
#    http://www.ietf.org/rfc/rfc1951.txt
#
#  But has some simplifications geared towards simpler and faster decompression
#  code.  Since we ship the decompression code along with the file, this seems
#  to pay off in practice.  The resulting memory file is empirically close to
#  the size produced by zip when used on the PyPy.js data.
#
#  Like deflate, literals and match lengths are combined into a single alphabet
#  and compressed using a huffman code, while distances are compressed using
#  a separate huffman code.  Unlike deflate, there are no block boundaries,
#  no extra-bits for encoding distances, and we use a single huffman code for
#  the entire string rather than constructing custom codes for each block.
#
#  The format of the compressed data is:
#
#    [huffman-coded data][literal huffman tree][distance huffman tree]
#
#  Where the tree data is in a format designed for easy direct lookup at
#  runtime.  There's no way to determine the offset of the tree data in
#  the memory file, this information is encoded directly in the decompression
#  code inserted into the host javascript file.
#
#  Future iterations might use a different scheme.  This can be done without
#  concern for backwards-compatibility - since we store the decompression code
#  inline in the host javascript, we can change it at will.
#
#  To generate the compressed data, we actually run it through standard
#  zlib compression, decode the zlib stream into an equivalent raw sequence
#  of LZ77 operations, then re-compress it in the custom format.  This avoids
#  having to take a dependency on any external compression software.
#

import os
import re
import sys
import zlib
import heapq
from collections import defaultdict


# ZLIB meta-huffman-tree alphabet symbols, in datastream order.

CODELEN_ALPHABET = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5,
                    11, 4, 12, 3, 13, 2, 14, 1, 15]


def compress_memory_file(source_filename):
    memory_filename = source_filename + ".mem"
    output_filename = source_filename + ".new"
    zmem_filename = source_filename + ".zmem"

    # Read in all the data.  Whatever, it's only a few MB...

    with open(source_filename) as f:
        jsdata = f.read()

    with open(memory_filename) as f:
        memdata = f.read()

    # Generate the compressed "zmem" file.

    lzops = decode_zlib_stream(Bitstream(zlib.compress(memdata, 9)))
    #lzops = merge_lz_operations(lzops)
    zmemdata, l_tree, d_tree = zencode(lzops)

    with open(zmem_filename, "w") as zmem_file:
        zmem_file.write(zmemdata)
        l_tree_root = zmem_file.tell()
        if l_tree_root % 2:
            zmem_file.write("\x00")
            l_tree_root += 1
        zmem_file.write(l_tree)
        d_tree_root = zmem_file.tell()
        if d_tree_root % 2:
            zmem_file.write("\x00")
            d_tree_root += 1
        zmem_file.write(d_tree)
        zmemsize = zmem_file.tell()

    # Generate the modified javascript code.

    try:
        with open(output_filename, "w") as output_file:
 
            assert "zmeminit" not in jsdata

            # Tell it to load the compressed memory file, not the raw one.

            jsdata = jsdata.replace(os.path.basename(memory_filename),
                                    os.path.basename(zmem_filename))

            # Find the (possibly minified) name of the Uint8 heap array,
            # so we can refer to it in the decompressor source code.

            r = re.compile(r"var ([a-zA-Z0-9]+)\s*=\s*new\s+global.Uint8Array")
            match = r.search(jsdata)
            if match is None:
                raise ValueError("heap view could not be found")
            HEAPU8 = match.group(1)

            r = re.compile(r"var ([a-zA-Z0-9]+)\s*=\s*new\s+global.Uint16Array")
            match = r.search(jsdata)
            if match is None:
                raise ValueError("heap view could not be found")
            HEAPU16 = match.group(1)

            # Add an function to the asmjs module that will decompress the
            # memory data in-place.  It's a hand-written asmjs decompressor.

            r = re.compile(r"}\s*// EMSCRIPTEN_END_FUNCS", re.MULTILINE)
            match = r.search(jsdata)
            if match is None:
                raise ValueError("EMSCRIPTEN_END_FUNCS not found")

            output_file.write(jsdata[:match.start()])
            output_file.write("}")
            output_file.write(UNZIP_CODE\
               .replace("{HEAPU8}", HEAPU8)
               .replace("{HEAPU16}", HEAPU16)
               .replace("{L_TREE_ROOT}", str(l_tree_root))
               .replace("{D_TREE_ROOT}", str(d_tree_root))
            )
            output_file.write(match.group(0)[1:])
            jsdata = jsdata[match.end():]

            # Export the function for use by shell code.

            r = re.compile(r"};?\s*}\)\s*// EMSCRIPTEN_END_ASM", re.MULTILINE)
            match = r.search(jsdata)
            if match is None:
                raise ValueError("EMSCRIPTEN_END_ASM not found")

            output_file.write(jsdata[:match.start()])
            output_file.write(",zmeminit:zmeminit")
            output_file.write(match.group(0))
            jsdata = jsdata[match.end():]

            # Find any code that loads the heap data, and have it write at
            # appropriate offset and call the decompressor function.
            # We arrange for the compressed data to sit at the end of
            # the final memory region, poking out just slightly past the
            # end.  This allows it to be decompressed in-place without
            # the possibility of overwriting un-processed data.

            zset = "HEAPU8.set(data, Runtime.GLOBAL_BASE+{zstart});"
            zset += "asm[\"zmeminit\"](Runtime.GLOBAL_BASE,"
            zset += "Runtime.GLOBAL_BASE+{zstart},Runtime.GLOBAL_BASE+{zend})"
            zstart = len(memdata)
            if zstart % 2 == 1:
                zstart += 1
            assert zmemsize % 2 == 0
            jsdata = re.sub(r"HEAPU8.set\(data,\s*Runtime.GLOBAL_BASE\)", zset.format(
              zstart=zstart,
              zend=zstart + zmemsize,
            ), jsdata)
            output_file.write(jsdata)


    except BaseException:
        os.unlink(output_filename)
        os.unlink(zmem_filename)
        raise
    else:
        os.rename(output_filename, source_filename)
        os.unlink(memory_filename)


def zencode(lzops):
    """Translate the given LZ operations into our deflate-like encoding.

    This function encodes the literals and (length,distance) pairs of the
    LZ operation stream into a sequence of bytes, using a huffman-coding
    scheme similar to deflate.  It returns a three tuple (data, l_tree, d_tree)
    giving the encoded bytes, and encoded tree structures for decoding the
    literals/lengths and distances respectively.
    """
    lzops = list(clamp_lz_operations(lzops, 2**15-1))
    # Calculate frequencies for huffman coding trees.
    l_freqs = defaultdict(lambda: 0.0)
    d_freqs = defaultdict(lambda: 0.0)
    for op in lzops:
        if isinstance(op, LZLiteral):
            for c in op.data:
                l_freqs[ord(c)] += 1
        else:
            l_freqs[op.length - 3 + 257] += 1
            d_freqs[op.distance] += 1
    l_freqs[256] += 1
    # XXX TODO: try using extra-bits encoding as used by deflate.
    # Lit/len tree is generally small enough to include in full.
    l_codes, l_tree = enhuffen(l_freqs)
    # The distance tree has a lot of unique entries, so we only
    # include the most popular and encode the rest directly.
    # XXX TODO: dynamically decide how many to include.
    d_top = set()
    for f,d in sorted(((f,d) for (d,f) in d_freqs.iteritems()), reverse=True):
        d_top.add(d)
        if len(d_top) >= 1024:
            break
    d_top_freqs = defaultdict(lambda: 0.0)
    for (d,f) in d_freqs.iteritems():
        if d in d_top:
            d_top_freqs[d] = f
        else:
            d_top_freqs[0] += f
    d_top_codes, d_top_tree = enhuffen(d_top_freqs)
    # Build the final binary string.  This is a giant string of
    # "1" and "0" chars, which is pretty terrible but is easy to
    # work with in python.
    output = []
    for op in lzops:
        if isinstance(op, LZLiteral):
            for c in op.data:
                output.append(l_codes[ord(c)])
        else:
            output.append(l_codes[op.length - 3 + 257])
            if op.distance in d_top_codes:
                output.append(d_top_codes[op.distance])
            else:
                output.append(d_top_codes[0])
                # Encode in 15 bits; top bit is always zero
                output.append(bin(op.distance)[2:].rjust(15, "0"))
    output.append(l_codes[256])
    output = "".join(output)
    # Translate each eight bits into an actul byte.
    final = []
    for i in xrange(0, len(output), 8):
        byte = output[i:i+8].ljust(8, "0")
        final.append(chr(int(byte, 2)))
    final = "".join(final)
    return final, l_tree, d_top_tree


def enhuffen(frequencies):
    """Produce huffman encoding for the given symbol:frequency map.

    This function constructs a huffman tree to encode the symbols.  It returns
    a dict mapping symbols to their corresponding code as a string of "0" and
    "1" characters, and a string encoding a tree lookup structure for decoding
    with the tree at runtime.

    All symbols are assumed to fit in 15 bytes, and the tree is encoded for
    lookup as follows.  Each node of the tree occupies four bytes in the
    lookup structure.  The first two bytes encoding the child for a "0" and
    the second two bytes encode the child for a "1".  If the high bit is set
    on those bytes then it's a leaf node, with the low 15 bits giving the
    symbol.  If not then it's the offset of the next node in the tree, whose
    data can be read at offset*2 bytes from the start of the string.
    """
    total = sum(f for f in frequencies.itervalues())
    in_queue = []
    for c in frequencies:
        in_queue.append((frequencies[c] / total, [c]))
    in_queue.sort()
    queue = []
    codes = defaultdict(lambda: "")

    def popmin():
        if not queue:
            return heapq.heappop(in_queue)
        if not in_queue:
            return heapq.heappop(queue)
        if queue[0][0] < in_queue[0][0]:
            return heapq.heappop(queue)
        return heapq.heappop(in_queue)

    while len(in_queue) > 0 or len(queue) > 1:
        (p1, s1) = popmin()
        (p2, s2) = popmin()
        for c in s1:
            codes[c] = "0" + codes[c]
        for c in s2:
            codes[c] = "1" + codes[c]
        heapq.heappush(queue, (p1 + p2, s1 + s2))

    def encode_symbol(n):
        assert n < 0x8000, "symbol too big: " + str(n)
        return chr(n & 0xFF) + chr(0x80 | (n >> 8))

    def encode_subtree(n):
        assert n < 0x8000, "subtree too big: " + str(n)
        return chr(n & 0xFF) + chr(n >> 8)

    NULL = encode_subtree(0)
    tree = [NULL, NULL]

    branch0 = []
    branch1 = []
    for symbol, code in codes.iteritems():
        if code[0] == "0":
            branch0.append((code[1:], symbol))
        else:
            branch1.append((code[1:], symbol))
    pending_subtrees = [(0, branch0), (1, branch1)]

    while pending_subtrees:
        (idx, subtree) = pending_subtrees.pop()
        assert tree[idx] == NULL
        if len(subtree) == 1:
            assert subtree[0][0] == ""
            tree[idx] = encode_symbol(subtree[0][1])
        else:
            branch0 = []
            branch1 = []
            for code_suffix, symbol in subtree:
                if code_suffix[0] == "0":
                    branch0.append((code_suffix[1:], symbol))
                else:
                    branch1.append((code_suffix[1:], symbol))
            tree[idx] = encode_subtree(len(tree))
            pending_subtrees.append((len(tree), branch0))
            tree.append(NULL)
            pending_subtrees.append((len(tree), branch1))
            tree.append(NULL)

    return codes, "".join(tree)


class LZLiteral(object):
    """A literal block of characters to include in the stream."""

    def __init__(self, data):
        self.length = len(data)
        self.data = data


class LZMatch(object):
    """A length/distance match to include in the stream."""

    def __init__(self, length, distance):
        self.length = length
        self.distance = distance


class Bitstream(object):
    """Read a string as a stream of bits.

    This is a simple iterator-like class to process a string as a stream
    of bits in the correct order for deflate decompression.  It visits
    the zeroth through seventh bit in each byte in order.
    """

    def __init__(self, data):
        self._data = data
        self._byte_offset = 0
        self._bit_offset = 0
        self._byte = ord(self._data[0])

    def _next(self):
        if self._bit_offset > 7:
            self._bit_offset = 0
            self._byte_offset += 1
            self._byte = ord(self._data[self._byte_offset])
        bit = (self._byte & (2**self._bit_offset)) >> self._bit_offset
        self._bit_offset += 1
        return bit

    def read(self, num=1):
        """Read one or more bits from the stream.

        Multi-bit reads are returns as reading the least significant bit
        first.
        """
        out = 0
        for i in xrange(num):
            out |= self._next() << i
        return out

    def byte_align(self):
        """Skip ahead to the next whole-byte boundary in the stream."""
        if self._bit_offset > 0:
            self._bit_offset = 0
            self._byte_offset += 1
            self._byte = ord(self._data[self._byte_offset])


class HuffmanDecoder(object):
    """Decoder for the huffman encoding scheme used in deflate.

    Deflate encodes an alphabet of symbols from 0 to N as a huffman code
    that is uniquely identified by a list of N code lengths, one for each
    symbol in the alphabet in order.  This class takes such a list of
    code lengths and generates a decoder tree.
    """

    def __init__(self, codelens):
        self.root = [None, None]
        self.codes = {}
        # Find out how many codes we need of each length.
        codelen_counts = defaultdict(lambda: 0)
        codelen_max = 0
        for codelen in codelens:
            codelen_counts[codelen] += 1
            if codelen > codelen_max:
                codelen_max = codelen
        codelen_counts[0] = 0
        # Sanity-check that we're not creating a code that would defy
        # the basic laws of information theory.
        for codelen, count in codelen_counts.iteritems():
            if count > 2**codelen:
                msg = "cant have %d codes of length %d" % (count, codelen)
                raise ValueError(msg)
        # Construct the lexicographically first code of each length.
        code = 0
        next_code = {}
        for codelen in xrange(1, codelen_max + 1):
            code = (code + codelen_counts[codelen - 1]) << 1
            next_code[codelen] = code
        # Assign a unique code to each symbol in the alphabet.
        for symbol, codelen in enumerate(codelens):
            if codelen > 0:
                self.codes[symbol] = next_code[codelen]
                next_code[codelen] += 1
        # Build the decoder tree.
        for symbol, code in self.codes.iteritems():
            bits = bin(code)[2:].rjust(codelens[symbol], '0')
            node = self.root
            for bit in bits[:-1]:
                bit = int(bit)
                if node[bit] is None:
                    node[bit] = [None, None]
                node = node[bit]
                if not isinstance(node, list):
                    msg = "code conflict between %d and %d" % (symbol, node)
                    raise ValueError(msg)
            node[int(bits[-1])] = symbol

    def decode(self, bits):
        bit = bits.read()
        node = self.root[bit]
        while isinstance(node, list):
            bit = bits.read()
            node = node[bit]
        return node

        

def merge_lz_operations(lzops):
    """Merge consecutive LZ operations into single ops if possible."""
    lzops = iter(lzops)
    try:
        prev = lzops.next()
        while True:
            cur = lzops.next()
            if isinstance(cur, LZLiteral):
                if isinstance(prev, LZLiteral):
                    prev.data += cur.data
                else:
                    yield prev; prev = cur
            else:
                if isinstance(prev, LZLiteral):
                    yield prev; prev = cur
                else:
                    if prev.distance == cur.distance:
                        prev.length += cur.length
                    else:
                        yield prev; prev = cur
    except StopIteration:
        pass


def clamp_lz_operations(lzops, maxlen):
    """Clamp lengths in lz operations to a maximum value."""
    for op in lzops:
        if isinstance(op, LZLiteral):
            while op.length >= maxlen:
                yield LZLiteral(op.data[:maxlen-1])
                op.data = op.data[maxlen-1:]
            yield op
        else:
            while op.length >= maxlen:
                yield LZMatch(maxlen-3, op.distance)
                op.length -= maxlen-3
            yield op


def decode_zlib_stream(bits):
    """Decode a zlib bitstream into LZLiteral and LZMatch objects.

    This function parses  a zlib bitstream, interprets the huffman encoding,
    and produces a sequence of LZLiteral() and LZMatch() objects representing
    the LZ77 decompression operations.
    """
    CM = bits.read(4)
    CINFO = bits.read(4)
    FCHECK = bits.read(5)
    FDICT = bits.read(1)
    FLEVEL = bits.read(2)
    FLAG = (FCHECK << 3) | (FDICT << 2) | FLEVEL
    # TODO: assert ((CM << 12) | (CINFO << 8) | FLAG) % 31 == 0
    # We only support DEFLATE-encoded zlib streams,
    # with window size <=32K and no pre-set dictionary.
    assert CM == 8
    assert CINFO <= 7  # it must have window size <= 32K
    assert not FDICT  # we don't support pre-set dictionaries
    # Process the contained DEFLATE stream.
    for op in decode_deflate_stream(bits):
        yield op
    # Checksum and additional data may follow; ignore it.


def decode_deflate_stream(bits):
    """Decode a deflate bistream into LZLiteral and LZMatch objects."""
    while True:
        BFINAL = bits.read()
        BTYPE = bits.read(2)
        assert BTYPE != 3
        if BTYPE == 0:
            for op in decode_literal_block(bits):
                yield op
        else:
            if BTYPE == 1:
                h_litlen = DEFAULT_LITLEN_DECODER
                h_dist = DEFAULT_DISTANCE_DECODER
            else:
                h_litlen, h_dist = decode_huffman_data(bits)
            for c in decode_huffman_block(bits, h_litlen, h_dist):
                yield c
        if BFINAL:
            break

def decode_huffman_data(bits):
    """Decode the litlen/dist huffman trees for a dynamic huffman block."""
    HLIT = bits.read(5)
    HDIST = bits.read(5)
    HCLEN = bits.read(4)
    assert HLIT + 257 <= 286
    assert HDIST + 1 <= 32
    assert HCLEN + 4 <= 32
    # Read the huffman tree for the huffman tree data.
    codelen_codelens = [0] * len(CODELEN_ALPHABET)
    for i in xrange(HCLEN + 4):
        codelen_codelens[CODELEN_ALPHABET[i]] = bits.read(3)
    h_codelen = HuffmanDecoder(codelen_codelens)
    # Read all the codelengths for litlen and dist trees.
    # By spec, we have to read them as a single sequence.
    codelens = []
    while len(codelens) < HLIT + HDIST + 258:
        codelen = h_codelen.decode(bits)
        if codelen <= 15:
            codelens.append(codelen)
        elif codelen == 16:
            num_copies = bits.read(2) + 3
            codelens += [codelens[-1]] * num_copies
        elif codelen == 17:
            num_zeros = bits.read(3) + 3
            codelens += [0] * num_zeros
        else:
            assert codelen == 18
            num_zeros = bits.read(7) + 11
            codelens += [0] * num_zeros
    # Check that we read precisely the right number of codelens.
    assert len(codelens) == HLIT + HDIST + 258
    # Now we can make a pair of decoders.
    return (
        HuffmanDecoder(codelens[:HLIT + 257]),
        HuffmanDecoder(codelens[HLIT + 257:])
    )


def decode_literal_block(bits):
    """Decode a DEFLATE literal block."""
    bits.byte_align()
    LEN = bits.read(16)
    NLEN = bits.read(16)
    assert LEN == ~NLEN & 0xFFFF
    chars = []
    for _ in xrange(LEN):
        chars.append(chr(bits.read(8)))
    yield LZLiteral("".join(chars))


def decode_huffman_block(bits, h_litlen, h_dist):
    """Decode a DEFLATE huffman block using the given decoders."""
    literals = []
    while True:
        # Read a literal, length, or end-of-block symbol.
        litlen = h_litlen.decode(bits)
        if litlen == 256:
            # End of block.
            if literals:
                yield LZLiteral("".join(literals))
            break
        elif litlen < 256:
            # LZLiteral char, buffer it to yield runs as a single string.
            literals.append(chr(litlen))
        else:
            # Yield any buffered literal data.
            if literals:
                yield LZLiteral("".join(literals))
                literals = []
            length = decode_extra_length(bits, litlen)
            dist = h_dist.decode(bits)
            dist = decode_extra_distance(bits, dist)
            yield LZMatch(length, dist)


def decode_extra_length(bits, length):
    """Decode extra bits for a match length symbol."""
    if length == 285:
        return 258
    extra = (length - 257) / 4 - 1
    length = length - 254
    if extra > 0:
        ebits = bits.read(extra)
        length = 2**(extra+2) + 3 + (((length + 1) % 4) * (2**extra)) + ebits
    return length


def decode_extra_distance(bits, dist):
    """Decode extra bits for a match distance symbol."""
    assert dist <= 29
    if dist >= 4:
        extra = (dist - 2) / 2
        if extra:
            ebits = bits.read(extra)
            dist = 2**(extra+1) + ((dist % 2) * (2**extra)) + ebits
    dist += 1
    return dist


DEFAULT_LITLEN_DECODER = HuffmanDecoder(
  ([8] * 144) + ([9] * 112) + ([7] * 24) + ([8] * 8)
)

DEFAULT_DISTANCE_DECODER = HuffmanDecoder(
  ([5] * 32)
)


# The following is custom asmjs code to inflat a stream compressed
# by the `zencode` function above.  It processes the input data
# one bit at a time, looking up each symbol in the inline huffman trees.

UNZIP_CODE = """
  function zmeminit(base, zstart, zend) {
    base=base|0
    zstart=zstart|0
    zend=zend|0
    var zcur=0,byte=0,bit=0,shift=0,tree=0,node=0,mlen=0,mxbits=0
    zcur=zstart
    tree=zstart+{L_TREE_ROOT}|0
    Z:while(1) {
      byte={HEAPU8}[zcur]|0
      zcur=zcur+1|0
      shift=7
      while(shift>>0 >= 0) {
        bit=(byte>>shift) & 0x01
        shift=shift-1|0
        if(mxbits>>0 > 0) {
          node=(node<<1)|bit
          mxbits=mxbits-1|0
          if(mxbits>>0 > 0) {
            continue
          }
        } else {
          node={HEAPU16}[(tree+node+node+bit+bit)>>1]|0
          if((node & 0x8000) == 0) {
            continue
          }
          node=node & 0x7FFF
        }
        if(tree>>0 == zstart+{L_TREE_ROOT}>>0) {
          if (node>>0 == 256) { break Z }
          if (node>>0 < 256) {
            {HEAPU8}[base] = node|0
            base=base+1|0;
            node=0
          } else {
            mlen=node-257+3|0
            tree=zstart+{D_TREE_ROOT}|0
            node=0
          }
        } else {
          if(node>>0 == 0) {
            // decode extra distance
            mxbits = 15
          } else {
            // Copy match data to output.
            while(mlen>>0 != 0) {
              {HEAPU8}[base]={HEAPU8}[(base - node)>>0]|0;
              base=base+1|0;
              mlen=mlen-1|0;
            }
            tree=zstart+{L_TREE_ROOT}|0
            node=0
          }
        }
      }
    }
    // zero out remaining compressed data
    while((base|0) < (zend|0)) {
      {HEAPU8}[base]=0;
      base=base+1|0;
    }
  }
"""


if __name__ == "__main__":
    source_filename = sys.argv[1]
    compress_memory_file(source_filename)

