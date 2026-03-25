# Source Generated with Decompyle++
# File: soundfile.pyc (Python 3.12)

__doc__ = 'python-soundfile is an audio library based on libsndfile, CFFI and NumPy.\n\nSound files can be read or written directly using the functions\n`read()` and `write()`.\nTo read a sound file in a block-wise fashion, use `blocks()`.\nAlternatively, sound files can be opened as `SoundFile` objects.\n\nFor further information, see https://python-soundfile.readthedocs.io/.\n\n'
__version__ = '0.13.1'
import os as _os
import sys as _sys
from os import SEEK_SET, SEEK_CUR, SEEK_END
from ctypes.util import find_library as _find_library
from _soundfile import ffi as _ffi
_unicode = unicode
_str_types = {
    'title': 1,
    'copyright': 2,
    'software': 3,
    'artist': 4,
    'comment': 5,
    'date': 6,
    'album': 7,
    'license': 8,
    'tracknumber': 9,
    'genre': 16 }
# WARNING: Decompyle incomplete
