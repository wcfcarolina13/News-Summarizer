# Source Generated with Decompyle++
# File: glob.pyc (Python 3.12)

'''Filename globbing utility.'''
import contextlib
import os
import re
import fnmatch
import itertools
import stat
import sys
__all__ = [
    'glob',
    'iglob',
    'escape']

def glob(pathname = None, *, root_dir, dir_fd, recursive, include_hidden):
    """Return a list of paths matching a pathname pattern.

    The pattern may contain simple shell-style wildcards a la
    fnmatch. Unlike fnmatch, filenames starting with a
    dot are special cases that are not matched by '*' and '?'
    patterns by default.

    If `include_hidden` is true, the patterns '*', '?', '**'  will match hidden
    directories.

    If `recursive` is true, the pattern '**' will match any files and
    zero or more directories and subdirectories.
    """
    return list(iglob(pathname, root_dir = root_dir, dir_fd = dir_fd, recursive = recursive, include_hidden = include_hidden))


def iglob(pathname = None, *, root_dir, dir_fd, recursive, include_hidden):
    """Return an iterator which yields the paths matching a pathname pattern.

    The pattern may contain simple shell-style wildcards a la
    fnmatch. However, unlike fnmatch, filenames starting with a
    dot are special cases that are not matched by '*' and '?'
    patterns.

    If recursive is true, the pattern '**' will match any files and
    zero or more directories and subdirectories.
    """
    sys.audit('glob.glob', pathname, recursive)
    sys.audit('glob.glob/2', pathname, recursive, root_dir, dir_fd)
# WARNING: Decompyle incomplete


def _iglob(pathname, root_dir, dir_fd, recursive, dironly, include_hidden = (False,)):
    pass
# WARNING: Decompyle incomplete


def _glob1(dirname, pattern, dir_fd, dironly, include_hidden = (False,)):
    pass
# WARNING: Decompyle incomplete


def _glob0(dirname, basename, dir_fd, dironly, include_hidden = (False,)):
    if basename:
        if _lexists(_join(dirname, basename), dir_fd):
            return [
                basename]
        return None
    if None(dirname, dir_fd):
        return [
            basename]


def glob0(dirname, pattern):
    return _glob0(dirname, pattern, None, False)


def glob1(dirname, pattern):
    return _glob1(dirname, pattern, None, False)


def _glob2(dirname, pattern, dir_fd, dironly, include_hidden = (False,)):
    pass
# WARNING: Decompyle incomplete


def _iterdir(dirname, dir_fd, dironly):
    pass
# WARNING: Decompyle incomplete


def _listdir(dirname, dir_fd, dironly):
    pass
# WARNING: Decompyle incomplete


def _rlistdir(dirname, dir_fd, dironly, include_hidden = (False,)):
    pass
# WARNING: Decompyle incomplete


def _lexists(pathname, dir_fd):
    pass
# WARNING: Decompyle incomplete


def _isdir(pathname, dir_fd):
    pass
# WARNING: Decompyle incomplete


def _join(dirname, basename):
    if not dirname or basename:
        if not dirname:
            dirname
        return basename
    return None.path.join(dirname, basename)

magic_check = re.compile('([*?[])')
magic_check_bytes = re.compile(b'([*?[])')

def has_magic(s):
    if isinstance(s, bytes):
        match = magic_check_bytes.search(s)
        return match is not None
    match = None.search(s)
    return match is not None


def _ishidden(path):
    return path[0] in ('.', 46)


def _isrecursive(pattern):
    if isinstance(pattern, bytes):
        return pattern == b'**'
    return None == '**'


def escape(pathname):
    '''Escape all special characters.
    '''
    (drive, pathname) = os.path.splitdrive(pathname)
    if isinstance(pathname, bytes):
        pathname = magic_check_bytes.sub(b'[\\1]', pathname)
        return drive + pathname
    pathname = None.sub('[\\1]', pathname)
    return drive + pathname

_dir_open_flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
