# Source Generated with Decompyle++
# File: pickle.pyc (Python 3.12)

__doc__ = 'Create portable serialized representations of Python objects.\n\nSee module copyreg for a mechanism for registering custom picklers.\nSee module pickletools source for extensive comments.\n\nClasses:\n\n    Pickler\n    Unpickler\n\nFunctions:\n\n    dump(object, file)\n    dumps(object) -> string\n    load(file) -> object\n    loads(bytes) -> object\n\nMisc variables:\n\n    __version__\n    format_version\n    compatible_formats\n\n'
from types import FunctionType
from copyreg import dispatch_table
from copyreg import _extension_registry, _inverted_registry, _extension_cache
from itertools import islice
from functools import partial
import sys
from sys import maxsize
from struct import pack, unpack
import re
import io
import codecs
import _compat_pickle
__all__ = [
    'PickleError',
    'PicklingError',
    'UnpicklingError',
    'Pickler',
    'Unpickler',
    'dump',
    'dumps',
    'load',
    'loads']
from _pickle import PickleBuffer
__all__.append('PickleBuffer')
_HAVE_PICKLE_BUFFER = True
bytes_types = (bytes, bytearray)
format_version = '4.0'
compatible_formats = [
    '1.0',
    '1.1',
    '1.2',
    '1.3',
    '2.0',
    '3.0',
    '4.0',
    '5.0']
HIGHEST_PROTOCOL = 5
DEFAULT_PROTOCOL = 4

class PickleError(Exception):
    '''A common base class for the other pickling exceptions.'''
    pass


class PicklingError(PickleError):
    '''This exception is raised when an unpicklable object is passed to the
    dump() method.

    '''
    pass


class UnpicklingError(PickleError):
    '''This exception is raised when there is a problem unpickling an object,
    such as a security violation.

    Note that other exceptions may also be raised during unpickling, including
    (but not necessarily limited to) AttributeError, EOFError, ImportError,
    and IndexError.

    '''
    pass


class _Stop(Exception):
    
    def __init__(self, value):
        self.value = value


MARK = b'('
STOP = b'.'
POP = b'0'
POP_MARK = b'1'
DUP = b'2'
FLOAT = b'F'
INT = b'I'
BININT = b'J'
BININT1 = b'K'
LONG = b'L'
BININT2 = b'M'
NONE = b'N'
PERSID = b'P'
BINPERSID = b'Q'
REDUCE = b'R'
STRING = b'S'
BINSTRING = b'T'
SHORT_BINSTRING = b'U'
UNICODE = b'V'
BINUNICODE = b'X'
APPEND = b'a'
BUILD = b'b'
GLOBAL = b'c'
DICT = b'd'
EMPTY_DICT = b'}'
APPENDS = b'e'
GET = b'g'
BINGET = b'h'
INST = b'i'
LONG_BINGET = b'j'
LIST = b'l'
EMPTY_LIST = b']'
OBJ = b'o'
PUT = b'p'
BINPUT = b'q'
LONG_BINPUT = b'r'
SETITEM = b's'
TUPLE = b't'
EMPTY_TUPLE = b')'
SETITEMS = b'u'
BINFLOAT = b'G'
TRUE = b'I01\n'
FALSE = b'I00\n'
PROTO = b'\x80'
NEWOBJ = b'\x81'
EXT1 = b'\x82'
EXT2 = b'\x83'
EXT4 = b'\x84'
TUPLE1 = b'\x85'
TUPLE2 = b'\x86'
TUPLE3 = b'\x87'
NEWTRUE = b'\x88'
NEWFALSE = b'\x89'
LONG1 = b'\x8a'
LONG4 = b'\x8b'
_tuplesize2code = [
    EMPTY_TUPLE,
    TUPLE1,
    TUPLE2,
    TUPLE3]
BINBYTES = b'B'
SHORT_BINBYTES = b'C'
SHORT_BINUNICODE = b'\x8c'
BINUNICODE8 = b'\x8d'
BINBYTES8 = b'\x8e'
EMPTY_SET = b'\x8f'
ADDITEMS = b'\x90'
FROZENSET = b'\x91'
NEWOBJ_EX = b'\x92'
STACK_GLOBAL = b'\x93'
MEMOIZE = b'\x94'
FRAME = b'\x95'
BYTEARRAY8 = b'\x96'
NEXT_BUFFER = b'\x97'
READONLY_BUFFER = b'\x98'
# WARNING: Decompyle incomplete
