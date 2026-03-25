# Source Generated with Decompyle++
# File: tempfile.pyc (Python 3.12)

"""Temporary files.

This module provides generic, low- and high-level interfaces for
creating temporary files and directories.  All of the interfaces
provided by this module can be used without fear of race conditions
except for 'mktemp'.  'mktemp' is subject to race conditions and
should not be used; it is provided for backward compatibility only.

The default path names are returned as str.  If you supply bytes as
input, all return values will be in bytes.  Ex:

    >>> tempfile.mkstemp()
    (4, '/tmp/tmptpu9nin8')
    >>> tempfile.mkdtemp(suffix=b'')
    b'/tmp/tmppbi8f0hy'

This module also provides some data items to the user:

  TMP_MAX  - maximum number of names that will be tried before
             giving up.
  tempdir  - If this is set to a string before the first use of
             any routine from this module, it will be considered as
             another candidate location to store temporary files.
"""
__all__ = [
    'NamedTemporaryFile',
    'TemporaryFile',
    'SpooledTemporaryFile',
    'TemporaryDirectory',
    'mkstemp',
    'mkdtemp',
    'mktemp',
    'TMP_MAX',
    'gettempprefix',
    'tempdir',
    'gettempdir',
    'gettempprefixb',
    'gettempdirb']
import functools as _functools
import warnings as _warnings
import io as _io
import os as _os
import shutil as _shutil
import errno as _errno
from random import Random as _Random
import sys as _sys
import types as _types
import weakref as _weakref
import _thread
_allocate_lock = _thread.allocate_lock
_text_openflags = _os.O_RDWR | _os.O_CREAT | _os.O_EXCL
if hasattr(_os, 'O_NOFOLLOW'):
    _text_openflags |= _os.O_NOFOLLOW
_bin_openflags = _text_openflags
if hasattr(_os, 'O_BINARY'):
    _bin_openflags |= _os.O_BINARY
if hasattr(_os, 'TMP_MAX'):
    TMP_MAX = _os.TMP_MAX
else:
    TMP_MAX = 10000
template = 'tmp'
_once_lock = _allocate_lock()

def _exists(fn):
    _os.lstat(fn)
    return True
# WARNING: Decompyle incomplete


def _infer_return_type(*args):
    '''Look at the type of all args and divine their implied return type.'''
    return_type = None
# WARNING: Decompyle incomplete


def _sanitize_params(prefix, suffix, dir):
    '''Common parameter processing for most APIs in this module.'''
    output_type = _infer_return_type(prefix, suffix, dir)
# WARNING: Decompyle incomplete


class _RandomNameSequence:
    '''An instance of _RandomNameSequence generates an endless
    sequence of unpredictable strings which can safely be incorporated
    into file names.  Each string is eight characters long.  Multiple
    threads can safely use the same instance at the same time.

    _RandomNameSequence is an iterator.'''
    characters = 'abcdefghijklmnopqrstuvwxyz0123456789_'
    rng = (lambda self: cur_pid = _os.getpid()if cur_pid != getattr(self, '_rng_pid', None):
self._rng = _Random()self._rng_pid = cur_pidself._rng)()
    
    def __iter__(self):
        return self

    
    def __next__(self):
        return ''.join(self.rng.choices(self.characters, k = 8))



def _candidate_tempdir_list():
    '''Generate a list of candidate temporary directories which
    _get_default_tempdir will try.'''
    dirlist = []
    for envname in ('TMPDIR', 'TEMP', 'TMP'):
        dirname = _os.getenv(envname)
        if not dirname:
            continue
        dirlist.append(dirname)
    if _os.name == 'nt':
        dirlist.extend([
            _os.path.expanduser('~\\AppData\\Local\\Temp'),
            _os.path.expandvars('%SYSTEMROOT%\\Temp'),
            'c:\\temp',
            'c:\\tmp',
            '\\temp',
            '\\tmp'])
    else:
        dirlist.extend([
            '/tmp',
            '/var/tmp',
            '/usr/tmp'])
    dirlist.append(_os.getcwd())
    return dirlist
# WARNING: Decompyle incomplete


def _get_default_tempdir():
    '''Calculate the default directory to use for temporary files.
    This routine should be called exactly once.

    We determine whether or not a candidate temp dir is usable by
    trying to create and write to a file in that directory.  If this
    is successful, the test file is deleted.  To prevent denial of
    service, the name of the test file must be randomized.'''
    namer = _RandomNameSequence()
    dirlist = _candidate_tempdir_list()
    for dir in dirlist:
        if dir != _os.curdir:
            dir = _os.path.abspath(dir)
        for seq in range(100):
            name = next(namer)
            filename = _os.path.join(dir, name)
            fd = _os.open(filename, _bin_openflags, 384)
            _os.write(fd, b'blat')
            _os.close(fd)
            _os.unlink(filename)
            
            
            return dirlist, range(100), dir
    raise FileNotFoundError(_errno.ENOENT, 'No usable temporary directory found in %s' % dirlist)
# WARNING: Decompyle incomplete

_name_sequence = None

def _get_candidate_names():
    '''Common setup sequence for all user-callable interfaces.'''
    pass
# WARNING: Decompyle incomplete


def _mkstemp_inner(dir, pre, suf, flags, output_type):
    '''Code common to mkstemp, TemporaryFile, and NamedTemporaryFile.'''
    dir = _os.path.abspath(dir)
    names = _get_candidate_names()
    if output_type is bytes:
        names = map(_os.fsencode, names)
    for seq in range(TMP_MAX):
        name = next(names)
        file = _os.path.join(dir, pre + name + suf)
        _sys.audit('tempfile.mkstemp', file)
        fd = _os.open(file, flags, 384)
        
        return range(TMP_MAX), (fd, file)
    raise FileExistsError(_errno.EEXIST, 'No usable temporary file name found')
# WARNING: Decompyle incomplete


def gettempprefix():
    '''The default prefix for temporary directories as string.'''
    return _os.fsdecode(template)


def gettempprefixb():
    '''The default prefix for temporary directories as bytes.'''
    return _os.fsencode(template)

tempdir = None

def _gettempdir():
    '''Private accessor for tempfile.tempdir.'''
    pass
# WARNING: Decompyle incomplete


def gettempdir():
    '''Returns tempfile.tempdir as str.'''
    return _os.fsdecode(_gettempdir())


def gettempdirb():
    '''Returns tempfile.tempdir as bytes.'''
    return _os.fsencode(_gettempdir())


def mkstemp(suffix, prefix, dir, text = (None, None, None, False)):
    """User-callable function to create and return a unique temporary
    file.  The return value is a pair (fd, name) where fd is the
    file descriptor returned by os.open, and name is the filename.

    If 'suffix' is not None, the file name will end with that suffix,
    otherwise there will be no suffix.

    If 'prefix' is not None, the file name will begin with that prefix,
    otherwise a default prefix is used.

    If 'dir' is not None, the file will be created in that directory,
    otherwise a default directory is used.

    If 'text' is specified and true, the file is opened in text
    mode.  Else (the default) the file is opened in binary mode.

    If any of 'suffix', 'prefix' and 'dir' are not None, they must be the
    same type.  If they are bytes, the returned name will be bytes; str
    otherwise.

    The file is readable and writable only by the creating user ID.
    If the operating system uses permission bits to indicate whether a
    file is executable, the file is executable by no one. The file
    descriptor is not inherited by children of this process.

    Caller is responsible for deleting the file when done with it.
    """
    (prefix, suffix, dir, output_type) = _sanitize_params(prefix, suffix, dir)
    if text:
        flags = _text_openflags
    else:
        flags = _bin_openflags
    return _mkstemp_inner(dir, prefix, suffix, flags, output_type)


def mkdtemp(suffix, prefix, dir = (None, None, None)):
    """User-callable function to create and return a unique temporary
    directory.  The return value is the pathname of the directory.

    Arguments are as for mkstemp, except that the 'text' argument is
    not accepted.

    The directory is readable, writable, and searchable only by the
    creating user.

    Caller is responsible for deleting the directory when done with it.
    """
    (prefix, suffix, dir, output_type) = _sanitize_params(prefix, suffix, dir)
    names = _get_candidate_names()
    if output_type is bytes:
        names = map(_os.fsencode, names)
    for seq in range(TMP_MAX):
        name = next(names)
        file = _os.path.join(dir, prefix + name + suffix)
        _sys.audit('tempfile.mkdtemp', file)
        _os.mkdir(file, 448)
        
        return range(TMP_MAX), _os.path.abspath(file)
    raise FileExistsError(_errno.EEXIST, 'No usable temporary directory name found')
# WARNING: Decompyle incomplete


def mktemp(suffix, prefix, dir = ('', template, None)):
    """User-callable function to return a unique temporary file name.  The
    file is not created.

    Arguments are similar to mkstemp, except that the 'text' argument is
    not accepted, and suffix=None, prefix=None and bytes file names are not
    supported.

    THIS FUNCTION IS UNSAFE AND SHOULD NOT BE USED.  The file name may
    refer to a file that did not exist at some point, but by the time
    you get around to creating it, someone else may have beaten you to
    the punch.
    """
    pass
# WARNING: Decompyle incomplete


class _TemporaryFileCloser:
    """A separate object allowing proper closing of a temporary file's
    underlying file object, without adding a __del__ method to the
    temporary file."""
    cleanup_called = False
    close_called = False
    
    def __init__(self, file, name, delete, delete_on_close = (True, True)):
        self.file = file
        self.name = name
        self.delete = delete
        self.delete_on_close = delete_on_close

    
    def cleanup(self, windows, unlink = (_os.name == 'nt', _os.unlink)):
        if not self.cleanup_called:
            self.cleanup_called = True
            if not self.close_called:
                self.close_called = True
                self.file.close()
            if self.delete:
                if not windows or self.delete_on_close:
                    unlink(self.name)
                    return None
                return None
            return None
        return None
    # WARNING: Decompyle incomplete

    
    def close(self):
        if not self.close_called:
            self.close_called = True
            self.file.close()
            if self.delete:
                if self.delete_on_close:
                    self.cleanup()
                    return None
                return None
            return None
        return None
    # WARNING: Decompyle incomplete

    
    def __del__(self):
        self.cleanup()



class _TemporaryFileWrapper:
    '''Temporary file wrapper

    This class provides a wrapper around files opened for
    temporary use.  In particular, it seeks to automatically
    remove the file when it is no longer needed.
    '''
    
    def __init__(self, file, name, delete, delete_on_close = (True, True)):
        self.file = file
        self.name = name
        self._closer = _TemporaryFileCloser(file, name, delete, delete_on_close)

    
    def __getattr__(self, name):
        pass
    # WARNING: Decompyle incomplete

    
    def __enter__(self):
        self.file.__enter__()
        return self

    
    def __exit__(self, exc, value, tb):
        result = self.file.__exit__(exc, value, tb)
        self._closer.cleanup()
        return result

    
    def close(self):
        '''
        Close the temporary file, possibly deleting it.
        '''
        self._closer.close()

    
    def __iter__(self):
        pass
    # WARNING: Decompyle incomplete



def NamedTemporaryFile(mode, buffering, encoding, newline, suffix, prefix = None, dir = ('w+b', -1, None, None, None, None, None, True), delete = {
    'errors': None,
    'delete_on_close': True }, *, errors, delete_on_close):
    '''Create and return a temporary file.
    Arguments:
    \'prefix\', \'suffix\', \'dir\' -- as for mkstemp.
    \'mode\' -- the mode argument to io.open (default "w+b").
    \'buffering\' -- the buffer size argument to io.open (default -1).
    \'encoding\' -- the encoding argument to io.open (default None)
    \'newline\' -- the newline argument to io.open (default None)
    \'delete\' -- whether the file is automatically deleted (default True).
    \'delete_on_close\' -- if \'delete\', whether the file is deleted on close
       (default True) or otherwise either on context manager exit
       (if context manager was used) or on object finalization. .
    \'errors\' -- the errors argument to io.open (default None)
    The file is created as mkstemp() would do it.

    Returns an object with a file-like interface; the name of the file
    is accessible as its \'name\' attribute.  The file will be automatically
    deleted when it is closed unless the \'delete\' argument is set to False.

    On POSIX, NamedTemporaryFiles cannot be automatically deleted if
    the creating process is terminated abruptly with a SIGKILL signal.
    Windows can delete the file even in this case.
    '''
    pass
# WARNING: Decompyle incomplete


class SpooledTemporaryFile(_io.IOBase):
    '''Temporary file wrapper, specialized to switch from BytesIO
    or StringIO to a real file when it exceeds a certain size or
    when a fileno is needed.
    '''
    _rolled = False
    
    def __init__(self, max_size, mode, buffering, encoding, newline, suffix = None, prefix = (0, 'w+b', -1, None, None, None, None, None), dir = {
        'errors': None }, *, errors):
        if 'b' in mode:
            self._file = _io.BytesIO()
        else:
            encoding = _io.text_encoding(encoding)
            self._file = _io.TextIOWrapper(_io.BytesIO(), encoding = encoding, errors = errors, newline = newline)
        self._max_size = max_size
        self._rolled = False
        self._TemporaryFileArgs = {
            'mode': mode,
            'buffering': buffering,
            'suffix': suffix,
            'prefix': prefix,
            'encoding': encoding,
            'newline': newline,
            'dir': dir,
            'errors': errors }

    __class_getitem__ = classmethod(_types.GenericAlias)
    
    def _check(self, file):
        if self._rolled:
            return None
        max_size = self._max_size
        if max_size:
            if file.tell() > max_size:
                self.rollover()
                return None
            return None

    
    def rollover(self):
        if self._rolled:
            return None
        file = self._file
    # WARNING: Decompyle incomplete

    
    def __enter__(self):
        if self._file.closed:
            raise ValueError('Cannot enter context with closed file')
        return self

    
    def __exit__(self, exc, value, tb):
        self._file.close()

    
    def __iter__(self):
        return self._file.__iter__()

    
    def __del__(self):
        if not self.closed:
            _warnings.warn('Unclosed file {!r}'.format(self), ResourceWarning, stacklevel = 2, source = self)
            self.close()
            return None

    
    def close(self):
        self._file.close()

    closed = (lambda self: self._file.closed)()
    encoding = (lambda self: self._file.encoding)()
    errors = (lambda self: self._file.errors)()
    
    def fileno(self):
        self.rollover()
        return self._file.fileno()

    
    def flush(self):
        self._file.flush()

    
    def isatty(self):
        return self._file.isatty()

    mode = (lambda self: self._file.mode# WARNING: Decompyle incomplete
)()
    name = (lambda self: self._file.name# WARNING: Decompyle incomplete
)()
    newlines = (lambda self: self._file.newlines)()
    
    def readable(self):
        return self._file.readable()

    
    def read(self, *args):
        pass
    # WARNING: Decompyle incomplete

    
    def read1(self, *args):
        pass
    # WARNING: Decompyle incomplete

    
    def readinto(self, b):
        return self._file.readinto(b)

    
    def readinto1(self, b):
        return self._file.readinto1(b)

    
    def readline(self, *args):
        pass
    # WARNING: Decompyle incomplete

    
    def readlines(self, *args):
        pass
    # WARNING: Decompyle incomplete

    
    def seekable(self):
        return self._file.seekable()

    
    def seek(self, *args):
        pass
    # WARNING: Decompyle incomplete

    
    def tell(self):
        return self._file.tell()

    
    def truncate(self, size = (None,)):
        pass
    # WARNING: Decompyle incomplete

    
    def writable(self):
        return self._file.writable()

    
    def write(self, s):
        file = self._file
        rv = file.write(s)
        self._check(file)
        return rv

    
    def writelines(self, iterable):
        file = self._file
        rv = file.writelines(iterable)
        self._check(file)
        return rv

    
    def detach(self):
        return self._file.detach()



class TemporaryDirectory:
    '''Create and return a temporary directory.  This has the same
    behavior as mkdtemp but can be used as a context manager.  For
    example:

        with TemporaryDirectory() as tmpdir:
            ...

    Upon exiting the context, the directory and everything contained
    in it are removed (unless delete=False is passed or an exception
    is raised during cleanup and ignore_cleanup_errors is not True).

    Optional Arguments:
        suffix - A str suffix for the directory name.  (see mkdtemp)
        prefix - A str prefix for the directory name.  (see mkdtemp)
        dir - A directory to create this temp dir in.  (see mkdtemp)
        ignore_cleanup_errors - False; ignore exceptions during cleanup?
        delete - True; whether the directory is automatically deleted.
    '''
    
    def __init__(self, suffix, prefix = None, dir = (None, None, None, False), ignore_cleanup_errors = {
        'delete': True }, *, delete):
        self.name = mkdtemp(suffix, prefix, dir)
        self._ignore_cleanup_errors = ignore_cleanup_errors
        self._delete = delete
        self._finalizer = _weakref.finalize(self, self._cleanup, self.name, warn_message = 'Implicitly cleaning up {!r}'.format(self), ignore_errors = self._ignore_cleanup_errors, delete = self._delete)

    _rmtree = (lambda cls, name, ignore_errors = (False,): pass# WARNING: Decompyle incomplete
)()
    _cleanup = (lambda cls, name, warn_message, ignore_errors, delete = (False, True): if delete:
cls._rmtree(name, ignore_errors = ignore_errors)_warnings.warn(warn_message, ResourceWarning)None)()
    
    def __repr__(self):
        return '<{} {!r}>'.format(self.__class__.__name__, self.name)

    
    def __enter__(self):
        return self.name

    
    def __exit__(self, exc, value, tb):
        if self._delete:
            self.cleanup()
            return None

    
    def cleanup(self):
        if self._finalizer.detach() or _os.path.exists(self.name):
            self._rmtree(self.name, ignore_errors = self._ignore_cleanup_errors)
            return None

    __class_getitem__ = classmethod(_types.GenericAlias)

