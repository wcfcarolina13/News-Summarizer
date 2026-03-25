# Source Generated with Decompyle++
# File: gzip.pyc (Python 3.12)

"""Functions that read and write gzipped files.

The user of the file doesn't have to worry about the compression,
but random access is not allowed."""
import struct
import sys
import time
import os
import zlib
import builtins
import io
import _compression
__all__ = [
    'BadGzipFile',
    'GzipFile',
    'open',
    'compress',
    'decompress']
(FTEXT, FHCRC, FEXTRA, FNAME, FCOMMENT) = (1, 2, 4, 8, 16)
(READ, WRITE) = (1, 2)
_COMPRESS_LEVEL_FAST = 1
_COMPRESS_LEVEL_TRADEOFF = 6
_COMPRESS_LEVEL_BEST = 9
READ_BUFFER_SIZE = 131072
_WRITE_BUFFER_SIZE = 4 * io.DEFAULT_BUFFER_SIZE

def open(filename, mode, compresslevel, encoding, errors, newline = ('rb', _COMPRESS_LEVEL_BEST, None, None, None)):
    '''Open a gzip-compressed file in binary or text mode.

    The filename argument can be an actual filename (a str or bytes object), or
    an existing file object to read from or write to.

    The mode argument can be "r", "rb", "w", "wb", "x", "xb", "a" or "ab" for
    binary mode, or "rt", "wt", "xt" or "at" for text mode. The default mode is
    "rb", and the default compresslevel is 9.

    For binary mode, this function is equivalent to the GzipFile constructor:
    GzipFile(filename, mode, compresslevel). In this case, the encoding, errors
    and newline arguments must not be provided.

    For text mode, a GzipFile object is created, and wrapped in an
    io.TextIOWrapper instance with the specified encoding, error handling
    behavior, and line ending(s).

    '''
    if 't' in mode or 'b' in mode:
        raise ValueError(f'''Invalid mode: {mode!r}''')
# WARNING: Decompyle incomplete


def write32u(output, value):
    output.write(struct.pack('<L', value))


class _PaddedFile:
    """Minimal read-only file object that prepends a string to the contents
    of an actual file. Shouldn't be used outside of gzip.py, as it lacks
    essential functionality."""
    
    def __init__(self, f, prepend = (b'',)):
        self._buffer = prepend
        self._length = len(prepend)
        self.file = f
        self._read = 0

    
    def read(self, size):
        pass
    # WARNING: Decompyle incomplete

    
    def prepend(self, prepend = (b'',)):
        pass
    # WARNING: Decompyle incomplete

    
    def seek(self, off):
        self._read = None
        self._buffer = None
        return self.file.seek(off)

    
    def seekable(self):
        return True



class BadGzipFile(OSError):
    '''Exception raised in some cases for invalid gzip files.'''
    pass


class _WriteBufferStream(io.RawIOBase):
    '''Minimal object to pass WriteBuffer flushes into GzipFile'''
    
    def __init__(self, gzip_file):
        self.gzip_file = gzip_file

    
    def write(self, data):
        return self.gzip_file._write_raw(data)

    
    def seekable(self):
        return False

    
    def writable(self):
        return True



class GzipFile(_compression.BaseStream):
    pass
# WARNING: Decompyle incomplete


def _read_exact(fp, n):
    '''Read exactly *n* bytes from `fp`

    This method is required because fp may be unbuffered,
    i.e. return short reads.
    '''
    data = fp.read(n)
    if len(data) < n:
        b = fp.read(n - len(data))
        if not b:
            raise EOFError('Compressed file ended before the end-of-stream marker was reached')
        data += b
        if len(data) < n:
            continue
    return data


def _read_gzip_header(fp):
    '''Read a gzip header from `fp` and progress to the end of the header.

    Returns last mtime if header was present or None otherwise.
    '''
    magic = fp.read(2)
    if magic == b'':
        return None
    if magic != b'\x1f\x8b':
        raise BadGzipFile('Not a gzipped file (%r)' % magic)
    (method, flag, last_mtime) = struct.unpack('<BBIxx', _read_exact(fp, 8))
    if method != 8:
        raise BadGzipFile('Unknown compression method')
    if flag & FEXTRA:
        (extra_len,) = struct.unpack('<H', _read_exact(fp, 2))
        _read_exact(fp, extra_len)
    if flag & FNAME:
        s = fp.read(1)
        if s or s == b'\x00':
            pass
        
    if flag & FCOMMENT:
        s = fp.read(1)
        if s or s == b'\x00':
            pass
        
    if flag & FHCRC:
        _read_exact(fp, 2)
    return last_mtime


class _GzipReader(_compression.DecompressReader):
    pass
# WARNING: Decompyle incomplete


def _create_simple_gzip_header(compresslevel = None, mtime = None):
    '''
    Write a simple gzip header with no extra fields.
    :param compresslevel: Compresslevel used to determine the xfl bytes.
    :param mtime: The mtime (must support conversion to a 32-bit integer).
    :return: A bytes object representing the gzip header.
    '''
    pass
# WARNING: Decompyle incomplete


def compress(data = None, compresslevel = (_COMPRESS_LEVEL_BEST,), *, mtime):
    '''Compress data in one shot and return the compressed string.

    compresslevel sets the compression level in range of 0-9.
    mtime can be used to set the modification time. The modification time is
    set to the current time by default.
    '''
    if mtime == 0:
        return zlib.compress(data, level = compresslevel, wbits = 31)
    header = None(compresslevel, mtime)
    trailer = struct.pack('<LL', zlib.crc32(data), len(data) & 0xFFFFFFFF)
    return header + zlib.compress(data, level = compresslevel, wbits = -15) + trailer


def decompress(data):
    '''Decompress a gzip compressed string in one shot.
    Return the decompressed string.
    '''
    decompressed_members = []
    fp = io.BytesIO(data)
# WARNING: Decompyle incomplete


def main():
    ArgumentParser = ArgumentParser
    import argparse
    parser = ArgumentParser(description = 'A simple command line interface for the gzip module: act like gzip, but do not delete the input file.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--fast', action = 'store_true', help = 'compress faster')
    group.add_argument('--best', action = 'store_true', help = 'compress better')
    group.add_argument('-d', '--decompress', action = 'store_true', help = 'act like gunzip instead of gzip')
    parser.add_argument('args', nargs = '*', default = [
        '-'], metavar = 'file')
    args = parser.parse_args()
    compresslevel = _COMPRESS_LEVEL_TRADEOFF
    if args.fast:
        compresslevel = _COMPRESS_LEVEL_FAST
    elif args.best:
        compresslevel = _COMPRESS_LEVEL_BEST
    for arg in args.args:
        if args.decompress:
            if arg == '-':
                f = GzipFile(filename = '', mode = 'rb', fileobj = sys.stdin.buffer)
                g = sys.stdout.buffer
            elif arg[-3:] != '.gz':
                sys.exit(f'''filename doesn\'t end in .gz: {arg!r}''')
            f = open(arg, 'rb')
            g = builtins.open(arg[:-3], 'wb')
        elif arg == '-':
            f = sys.stdin.buffer
            g = GzipFile(filename = '', mode = 'wb', fileobj = sys.stdout.buffer, compresslevel = compresslevel)
        else:
            f = builtins.open(arg, 'rb')
            g = open(arg + '.gz', 'wb')
        chunk = f.read(READ_BUFFER_SIZE)
        if not chunk:
            pass
        else:
            g.write(chunk)
        if g is not sys.stdout.buffer:
            g.close()
        if not f is not sys.stdin.buffer:
            continue
        f.close()

if __name__ == '__main__':
    main()
    return None
