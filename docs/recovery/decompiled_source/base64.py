# Source Generated with Decompyle++
# File: base64.pyc (Python 3.12)

'''Base16, Base32, Base64 (RFC 3548), Base85 and Ascii85 data encodings'''
import re
import struct
import binascii
__all__ = [
    'encode',
    'decode',
    'encodebytes',
    'decodebytes',
    'b64encode',
    'b64decode',
    'b32encode',
    'b32decode',
    'b32hexencode',
    'b32hexdecode',
    'b16encode',
    'b16decode',
    'b85encode',
    'b85decode',
    'a85encode',
    'a85decode',
    'standard_b64encode',
    'standard_b64decode',
    'urlsafe_b64encode',
    'urlsafe_b64decode']
bytes_types = (bytes, bytearray)

def _bytes_from_decode_data(s):
    if isinstance(s, str):
        return s.encode('ascii')
    if None(s, bytes_types):
        return s
    return memoryview(s).tobytes()
# WARNING: Decompyle incomplete


def b64encode(s, altchars = (None,)):
    """Encode the bytes-like object s using Base64 and return a bytes object.

    Optional altchars should be a byte string of length 2 which specifies an
    alternative alphabet for the '+' and '/' characters.  This allows an
    application to e.g. generate url or filesystem safe Base64 strings.
    """
    encoded = binascii.b2a_base64(s, newline = False)
# WARNING: Decompyle incomplete


def b64decode(s, altchars, validate = (None, False)):
    """Decode the Base64 encoded bytes-like object or ASCII string s.

    Optional altchars must be a bytes-like object or ASCII string of length 2
    which specifies the alternative alphabet used instead of the '+' and '/'
    characters.

    The result is returned as a bytes object.  A binascii.Error is raised if
    s is incorrectly padded.

    If validate is False (the default), characters that are neither in the
    normal base-64 alphabet nor the alternative alphabet are discarded prior
    to the padding check.  If validate is True, these non-alphabet characters
    in the input result in a binascii.Error.
    For more information about the strict base64 check, see:

    https://docs.python.org/3.11/library/binascii.html#binascii.a2b_base64
    """
    s = _bytes_from_decode_data(s)
# WARNING: Decompyle incomplete


def standard_b64encode(s):
    '''Encode bytes-like object s using the standard Base64 alphabet.

    The result is returned as a bytes object.
    '''
    return b64encode(s)


def standard_b64decode(s):
    '''Decode bytes encoded with the standard Base64 alphabet.

    Argument s is a bytes-like object or ASCII string to decode.  The result
    is returned as a bytes object.  A binascii.Error is raised if the input
    is incorrectly padded.  Characters that are not in the standard alphabet
    are discarded prior to the padding check.
    '''
    return b64decode(s)

_urlsafe_encode_translation = bytes.maketrans(b'+/', b'-_')
_urlsafe_decode_translation = bytes.maketrans(b'-_', b'+/')

def urlsafe_b64encode(s):
    """Encode bytes using the URL- and filesystem-safe Base64 alphabet.

    Argument s is a bytes-like object to encode.  The result is returned as a
    bytes object.  The alphabet uses '-' instead of '+' and '_' instead of
    '/'.
    """
    return b64encode(s).translate(_urlsafe_encode_translation)


def urlsafe_b64decode(s):
    """Decode bytes using the URL- and filesystem-safe Base64 alphabet.

    Argument s is a bytes-like object or ASCII string to decode.  The result
    is returned as a bytes object.  A binascii.Error is raised if the input
    is incorrectly padded.  Characters that are not in the URL-safe base-64
    alphabet, and are not a plus '+' or slash '/', are discarded prior to the
    padding check.

    The alphabet uses '-' instead of '+' and '_' instead of '/'.
    """
    s = _bytes_from_decode_data(s)
    s = s.translate(_urlsafe_decode_translation)
    return b64decode(s)

_B32_ENCODE_DOCSTRING = '\nEncode the bytes-like objects using {encoding} and return a bytes object.\n'
_B32_DECODE_DOCSTRING = '\nDecode the {encoding} encoded bytes-like object or ASCII string s.\n\nOptional casefold is a flag specifying whether a lowercase alphabet is\nacceptable as input.  For security purposes, the default is False.\n{extra_args}\nThe result is returned as a bytes object.  A binascii.Error is raised if\nthe input is incorrectly padded or if there are non-alphabet\ncharacters present in the input.\n'
_B32_DECODE_MAP01_DOCSTRING = '\nRFC 3548 allows for optional mapping of the digit 0 (zero) to the\nletter O (oh), and for optional mapping of the digit 1 (one) to\neither the letter I (eye) or letter L (el).  The optional argument\nmap01 when not None, specifies which letter the digit 1 should be\nmapped to (when map01 is not None, the digit 0 is always mapped to\nthe letter O).  For security purposes the default is None, so that\n0 and 1 are not allowed in the input.\n'
_b32alphabet = b'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
_b32hexalphabet = b'0123456789ABCDEFGHIJKLMNOPQRSTUV'
_b32tab2 = { }
_b32rev = { }

def _b32encode(alphabet, s):
    pass
# WARNING: Decompyle incomplete


def _b32decode(alphabet, s, casefold, map01 = (False, None)):
    pass
# WARNING: Decompyle incomplete


def b32encode(s):
    return _b32encode(_b32alphabet, s)

b32encode.__doc__ = _B32_ENCODE_DOCSTRING.format(encoding = 'base32')

def b32decode(s, casefold, map01 = (False, None)):
    return _b32decode(_b32alphabet, s, casefold, map01)

b32decode.__doc__ = _B32_DECODE_DOCSTRING.format(encoding = 'base32', extra_args = _B32_DECODE_MAP01_DOCSTRING)

def b32hexencode(s):
    return _b32encode(_b32hexalphabet, s)

b32hexencode.__doc__ = _B32_ENCODE_DOCSTRING.format(encoding = 'base32hex')

def b32hexdecode(s, casefold = (False,)):
    return _b32decode(_b32hexalphabet, s, casefold)

b32hexdecode.__doc__ = _B32_DECODE_DOCSTRING.format(encoding = 'base32hex', extra_args = '')

def b16encode(s):
    '''Encode the bytes-like object s using Base16 and return a bytes object.
    '''
    return binascii.hexlify(s).upper()


def b16decode(s, casefold = (False,)):
    '''Decode the Base16 encoded bytes-like object or ASCII string s.

    Optional casefold is a flag specifying whether a lowercase alphabet is
    acceptable as input.  For security purposes, the default is False.

    The result is returned as a bytes object.  A binascii.Error is raised if
    s is incorrectly padded or if there are non-alphabet characters present
    in the input.
    '''
    s = _bytes_from_decode_data(s)
    if casefold:
        s = s.upper()
    if re.search(b'[^0-9A-F]', s):
        raise binascii.Error('Non-base16 digit found')
    return binascii.unhexlify(s)

_a85chars = None
_a85chars2 = None
_A85START = b'<~'
_A85END = b'~>'

def _85encode(b, chars, chars2, pad, foldnuls, foldspaces = (False, False, False)):
    if not isinstance(b, bytes_types):
        b = memoryview(b).tobytes()
    padding = -len(b) % 4
    if padding:
        b = b + b'\x00' * padding
    words = struct.Struct('!%dI' % len(b) // 4).unpack(b)
# WARNING: Decompyle incomplete


def a85encode(b = None, *, foldspaces, wrapcol, pad, adobe):
    '''Encode bytes-like object b using Ascii85 and return a bytes object.

    foldspaces is an optional flag that uses the special short sequence \'y\'
    instead of 4 consecutive spaces (ASCII 0x20) as supported by \'btoa\'. This
    feature is not supported by the "standard" Adobe encoding.

    wrapcol controls whether the output should have newline (b\'\\n\') characters
    added to it. If this is non-zero, each output line will be at most this
    many characters long.

    pad controls whether the input is padded to a multiple of 4 before
    encoding. Note that the btoa implementation always pads.

    adobe controls whether the encoded byte sequence is framed with <~ and ~>,
    which is used by the Adobe implementation.
    '''
    pass
# WARNING: Decompyle incomplete


def a85decode(b = None, *, foldspaces, adobe, ignorechars):
    '''Decode the Ascii85 encoded bytes-like object or ASCII string b.

    foldspaces is a flag that specifies whether the \'y\' short sequence should be
    accepted as shorthand for 4 consecutive spaces (ASCII 0x20). This feature is
    not supported by the "standard" Adobe encoding.

    adobe controls whether the input sequence is in Adobe Ascii85 format (i.e.
    is framed with <~ and ~>).

    ignorechars should be a byte string containing characters to ignore from the
    input. This should only contain whitespace characters, and by default
    contains all whitespace characters in ASCII.

    The result is returned as a bytes object.
    '''
    b = _bytes_from_decode_data(b)
    if adobe:
        if not b.endswith(_A85END):
            raise ValueError('Ascii85 encoded byte sequences must end with {!r}'.format(_A85END))
        if b.startswith(_A85START):
            b = b[2:-2]
        else:
            b = b[:-2]
    packI = struct.Struct('!I').pack
    decoded = []
    decoded_append = decoded.append
    curr = []
    curr_append = curr.append
    curr_clear = curr.clear
    for x in b + b'uuuu':
        if  <= 33, x or 33, x <= 117:
            pass
        else:
            b + b'uuuu'
    curr_append(x)
    if not len(curr) == 5:
        continue
    for None in curr:
        acc = 85 * acc + (x - 33)
    decoded_append(packI(acc))
    curr_clear()
    continue
    if x == 122:
        if curr:
            raise ValueError('z inside Ascii85 5-tuple')
        decoded_append(b'\x00\x00\x00\x00')
        continue
    if foldspaces and x == 121:
        if curr:
            raise ValueError('y inside Ascii85 5-tuple')
        decoded_append(b'    ')
        continue
    if x in ignorechars:
        continue
    raise ValueError('Non-Ascii85 digit found: %c' % x)
    result = b''.join(decoded)
    padding = 4 - len(curr)
    if padding:
        result = result[:-padding]
    return result
# WARNING: Decompyle incomplete

_b85alphabet = b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{|}~'
_b85chars = None
_b85chars2 = None
_b85dec = None

def b85encode(b, pad = (False,)):
    """Encode bytes-like object b in base85 format and return a bytes object.

    If pad is true, the input is padded with b'\\0' so its length is a multiple of
    4 bytes before encoding.
    """
    pass
# WARNING: Decompyle incomplete


def b85decode(b):
    '''Decode the base85-encoded bytes-like object or ASCII string b

    The result is returned as a bytes object.
    '''
    pass
# WARNING: Decompyle incomplete

MAXLINESIZE = 76
MAXBINSIZE = (MAXLINESIZE // 4) * 3

def encode(input, output):
    '''Encode a file; input and output are binary files.'''
    s = input.read(MAXBINSIZE)
    if input.read(MAXBINSIZE):
        if len(s) < MAXBINSIZE:
            ns = input.read(MAXBINSIZE - len(s))
            if input.read(MAXBINSIZE - len(s)):
                s += ns
                if len(s) < MAXBINSIZE:
                    ns = input.read(MAXBINSIZE - len(s))
                    if input.read(MAXBINSIZE - len(s)):
                        continue
        line = binascii.b2a_base64(s)
        output.write(line)
        s = input.read(MAXBINSIZE)
        if input.read(MAXBINSIZE):
            continue
        return None


def decode(input, output):
    '''Decode a file; input and output are binary files.'''
    line = input.readline()
    if input.readline():
        s = binascii.a2b_base64(line)
        output.write(s)
        line = input.readline()
        if input.readline():
            continue
        return None


def _input_type_check(s):
    m = memoryview(s)
    if m.format not in ('c', 'b', 'B'):
        msg = f'''expected single byte elements, not {m.format!r} from {s.__class__.__name__!s}'''
        raise TypeError(msg)
    if m.ndim != 1:
        msg = 'expected 1-D data, not %d-D data from %s' % (m.ndim, s.__class__.__name__)
        raise TypeError(msg)
    return None
# WARNING: Decompyle incomplete


def encodebytes(s):
    '''Encode a bytestring into a bytes object containing multiple lines
    of base-64 data.'''
    _input_type_check(s)
    pieces = []
    for i in range(0, len(s), MAXBINSIZE):
        chunk = s[i:i + MAXBINSIZE]
        pieces.append(binascii.b2a_base64(chunk))
    return b''.join(pieces)


def decodebytes(s):
    '''Decode a bytestring of base-64 data into a bytes object.'''
    _input_type_check(s)
    return binascii.a2b_base64(s)


def main():
    '''Small main program'''
    import sys
    import getopt
    usage = f'''usage: {sys.argv[0]} [-h|-d|-e|-u] [file|-]\n        -h: print this help message and exit\n        -d, -u: decode\n        -e: encode (default)'''
    (opts, args) = getopt.getopt(sys.argv[1:], 'hdeu')
    func = encode
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    main()
    return None
