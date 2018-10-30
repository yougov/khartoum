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
