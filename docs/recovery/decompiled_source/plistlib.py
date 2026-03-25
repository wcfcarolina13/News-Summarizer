# Source Generated with Decompyle++
# File: plistlib.pyc (Python 3.12)

'''plistlib.py -- a tool to generate and parse MacOSX .plist files.

The property list (.plist) file format is a simple XML pickle supporting
basic object types, like dictionaries, lists, numbers and strings.
Usually the top level object is a dictionary.

To write out a plist file, use the dump(value, file)
function. \'value\' is the top level object, \'file\' is
a (writable) file object.

To parse a plist from a file, use the load(file) function,
with a (readable) file object as the only argument. It
returns the top level object (again, usually a dictionary).

To work with plist data in bytes objects, you can use loads()
and dumps().

Values can be strings, integers, floats, booleans, tuples, lists,
dictionaries (but only with string keys), Data, bytes, bytearray, or
datetime.datetime objects.

Generate Plist example:

    import datetime
    import plistlib

    pl = dict(
        aString = "Doodah",
        aList = ["A", "B", 12, 32.1, [1, 2, 3]],
        aFloat = 0.1,
        anInt = 728,
        aDict = dict(
            anotherString = "<hello & hi there!>",
            aThirdString = "M\\xe4ssig, Ma\\xdf",
            aTrueValue = True,
            aFalseValue = False,
        ),
        someData = b"<binary gunk>",
        someMoreData = b"<lots of binary gunk>" * 10,
        aDate = datetime.datetime.now()
    )
    print(plistlib.dumps(pl).decode())

Parse Plist example:

    import plistlib

    plist = b\'\'\'<plist version="1.0">
    <dict>
        <key>foo</key>
        <string>bar</string>
    </dict>
    </plist>\'\'\'
    pl = plistlib.loads(plist)
    print(pl["foo"])
'''
__all__ = [
    'InvalidFileException',
    'FMT_XML',
    'FMT_BINARY',
    'load',
    'dump',
    'loads',
    'dumps',
    'UID']
import binascii
import codecs
import datetime
import enum
from io import BytesIO
import itertools
import os
import re
import struct
from xml.parsers.expat import ParserCreate
PlistFormat = enum.Enum('PlistFormat', 'FMT_XML FMT_BINARY', module = __name__)
globals().update(PlistFormat.__members__)

class UID:
    
    def __init__(self, data):
        if not isinstance(data, int):
            raise TypeError('data must be an int')
        if data >= 0x10000000000000000:
            raise ValueError('UIDs cannot be >= 2**64')
        if data < 0:
            raise ValueError('UIDs must be positive')
        self.data = data

    
    def __index__(self):
        return self.data

    
    def __repr__(self):
        return f'''{self.__class__.__name__!s}({repr(self.data)!s})'''

    
    def __reduce__(self):
        return (self.__class__, (self.data,))

    
    def __eq__(self, other):
        if not isinstance(other, UID):
            return NotImplemented
        return None.data == other.data

    
    def __hash__(self):
        return hash(self.data)


PLISTHEADER = b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
_controlCharPat = re.compile('[\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\x0b\\x0c\\x0e\\x0f\\x10\\x11\\x12\\x13\\x14\\x15\\x16\\x17\\x18\\x19\\x1a\\x1b\\x1c\\x1d\\x1e\\x1f]')

def _encode_base64(s, maxlinelength = (76,)):
    maxbinsize = (maxlinelength // 4) * 3
    pieces = []
    for i in range(0, len(s), maxbinsize):
        chunk = s[i:i + maxbinsize]
        pieces.append(binascii.b2a_base64(chunk))
    return b''.join(pieces)


def _decode_base64(s):
    if isinstance(s, str):
        return binascii.a2b_base64(s.encode('utf-8'))
    return None.a2b_base64(s)

_dateParser = re.compile('(?P<year>\\d\\d\\d\\d)(?:-(?P<month>\\d\\d)(?:-(?P<day>\\d\\d)(?:T(?P<hour>\\d\\d)(?::(?P<minute>\\d\\d)(?::(?P<second>\\d\\d))?)?)?)?)?Z', re.ASCII)

def _date_from_string(s):
    order = ('year', 'month', 'day', 'hour', 'minute', 'second')
    gd = _dateParser.match(s).groupdict()
    lst = []
# WARNING: Decompyle incomplete


def _date_to_string(d):
    return '%04d-%02d-%02dT%02d:%02d:%02dZ' % (d.year, d.month, d.day, d.hour, d.minute, d.second)


def _escape(text):
    m = _controlCharPat.search(text)
# WARNING: Decompyle incomplete


class _PlistParser:
    
    def __init__(self, dict_type):
        self.stack = []
        self.current_key = None
        self.root = None
        self._dict_type = dict_type

    
    def parse(self, fileobj):
        self.parser = ParserCreate()
        self.parser.StartElementHandler = self.handle_begin_element
        self.parser.EndElementHandler = self.handle_end_element
        self.parser.CharacterDataHandler = self.handle_data
        self.parser.EntityDeclHandler = self.handle_entity_decl
        self.parser.ParseFile(fileobj)
        return self.root

    
    def handle_entity_decl(self, entity_name, is_parameter_entity, value, base, system_id, public_id, notation_name):
        raise InvalidFileException('XML entity declarations are not supported in plist files')

    
    def handle_begin_element(self, element, attrs):
        self.data = []
        handler = getattr(self, 'begin_' + element, None)
    # WARNING: Decompyle incomplete

    
    def handle_end_element(self, element):
        handler = getattr(self, 'end_' + element, None)
    # WARNING: Decompyle incomplete

    
    def handle_data(self, data):
        self.data.append(data)

    
    def add_object(self, value):
        pass
    # WARNING: Decompyle incomplete

    
    def get_data(self):
        data = ''.join(self.data)
        self.data = []
        return data

    
    def begin_dict(self, attrs):
        d = self._dict_type()
        self.add_object(d)
        self.stack.append(d)

    
    def end_dict(self):
        if self.current_key:
            raise ValueError("missing value for key '%s' at line %d" % (self.current_key, self.parser.CurrentLineNumber))
        self.stack.pop()

    
    def end_key(self):
        if not self.current_key or isinstance(self.stack[-1], dict):
            raise ValueError('unexpected key at line %d' % self.parser.CurrentLineNumber)
        self.current_key = self.get_data()

    
    def begin_array(self, attrs):
        a = []
        self.add_object(a)
        self.stack.append(a)

    
    def end_array(self):
        self.stack.pop()

    
    def end_true(self):
        self.add_object(True)

    
    def end_false(self):
        self.add_object(False)

    
    def end_integer(self):
        raw = self.get_data()
        if raw.startswith('0x') or raw.startswith('0X'):
            self.add_object(int(raw, 16))
            return None
        self.add_object(int(raw))

    
    def end_real(self):
        self.add_object(float(self.get_data()))

    
    def end_string(self):
        self.add_object(self.get_data())

    
    def end_data(self):
        self.add_object(_decode_base64(self.get_data()))

    
    def end_date(self):
        self.add_object(_date_from_string(self.get_data()))



class _DumbXMLWriter:
    
    def __init__(self, file, indent_level, indent = (0, '\t')):
        self.file = file
        self.stack = []
        self._indent_level = indent_level
        self.indent = indent

    
    def begin_element(self, element):
        self.stack.append(element)
        self.writeln('<%s>' % element)

    
    def end_element(self, element):
        pass
    # WARNING: Decompyle incomplete

    
    def simple_element(self, element, value = (None,)):
        pass
    # WARNING: Decompyle incomplete

    
    def writeln(self, line):
        if line:
            if isinstance(line, str):
                line = line.encode('utf-8')
            self.file.write(self._indent_level * self.indent)
            self.file.write(line)
        self.file.write(b'\n')



class _PlistWriter(_DumbXMLWriter):
    
    def __init__(self, file, indent_level, indent, writeHeader, sort_keys, skipkeys = (0, b'\t', 1, True, False)):
        if writeHeader:
            file.write(PLISTHEADER)
        _DumbXMLWriter.__init__(self, file, indent_level, indent)
        self._sort_keys = sort_keys
        self._skipkeys = skipkeys

    
    def write(self, value):
        self.writeln('<plist version="1.0">')
        self.write_value(value)
        self.writeln('</plist>')

    
    def write_value(self, value):
        if isinstance(value, str):
            self.simple_element('string', value)
            return None
        if value is True:
            self.simple_element('true')
            return None
        if value is False:
            self.simple_element('false')
            return None
        if isinstance(value, int):
            if  <= -0x8000000000000000, value or -0x8000000000000000, value < 0x10000000000000000:
                pass
            else:
                raise OverflowError(value)
            self.simple_element('integer', '%d' % value)
            return None
            raise OverflowError(value)
        if isinstance(value, float):
            self.simple_element('real', repr(value))
            return None
        if isinstance(value, dict):
            self.write_dict(value)
            return None
        if isinstance(value, (bytes, bytearray)):
            self.write_bytes(value)
            return None
        if isinstance(value, datetime.datetime):
            self.simple_element('date', _date_to_string(value))
            return None
        if isinstance(value, (tuple, list)):
            self.write_array(value)
            return None
        raise TypeError('unsupported type: %s' % type(value))

    
    def write_bytes(self, data):
        self.begin_element('data')
        max(16, 76 - len(self.indent.replace(b'\t', b'        ') * self._indent_level)) = self, self._indent_level -= 1, ._indent_level
        for line in _encode_base64(data, maxlinelength).split(b'\n'):
            if not line:
                continue
            self.writeln(line)
        self.end_element('data')

    
    def write_dict(self, d):
        if d:
            self.begin_element('dict')
            if self._sort_keys:
                items = sorted(d.items())
            else:
                items = d.items()
            for key, value in items:
                if not isinstance(key, str):
                    if self._skipkeys:
                        continue
                    raise TypeError('keys must be strings')
                self.simple_element('key', key)
                self.write_value(value)
            self.end_element('dict')
            return None
        self.simple_element('dict')

    
    def write_array(self, array):
        if array:
            self.begin_element('array')
            for value in array:
                self.write_value(value)
            self.end_element('array')
            return None
        self.simple_element('array')



def _is_fmt_xml(header):
    prefixes = (b'<?xml', b'<plist')
    for pfx in prefixes:
        if not header.startswith(pfx):
            continue
        prefixes
        return True
    for bom, encoding in ((codecs.BOM_UTF8, 'utf-8'), (codecs.BOM_UTF16_BE, 'utf-16-be'), (codecs.BOM_UTF16_LE, 'utf-16-le')):
        if not header.startswith(bom):
            continue
        for start in prefixes:
            prefix = bom + start.decode('ascii').encode(encoding)
            if not header[:len(prefix)] == prefix:
                continue
            prefixes
            ((codecs.BOM_UTF8, 'utf-8'), (codecs.BOM_UTF16_BE, 'utf-16-be'), (codecs.BOM_UTF16_LE, 'utf-16-le'))
            return True
    return False


class InvalidFileException(ValueError):
    
    def __init__(self, message = ('Invalid file',)):
        ValueError.__init__(self, message)


_BINARY_FORMAT = {
    1: 'B',
    2: 'H',
    4: 'L',
    8: 'Q' }
_undefined = object()

class _BinaryPlistParser:
    '''
    Read or write a binary plist file, following the description of the binary
    format.  Raise InvalidFileException in case of error, otherwise return the
    root object.

    see also: http://opensource.apple.com/source/CF/CF-744.18/CFBinaryPList.c
    '''
    
    def __init__(self, dict_type):
        self._dict_type = dict_type

    
    def parse(self, fp):
        self._fp = fp
        self._fp.seek(-32, os.SEEK_END)
        trailer = self._fp.read(32)
        if len(trailer) != 32:
            raise InvalidFileException()
        (offset_size, self._ref_size, num_objects, top_object, offset_table_offset) = struct.unpack('>6xBBQQQ', trailer)
        self._fp.seek(offset_table_offset)
        self._object_offsets = self._read_ints(num_objects, offset_size)
        self._objects = [
            _undefined] * num_objects
        return self._read_object(top_object)
    # WARNING: Decompyle incomplete

    
    def _get_size(self, tokenL):
        ''' return the size of the next object.'''
        if tokenL == 15:
            m = self._fp.read(1)[0] & 3
            s = 1 << m
            f = '>' + _BINARY_FORMAT[s]
            return struct.unpack(f, self._fp.read(s))[0]

    
    def _read_ints(self, n, size):
        pass
    # WARNING: Decompyle incomplete

    
    def _read_refs(self, n):
        return self._read_ints(n, self._ref_size)

    
    def _read_object(self, ref):
        '''
        read the object by reference.

        May recursively read sub-objects (content of an array/dict/set)
        '''
        pass
    # WARNING: Decompyle incomplete



def _count_to_size(count):
    if count < 256:
        return 1
    if count < 65536:
        return 2
    if count < 0x100000000:
        return 4
    return 8

_scalars = (str, int, float, datetime.datetime, bytes)

class _BinaryPlistWriter(object):
    
    def __init__(self, fp, sort_keys, skipkeys):
        self._fp = fp
        self._sort_keys = sort_keys
        self._skipkeys = skipkeys

    
    def write(self, value):
        self._objlist = []
        self._objtable = { }
        self._objidtable = { }
        self._flatten(value)
        num_objects = len(self._objlist)
        self._object_offsets = [
            0] * num_objects
        self._ref_size = _count_to_size(num_objects)
        self._ref_format = _BINARY_FORMAT[self._ref_size]
        self._fp.write(b'bplist00')
        for obj in self._objlist:
            self._write_object(obj)
        top_object = self._getrefnum(value)
        offset_table_offset = self._fp.tell()
        offset_size = _count_to_size(offset_table_offset)
        offset_format = '>' + _BINARY_FORMAT[offset_size] * num_objects
    # WARNING: Decompyle incomplete

    
    def _flatten(self, value):
        if isinstance(value, _scalars) or (type(value), value) in self._objtable:
            return None
            if id(value) in self._objidtable:
                return None
        refnum = len(self._objlist)
        self._objlist.append(value)
        if isinstance(value, _scalars):
            self._objtable[(type(value), value)] = refnum
        else:
            self._objidtable[id(value)] = refnum
        if isinstance(value, dict):
            keys = []
            values = []
            items = value.items()
            if self._sort_keys:
                items = sorted(items)
            for k, v in items:
                if not isinstance(k, str):
                    if self._skipkeys:
                        continue
                    raise TypeError('keys must be strings')
                keys.append(k)
                values.append(v)
            for o in itertools.chain(keys, values):
                self._flatten(o)
            return None
        if isinstance(value, (list, tuple)):
            for o in value:
                self._flatten(o)
            return None

    
    def _getrefnum(self, value):
        if isinstance(value, _scalars):
            return self._objtable[(type(value), value)]
        return None._objidtable[id(value)]

    
    def _write_size(self, token, size):
        if size < 15:
            self._fp.write(struct.pack('>B', token | size))
            return None
        if size < 256:
            self._fp.write(struct.pack('>BBB', token | 15, 16, size))
            return None
        if size < 65536:
            self._fp.write(struct.pack('>BBH', token | 15, 17, size))
            return None
        if size < 0x100000000:
            self._fp.write(struct.pack('>BBL', token | 15, 18, size))
            return None
        self._fp.write(struct.pack('>BBQ', token | 15, 19, size))

    
    def _write_object(self, value):
        ref = self._getrefnum(value)
        self._object_offsets[ref] = self._fp.tell()
    # WARNING: Decompyle incomplete



def _is_fmt_binary(header):
    return header[:8] == b'bplist00'

_FORMATS = {
    FMT_BINARY: dict(detect = _is_fmt_binary, parser = _BinaryPlistParser, writer = _BinaryPlistWriter),
    FMT_XML: dict(detect = _is_fmt_xml, parser = _PlistParser, writer = _PlistWriter) }

def load(fp = None, *, fmt, dict_type):
    """Read a .plist file. 'fp' should be a readable and binary file object.
    Return the unpacked root object (which usually is a dictionary).
    """
    pass
# WARNING: Decompyle incomplete


def loads(value = None, *, fmt, dict_type):
    '''Read a .plist file from a bytes object.
    Return the unpacked root object (which usually is a dictionary).
    '''
    fp = BytesIO(value)
    return load(fp, fmt = fmt, dict_type = dict_type)


def dump(value = None, fp = {
    'fmt': FMT_XML,
    'sort_keys': True,
    'skipkeys': False }, *, fmt, sort_keys, skipkeys):
    """Write 'value' to a .plist file. 'fp' should be a writable,
    binary file object.
    """
    if fmt not in _FORMATS:
        raise ValueError(f'''Unsupported format: {fmt!r}''')
    writer = _FORMATS[fmt]['writer'](fp, sort_keys = sort_keys, skipkeys = skipkeys)
    writer.write(value)


def dumps(value = None, *, fmt, skipkeys, sort_keys):
    '''Return a bytes object with the contents for a .plist file.
    '''
    fp = BytesIO()
    dump(value, fp, fmt = fmt, skipkeys = skipkeys, sort_keys = sort_keys)
    return fp.getvalue()

