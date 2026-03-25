# Source Generated with Decompyle++
# File: lzma.pyc (Python 3.12)

__doc__ = 'Interface to the liblzma compression library.\n\nThis module provides a class for reading and writing compressed files,\nclasses for incremental (de)compression, and convenience functions for\none-shot (de)compression.\n\nThese classes and functions support both the XZ and legacy LZMA\ncontainer formats, as well as raw compressed data streams.\n'
__all__ = [
    'CHECK_NONE',
    'CHECK_CRC32',
    'CHECK_CRC64',
    'CHECK_SHA256',
    'CHECK_ID_MAX',
    'CHECK_UNKNOWN',
    'FILTER_LZMA1',
    'FILTER_LZMA2',
    'FILTER_DELTA',
    'FILTER_X86',
    'FILTER_IA64',
    'FILTER_ARM',
    'FILTER_ARMTHUMB',
    'FILTER_POWERPC',
    'FILTER_SPARC',
    'FORMAT_AUTO',
    'FORMAT_XZ',
    'FORMAT_ALONE',
    'FORMAT_RAW',
    'MF_HC3',
    'MF_HC4',
    'MF_BT2',
    'MF_BT3',
    'MF_BT4',
    'MODE_FAST',
    'MODE_NORMAL',
    'PRESET_DEFAULT',
    'PRESET_EXTREME',
    'LZMACompressor',
    'LZMADecompressor',
    'LZMAFile',
    'LZMAError',
    'open',
    'compress',
    'decompress',
    'is_check_supported']
import builtins
import io
import os
# WARNING: Decompyle incomplete
