# Source Generated with Decompyle++
# File: hmac.pyc (Python 3.12)

__doc__ = 'HMAC (Keyed-Hashing for Message Authentication) module.\n\nImplements the HMAC algorithm as described by RFC 2104.\n'
import warnings as _warnings
import _hashlib as _hashopenssl
compare_digest = _hashopenssl.compare_digest
_functype = type(_hashopenssl.openssl_sha256)
import hashlib as _hashlib
trans_5C = (lambda .0: pass# WARNING: Decompyle incomplete
)(range(256)())
trans_36 = (lambda .0: pass# WARNING: Decompyle incomplete
)(range(256)())
digest_size = None

class HMAC:
    '''RFC 2104 HMAC class.  Also complies with RFC 4231.

    This supports the API for Cryptographic Hash Functions (PEP 247).
    '''
    blocksize = 64
    __slots__ = ('_hmac', '_inner', '_outer', 'block_size', 'digest_size')
    
    def __init__(self, key, msg, digestmod = (None, '')):
        '''Create a new HMAC object.

        key: bytes or buffer, key for the keyed hash object.
        msg: bytes or buffer, Initial input for the hash or None.
        digestmod: A hash name suitable for hashlib.new(). *OR*
                   A hashlib constructor returning a new hash object. *OR*
                   A module supporting PEP 247.

                   Required as of 3.8, despite its position after the optional
                   msg argument.  Passing it as a keyword argument is
                   recommended, though not required for legacy API reasons.
        '''
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError('key: expected bytes or bytearray, but got %r' % type(key).__name__)
        if not digestmod:
            raise TypeError("Missing required parameter 'digestmod'.")
        if _hashopenssl and isinstance(digestmod, (str, _functype)):
            self._init_hmac(key, msg, digestmod)
            return None
        self._init_old(key, msg, digestmod)
        return None
    # WARNING: Decompyle incomplete

    
    def _init_hmac(self, key, msg, digestmod):
        self._hmac = _hashopenssl.hmac_new(key, msg, digestmod = digestmod)
        self.digest_size = self._hmac.digest_size
        self.block_size = self._hmac.block_size

    
    def _init_old(self, key, msg, digestmod):
        pass
    # WARNING: Decompyle incomplete

    name = (lambda self: if self._hmac:
self._hmac.namef'''{self._inner.name}''')()
    
    def update(self, msg):
        '''Feed data from msg into this hashing object.'''
        if not self._hmac:
            self._hmac
        inst = self._inner
        inst.update(msg)

    
    def copy(self):
        """Return a separate copy of this hashing object.

        An update to this copy won't affect the original object.
        """
        other = self.__class__.__new__(self.__class__)
        other.digest_size = self.digest_size
        if self._hmac:
            other._hmac = self._hmac.copy()
            other._inner = None
            other._outer = None
            return other
        other._hmac = None
        other._inner = self._inner.copy()
        other._outer = self._outer.copy()
        return other

    
    def _current(self):
        '''Return a hash object for the current state.

        To be used only internally with digest() and hexdigest().
        '''
        if self._hmac:
            return self._hmac
        h = None._outer.copy()
        h.update(self._inner.digest())
        return h

    
    def digest(self):
        '''Return the hash value of this hashing object.

        This returns the hmac value as bytes.  The object is
        not altered in any way by this function; you can continue
        updating the object after calling this function.
        '''
        h = self._current()
        return h.digest()

    
    def hexdigest(self):
        '''Like digest(), but returns a string of hexadecimal digits instead.
        '''
        h = self._current()
        return h.hexdigest()



def new(key, msg, digestmod = (None, '')):
    '''Create a new hashing object and return it.

    key: bytes or buffer, The starting key for the hash.
    msg: bytes or buffer, Initial input for the hash, or None.
    digestmod: A hash name suitable for hashlib.new(). *OR*
               A hashlib constructor returning a new hash object. *OR*
               A module supporting PEP 247.

               Required as of 3.8, despite its position after the optional
               msg argument.  Passing it as a keyword argument is
               recommended, though not required for legacy API reasons.

    You can now feed arbitrary bytes into the object using its update()
    method, and can ask for the hash value at any time by calling its digest()
    or hexdigest() methods.
    '''
    return HMAC(key, msg, digestmod)


def digest(key, msg, digest):
    '''Fast inline implementation of HMAC.

    key: bytes or buffer, The key for the keyed hash object.
    msg: bytes or buffer, Input message.
    digest: A hash name suitable for hashlib.new() for best performance. *OR*
            A hashlib constructor returning a new hash object. *OR*
            A module supporting PEP 247.
    '''
    pass
# WARNING: Decompyle incomplete

return None
# WARNING: Decompyle incomplete
