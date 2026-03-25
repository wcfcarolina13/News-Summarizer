# Source Generated with Decompyle++
# File: hashlib.pyc (Python 3.12)

__doc__ = 'hashlib module - A common interface to many hash functions.\n\nnew(name, data=b\'\', **kwargs) - returns a new hash object implementing the\n                                given hash function; initializing the hash\n                                using the given binary data.\n\nNamed constructor functions are also available, these are faster\nthan using new(name):\n\nmd5(), sha1(), sha224(), sha256(), sha384(), sha512(), blake2b(), blake2s(),\nsha3_224, sha3_256, sha3_384, sha3_512, shake_128, and shake_256.\n\nMore algorithms may be available on your platform but the above are guaranteed\nto exist.  See the algorithms_guaranteed and algorithms_available attributes\nto find out what algorithm names can be passed to new().\n\nNOTE: If you want the adler32 or crc32 hash functions they are available in\nthe zlib module.\n\nChoose your hash function wisely.  Some have known collision weaknesses.\nsha384 and sha512 will be slow on 32 bit platforms.\n\nHash objects have these methods:\n - update(data): Update the hash object with the bytes in data. Repeated calls\n                 are equivalent to a single call with the concatenation of all\n                 the arguments.\n - digest():     Return the digest of the bytes passed to the update() method\n                 so far as a bytes object.\n - hexdigest():  Like digest() except the digest is returned as a string\n                 of double length, containing only hexadecimal digits.\n - copy():       Return a copy (clone) of the hash object. This can be used to\n                 efficiently compute the digests of datas that share a common\n                 initial substring.\n\nFor example, to obtain the digest of the byte string \'Nobody inspects the\nspammish repetition\':\n\n    >>> import hashlib\n    >>> m = hashlib.md5()\n    >>> m.update(b"Nobody inspects")\n    >>> m.update(b" the spammish repetition")\n    >>> m.digest()\n    b\'\\xbbd\\x9c\\x83\\xdd\\x1e\\xa5\\xc9\\xd9\\xde\\xc9\\xa1\\x8d\\xf0\\xff\\xe9\'\n\nMore condensed:\n\n    >>> hashlib.sha224(b"Nobody inspects the spammish repetition").hexdigest()\n    \'a4337bc45a8fc544c03f52dc550cd6e1e87021bc896588bd79e901e2\'\n\n'
__always_supported = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512', 'blake2b', 'blake2s', 'sha3_224', 'sha3_256', 'sha3_384', 'sha3_512', 'shake_128', 'shake_256')
algorithms_guaranteed = set(__always_supported)
algorithms_available = set(__always_supported)
__all__ = __always_supported + ('new', 'algorithms_guaranteed', 'algorithms_available', 'file_digest')
__builtin_constructor_cache = { }
__block_openssl_constructor = {
    'blake2b',
    'blake2s'}

def __get_builtin_constructor(name):
    cache = __builtin_constructor_cache
    constructor = cache.get(name)
# WARNING: Decompyle incomplete


def __get_openssl_constructor(name):
    if name in __block_openssl_constructor:
        return __get_builtin_constructor(name)
    f = getattr(_hashlib, 'openssl_' + name)
    f(usedforsecurity = False)
    return f
# WARNING: Decompyle incomplete


def __py_new(name, data = (b'',), **kwargs):
    """new(name, data=b'', **kwargs) - Return a new hashing object using the
    named algorithm; optionally initialized with data (which must be
    a bytes-like object).
    """
    pass
# WARNING: Decompyle incomplete


def __hash_new(name, data = (b'',), **kwargs):
    """new(name, data=b'') - Return a new hashing object using the named algorithm;
    optionally initialized with data (which must be a bytes-like object).
    """
    pass
# WARNING: Decompyle incomplete

import _hashlib
new = __hash_new
__get_hash = __get_openssl_constructor
algorithms_available = algorithms_available.union(_hashlib.openssl_md_meth_names)
from _hashlib import pbkdf2_hmac
__all__ += ('pbkdf2_hmac',)
from _hashlib import scrypt

def file_digest(fileobj = None, digest = {
    '_bufsize': 262144 }, *, _bufsize):
    """Hash the contents of a file-like object. Returns a digest object.

    *fileobj* must be a file-like object opened for reading in binary mode.
    It accepts file objects from open(), io.BytesIO(), and SocketIO objects.
    The function may bypass Python's I/O and use the file descriptor *fileno*
    directly.

    *digest* must either be a hash algorithm name as a *str*, a hash
    constructor, or a callable that returns a hash object.
    """
    if isinstance(digest, str):
        digestobj = new(digest)
    else:
        digestobj = digest()
    if hasattr(fileobj, 'getbuffer'):
        digestobj.update(fileobj.getbuffer())
        return digestobj
    if not None(fileobj, 'readinto') and hasattr(fileobj, 'readable') or fileobj.readable():
        raise ValueError(f'''\'{fileobj!r}\' is not a file-like object in binary reading mode.''')
    buf = bytearray(_bufsize)
    view = memoryview(buf)
    size = fileobj.readinto(buf)
    if size == 0:
        return digestobj
    None.update(view[:size])
    continue

for __func_name in __always_supported:
    globals()[__func_name] = __get_hash(__func_name)
del __always_supported
del __func_name
del __get_hash
del __py_new
del __hash_new
del __get_openssl_constructor
return None
# WARNING: Decompyle incomplete
