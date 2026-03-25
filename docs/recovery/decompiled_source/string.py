# Source Generated with Decompyle++
# File: string.pyc (Python 3.12)

'''A collection of string constants.

Public module variables:

whitespace -- a string containing all ASCII whitespace
ascii_lowercase -- a string containing all ASCII lowercase letters
ascii_uppercase -- a string containing all ASCII uppercase letters
ascii_letters -- a string containing all ASCII letters
digits -- a string containing all ASCII decimal digits
hexdigits -- a string containing all ASCII hexadecimal digits
octdigits -- a string containing all ASCII octal digits
punctuation -- a string containing all ASCII punctuation characters
printable -- a string containing all ASCII characters considered printable

'''
__all__ = [
    'ascii_letters',
    'ascii_lowercase',
    'ascii_uppercase',
    'capwords',
    'digits',
    'hexdigits',
    'octdigits',
    'printable',
    'punctuation',
    'whitespace',
    'Formatter',
    'Template']
import _string
whitespace = ' \t\n\r\x0b\x0c'
ascii_lowercase = 'abcdefghijklmnopqrstuvwxyz'
ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ascii_letters = ascii_lowercase + ascii_uppercase
digits = '0123456789'
hexdigits = digits + 'abcdef' + 'ABCDEF'
octdigits = '01234567'
punctuation = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
printable = digits + ascii_letters + punctuation + whitespace

def capwords(s, sep = (None,)):
    '''capwords(s [,sep]) -> string

    Split the argument into words using split, capitalize each
    word using capitalize, and join the capitalized words using
    join.  If the optional second argument sep is absent or None,
    runs of whitespace characters are replaced by a single space
    and leading and trailing whitespace are removed, otherwise
    sep is used to split and join the words.

    '''
    if not sep:
        sep
    return ' '.join(map(str.capitalize, s.split(sep)))

import re as _re
from collections import ChainMap as _ChainMap
_sentinel_dict = { }

class Template:
    pass
# WARNING: Decompyle incomplete

Template.__init_subclass__()

class Formatter:
    
    def format(self, format_string, *args, **kwargs):
        return self.vformat(format_string, args, kwargs)

    
    def vformat(self, format_string, args, kwargs):
        used_args = set()
        (result, _) = self._vformat(format_string, args, kwargs, used_args, 2)
        self.check_unused_args(used_args, args, kwargs)
        return result

    
    def _vformat(self, format_string, args, kwargs, used_args, recursion_depth, auto_arg_index = (0,)):
        if recursion_depth < 0:
            raise ValueError('Max string recursion exceeded')
        result = []
    # WARNING: Decompyle incomplete

    
    def get_value(self, key, args, kwargs):
        if isinstance(key, int):
            return args[key]
        return None[key]

    
    def check_unused_args(self, used_args, args, kwargs):
        pass

    
    def format_field(self, value, format_spec):
        return format(value, format_spec)

    
    def convert_field(self, value, conversion):
        pass
    # WARNING: Decompyle incomplete

    
    def parse(self, format_string):
        return _string.formatter_parser(format_string)

    
    def get_field(self, field_name, args, kwargs):
        (first, rest) = _string.formatter_field_name_split(field_name)
        obj = self.get_value(first, args, kwargs)
        for is_attr, i in rest:
            if is_attr:
                obj = getattr(obj, i)
                continue
            obj = obj[i]
        return (obj, first)


