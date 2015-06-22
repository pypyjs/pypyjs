#
#  Compress inline memory initializer for emscripten-compiled file.
#
#  Given an emscripten-compiled .js file with corresponding .js.mem file
#  for its memory initializer, this script will replace the memory initializer
#  with a compressed version in .js.lzmem, and will modify the javascript to
#  transparently decompress it at startup.
#
#  The compression scheme used is currently a variant of the LZ4 block format:
#
#    https://github.com/Cyan4973/lz4/blob/master/lz4_Block_format.md
#
#  It has been tweaked to provide empirically better compression for the kinds
#  of data in the PyPy.js memory initializer.  This scheme does not produce as
#   much compression as e.g. gzip, but the decompression code is very small
#  and runs very fast and so is highly suitable for running on every single
#  application startup.
#
#  Future iterations might use a different scheme.  This can be done without
#  concern for backwards-compatibility - since we store the decompression code
#  inline in the host javascript, we can change it at will.
#
#  To generate the compressed data, we actually run it through standard
#  zlib compression and then decode the zlib stream into an equivalent raw
#  sequence of LZ77 operations.  This avoids having to take a dependency on
#  any particular external compression software.
#

import os
import re
import sys
import zlib
from collections import defaultdict


# ZLIB meta-huffman-tree alphabet symbols, in datastream order.

CODELEN_ALPHABET = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5,
                    11, 4, 12, 3, 13, 2, 14, 1, 15]


def compress_memory_file(source_filename):
    memory_filename = source_filename + ".mem"
    output_filename = source_filename + ".new"
    lzmem_filename = source_filename + ".lzmem"

    # Read in all the data.  Whatever, it's only a few MB...

    with open(source_filename) as f:
        jsdata = f.read()

    with open(memory_filename) as f:
        memdata = f.read()

    # Generate the compressed "lzmem" file.

    zmemdata = zlib.compress(memdata, 9)
    lzmem = LZStream(decode_zlib_stream(Bitstream(zmemdata)))

    with open(lzmem_filename, "w") as lzmem_file:
        for lit, match in lzmem.iterpairs():
            lzmem_file.write(encode_lz_pair(lit, match))
        lzmem_size = lzmem_file.tell()

    # Generate the modified javascript code.

    try:
        with open(output_filename, "w") as output_file:
 
            assert "lzmeminit" not in jsdata

            # Tell it to load the compressed memory file, not the raw one.

            jsdata = jsdata.replace(os.path.basename(memory_filename),
                                    os.path.basename(lzmem_filename))

            # Find the (possibly minified) name of the Uint8 heap array,
            # so we can refer to it in the decompressor source code.

            r = re.compile(r"var ([a-zA-Z0-9]+)\s*=\s*new\s+global.Uint8Array")
            match = r.search(jsdata)
            if match is None:
                raise ValueError("heap view could not be found")
            HEAPU8 = match.group(1)

            # Add an function to the asmjs module that will decompress the
            # memory data in-place.  Yes, this is raw hand-written asmjs for
            # an LZ4 style decompressor, which is astonishingly compact.

            r = re.compile(r"}\s*// EMSCRIPTEN_END_FUNCS", re.MULTILINE)
            match = r.search(jsdata)
            if match is None:
                raise ValueError("EMSCRIPTEN_END_FUNCS not found")

            output_file.write(jsdata[:match.start()])
            output_file.write("}")
            output_file.write("""
              function lzmeminit(base, lzcur, lzend) {
                base=base|0;
                lzcur=lzcur|0;
                lzend=lzend|0;
                var byte=0,litlen=0,mlen=0,mdist=0,vint=0;
                while(1) {
                  // We assume that we don't overwrite the lz data...
                  // if(base >= lzcur) throw "OVERWRITTEN";
                  // Read and decode lengths from the token.
                  byte={HEAPU8}[lzcur]|0;
                  lzcur=lzcur+1|0;
                  litlen=(byte >> (8 - {TOKEN_BITS_LITERAL}))|0
                  mlen=(byte & {MAX_RAW_MATCHLEN})|0
                  // Read extra varint for litlen if present.
                  if (litlen>>0 == {MAX_RAW_LITLEN}) {
                    vint = 0;
                    do {
                      byte={HEAPU8}[lzcur]|0;
                      lzcur=lzcur+1|0;
                      vint = vint << 7 | (byte & 0x7F);
                    } while(byte & 0x80)
                    litlen = litlen + vint | 0;
                  }
                  // Copy literal data to output.
                  while(litlen>>0 != 0) {
                    byte={HEAPU8}[lzcur]|0;
                    lzcur=lzcur+1|0;
                    {HEAPU8}[base] = byte|0;
                    base=base+1|0;
                    litlen=litlen-1|0;
                  }
                  // Break if end of file.
                  if ((lzcur|0) >= (lzend|0)) break;
                  // Read match distance.
                  byte={HEAPU8}[lzcur]|0;
                  lzcur=lzcur+1|0;
                  mdist = byte & 0x7F;
                  if (byte & 0x80) {
                    byte={HEAPU8}[lzcur]|0;
                    lzcur=lzcur+1|0;
                    mdist = (byte << 7) | mdist;
                  }
                  mdist=mdist+1|0;
                  // Read extra varint for matchlen if present.
                  if (mlen>>0 == {MAX_RAW_MATCHLEN}) {
                    vint = 0;
                    do {
                      byte={HEAPU8}[lzcur]|0;
                      lzcur=lzcur+1|0;
                      vint = vint << 7 | (byte & 0x7F);
                    } while(byte & 0x80)
                    mlen = mlen + vint | 0;
                  }
                  mlen = mlen + 3 | 0;
                  // Copy match data to output.
                  while(mlen>>0 != 0) {
                    byte={HEAPU8}[(base - mdist)>>0]|0;
                    {HEAPU8}[base] = byte|0;
                    base=base+1|0;
                    mlen=mlen-1|0;
                  }
                  // Break if end of file.
                  if ((lzcur|0) >= (lzend|0)) break;
                }
                // zero out remaining compressed data
                while((base|0) < (lzend|0)) {
                  {HEAPU8}[base]=0;
                  base=base+1|0;
                }
              }
            """.replace("{HEAPU8}", HEAPU8)
               .replace("{TOKEN_BITS_LITERAL}", str(TOKEN_BITS_LITERAL))
               .replace("{MAX_RAW_LITLEN}", str(MAX_RAW_LITLEN))
               .replace("{MAX_RAW_MATCHLEN}", str(MAX_RAW_MATCHLEN))
            )
            output_file.write(match.group(0)[1:])
            jsdata = jsdata[match.end():]

            # Export the function for use by shell code.

            r = re.compile(r"}}\)\s*// EMSCRIPTEN_END_ASM", re.MULTILINE)
            match = r.search(jsdata)
            if match is None:
                raise ValueError("EMSCRIPTEN_END_ASM not found")

            output_file.write(jsdata[:match.start()])
            output_file.write(",lzmeminit:lzmeminit")
            output_file.write(match.group(0))
            jsdata = jsdata[match.end():]

            # Find any code that loads the heap data, and have it write at
            # appropriate offset and call the decompressor function.
            # We arrange for the compressed data to sit at the end of
            # the final memory region, poking out just slightly past the
            # end.  This allows it to be decompressed in-place without
            # the possibility of overwriting un-processed data.

            lzset = "HEAPU8.set(data, STATIC_BASE+{lzstart});"
            lzset += "asm[\"lzmeminit\"](STATIC_BASE,"
            lzset += "STATIC_BASE+{lzstart},STATIC_BASE+{lzend})"
            jsdata = re.sub(r"HEAPU8.set\(data,STATIC_BASE\)", lzset.format(
              lzstart=len(memdata) - lzmem_size + 1,
              lzend=len(memdata) + 1,
            ), jsdata)
            output_file.write(jsdata)


    except BaseException:
        os.unlink(output_filename)
        os.unlink(lzmem_filename)
        raise
    else:
        os.rename(output_filename, source_filename)
        os.unlink(memory_filename)



# Unlike standard LZ4, we use 3 token bits for literal lenghts and
# 5 token bits for match lengths.  This seems to consistently give
# better compression for .mem data file.

TOKEN_BITS_LITERAL = 3
MAX_RAW_LITLEN = 2**TOKEN_BITS_LITERAL - 1
MAX_RAW_MATCHLEN = 2**(8 - TOKEN_BITS_LITERAL) - 1

def encode_lz_pair(lit, match):
    l_head, l_tail = encode_lz_literal(lit)
    if match is None:
        m_head = 0
        m_tail = []
    else:
        m_head, m_tail = encode_lz_match(match)
    head = chr((l_head << (8 - TOKEN_BITS_LITERAL)) | m_head)
    return head + l_tail + m_tail


def encode_lz_literal(lit):
    litlen = len(lit.data)
    if litlen < MAX_RAW_LITLEN:
        return litlen, lit.data
    else:
        return MAX_RAW_LITLEN, encode_lz_varint(litlen - MAX_RAW_LITLEN) + lit.data


def encode_lz_match(match):
    # Unlike standard LZ4, encode distance in one or two bytes.
    # We know it's < 32K, so we can use high bit as flag.
    # This also means we can store 3-byte matches compactly, while
    # LZ4 uses a minimum match length of 4 bytes.
    dist = match.distance - 1
    assert dist & 0x8000 == 0
    if dist <= 0x7F:
        tail = chr(dist)
    else:
        tail = chr((dist & 0x7F) | 0x80) + chr(dist >> 7)
    # Encode length as token plus optional varint.
    matchlen = match.length - 3
    if matchlen < MAX_RAW_MATCHLEN:
        head = matchlen
    else:
        head = MAX_RAW_MATCHLEN
        tail += encode_lz_varint(matchlen - MAX_RAW_MATCHLEN)
    return head, tail


# Unlike standard LZ4, we encode long literal and match lengths as
# protobuf-style varints rather than runs of 255.  I'm not actually sure
# if this is a win in practice though...

def encode_lz_varint(value):
    bytes = []
    while value > 0x7F:
        bytes.append(value & 0x7F)
        value = value >> 7
    bytes.append(value)
    bytes.reverse()
    for i in xrange(len(bytes) - 1):
        bytes[i] |= 0x80
    return "".join(chr(b) for b in bytes)


class LZStream(object):
    """A sequence of LZLiteral and LZMatch objects encoding a datastream.

    An LZ77-encoded datastream is an sequence of alternating "literal" and
    "match" codes, representing data to be copied from the input stream or
    from a previous position in the output.  We follow lz4 convention by
    using a strictly alternating sequene, allowing arbitrary length of literals
    and matches, and ensuring that the stream ends with a literal.
    """

    def __init__(self, operations=()):
        self.operations = [LZLiteral("")]
        for op in operations:
            self.append(op)

    def append(self, op):
        prev = self.operations[-1]
        if isinstance(op, LZLiteral):
            if isinstance(prev, LZLiteral):
                prev.data += op.data
            else:
                self.operations.append(op)
        else:
            if isinstance(prev, LZLiteral):
                self.operations.append(op)
                # Short enough to merge into that literal?
                # XXX TODO: this seems to increase file size overall,
                # we may need to be strategic about which we merge.
                if False and op.length == 3 and op.distance > 127:
                    if op.length + len(prev.data) < MAX_RAW_LITLEN:
                        alldata = self.expand()
                        self.operations.pop()
                        prev.data += alldata[-1*op.length:]
            else:
                if prev.distance == op.distance:
                    prev.length += op.length
                else:
                    self.operations.append(LZLiteral(""))
                    self.operations.append(op)

    def iterpairs(self):
        num_ops = len(self.operations)
        if num_ops % 2 > 0:
            num_ops += 1
        try:
            for i in xrange(0, num_ops, 2):
                yield self.operations[i], self.operations[i+1]
        except IndexError:
            if i < len(self.operations):
                yield self.operations[i], None
            else:
                yield LZLiteral(""), None

    def expand(self):
        output = []
        for lit, match in self.iterpairs():
            if lit.data:
                output.extend(lit.data)
            if match is not None:
                length = match.length
                while length > 0:
                    output.append(output[-1 * match.distance])
                    length -= 1
        return "".join(output)
            

class LZLiteral(object):
    """A literal block of characters to include in the stream."""

    def __init__(self, data):
        self.data = data


class LZMatch(object):
    """A length/distance backreference to include in the stream."""

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
                h_dist = DEFAULT_DIST_DECODER
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
    """Decode extra bits for a backref length symbol."""
    if length == 285:
        return 258
    extra = (length - 257) / 4 - 1
    length = length - 254
    if extra > 0:
        ebits = bits.read(extra)
        length = 2**(extra+2) + 3 + (((length + 1) % 4) * (2**extra)) + ebits
    return length


def decode_extra_distance(bits, dist):
    """Decode extra bits for a backref distance symbol."""
    assert dist <= 29
    if dist >= 4:
        extra = (dist - 2) / 2
        if extra:
            ebits = bits.read(extra)
            dist = 2**(extra+1) + ((dist % 2) * (2**extra)) + ebits
    dist += 1
    return dist


DEFAULT_LENGTH_HTREE = HuffmanDecoder(
  ([8] * 144) + ([9] * 112) + ([7] * 24) + ([8] * 8)
)

DEFAULT_DISTANCE_HTREE = HuffmanDecoder(
  ([5] * 32)
)


if __name__ == "__main__":
    source_filename = sys.argv[1]
    compress_memory_file(source_filename)

