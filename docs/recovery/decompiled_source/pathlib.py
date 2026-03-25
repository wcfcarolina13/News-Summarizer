# Source Generated with Decompyle++
# File: pathlib.pyc (Python 3.12)

__doc__ = 'Object-oriented filesystem paths.\n\nThis module provides classes to represent abstract paths and concrete\npaths with operations that have semantics appropriate for different\noperating systems.\n'
import fnmatch
import functools
import io
import ntpath
import os
import posixpath
import re
import sys
import warnings
from _collections_abc import Sequence
from errno import ENOENT, ENOTDIR, EBADF, ELOOP
from stat import S_ISDIR, S_ISLNK, S_ISREG, S_ISSOCK, S_ISBLK, S_ISCHR, S_ISFIFO
from urllib.parse import quote_from_bytes as urlquote_from_bytes
__all__ = [
    'PurePath',
    'PurePosixPath',
    'PureWindowsPath',
    'Path',
    'PosixPath',
    'WindowsPath']
# WARNING: Decompyle incomplete
