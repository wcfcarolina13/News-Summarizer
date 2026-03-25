# Source Generated with Decompyle++
# File: tarfile.pyc (Python 3.12)

__doc__ = 'Read from and write to tar format archives.\n'
version = '0.9.0'
__author__ = 'Lars Gustäbel (lars@gustaebel.de)'
__credits__ = 'Gustavo Niemeyer, Niels Gustäbel, Richard Townsend.'
from builtins import open as bltn_open
import sys
import os
import io
import shutil
import stat
import time
import struct
import copy
import re
import warnings
import pwd
import grp
symlink_exception = (AttributeError, NotImplementedError, OSError)
__all__ = [
    'TarFile',
    'TarInfo',
    'is_tarfile',
    'TarError',
    'ReadError',
    'CompressionError',
    'StreamError',
    'ExtractError',
    'HeaderError',
    'ENCODING',
    'USTAR_FORMAT',
    'GNU_FORMAT',
    'PAX_FORMAT',
    'DEFAULT_FORMAT',
    'open',
    'fully_trusted_filter',
    'data_filter',
    'tar_filter',
    'FilterError',
    'AbsoluteLinkError',
    'OutsideDestinationError',
    'SpecialFileError',
    'AbsolutePathError',
    'LinkOutsideDestinationError']
NUL = b'\x00'
BLOCKSIZE = 512
RECORDSIZE = BLOCKSIZE * 20
GNU_MAGIC = b'ustar  \x00'
POSIX_MAGIC = b'ustar\x0000'
LENGTH_NAME = 100
LENGTH_LINK = 100
LENGTH_PREFIX = 155
REGTYPE = b'0'
AREGTYPE = b'\x00'
LNKTYPE = b'1'
SYMTYPE = b'2'
CHRTYPE = b'3'
BLKTYPE = b'4'
DIRTYPE = b'5'
FIFOTYPE = b'6'
CONTTYPE = b'7'
GNUTYPE_LONGNAME = b'L'
GNUTYPE_LONGLINK = b'K'
GNUTYPE_SPARSE = b'S'
XHDTYPE = b'x'
XGLTYPE = b'g'
SOLARIS_XHDTYPE = b'X'
USTAR_FORMAT = 0
GNU_FORMAT = 1
PAX_FORMAT = 2
DEFAULT_FORMAT = PAX_FORMAT
SUPPORTED_TYPES = (REGTYPE, AREGTYPE, LNKTYPE, SYMTYPE, DIRTYPE, FIFOTYPE, CONTTYPE, CHRTYPE, BLKTYPE, GNUTYPE_LONGNAME, GNUTYPE_LONGLINK, GNUTYPE_SPARSE)
REGULAR_TYPES = (REGTYPE, AREGTYPE, CONTTYPE, GNUTYPE_SPARSE)
GNU_TYPES = (GNUTYPE_LONGNAME, GNUTYPE_LONGLINK, GNUTYPE_SPARSE)
PAX_FIELDS = ('path', 'linkpath', 'size', 'mtime', 'uid', 'gid', 'uname', 'gname')
PAX_NAME_FIELDS = {
    'path',
    'gname',
    'uname',
    'linkpath'}
PAX_NUMBER_FIELDS = {
    'atime': float,
    'ctime': float,
    'mtime': float,
    'uid': int,
    'gid': int,
    'size': int }
if os.name == 'nt':
    ENCODING = 'utf-8'
else:
    ENCODING = sys.getfilesystemencoding()

def stn(s, length, encoding, errors):
    '''Convert a string to a null-terminated bytes object.
    '''
    pass
# WARNING: Decompyle incomplete


def nts(s, encoding, errors):
    '''Convert a null-terminated bytes object to a string.
    '''
    p = s.find(b'\x00')
    if p != -1:
        s = s[:p]
    return s.decode(encoding, errors)


def nti(s):
    '''Convert a number field to a python number.
    '''
    if s[0] in (128, 255):
        n = 0
        for i in range(len(s) - 1):
            n <<= 8
            n += s[i + 1]
        if s[0] == 255:
            n = -(256 ** (len(s) - 1) - n)
        return n
    s = nts(s, 'ascii', 'strict')
    if not s.strip():
        s.strip()
    n = int('0', 8)
    return n
# WARNING: Decompyle incomplete


def itn(n, digits, format = (8, DEFAULT_FORMAT)):
    '''Convert a python number to a number field.
    '''
    original_n = n
    n = int(n)
    if  <= 0, n or 0, n < 8 ** (digits - 1):
        pass
    
    return s
    if format == GNU_FORMAT:
        if  <= -256 ** (digits - 1), n or -256 ** (digits - 1), n < 256 ** (digits - 1):
            pass
        else:
            bytes('%0*o' % (digits - 1, n), 'ascii') + NUL
            raise ValueError('overflow in number field')
        for i in range(digits - 1):
            s.insert(1, n & 255)
            n >>= 8
        return s
    raise bytes('%0*o' % (digits - 1, n), 'ascii') + NUL('overflow in number field')


def calc_chksums(buf):
    """Calculate the checksum for a member's header by summing up all
       characters except for the chksum field which is treated as if
       it was filled with spaces. According to the GNU tar sources,
       some tars (Sun and NeXT) calculate chksum with signed char,
       which will be different if there are chars in the buffer with
       the high bit set. So we calculate two checksums, unsigned and
       signed.
    """
    unsigned_chksum = 256 + sum(struct.unpack_from('148B8x356B', buf))
    signed_chksum = 256 + sum(struct.unpack_from('148b8x356b', buf))
    return (unsigned_chksum, signed_chksum)


def copyfileobj(src, dst, length, exception, bufsize = (None, OSError, None)):
    '''Copy length bytes from fileobj src to fileobj dst.
       If length is None, copy the entire content.
    '''
    if not bufsize:
        bufsize
    bufsize = 16384
    if length == 0:
        return None
# WARNING: Decompyle incomplete


def _safe_print(s):
    encoding = getattr(sys.stdout, 'encoding', None)
# WARNING: Decompyle incomplete


class TarError(Exception):
    '''Base exception.'''
    pass


class ExtractError(TarError):
    '''General exception for extract errors.'''
    pass


class ReadError(TarError):
    '''Exception for unreadable tar archives.'''
    pass


class CompressionError(TarError):
    '''Exception for unavailable compression methods.'''
    pass


class StreamError(TarError):
    '''Exception for unsupported operations on stream-like TarFiles.'''
    pass


class HeaderError(TarError):
    '''Base exception for header errors.'''
    pass


class EmptyHeaderError(HeaderError):
    '''Exception for empty headers.'''
    pass


class TruncatedHeaderError(HeaderError):
    '''Exception for truncated headers.'''
    pass


class EOFHeaderError(HeaderError):
    '''Exception for end of file headers.'''
    pass


class InvalidHeaderError(HeaderError):
    '''Exception for invalid headers.'''
    pass


class SubsequentHeaderError(HeaderError):
    '''Exception for missing and invalid extended headers.'''
    pass


class _LowLevelFile:
    '''Low-level file object. Supports reading and writing.
       It is used instead of a regular file object for streaming
       access.
    '''
    
    def __init__(self, name, mode):
        mode = {
            'r': os.O_RDONLY,
            'w': os.O_WRONLY | os.O_CREAT | os.O_TRUNC }[mode]
        if hasattr(os, 'O_BINARY'):
            mode |= os.O_BINARY
        self.fd = os.open(name, mode, 438)

    
    def close(self):
        os.close(self.fd)

    
    def read(self, size):
        return os.read(self.fd, size)

    
    def write(self, s):
        os.write(self.fd, s)



class _Stream:
    '''Class that serves as an adapter between TarFile and
       a stream-like object.  The stream-like object only
       needs to have a read() or write() method and is accessed
       blockwise.  Use of gzip or bzip2 compression is possible.
       A stream-like object could be for example: sys.stdin,
       sys.stdout, a socket, a tape device etc.

       _Stream is intended to be used only internally.
    '''
    
    def __init__(self, name, mode, comptype, fileobj, bufsize, compresslevel):
        '''Construct a _Stream object.
        '''
        self._extfileobj = True
    # WARNING: Decompyle incomplete

    
    def __del__(self):
        if hasattr(self, 'closed'):
            if not self.closed:
                self.close()
                return None
            return None

    
    def _init_write_gz(self, compresslevel):
        '''Initialize for writing with gzip compression.
        '''
        self.cmp = self.zlib.compressobj(compresslevel, self.zlib.DEFLATED, -(self.zlib.MAX_WBITS), self.zlib.DEF_MEM_LEVEL, 0)
        timestamp = struct.pack('<L', int(time.time()))
        self._Stream__write(b'\x1f\x8b\x08\x08' + timestamp + b'\x02\xff')
        if self.name.endswith('.gz'):
            self.name = self.name[:-3]
        self.name = os.path.basename(self.name)
        self._Stream__write(self.name.encode('iso-8859-1', 'replace') + NUL)

    
    def write(self, s):
        '''Write string s to the stream.
        '''
        if self.comptype == 'gz':
            self.crc = self.zlib.crc32(s, self.crc)
        if self.comptype != 'tar':
            self.cmp.compress(s) = self, self.pos += len(s), .pos
        self._Stream__write(s)

    
    def _Stream__write(self, s):
        '''Write string s to the stream if a whole new block
           is ready to be written.
        '''
        if len(self.buf) > self.bufsize:
            self.fileobj.write(self.buf[:self.bufsize])
            self.buf[self.bufsize:] = self, self.buf += s, .buf
            if len(self.buf) > self.bufsize:
                continue
            return None

    
    def close(self):
        '''Close the _Stream object. No operation should be
           done on it afterwards.
        '''
        if self.closed:
            return None
        self.closed = True
        if self.mode == 'w' and self.comptype != 'tar':
            pass
        if self.mode == 'w' and self.buf:
            self.fileobj.write(self.buf)
            b'' = self, self.buf += self.cmp.flush(), .buf
            if self.comptype == 'gz':
                self.fileobj.write(struct.pack('<L', self.crc))
                self.fileobj.write(struct.pack('<L', self.pos & 0xFFFFFFFF))
        if not self._extfileobj:
            self.fileobj.close()
            return None
        return None
    # WARNING: Decompyle incomplete

    
    def _init_read_gz(self):
        '''Initialize for reading a gzip compressed fileobj.
        '''
        self.cmp = self.zlib.decompressobj(-(self.zlib.MAX_WBITS))
        self.dbuf = b''
        if self._Stream__read(2) != b'\x1f\x8b':
            raise ReadError('not a gzip file')
        if self._Stream__read(1) != b'\x08':
            raise CompressionError('unsupported compression method')
        flag = ord(self._Stream__read(1))
        self._Stream__read(6)
        if flag & 4:
            xlen = ord(self._Stream__read(1)) + 256 * ord(self._Stream__read(1))
            self.read(xlen)
        if flag & 8:
            s = self._Stream__read(1)
            if s or s == NUL:
                pass
            
        if flag & 16:
            s = self._Stream__read(1)
            if s or s == NUL:
                pass
            
        if flag & 2:
            self._Stream__read(2)
            return None

    
    def tell(self):
        """Return the stream's file pointer position.
        """
        return self.pos

    
    def seek(self, pos = (0,)):
        """Set the stream's file pointer to pos. Negative seeking
           is forbidden.
        """
        if pos - self.pos >= 0:
            (blocks, remainder) = divmod(pos - self.pos, self.bufsize)
            for i in range(blocks):
                self.read(self.bufsize)
            self.read(remainder)
            return self.pos
        raise None('seeking backwards is not allowed')

    
    def read(self, size):
        '''Return the next size number of bytes from the stream.'''
        pass
    # WARNING: Decompyle incomplete

    
    def _read(self, size):
        '''Return size bytes from the stream.
        '''
        if self.comptype == 'tar':
            return self._Stream__read(size)
        c = None(self.dbuf)
        t = [
            self.dbuf]
        if c < size:
            if self.buf:
                buf = self.buf
                self.buf = b''
            else:
                buf = self.fileobj.read(self.bufsize)
                if not buf:
                    pass
                else:
                    buf = self.cmp.decompress(buf)
                    t.append(buf)
                    c += len(buf)
                    if c < size:
                        continue
        t = b''.join(t)
        self.dbuf = t[size:]
        return t[:size]
    # WARNING: Decompyle incomplete

    
    def _Stream__read(self, size):
        '''Return size bytes from stream. If internal buffer is empty,
           read another block from the stream.
        '''
        c = len(self.buf)
        t = [
            self.buf]
        if c < size:
            buf = self.fileobj.read(self.bufsize)
            if not buf:
                pass
            else:
                t.append(buf)
                c += len(buf)
                if c < size:
                    continue
        t = b''.join(t)
        self.buf = t[size:]
        return t[:size]



class _StreamProxy(object):
    """Small proxy class that enables transparent compression
       detection for the Stream interface (mode 'r|*').
    """
    
    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.buf = self.fileobj.read(BLOCKSIZE)

    
    def read(self, size):
        self.read = self.fileobj.read
        return self.buf

    
    def getcomptype(self):
        if self.buf.startswith(b'\x1f\x8b\x08'):
            return 'gz'
        if self.buf[0:3] == b'BZh' and self.buf[4:10] == b'1AY&SY':
            return 'bz2'
        if self.buf.startswith((b']\x00\x00\x80', b'\xfd7zXZ')):
            return 'xz'
        return 'tar'

    
    def close(self):
        self.fileobj.close()



class _FileInFile(object):
    '''A thin wrapper around an existing file object that
       provides a part of its data as an individual file
       object.
    '''
    
    def __init__(self, fileobj, offset, size, name, blockinfo = (None,)):
        self.fileobj = fileobj
        self.offset = offset
        self.size = size
        self.position = 0
        self.name = name
        self.closed = False
    # WARNING: Decompyle incomplete

    
    def flush(self):
        pass

    
    def readable(self):
        return True

    
    def writable(self):
        return False

    
    def seekable(self):
        return self.fileobj.seekable()

    
    def tell(self):
        '''Return the current file position.
        '''
        return self.position

    
    def seek(self, position, whence = (io.SEEK_SET,)):
        '''Seek to a position in the file.
        '''
        if whence == io.SEEK_SET:
            self.position = min(max(position, 0), self.size)
            return self.position
        if None == io.SEEK_CUR:
            if position < 0:
                self.position = max(self.position + position, 0)
                return self.position
            self.position = None(self.position + position, self.size)
            return self.position
        if None == io.SEEK_END:
            self.position = max(min(self.size + position, self.size), 0)
            return self.position
        raise None('Invalid argument')

    
    def read(self, size = (None,)):
        '''Read data from the file.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def readinto(self, b):
        buf = self.read(len(b))
        b[:len(buf)] = buf
        return len(buf)

    
    def close(self):
        self.closed = True



class ExFileObject(io.BufferedReader):
    pass
# WARNING: Decompyle incomplete


class FilterError(TarError):
    pass


class AbsolutePathError(FilterError):
    pass
# WARNING: Decompyle incomplete


class OutsideDestinationError(FilterError):
    pass
# WARNING: Decompyle incomplete


class SpecialFileError(FilterError):
    pass
# WARNING: Decompyle incomplete


class AbsoluteLinkError(FilterError):
    pass
# WARNING: Decompyle incomplete


class LinkOutsideDestinationError(FilterError):
    pass
# WARNING: Decompyle incomplete


def _get_filtered_attrs(member, dest_path, for_data = (True,)):
    new_attrs = { }
    name = member.name
    dest_path = os.path.realpath(dest_path)
    if name.startswith(('/', os.sep)):
        name = member.path.lstrip('/' + os.sep)
        new_attrs['name'] = member.path.lstrip('/' + os.sep)
    if os.path.isabs(name):
        raise AbsolutePathError(member)
    target_path = os.path.realpath(os.path.join(dest_path, name))
    if os.path.commonpath([
        target_path,
        dest_path]) != dest_path:
        raise OutsideDestinationError(member, target_path)
    mode = member.mode
# WARNING: Decompyle incomplete


def fully_trusted_filter(member, dest_path):
    return member


def tar_filter(member, dest_path):
    new_attrs = _get_filtered_attrs(member, dest_path, False)
# WARNING: Decompyle incomplete


def data_filter(member, dest_path):
    new_attrs = _get_filtered_attrs(member, dest_path, True)
# WARNING: Decompyle incomplete

_NAMED_FILTERS = {
    'fully_trusted': fully_trusted_filter,
    'tar': tar_filter,
    'data': data_filter }
_KEEP = object()

class TarInfo(object):
    __module__ = __name__
    __qualname__ = 'TarInfo'
    __doc__ = 'Informational class which holds the details about an\n       archive member given by a tar header block.\n       TarInfo objects are returned by TarFile.getmember(),\n       TarFile.getmembers() and TarFile.gettarinfo() and are\n       usually created internally.\n    '
# WARNING: Decompyle incomplete


class TarFile(object):
    '''The TarFile Class provides an interface to tar archives.
    '''
    debug = 0
    dereference = False
    ignore_zeros = False
    errorlevel = 1
    format = DEFAULT_FORMAT
    encoding = ENCODING
    errors = None
    tarinfo = TarInfo
    fileobject = ExFileObject
    extraction_filter = None
    
    def __init__(self, name, mode, fileobj, format, tarinfo, dereference, ignore_zeros, encoding, errors, pax_headers, debug, errorlevel, copybufsize = (None, 'r', None, None, None, None, None, None, 'surrogateescape', None, None, None, None)):
        """Open an (uncompressed) tar archive `name'. `mode' is either 'r' to
           read from an existing archive, 'a' to append data to an existing
           file or 'w' to create a new file overwriting an existing one. `mode'
           defaults to 'r'.
           If `fileobj' is given, it is used for reading or writing data. If it
           can be determined, `mode' is overridden by `fileobj's mode.
           `fileobj' is not closed, when TarFile is closed.
        """
        modes = {
            'r': 'rb',
            'a': 'r+b',
            'w': 'wb',
            'x': 'xb' }
        if mode not in modes:
            raise ValueError("mode must be 'r', 'a', 'w' or 'x'")
        self.mode = mode
        self._mode = modes[mode]
        if not fileobj:
            if not self.mode == 'a' and os.path.exists(name):
                self.mode = 'w'
                self._mode = 'wb'
            fileobj = bltn_open(name, self._mode)
            self._extfileobj = False
    # WARNING: Decompyle incomplete

    open = (lambda cls, name, mode, fileobj, bufsize = (None, 'r', None, RECORDSIZE): pass# WARNING: Decompyle incomplete
)()
    taropen = (lambda cls, name, mode, fileobj = ('r', None): if mode not in ('r', 'a', 'w', 'x'):
raise ValueError("mode must be 'r', 'a', 'w' or 'x'")# WARNING: Decompyle incomplete
)()
    gzopen = (lambda cls, name, mode, fileobj, compresslevel = ('r', None, 9): if mode not in ('r', 'w', 'x'):
raise ValueError("mode must be 'r', 'w' or 'x'")GzipFile = GzipFileimport gzipfileobj = GzipFile(name, mode + 'b', compresslevel, fileobj)# WARNING: Decompyle incomplete
)()
    bz2open = (lambda cls, name, mode, fileobj, compresslevel = ('r', None, 9): if mode not in ('r', 'w', 'x'):
raise ValueError("mode must be 'r', 'w' or 'x'")BZ2File = BZ2Fileimport bz2if not fileobj:
fileobjfileobj = BZ2File(name, mode, compresslevel = compresslevel)# WARNING: Decompyle incomplete
)()
    xzopen = (lambda cls, name, mode, fileobj, preset = ('r', None, None): if mode not in ('r', 'w', 'x'):
raise ValueError("mode must be 'r', 'w' or 'x'")LZMAFile = LZMAFileLZMAError = LZMAErrorimport lzmaif not fileobj:
fileobjfileobj = LZMAFile(name, mode, preset = preset)# WARNING: Decompyle incomplete
)()
    OPEN_METH = {
        'tar': 'taropen',
        'gz': 'gzopen',
        'bz2': 'bz2open',
        'xz': 'xzopen' }
    
    def close(self):
        '''Close the TarFile. In write-mode, two finishing zero blocks are
           appended to the archive.
        '''
        if self.closed:
            return None
        self.closed = True
        if self.mode in ('a', 'w', 'x'):
            self.fileobj.write(NUL * BLOCKSIZE * 2)
            (blocks, remainder) = divmod(self.offset, RECORDSIZE)
            if remainder > 0:
                self.fileobj.write(NUL * (RECORDSIZE - remainder))
        if not self._extfileobj:
            self.fileobj.close()
            return None
        return None
    # WARNING: Decompyle incomplete

    
    def getmember(self, name):
        """Return a TarInfo object for member `name'. If `name' can not be
           found in the archive, KeyError is raised. If a member occurs more
           than once in the archive, its last occurrence is assumed to be the
           most up-to-date version.
        """
        tarinfo = self._getmember(name.rstrip('/'))
    # WARNING: Decompyle incomplete

    
    def getmembers(self):
        '''Return the members of the archive as a list of TarInfo objects. The
           list has the same order as the members in the archive.
        '''
        self._check()
        if not self._loaded:
            self._load()
        return self.members

    
    def getnames(self):
        '''Return the members of the archive as a list of their names. It has
           the same order as the list returned by getmembers().
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def gettarinfo(self, name, arcname, fileobj = (None, None, None)):
        """Create a TarInfo object from the result of os.stat or equivalent
           on an existing file. The file is either named by `name', or
           specified as a file object `fileobj' with a file descriptor. If
           given, `arcname' specifies an alternative name for the file in the
           archive, otherwise, the name is taken from the 'name' attribute of
           'fileobj', or the 'name' argument. The name should be a text
           string.
        """
        self._check('awx')
    # WARNING: Decompyle incomplete

    
    def list(self = classmethod, verbose = (True,), *, members):
        """Print a table of contents to sys.stdout. If `verbose' is False, only
           the names of the members are printed. If it is True, an `ls -l'-like
           output is produced. `members' is optional and must be a subset of the
           list returned by getmembers().
        """
        self._check()
    # WARNING: Decompyle incomplete

    
    def add(self, name = classmethod, arcname = (None, True), recursive = {
        'filter': None }, *, filter):
        """Add the file `name' to the archive. `name' may be any type of file
           (directory, fifo, symbolic link, etc.). If given, `arcname'
           specifies an alternative name for the file in the archive.
           Directories are added recursively by default. This can be avoided by
           setting `recursive' to False. `filter' is a function
           that expects a TarInfo object argument and returns the changed
           TarInfo object, if it returns None the TarInfo object will be
           excluded from the archive.
        """
        self._check('awx')
    # WARNING: Decompyle incomplete

    
    def addfile(self, tarinfo, fileobj = (None,)):
        """Add the TarInfo object `tarinfo' to the archive. If `fileobj' is
           given, it should be a binary file, and tarinfo.size bytes are read
           from it and added to the archive. You can create TarInfo objects
           directly, or by using gettarinfo().
        """
        self._check('awx')
        tarinfo = copy.copy(tarinfo)
        buf = tarinfo.tobuf(self.format, self.encoding, self.errors)
        self.fileobj.write(buf)
        self.copybufsize = self, self.offset += len(buf), .offset
    # WARNING: Decompyle incomplete

    
    def _get_filter_function(self, filter):
        pass
    # WARNING: Decompyle incomplete

    
    def extractall(self = classmethod, path = ('.', None), members = {
        'numeric_owner': False,
        'filter': None }, *, numeric_owner, filter):
        """Extract all members from the archive to the current working
           directory and set owner, modification time and permissions on
           directories afterwards. `path' specifies a different directory
           to extract to. `members' is optional and must be a subset of the
           list returned by getmembers(). If `numeric_owner` is True, only
           the numbers for user/group names are used and not the names.

           The `filter` function will be called on each member just
           before extraction.
           It can return a changed TarInfo or None to skip the member.
           String names of common filters are accepted.
        """
        directories = []
        filter_function = self._get_filter_function(filter)
    # WARNING: Decompyle incomplete

    
    def extract(self, member = classmethod, path = ('', True), set_attrs = {
        'numeric_owner': False,
        'filter': None }, *, numeric_owner, filter):
        """Extract a member from the archive to the current working directory,
           using its full name. Its file information is extracted as accurately
           as possible. `member' may be a filename or a TarInfo object. You can
           specify a different directory using `path'. File attributes (owner,
           mtime, mode) are set unless `set_attrs' is False. If `numeric_owner`
           is True, only the numbers for user/group names are used and not
           the names.

           The `filter` function will be called before extraction.
           It can return a changed TarInfo or None to skip the member.
           String names of common filters are accepted.
        """
        filter_function = self._get_filter_function(filter)
        tarinfo = self._get_extract_tarinfo(member, filter_function, path)
    # WARNING: Decompyle incomplete

    
    def _get_extract_tarinfo(self, member, filter_function, path):
        '''Get filtered TarInfo (or None) from member, which might be a str'''
        if isinstance(member, str):
            tarinfo = self.getmember(member)
        else:
            tarinfo = member
        unfiltered = tarinfo
        tarinfo = filter_function(tarinfo, path)
    # WARNING: Decompyle incomplete

    
    def _extract_one(self, tarinfo, path, set_attrs, numeric_owner):
        '''Extract from filtered tarinfo to disk'''
        self._check('r')
        self._extract_member(tarinfo, os.path.join(path, tarinfo.name), set_attrs = set_attrs, numeric_owner = numeric_owner)
        return None
    # WARNING: Decompyle incomplete

    
    def _handle_nonfatal_error(self, e):
        '''Handle non-fatal error (ExtractError) according to errorlevel'''
        if self.errorlevel > 1:
            raise 
        self._dbg(1, 'tarfile: %s' % e)

    
    def _handle_fatal_error(self, e):
        '''Handle "fatal" error according to self.errorlevel'''
        if self.errorlevel > 0:
            raise 
    # WARNING: Decompyle incomplete

    
    def extractfile(self, member):
        """Extract a member from the archive as a file object. `member' may be
           a filename or a TarInfo object. If `member' is a regular file or
           a link, an io.BufferedReader object is returned. For all other
           existing members, None is returned. If `member' does not appear
           in the archive, KeyError is raised.
        """
        self._check('r')
        if isinstance(member, str):
            tarinfo = self.getmember(member)
        else:
            tarinfo = member
        if tarinfo.isreg() or tarinfo.type not in SUPPORTED_TYPES:
            return self.fileobject(self, tarinfo)
        if None.islnk() or tarinfo.issym():
            if isinstance(self.fileobj, _Stream):
                raise StreamError('cannot extract (sym)link as file object')
            return self.extractfile(self._find_link_target(tarinfo))

    
    def _extract_member(self, tarinfo, targetpath, set_attrs, numeric_owner = (True, False)):
        '''Extract the TarInfo object tarinfo to a physical
           file called targetpath.
        '''
        targetpath = targetpath.rstrip('/')
        targetpath = targetpath.replace('/', os.sep)
        upperdirs = os.path.dirname(targetpath)
        if not upperdirs and os.path.exists(upperdirs):
            os.makedirs(upperdirs)
        if tarinfo.islnk() or tarinfo.issym():
            self._dbg(1, f'''{tarinfo.name!s} -> {tarinfo.linkname!s}''')
        else:
            self._dbg(1, tarinfo.name)
        if tarinfo.isreg():
            self.makefile(tarinfo, targetpath)
        elif tarinfo.isdir():
            self.makedir(tarinfo, targetpath)
        elif tarinfo.isfifo():
            self.makefifo(tarinfo, targetpath)
        elif tarinfo.ischr() or tarinfo.isblk():
            self.makedev(tarinfo, targetpath)
        elif tarinfo.islnk() or tarinfo.issym():
            self.makelink(tarinfo, targetpath)
        elif tarinfo.type not in SUPPORTED_TYPES:
            self.makeunknown(tarinfo, targetpath)
        else:
            self.makefile(tarinfo, targetpath)
        if set_attrs:
            self.chown(tarinfo, targetpath, numeric_owner)
            if not tarinfo.issym():
                self.chmod(tarinfo, targetpath)
                self.utime(tarinfo, targetpath)
                return None
            return None

    
    def makedir(self, tarinfo, targetpath):
        '''Make a directory called targetpath.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def makefile(self, tarinfo, targetpath):
        '''Make a file called targetpath.
        '''
        source = self.fileobj
        source.seek(tarinfo.offset_data)
        bufsize = self.copybufsize
    # WARNING: Decompyle incomplete

    
    def makeunknown(self, tarinfo, targetpath):
        '''Make a file from a TarInfo object with an unknown type
           at targetpath.
        '''
        self.makefile(tarinfo, targetpath)
        self._dbg(1, 'tarfile: Unknown file type %r, extracted as regular file.' % tarinfo.type)

    
    def makefifo(self, tarinfo, targetpath):
        '''Make a fifo called targetpath.
        '''
        if hasattr(os, 'mkfifo'):
            os.mkfifo(targetpath)
            return None
        raise ExtractError('fifo not supported by system')

    
    def makedev(self, tarinfo, targetpath):
        '''Make a character or block device called targetpath.
        '''
        if not hasattr(os, 'mknod') or hasattr(os, 'makedev'):
            raise ExtractError('special devices not supported by system')
        mode = tarinfo.mode
    # WARNING: Decompyle incomplete

    
    def makelink(self, tarinfo, targetpath):
        '''Make a (symbolic) link called targetpath. If it cannot be created
          (platform limitation), we try to make a copy of the referenced file
          instead of a link.
        '''
        if tarinfo.issym():
            if os.path.lexists(targetpath):
                os.unlink(targetpath)
            os.symlink(tarinfo.linkname, targetpath)
            return None
        if os.path.exists(tarinfo._link_target):
            os.link(tarinfo._link_target, targetpath)
            return None
        self._extract_member(self._find_link_target(tarinfo), targetpath)
        return None
    # WARNING: Decompyle incomplete

    
    def chown(self, tarinfo, targetpath, numeric_owner):
        '''Set owner of targetpath according to tarinfo. If numeric_owner
           is True, use .gid/.uid instead of .gname/.uname. If numeric_owner
           is False, fall back to .gid/.uid when the search based on name
           fails.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def chmod(self, tarinfo, targetpath):
        '''Set file permissions of targetpath according to tarinfo.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def utime(self, tarinfo, targetpath):
        '''Set modification time of targetpath according to tarinfo.
        '''
        mtime = tarinfo.mtime
    # WARNING: Decompyle incomplete

    
    def next(self):
        '''Return the next member of the archive as a TarInfo object, when
           TarFile is opened for reading. Return None if there is no more
           available.
        '''
        self._check('ra')
    # WARNING: Decompyle incomplete

    
    def _getmember(self, name, tarinfo, normalize = (None, False)):
        '''Find an archive member by name from bottom to top.
           If tarinfo is given, it is used as the starting point.
        '''
        members = self.getmembers()
        skipping = False
    # WARNING: Decompyle incomplete

    
    def _load(self):
        '''Read through the entire archive file and look for readable
           members.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _check(self, mode = (None,)):
        """Check if TarFile is still open, and if the operation's mode
           corresponds to TarFile's mode.
        """
        if self.closed:
            raise OSError('%s is closed' % self.__class__.__name__)
    # WARNING: Decompyle incomplete

    
    def _find_link_target(self, tarinfo):
        '''Find the target member of a symlink or hardlink member in the
           archive.
        '''
        if tarinfo.issym():
            linkname = '/'.join(filter(None, (os.path.dirname(tarinfo.name), tarinfo.linkname)))
            limit = None
        else:
            linkname = tarinfo.linkname
            limit = tarinfo
        member = self._getmember(linkname, tarinfo = limit, normalize = True)
    # WARNING: Decompyle incomplete

    
    def __iter__(self):
        '''Provide an iterator object.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _dbg(self, level, msg):
        '''Write debugging output to sys.stderr.
        '''
        if level <= self.debug:
            print(msg, file = sys.stderr)
            return None

    
    def __enter__(self):
        self._check()
        return self

    
    def __exit__(self, type, value, traceback):
        pass
    # WARNING: Decompyle incomplete



def is_tarfile(name):
    """Return True if name points to a tar archive that we
       are able to handle, else return False.

       'name' should be a string, file, or file-like object.
    """
    if hasattr(name, 'read'):
        pos = name.tell()
        t = open(fileobj = name)
        name.seek(pos)
    else:
        t = open(name)
    t.close()
    return True
# WARNING: Decompyle incomplete

open = TarFile.open

def main():
    import argparse
    description = 'A simple command-line interface for tarfile module.'
    parser = argparse.ArgumentParser(description = description)
    parser.add_argument('-v', '--verbose', action = 'store_true', default = False, help = 'Verbose output')
    parser.add_argument('--filter', metavar = '<filtername>', choices = _NAMED_FILTERS, help = 'Filter for extraction')
    group = parser.add_mutually_exclusive_group(required = True)
    group.add_argument('-l', '--list', metavar = '<tarfile>', help = 'Show listing of a tarfile')
    group.add_argument('-e', '--extract', nargs = '+', metavar = ('<tarfile>', '<output_dir>'), help = 'Extract tarfile into target dir')
    group.add_argument('-c', '--create', nargs = '+', metavar = ('<name>', '<file>'), help = 'Create tarfile from sources')
    group.add_argument('-t', '--test', metavar = '<tarfile>', help = 'Test if a tarfile is valid')
    args = parser.parse_args()
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    main()
    return None
return None
# WARNING: Decompyle incomplete
