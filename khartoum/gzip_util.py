import zlib
import struct
import time


def parse_encoding_header(header):
    """
    Parse the HTTP Accept-Encoding header into a dict of the form,
    {encoding: qvalue}.

    >>> parse_encoding_header('') == {'': 1, 'identity': 1.0}
    True

    >>> parse_encoding_header('*') == {'*': 1, 'identity': 1.0}
    True

    >>> expected = {'identity': 1.0, 'gzip': 1.0, 'compress': 0.5}
    >>> parse_encoding_header('compress;q=0.5, gzip;q=1.0') == expected
    True

    >>> expected = {'*': 0.0, 'gzip': 1.0, 'identity': 0.5}
    >>> parse_encoding_header('gzip;q=1.0, identity; q=0.5, *;q=0') == expected
    True
    """
    encodings = {'identity': 1.0}

    for encoding in header.split(","):
        encoding, sep, params = encoding.partition(';')
        encoding = encoding.strip()
        key, sep, qvalue = params.partition('=')
        encodings[encoding] = float(qvalue or 1)

    return encodings


def gzip_requested(accept_encoding_header):
    """
    Check to see if the client can accept gzipped output, and whether or
    not it is even the preferred method. If `identity` is higher, then no
    gzipping should occur.
    """
    encodings = parse_encoding_header(accept_encoding_header)
    enc = encodings.get('gzip', encodings.get('*'))
    return bool(enc and enc >= encodings['identity'])


# After much Googling and gnashing of teeth, this function stolen from
# cherrypy.lib.encoding seems to be the most straightforward way to do gzip
# encoding of a stream without loading the whole thing into memory at once.
def compress(body, compress_level):
    """
    Compress 'body' at the given compress_level, where 'body' is an iterable
    over chunks of bytes.
    """

    # See http://www.gzip.org/zlib/rfc-gzip.html
    yield b'\x1f\x8b'       # ID1 and ID2: gzip marker
    yield b'\x08'           # CM: compression method
    yield b'\x00'           # FLG: none set
    # MTIME: 4 bytes
    yield struct.pack("<L", int(time.time()) & int('FFFFFFFF', 16))
    yield b'\x02'           # XFL: max compression, slowest algo
    yield b'\xff'           # OS: unknown

    crc = zlib.crc32(b"")
    size = 0
    zobj = zlib.compressobj(compress_level,
                            zlib.DEFLATED, -zlib.MAX_WBITS,
                            zlib.DEF_MEM_LEVEL, 0)
    for line in body:
        size += len(line)
        crc = zlib.crc32(line, crc)
        yield zobj.compress(line)
    yield zobj.flush()

    # CRC32: 4 bytes
    yield struct.pack("<L", crc & int('FFFFFFFF', 16))
    # ISIZE: 4 bytes
    yield struct.pack("<L", size & int('FFFFFFFF', 16))
