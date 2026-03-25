# Source Generated with Decompyle++
# File: uuid.pyc (Python 3.12)

__doc__ = "UUID objects (universally unique identifiers) according to RFC 4122.\n\nThis module provides immutable UUID objects (class UUID) and the functions\nuuid1(), uuid3(), uuid4(), uuid5() for generating version 1, 3, 4, and 5\nUUIDs as specified in RFC 4122.\n\nIf all you want is a unique ID, you should probably call uuid1() or uuid4().\nNote that uuid1() may compromise privacy since it creates a UUID containing\nthe computer's network address.  uuid4() creates a random UUID.\n\nTypical usage:\n\n    >>> import uuid\n\n    # make a UUID based on the host ID and current time\n    >>> uuid.uuid1()    # doctest: +SKIP\n    UUID('a8098c1a-f86e-11da-bd1a-00112444be1e')\n\n    # make a UUID using an MD5 hash of a namespace UUID and a name\n    >>> uuid.uuid3(uuid.NAMESPACE_DNS, 'python.org')\n    UUID('6fa459ea-ee8a-3ca4-894e-db77e160355e')\n\n    # make a random UUID\n    >>> uuid.uuid4()    # doctest: +SKIP\n    UUID('16fd2706-8baf-433b-82eb-8c7fada847da')\n\n    # make a UUID using a SHA-1 hash of a namespace UUID and a name\n    >>> uuid.uuid5(uuid.NAMESPACE_DNS, 'python.org')\n    UUID('886313e1-3b8a-5372-9b90-0c9aee199e5d')\n\n    # make a UUID from a string of hex digits (braces and hyphens ignored)\n    >>> x = uuid.UUID('{00010203-0405-0607-0809-0a0b0c0d0e0f}')\n\n    # convert a UUID to a string of hex digits in standard form\n    >>> str(x)\n    '00010203-0405-0607-0809-0a0b0c0d0e0f'\n\n    # get the raw 16 bytes of the UUID\n    >>> x.bytes\n    b'\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\t\\n\\x0b\\x0c\\r\\x0e\\x0f'\n\n    # make a UUID from a 16-byte string\n    >>> uuid.UUID(bytes=x.bytes)\n    UUID('00010203-0405-0607-0809-0a0b0c0d0e0f')\n"
import os
import sys
from enum import Enum, _simple_enum
__author__ = 'Ka-Ping Yee <ping@zesty.ca>'
if sys.platform in ('win32', 'darwin', 'emscripten', 'wasi'):
    _AIX = False
    _LINUX = False
else:
    import platform
    _platform_system = platform.system()
    _AIX = _platform_system == 'AIX'
    _LINUX = _platform_system == 'Linux'
_MAC_DELIM = b':'
_MAC_OMITS_LEADING_ZEROES = False
if _AIX:
    _MAC_DELIM = b'.'
    _MAC_OMITS_LEADING_ZEROES = True
(RESERVED_NCS, RFC_4122, RESERVED_MICROSOFT, RESERVED_FUTURE) = [
    'reserved for NCS compatibility',
    'specified in RFC 4122',
    'reserved for Microsoft compatibility',
    'reserved for future definition']
int_ = int
bytes_ = bytes
SafeUUID = <NODE:12>()

class UUID:
    """Instances of the UUID class represent UUIDs as specified in RFC 4122.
    UUID objects are immutable, hashable, and usable as dictionary keys.
    Converting a UUID to a string with str() yields something in the form
    '12345678-1234-1234-1234-123456789abc'.  The UUID constructor accepts
    five possible forms: a similar string of hexadecimal digits, or a tuple
    of six integer fields (with 32-bit, 16-bit, 16-bit, 8-bit, 8-bit, and
    48-bit values respectively) as an argument named 'fields', or a string
    of 16 bytes (with all the integer fields in big-endian order) as an
    argument named 'bytes', or a string of 16 bytes (with the first three
    fields in little-endian order) as an argument named 'bytes_le', or a
    single 128-bit integer as an argument named 'int'.

    UUIDs have these read-only attributes:

        bytes       the UUID as a 16-byte string (containing the six
                    integer fields in big-endian byte order)

        bytes_le    the UUID as a 16-byte string (with time_low, time_mid,
                    and time_hi_version in little-endian byte order)

        fields      a tuple of the six integer fields of the UUID,
                    which are also available as six individual attributes
                    and two derived attributes:

            time_low                the first 32 bits of the UUID
            time_mid                the next 16 bits of the UUID
            time_hi_version         the next 16 bits of the UUID
            clock_seq_hi_variant    the next 8 bits of the UUID
            clock_seq_low           the next 8 bits of the UUID
            node                    the last 48 bits of the UUID

            time                    the 60-bit timestamp
            clock_seq               the 14-bit sequence number

        hex         the UUID as a 32-character hexadecimal string

        int         the UUID as a 128-bit integer

        urn         the UUID as a URN as specified in RFC 4122

        variant     the UUID variant (one of the constants RESERVED_NCS,
                    RFC_4122, RESERVED_MICROSOFT, or RESERVED_FUTURE)

        version     the UUID version number (1 through 5, meaningful only
                    when the variant is RFC_4122)

        is_safe     An enum indicating whether the UUID has been generated in
                    a way that is safe for multiprocessing applications, via
                    uuid_generate_time_safe(3).
    """
    __slots__ = ('int', 'is_safe', '__weakref__')
    
    def __init__(self, hex, bytes, bytes_le, fields = None, int = (None, None, None, None, None, None), version = {
        'is_safe': SafeUUID.unknown }, *, is_safe):
        """Create a UUID from either a string of 32 hexadecimal digits,
        a string of 16 bytes as the 'bytes' argument, a string of 16 bytes
        in little-endian order as the 'bytes_le' argument, a tuple of six
        integers (32-bit time_low, 16-bit time_mid, 16-bit time_hi_version,
        8-bit clock_seq_hi_variant, 8-bit clock_seq_low, 48-bit node) as
        the 'fields' argument, or a single 128-bit integer as the 'int'
        argument.  When a string of hex digits is given, curly braces,
        hyphens, and a URN prefix are all optional.  For example, these
        expressions all yield the same UUID:

        UUID('{12345678-1234-5678-1234-567812345678}')
        UUID('12345678123456781234567812345678')
        UUID('urn:uuid:12345678-1234-5678-1234-567812345678')
        UUID(bytes='\\x12\\x34\\x56\\x78'*4)
        UUID(bytes_le='\\x78\\x56\\x34\\x12\\x34\\x12\\x78\\x56' +
                      '\\x12\\x34\\x56\\x78\\x12\\x34\\x56\\x78')
        UUID(fields=(0x12345678, 0x1234, 0x5678, 0x12, 0x34, 0x567812345678))
        UUID(int=0x12345678123456781234567812345678)

        Exactly one of 'hex', 'bytes', 'bytes_le', 'fields', or 'int' must
        be given.  The 'version' argument is optional; if given, the resulting
        UUID will have its variant and version set according to RFC 4122,
        overriding the given 'hex', 'bytes', 'bytes_le', 'fields', or 'int'.

        is_safe is an enum exposed as an attribute on the instance.  It
        indicates whether the UUID has been generated in a way that is safe
        for multiprocessing applications, via uuid_generate_time_safe(3).
        """
        if [
            hex,
            bytes,
            bytes_le,
            fields,
            int].count(None) != 4:
            raise TypeError('one of the hex, bytes, bytes_le, fields, or int arguments must be given')
    # WARNING: Decompyle incomplete

    
    def __getstate__(self):
        d = {
            'int': self.int }
        if self.is_safe != SafeUUID.unknown:
            d['is_safe'] = self.is_safe.value
        return d

    
    def __setstate__(self, state):
        object.__setattr__(self, 'int', state['int'])
        if 'is_safe' in state:
            object.__setattr__(self, 'is_safe', SafeUUID(state['is_safe']))
            return None
        None(None, None, SafeUUID.unknown)

    
    def __eq__(self, other):
        if isinstance(other, UUID):
            return self.int == other.int

    
    def __lt__(self, other):
        if isinstance(other, UUID):
            return self.int < other.int

    
    def __gt__(self, other):
        if isinstance(other, UUID):
            return self.int > other.int

    
    def __le__(self, other):
        if isinstance(other, UUID):
            return self.int <= other.int

    
    def __ge__(self, other):
        if isinstance(other, UUID):
            return self.int >= other.int

    
    def __hash__(self):
        return hash(self.int)

    
    def __int__(self):
        return self.int

    
    def __repr__(self):
        return f'''{self.__class__.__name__!s}({str(self)!r})'''

    
    def __setattr__(self, name, value):
        raise TypeError('UUID objects are immutable')

    
    def __str__(self):
        hex = '%032x' % self.int
        return f'''{hex[:8]!s}-{hex[8:12]!s}-{hex[12:16]!s}-{hex[16:20]!s}-{hex[20:]!s}'''

    bytes = (lambda self: self.int.to_bytes(16))()
    bytes_le = (lambda self: bytes = self.bytesbytes[3::-1] + bytes[5:3:-1] + bytes[7:5:-1] + bytes[8:])()
    fields = (lambda self: (self.time_low, self.time_mid, self.time_hi_version, self.clock_seq_hi_variant, self.clock_seq_low, self.node))()
    time_low = (lambda self: self.int >> 96)()
    time_mid = (lambda self: self.int >> 80 & 65535)()
    time_hi_version = (lambda self: self.int >> 64 & 65535)()
    clock_seq_hi_variant = (lambda self: self.int >> 56 & 255)()
    clock_seq_low = (lambda self: self.int >> 48 & 255)()
    time = (lambda self: (self.time_hi_version & 4095) << 48 | self.time_mid << 32 | self.time_low)()
    clock_seq = (lambda self: (self.clock_seq_hi_variant & 63) << 8 | self.clock_seq_low)()
    node = (lambda self: self.int & 0xFFFFFFFFFFFF)()
    hex = (lambda self: '%032x' % self.int)()
    urn = (lambda self: 'urn:uuid:' + str(self))()
    variant = (lambda self: if not self.int & 0x8000000000000000:
RESERVED_NCSif not None.int & 0x4000000000000000:
RFC_4122if not None.int & 0x2000000000000000:
RESERVED_MICROSOFT)()
    version = (lambda self: if self.variant == RFC_4122:
int(self.int >> 76 & 15))()


def _get_command_stdout(command, *args):
    import io
    import os
    import shutil
    import subprocess
    path_dirs = os.environ.get('PATH', os.defpath).split(os.pathsep)
    path_dirs.extend([
        '/sbin',
        '/usr/sbin'])
    executable = shutil.which(command, path = os.pathsep.join(path_dirs))
# WARNING: Decompyle incomplete


def _is_universal(mac):
    return not (mac & 0x20000000000)


def _find_mac_near_keyword(command, args, keywords, get_word_index):
    """Searches a command's output for a MAC address near a keyword.

    Each line of words in the output is case-insensitively searched for
    any of the given keywords.  Upon a match, get_word_index is invoked
    to pick a word from the line, given the index of the match.  For
    example, lambda i: 0 would get the first word on the line, while
    lambda i: i - 1 would get the word preceding the keyword.
    """
    stdout = _get_command_stdout(command, args)
# WARNING: Decompyle incomplete


def _parse_mac(word):
    parts = word.split(_MAC_DELIM)
    if len(parts) != 6:
        return None
    if _MAC_OMITS_LEADING_ZEROES:
        if not (lambda .0: pass# WARNING: Decompyle incomplete
)(parts()):
            return None
        hexstr = (lambda .0: pass# WARNING: Decompyle incomplete
)(parts())
    elif not (lambda .0: pass# WARNING: Decompyle incomplete
)(parts()):
        return None
    hexstr = b''.join(parts)
    return int(hexstr, 16)
# WARNING: Decompyle incomplete


def _find_mac_under_heading(command, args, heading):
    """Looks for a MAC address under a heading in a command's output.

    The first line of words in the output is searched for the given
    heading. Words at the same word index as the heading in subsequent
    lines are then examined to see if they look like MAC addresses.
    """
    stdout = _get_command_stdout(command, args)
# WARNING: Decompyle incomplete


def _ifconfig_getnode():
    '''Get the hardware address on Unix by running ifconfig.'''
    keywords = (b'hwaddr', b'ether', b'address:', b'lladdr')
    for args in ('', '-a', '-av'):
        mac = _find_mac_near_keyword('ifconfig', args, keywords, (lambda i: i + 1))
        if not mac:
            continue
        
        return ('', '-a', '-av'), mac


def _ip_getnode():
    '''Get the hardware address on Unix by running ip.'''
    mac = _find_mac_near_keyword('ip', 'link', [
        b'link/ether'], (lambda i: i + 1))
    if mac:
        return mac


def _arp_getnode():
    '''Get the hardware address on Unix by running arp.'''
    import os
    import socket
    if not hasattr(socket, 'gethostbyname'):
        return None
    ip_addr = socket.gethostbyname(socket.gethostname())
    mac = _find_mac_near_keyword('arp', '-an', [
        os.fsencode(ip_addr)], (lambda i: -1))
    if mac:
        return mac
    mac = None('arp', '-an', [
        os.fsencode(ip_addr)], (lambda i: i + 1))
    if mac:
        return mac
    mac = None('arp', '-an', [
        os.fsencode('(%s)' % ip_addr)], (lambda i: i + 2))
    if mac:
        return mac
# WARNING: Decompyle incomplete


def _lanscan_getnode():
    '''Get the hardware address on Unix by running lanscan.'''
    return _find_mac_near_keyword('lanscan', '-ai', [
        b'lan0'], (lambda i: 0))


def _netstat_getnode():
    '''Get the hardware address on Unix by running netstat.'''
    return _find_mac_under_heading('netstat', '-ian', b'Address')


def _ipconfig_getnode():
    '''[DEPRECATED] Get the hardware address on Windows.'''
    return _windll_getnode()


def _netbios_getnode():
    '''[DEPRECATED] Get the hardware address on Windows.'''
    return _windll_getnode()

import _uuid
_generate_time_safe = getattr(_uuid, 'generate_time_safe', None)
_UuidCreate = getattr(_uuid, 'UuidCreate', None)
_has_uuid_generate_time_safe = _uuid.has_uuid_generate_time_safe

def _load_system_functions():
    '''[DEPRECATED] Platform-specific functions loaded at import time'''
    pass


def _unix_getnode():
    '''Get the hardware address on Unix using the _uuid extension module.'''
    if _generate_time_safe:
        (uuid_time, _) = _generate_time_safe()
        return UUID(bytes = uuid_time).node


def _windll_getnode():
    '''Get the hardware address on Windows using the _uuid extension module.'''
    if _UuidCreate:
        uuid_bytes = _UuidCreate()
        return UUID(bytes_le = uuid_bytes).node


def _random_getnode():
    '''Get a random node ID.'''
    import random
    return random.getrandbits(48) | 0x10000000000

if _LINUX:
    _OS_GETTERS = [
        _ip_getnode,
        _ifconfig_getnode]
elif sys.platform == 'darwin':
    _OS_GETTERS = [
        _ifconfig_getnode,
        _arp_getnode,
        _netstat_getnode]
elif sys.platform == 'win32':
    _OS_GETTERS = []
elif _AIX:
    _OS_GETTERS = [
        _netstat_getnode]
else:
    _OS_GETTERS = [
        _ifconfig_getnode,
        _ip_getnode,
        _arp_getnode,
        _netstat_getnode,
        _lanscan_getnode]
if os.name == 'posix':
    _GETTERS = [
        _unix_getnode] + _OS_GETTERS
elif os.name == 'nt':
    _GETTERS = [
        _windll_getnode] + _OS_GETTERS
else:
    _GETTERS = _OS_GETTERS
_node = None

def getnode():
    '''Get the hardware address as a 48-bit positive integer.

    The first time this runs, it may launch a separate program, which could
    be quite slow.  If all attempts to obtain the hardware address fail, we
    choose a random 48-bit number with its eighth bit set to 1 as recommended
    in RFC 4122.
    '''
    pass
# WARNING: Decompyle incomplete

_last_timestamp = None

def uuid1(node, clock_seq = (None, None)):
    """Generate a UUID from a host ID, sequence number, and the current time.
    If 'node' is not given, getnode() is used to obtain the hardware
    address.  If 'clock_seq' is given, it is used as the sequence number;
    otherwise a random 14-bit sequence number is chosen."""
    pass
# WARNING: Decompyle incomplete


def uuid3(namespace, name):
    '''Generate a UUID from the MD5 hash of a namespace UUID and a name.'''
    if isinstance(name, str):
        name = bytes(name, 'utf-8')
    md5 = md5
    import hashlib
    digest = md5(namespace.bytes + name, usedforsecurity = False).digest()
    return UUID(bytes = digest[:16], version = 3)


def uuid4():
    '''Generate a random UUID.'''
    return UUID(bytes = os.urandom(16), version = 4)


def uuid5(namespace, name):
    '''Generate a UUID from the SHA-1 hash of a namespace UUID and a name.'''
    if isinstance(name, str):
        name = bytes(name, 'utf-8')
    sha1 = sha1
    import hashlib
    hash = sha1(namespace.bytes + name).digest()
    return UUID(bytes = hash[:16], version = 5)


def main():
    '''Run the uuid command line interface.'''
    uuid_funcs = {
        'uuid1': uuid1,
        'uuid3': uuid3,
        'uuid4': uuid4,
        'uuid5': uuid5 }
    uuid_namespace_funcs = ('uuid3', 'uuid5')
    namespaces = {
        '@dns': NAMESPACE_DNS,
        '@url': NAMESPACE_URL,
        '@oid': NAMESPACE_OID,
        '@x500': NAMESPACE_X500 }
    import argparse
    parser = argparse.ArgumentParser(description = 'Generates a uuid using the selected uuid function.')
    parser.add_argument('-u', '--uuid', choices = uuid_funcs.keys(), default = 'uuid4', help = 'The function to use to generate the uuid. By default uuid4 function is used.')
    parser.add_argument('-n', '--namespace', help = "The namespace is a UUID, or '@ns' where 'ns' is a well-known predefined UUID addressed by namespace name. Such as @dns, @url, @oid, and @x500. Only required for uuid3/uuid5 functions.")
    parser.add_argument('-N', '--name', help = 'The name used as part of generating the uuid. Only required for uuid3/uuid5 functions.')
    args = parser.parse_args()
    uuid_func = uuid_funcs[args.uuid]
    namespace = args.namespace
    name = args.name
    if args.uuid in uuid_namespace_funcs:
        if not namespace or name:
            parser.error(f'''Incorrect number of arguments. {args.uuid} requires a namespace and a name. Run \'python -m uuid -h\' for more information.''')
        namespace = namespaces[namespace] if namespace in namespaces else UUID(namespace)
        print(uuid_func(namespace, name))
        return None
    print(uuid_func())

NAMESPACE_DNS = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_URL = UUID('6ba7b811-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_OID = UUID('6ba7b812-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_X500 = UUID('6ba7b814-9dad-11d1-80b4-00c04fd430c8')
if __name__ == '__main__':
    main()
    return None
return None
# WARNING: Decompyle incomplete
