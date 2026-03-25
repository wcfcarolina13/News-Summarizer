# Source Generated with Decompyle++
# File: ipaddress.pyc (Python 3.12)

'''A fast, lightweight IPv4/IPv6 manipulation library in Python.

This library is used to create/poke/manipulate IPv4 and IPv6 addresses
and networks.

'''
__version__ = '1.0'
import functools
IPV4LENGTH = 32
IPV6LENGTH = 128

class AddressValueError(ValueError):
    '''A Value Error related to the address.'''
    pass


class NetmaskValueError(ValueError):
    '''A Value Error related to the netmask.'''
    pass


def ip_address(address):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP address.  Either IPv4 or
          IPv6 addresses may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.

    Returns:
        An IPv4Address or IPv6Address object.

    Raises:
        ValueError: if the *address* passed isn't either a v4 or a v6
          address

    """
    return IPv4Address(address)
# WARNING: Decompyle incomplete


def ip_network(address, strict = (True,)):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP network.  Either IPv4 or
          IPv6 networks may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.

    Returns:
        An IPv4Network or IPv6Network object.

    Raises:
        ValueError: if the string passed isn't either a v4 or a v6
          address. Or if the network has host bits set.

    """
    return IPv4Network(address, strict)
# WARNING: Decompyle incomplete


def ip_interface(address):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP address.  Either IPv4 or
          IPv6 addresses may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.

    Returns:
        An IPv4Interface or IPv6Interface object.

    Raises:
        ValueError: if the string passed isn't either a v4 or a v6
          address.

    Notes:
        The IPv?Interface classes describe an Address on a particular
        Network, so they're basically a combination of both the Address
        and Network classes.

    """
    return IPv4Interface(address)
# WARNING: Decompyle incomplete


def v4_int_to_packed(address):
    '''Represent an address as 4 packed bytes in network (big-endian) order.

    Args:
        address: An integer representation of an IPv4 IP address.

    Returns:
        The integer address packed as 4 bytes in network (big-endian) order.

    Raises:
        ValueError: If the integer is negative or too large to be an
          IPv4 IP address.

    '''
    return address.to_bytes(4)
# WARNING: Decompyle incomplete


def v6_int_to_packed(address):
    '''Represent an address as 16 packed bytes in network (big-endian) order.

    Args:
        address: An integer representation of an IPv6 IP address.

    Returns:
        The integer address packed as 16 bytes in network (big-endian) order.

    '''
    return address.to_bytes(16)
# WARNING: Decompyle incomplete


def _split_optional_netmask(address):
    '''Helper to split the netmask and raise AddressValueError if needed'''
    addr = str(address).split('/')
    if len(addr) > 2:
        raise AddressValueError(f'''Only one \'/\' permitted in {address!r}''')
    return addr


def _find_address_range(addresses):
    '''Find a sequence of sorted deduplicated IPv#Address.

    Args:
        addresses: a list of IPv#Address objects.

    Yields:
        A tuple containing the first and last IP addresses in the sequence.

    '''
    pass
# WARNING: Decompyle incomplete


def _count_righthand_zero_bits(number, bits):
    '''Count the number of zero bits on the right hand side.

    Args:
        number: an integer.
        bits: maximum number of bits to count.

    Returns:
        The number of zero bits on the right hand side of the number.

    '''
    if number == 0:
        return bits
    return None(bits, (~number & number - 1).bit_length())


def summarize_address_range(first, last):
    """Summarize a network range given the first and last IP addresses.

    Example:
        >>> list(summarize_address_range(IPv4Address('192.0.2.0'),
        ...                              IPv4Address('192.0.2.130')))
        ...                                #doctest: +NORMALIZE_WHITESPACE
        [IPv4Network('192.0.2.0/25'), IPv4Network('192.0.2.128/31'),
         IPv4Network('192.0.2.130/32')]

    Args:
        first: the first IPv4Address or IPv6Address in the range.
        last: the last IPv4Address or IPv6Address in the range.

    Returns:
        An iterator of the summarized IPv(4|6) network objects.

    Raise:
        TypeError:
            If the first and last objects are not IP addresses.
            If the first and last objects are not the same version.
        ValueError:
            If the last object is not greater than the first.
            If the version of the first address is not 4 or 6.

    """
    pass
# WARNING: Decompyle incomplete


def _collapse_addresses_internal(addresses):
    """Loops through the addresses, collapsing concurrent netblocks.

    Example:

        ip1 = IPv4Network('192.0.2.0/26')
        ip2 = IPv4Network('192.0.2.64/26')
        ip3 = IPv4Network('192.0.2.128/26')
        ip4 = IPv4Network('192.0.2.192/26')

        _collapse_addresses_internal([ip1, ip2, ip3, ip4]) ->
          [IPv4Network('192.0.2.0/24')]

        This shouldn't be called directly; it is called via
          collapse_addresses([]).

    Args:
        addresses: A list of IPv4Network's or IPv6Network's

    Returns:
        A list of IPv4Network's or IPv6Network's depending on what we were
        passed.

    """
    pass
# WARNING: Decompyle incomplete


def collapse_addresses(addresses):
    """Collapse a list of IP objects.

    Example:
        collapse_addresses([IPv4Network('192.0.2.0/25'),
                            IPv4Network('192.0.2.128/25')]) ->
                           [IPv4Network('192.0.2.0/24')]

    Args:
        addresses: An iterator of IPv4Network or IPv6Network objects.

    Returns:
        An iterator of the collapsed IPv(4|6)Network objects.

    Raises:
        TypeError: If passed a list of mixed version objects.

    """
    addrs = []
    ips = []
    nets = []
    for ip in addresses:
        if isinstance(ip, _BaseAddress):
            if ips and ips[-1]._version != ip._version:
                raise TypeError(f'''{ip!s} and {ips[-1]!s} are not of the same version''')
            ips.append(ip)
            continue
        if ip._prefixlen == ip._max_prefixlen:
            if ips and ips[-1]._version != ip._version:
                raise TypeError(f'''{ip!s} and {ips[-1]!s} are not of the same version''')
            ips.append(ip.ip)
            continue
        if nets and nets[-1]._version != ip._version:
            raise TypeError(f'''{ip!s} and {nets[-1]!s} are not of the same version''')
        nets.append(ip)
    ips = sorted(set(ips))
    if ips:
        for first, last in _find_address_range(ips):
            addrs.extend(summarize_address_range(first, last))
    return _collapse_addresses_internal(addrs + nets)
# WARNING: Decompyle incomplete


def get_mixed_type_key(obj):
    """Return a key suitable for sorting between networks and addresses.

    Address and Network objects are not sortable by default; they're
    fundamentally different so the expression

        IPv4Address('192.0.2.0') <= IPv4Network('192.0.2.0/24')

    doesn't make any sense.  There are some times however, where you may wish
    to have ipaddress sort these for you anyway. If you need to do this, you
    can use this function as the key= argument to sorted().

    Args:
      obj: either a Network or Address object.
    Returns:
      appropriate key.

    """
    if isinstance(obj, _BaseNetwork):
        return obj._get_networks_key()
    if None(obj, _BaseAddress):
        return obj._get_address_key()


class _IPAddressBase:
    '''The mother class.'''
    __slots__ = ()
    exploded = (lambda self: self._explode_shorthand_ip_string())()
    compressed = (lambda self: str(self))()
    reverse_pointer = (lambda self: self._reverse_pointer())()
    version = (lambda self: msg = '%200s has no version specified' % (type(self),)raise NotImplementedError(msg))()
    
    def _check_int_address(self, address):
        if address < 0:
            msg = '%d (< 0) is not permitted as an IPv%d address'
            raise AddressValueError(msg % (address, self._version))
        if address > self._ALL_ONES:
            msg = '%d (>= 2**%d) is not permitted as an IPv%d address'
            raise AddressValueError(msg % (address, self._max_prefixlen, self._version))

    
    def _check_packed_address(self, address, expected_len):
        address_len = len(address)
        if address_len != expected_len:
            msg = '%r (len %d != %d) is not permitted as an IPv%d address'
            raise AddressValueError(msg % (address, address_len, expected_len, self._version))

    _ip_int_from_prefix = (lambda cls, prefixlen: cls._ALL_ONES ^ cls._ALL_ONES >> prefixlen)()
    _prefix_from_ip_int = (lambda cls, ip_int: trailing_zeroes = _count_righthand_zero_bits(ip_int, cls._max_prefixlen)prefixlen = cls._max_prefixlen - trailing_zeroesleading_ones = ip_int >> trailing_zeroesall_ones = (1 << prefixlen) - 1if leading_ones != all_ones:
byteslen = cls._max_prefixlen // 8details = ip_int.to_bytes(byteslen, 'big')msg = 'Netmask pattern %r mixes zeroes & ones'raise ValueError(msg % details)prefixlen)()
    _report_invalid_netmask = (lambda cls, netmask_str: msg = '%r is not a valid netmask' % netmask_strraise NetmaskValueError(msg), None)()
    _prefix_from_prefix_string = (lambda cls, prefixlen_str: if not prefixlen_str.isascii() or prefixlen_str.isdigit():
cls._report_invalid_netmask(prefixlen_str)prefixlen = int(prefixlen_str)# WARNING: Decompyle incomplete
)()
    _prefix_from_ip_string = (lambda cls, ip_str: ip_int = cls._ip_int_from_string(ip_str)# WARNING: Decompyle incomplete
)()
    _split_addr_prefix = (lambda cls, address: if isinstance(address, (bytes, int)):
(address, cls._max_prefixlen)if not None(address, tuple):
address = _split_optional_netmask(address)if len(address) > 1:
address(None[0], cls._max_prefixlen))()
    
    def __reduce__(self):
        return (self.__class__, (str(self),))


_address_fmt_re = None
_BaseAddress = <NODE:12>()
_BaseNetwork = <NODE:12>()

class _BaseConstants:
    _private_networks = []

_BaseNetwork._constants = _BaseConstants

class _BaseV4:
    '''Base IPv4 object.

    The following methods are used by IPv4 objects in both single IP
    addresses and networks.

    '''
    __slots__ = ()
    _version = 4
    _ALL_ONES = 2 ** IPV4LENGTH - 1
    _max_prefixlen = IPV4LENGTH
    _netmask_cache = { }
    
    def _explode_shorthand_ip_string(self):
        return str(self)

    _make_netmask = (lambda cls, arg: if arg not in cls._netmask_cache:
IPv4Address(cls._ip_int_from_prefix(prefixlen)) = None if isinstance(arg, int) else cls._prefix_from_prefix_string(arg)cls._netmask_cache[arg] = (netmask, prefixlen)cls._netmask_cache[arg]# WARNING: Decompyle incomplete
)()
    _ip_int_from_string = (lambda cls, ip_str: if not ip_str:
raise AddressValueError('Address cannot be empty')octets = ip_str.split('.')if len(octets) != 4:
raise AddressValueError('Expected 4 octets in %r' % ip_str)int.from_bytes(map(cls._parse_octet, octets), 'big')# WARNING: Decompyle incomplete
)()
    _parse_octet = (lambda cls, octet_str: if not octet_str:
raise ValueError('Empty octet not permitted')if not octet_str.isascii() or octet_str.isdigit():
msg = 'Only decimal digits permitted in %r'raise ValueError(msg % octet_str)if len(octet_str) > 3:
msg = 'At most 3 characters permitted in %r'raise ValueError(msg % octet_str)if octet_str != '0' and octet_str[0] == '0':
msg = 'Leading zeros are not permitted in %r'raise ValueError(msg % octet_str)octet_int = int(octet_str, 10)if octet_int > 255:
raise ValueError('Octet %d (> 255) not permitted' % octet_int)octet_int)()
    _string_from_ip_int = (lambda cls, ip_int: '.'.join(map(str, ip_int.to_bytes(4, 'big'))))()
    
    def _reverse_pointer(self):
        '''Return the reverse DNS pointer name for the IPv4 address.

        This implements the method described in RFC1035 3.5.

        '''
        reverse_octets = str(self).split('.')[::-1]
        return '.'.join(reverse_octets) + '.in-addr.arpa'

    max_prefixlen = (lambda self: self._max_prefixlen)()
    version = (lambda self: self._version)()


class IPv4Address(_BaseAddress, _BaseV4):
    '''Represent and manipulate single IPv4 Addresses.'''
    __slots__ = ('_ip', '__weakref__')
    
    def __init__(self, address):
        """
        Args:
            address: A string or integer representing the IP

              Additionally, an integer can be passed, so
              IPv4Address('192.0.2.1') == IPv4Address(3221225985).
              or, more generally
              IPv4Address(int(IPv4Address('192.0.2.1'))) ==
                IPv4Address('192.0.2.1')

        Raises:
            AddressValueError: If ipaddress isn't a valid IPv4 address.

        """
        if isinstance(address, int):
            self._check_int_address(address)
            self._ip = address
            return None
        if isinstance(address, bytes):
            self._check_packed_address(address, 4)
            self._ip = int.from_bytes(address)
            return None
        addr_str = str(address)
        if '/' in addr_str:
            raise AddressValueError(f'''Unexpected \'/\' in {address!r}''')
        self._ip = self._ip_int_from_string(addr_str)

    packed = (lambda self: v4_int_to_packed(self._ip))()
    is_reserved = (lambda self: self in self._constants._reserved_network)()
    is_private = (lambda self: pass# WARNING: Decompyle incomplete
)()()
    is_global = (lambda self: if self not in self._constants._public_network:
self not in self._constants._public_networknot (self.is_private))()()
    is_multicast = (lambda self: self in self._constants._multicast_network)()
    is_unspecified = (lambda self: self == self._constants._unspecified_address)()
    is_loopback = (lambda self: self in self._constants._loopback_network)()
    is_link_local = (lambda self: self in self._constants._linklocal_network)()


class IPv4Interface(IPv4Address):
    
    def __init__(self, address):
        (addr, mask) = self._split_addr_prefix(address)
        IPv4Address.__init__(self, addr)
        self.network = IPv4Network((addr, mask), strict = False)
        self.netmask = self.network.netmask
        self._prefixlen = self.network._prefixlen

    hostmask = (lambda self: self.network.hostmask)()
    
    def __str__(self):
        return '%s/%d' % (self._string_from_ip_int(self._ip), self._prefixlen)

    
    def __eq__(self, other):
        address_equal = IPv4Address.__eq__(self, other)
        if not address_equal is NotImplemented or address_equal:
            return address_equal
        return self.network == other.network
    # WARNING: Decompyle incomplete

    
    def __lt__(self, other):
        address_less = IPv4Address.__lt__(self, other)
        if address_less is NotImplemented:
            return NotImplemented
        if not self.network < other.network:
            self.network < other.network
            if self.network == other.network:
                self.network == other.network
        return address_less
    # WARNING: Decompyle incomplete

    
    def __hash__(self):
        return hash((self._ip, self._prefixlen, int(self.network.network_address)))

    __reduce__ = _IPAddressBase.__reduce__
    ip = (lambda self: IPv4Address(self._ip))()
    with_prefixlen = (lambda self: f'''{self._string_from_ip_int(self._ip)!s}/{self._prefixlen!s}''')()
    with_netmask = (lambda self: f'''{self._string_from_ip_int(self._ip)!s}/{self.netmask!s}''')()
    with_hostmask = (lambda self: f'''{self._string_from_ip_int(self._ip)!s}/{self.hostmask!s}''')()


class IPv4Network(_BaseNetwork, _BaseV4):
    """This class represents and manipulates 32-bit IPv4 network + addresses..

    Attributes: [examples for IPv4Network('192.0.2.0/27')]
        .network_address: IPv4Address('192.0.2.0')
        .hostmask: IPv4Address('0.0.0.31')
        .broadcast_address: IPv4Address('192.0.2.32')
        .netmask: IPv4Address('255.255.255.224')
        .prefixlen: 27

    """
    _address_class = IPv4Address
    
    def __init__(self, address, strict = (True,)):
        """Instantiate a new IPv4 network object.

        Args:
            address: A string or integer representing the IP [& network].
              '192.0.2.0/24'
              '192.0.2.0/255.255.255.0'
              '192.0.2.0/0.0.0.255'
              are all functionally the same in IPv4. Similarly,
              '192.0.2.1'
              '192.0.2.1/255.255.255.255'
              '192.0.2.1/32'
              are also functionally equivalent. That is to say, failing to
              provide a subnetmask will create an object with a mask of /32.

              If the mask (portion after the / in the argument) is given in
              dotted quad form, it is treated as a netmask if it starts with a
              non-zero field (e.g. /255.0.0.0 == /8) and as a hostmask if it
              starts with a zero field (e.g. 0.255.255.255 == /8), with the
              single exception of an all-zero mask which is treated as a
              netmask == /0. If no mask is given, a default of /32 is used.

              Additionally, an integer can be passed, so
              IPv4Network('192.0.2.1') == IPv4Network(3221225985)
              or, more generally
              IPv4Interface(int(IPv4Interface('192.0.2.1'))) ==
                IPv4Interface('192.0.2.1')

        Raises:
            AddressValueError: If ipaddress isn't a valid IPv4 address.
            NetmaskValueError: If the netmask isn't valid for
              an IPv4 address.
            ValueError: If strict is True and a network address is not
              supplied.
        """
        pass
    # WARNING: Decompyle incomplete

    is_global = (lambda self: if self.network_address in IPv4Network('100.64.0.0/10'):
self.network_address in IPv4Network('100.64.0.0/10')if not (self.broadcast_address in IPv4Network('100.64.0.0/10')):
not (self.broadcast_address in IPv4Network('100.64.0.0/10'))not (self.is_private))()()


class _IPv4Constants:
    _linklocal_network = IPv4Network('169.254.0.0/16')
    _loopback_network = IPv4Network('127.0.0.0/8')
    _multicast_network = IPv4Network('224.0.0.0/4')
    _public_network = IPv4Network('100.64.0.0/10')
    _private_networks = [
        IPv4Network('0.0.0.0/8'),
        IPv4Network('10.0.0.0/8'),
        IPv4Network('127.0.0.0/8'),
        IPv4Network('169.254.0.0/16'),
        IPv4Network('172.16.0.0/12'),
        IPv4Network('192.0.0.0/29'),
        IPv4Network('192.0.0.170/31'),
        IPv4Network('192.0.2.0/24'),
        IPv4Network('192.168.0.0/16'),
        IPv4Network('198.18.0.0/15'),
        IPv4Network('198.51.100.0/24'),
        IPv4Network('203.0.113.0/24'),
        IPv4Network('240.0.0.0/4'),
        IPv4Network('255.255.255.255/32')]
    _reserved_network = IPv4Network('240.0.0.0/4')
    _unspecified_address = IPv4Address('0.0.0.0')

IPv4Address._constants = _IPv4Constants
IPv4Network._constants = _IPv4Constants

class _BaseV6:
    '''Base IPv6 object.

    The following methods are used by IPv6 objects in both single IP
    addresses and networks.

    '''
    __slots__ = ()
    _version = 6
    _ALL_ONES = 2 ** IPV6LENGTH - 1
    _HEXTET_COUNT = 8
    _HEX_DIGITS = frozenset('0123456789ABCDEFabcdef')
    _max_prefixlen = IPV6LENGTH
    _netmask_cache = { }
    _make_netmask = (lambda cls, arg: if arg not in cls._netmask_cache:
IPv6Address(cls._ip_int_from_prefix(prefixlen)) = None if isinstance(arg, int) else cls._prefix_from_prefix_string(arg)cls._netmask_cache[arg] = (netmask, prefixlen)cls._netmask_cache[arg])()
    _ip_int_from_string = (lambda cls, ip_str: if not ip_str:
raise AddressValueError('Address cannot be empty')parts = ip_str.split(':')_min_parts = 3if len(parts) < _min_parts:
msg = 'At least %d parts expected in %r' % (_min_parts, ip_str)raise AddressValueError(msg)if '.' in parts[-1]:
ipv4_int = IPv4Address(parts.pop())._ipparts.append('%x' % (ipv4_int >> 16 & 65535))parts.append('%x' % (ipv4_int & 65535))_max_parts = cls._HEXTET_COUNT + 1if len(parts) > _max_parts:
msg = 'At most %d colons permitted in %r' % (_max_parts - 1, ip_str)raise AddressValueError(msg)skip_index = None# WARNING: Decompyle incomplete
)()
    _parse_hextet = (lambda cls, hextet_str: if not cls._HEX_DIGITS.issuperset(hextet_str):
raise ValueError('Only hex digits permitted in %r' % hextet_str)if len(hextet_str) > 4:
msg = 'At most 4 characters permitted in %r'raise ValueError(msg % hextet_str)int(hextet_str, 16))()
    _compress_hextets = (lambda cls, hextets: best_doublecolon_start = -1best_doublecolon_len = 0doublecolon_start = -1doublecolon_len = 0for index, hextet in enumerate(hextets):
if hextet == '0':
doublecolon_len += 1if doublecolon_start == -1:
doublecolon_start = indexif not doublecolon_len > best_doublecolon_len:
continuebest_doublecolon_len = doublecolon_lenbest_doublecolon_start = doublecolon_startcontinuedoublecolon_len = 0doublecolon_start = -1if best_doublecolon_len > 1:
best_doublecolon_end = best_doublecolon_start + best_doublecolon_lenif best_doublecolon_end == len(hextets):
hextets += [
'']hextets[best_doublecolon_start:best_doublecolon_end] = [
'']if best_doublecolon_start == 0:
hextets = [
''] + hextetshextets)()
    _string_from_ip_int = (lambda cls, ip_int = (None,): pass# WARNING: Decompyle incomplete
)()
    
    def _explode_shorthand_ip_string(self):
        '''Expand a shortened IPv6 address.

        Returns:
            A string, the expanded IPv6 address.

        '''
        if isinstance(self, IPv6Network):
            ip_str = str(self.network_address)
        elif isinstance(self, IPv6Interface):
            ip_str = str(self.ip)
        else:
            ip_str = str(self)
        ip_int = self._ip_int_from_string(ip_str)
        hex_str = '%032x' % ip_int
    # WARNING: Decompyle incomplete

    
    def _reverse_pointer(self):
        '''Return the reverse DNS pointer name for the IPv6 address.

        This implements the method described in RFC3596 2.5.

        '''
        reverse_chars = self.exploded[::-1].replace(':', '')
        return '.'.join(reverse_chars) + '.ip6.arpa'

    _split_scope_id = (lambda ip_str: (addr, sep, scope_id) = ip_str.partition('%')if not sep:
scope_id = None(addr, scope_id)if None or '%' in scope_id:
raise AddressValueError('Invalid IPv6 address: "%r"' % ip_str)(addr, scope_id))()
    max_prefixlen = (lambda self: self._max_prefixlen)()
    version = (lambda self: self._version)()


class IPv6Address(_BaseAddress, _BaseV6):
    pass
# WARNING: Decompyle incomplete


class IPv6Interface(IPv6Address):
    pass
# WARNING: Decompyle incomplete


class IPv6Network(_BaseNetwork, _BaseV6):
    """This class represents and manipulates 128-bit IPv6 networks.

    Attributes: [examples for IPv6('2001:db8::1000/124')]
        .network_address: IPv6Address('2001:db8::1000')
        .hostmask: IPv6Address('::f')
        .broadcast_address: IPv6Address('2001:db8::100f')
        .netmask: IPv6Address('ffff:ffff:ffff:ffff:ffff:ffff:ffff:fff0')
        .prefixlen: 124

    """
    _address_class = IPv6Address
    
    def __init__(self, address, strict = (True,)):
        """Instantiate a new IPv6 Network object.

        Args:
            address: A string or integer representing the IPv6 network or the
              IP and prefix/netmask.
              '2001:db8::/128'
              '2001:db8:0000:0000:0000:0000:0000:0000/128'
              '2001:db8::'
              are all functionally the same in IPv6.  That is to say,
              failing to provide a subnetmask will create an object with
              a mask of /128.

              Additionally, an integer can be passed, so
              IPv6Network('2001:db8::') ==
                IPv6Network(42540766411282592856903984951653826560)
              or, more generally
              IPv6Network(int(IPv6Network('2001:db8::'))) ==
                IPv6Network('2001:db8::')

            strict: A boolean. If true, ensure that we have been passed
              A true network address, eg, 2001:db8::1000/124 and not an
              IP address on a network, eg, 2001:db8::1/124.

        Raises:
            AddressValueError: If address isn't a valid IPv6 address.
            NetmaskValueError: If the netmask isn't valid for
              an IPv6 address.
            ValueError: If strict was True and a network address was not
              supplied.
        """
        pass
    # WARNING: Decompyle incomplete

    
    def hosts(self):
        """Generate Iterator over usable hosts in a network.

          This is like __iter__ except it doesn't return the
          Subnet-Router anycast address.

        """
        pass
    # WARNING: Decompyle incomplete

    is_site_local = (lambda self: if self.network_address.is_site_local:
self.network_address.is_site_localself.broadcast_address.is_site_local)()


class _IPv6Constants:
    _linklocal_network = IPv6Network('fe80::/10')
    _multicast_network = IPv6Network('ff00::/8')
    _private_networks = [
        IPv6Network('::1/128'),
        IPv6Network('::/128'),
        IPv6Network('::ffff:0:0/96'),
        IPv6Network('100::/64'),
        IPv6Network('2001::/23'),
        IPv6Network('2001:2::/48'),
        IPv6Network('2001:db8::/32'),
        IPv6Network('2001:10::/28'),
        IPv6Network('fc00::/7'),
        IPv6Network('fe80::/10')]
    _reserved_networks = [
        IPv6Network('::/8'),
        IPv6Network('100::/8'),
        IPv6Network('200::/7'),
        IPv6Network('400::/6'),
        IPv6Network('800::/5'),
        IPv6Network('1000::/4'),
        IPv6Network('4000::/3'),
        IPv6Network('6000::/3'),
        IPv6Network('8000::/3'),
        IPv6Network('A000::/3'),
        IPv6Network('C000::/3'),
        IPv6Network('E000::/4'),
        IPv6Network('F000::/5'),
        IPv6Network('F800::/6'),
        IPv6Network('FE00::/9')]
    _sitelocal_network = IPv6Network('fec0::/10')

IPv6Address._constants = _IPv6Constants
IPv6Network._constants = _IPv6Constants
