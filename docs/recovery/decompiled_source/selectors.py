# Source Generated with Decompyle++
# File: selectors.pyc (Python 3.12)

'''Selectors module.

This module allows high-level and efficient I/O multiplexing, built upon the
`select` module primitives.
'''
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from collections.abc import Mapping
import math
import select
import sys
EVENT_READ = 1
EVENT_WRITE = 2

def _fileobj_to_fd(fileobj):
    '''Return a file descriptor from a file object.

    Parameters:
    fileobj -- file object or file descriptor

    Returns:
    corresponding file descriptor

    Raises:
    ValueError if the object is invalid
    '''
    if isinstance(fileobj, int):
        fd = fileobj
    else:
        fd = int(fileobj.fileno())
    if fd < 0:
        raise ValueError('Invalid file descriptor: {}'.format(fd))
    return fd
# WARNING: Decompyle incomplete

SelectorKey = namedtuple('SelectorKey', [
    'fileobj',
    'fd',
    'events',
    'data'])
SelectorKey.__doc__ = 'SelectorKey(fileobj, fd, events, data)\n\n    Object used to associate a file object to its backing\n    file descriptor, selected event mask, and attached data.\n'
SelectorKey.fileobj.__doc__ = 'File object registered.'
SelectorKey.fd.__doc__ = 'Underlying file descriptor.'
SelectorKey.events.__doc__ = 'Events that must be waited for on this file object.'
SelectorKey.data.__doc__ = 'Optional opaque data associated to this file object.\nFor example, this could be used to store a per-client session ID.'

class _SelectorMapping(Mapping):
    '''Mapping of file objects to selector keys.'''
    
    def __init__(self, selector):
        self._selector = selector

    
    def __len__(self):
        return len(self._selector._fd_to_key)

    
    def __getitem__(self, fileobj):
        fd = self._selector._fileobj_lookup(fileobj)
        return self._selector._fd_to_key[fd]
    # WARNING: Decompyle incomplete

    
    def __iter__(self):
        return iter(self._selector._fd_to_key)



def BaseSelector():
    '''BaseSelector'''
    __doc__ = 'Selector abstract base class.\n\n    A selector supports registering file objects to be monitored for specific\n    I/O events.\n\n    A file object is a file descriptor or any object with a `fileno()` method.\n    An arbitrary object can be attached to the file object, which can be used\n    for example to store context information, a callback, etc.\n\n    A selector can use various implementations (select(), poll(), epoll()...)\n    depending on the platform. The default `Selector` class uses the most\n    efficient implementation on the current platform.\n    '
    register = (lambda self, fileobj, events, data = (None,): raise NotImplementedError)()
    unregister = (lambda self, fileobj: raise NotImplementedError)()
    
    def modify(self, fileobj, events, data = (None,)):
        '''Change a registered file object monitored events or attached data.

        Parameters:
        fileobj -- file object or file descriptor
        events  -- events to monitor (bitwise mask of EVENT_READ|EVENT_WRITE)
        data    -- attached data

        Returns:
        SelectorKey instance

        Raises:
        Anything that unregister() or register() raises
        '''
        self.unregister(fileobj)
        return self.register(fileobj, events, data)

    select = (lambda self, timeout = (None,): raise NotImplementedError)()
    
    def close(self):
        '''Close the selector.

        This must be called to make sure that any underlying resource is freed.
        '''
        pass

    
    def get_key(self, fileobj):
        '''Return the key associated to a registered file object.

        Returns:
        SelectorKey for this file object
        '''
        mapping = self.get_map()
    # WARNING: Decompyle incomplete

    get_map = (lambda self: raise NotImplementedError)()
    
    def __enter__(self):
        return self

    
    def __exit__(self, *args):
        self.close()


BaseSelector = <NODE:27>(BaseSelector, 'BaseSelector', metaclass = ABCMeta)

class _BaseSelectorImpl(BaseSelector):
    '''Base selector implementation.'''
    
    def __init__(self):
        self._fd_to_key = { }
        self._map = _SelectorMapping(self)

    
    def _fileobj_lookup(self, fileobj):
        '''Return a file descriptor from a file object.

        This wraps _fileobj_to_fd() to do an exhaustive search in case
        the object is invalid but we still have it in our map.  This
        is used by unregister() so we can unregister an object that
        was previously registered even if it is closed.  It is also
        used by _SelectorMapping.
        '''
        return _fileobj_to_fd(fileobj)
    # WARNING: Decompyle incomplete

    
    def register(self, fileobj, events, data = (None,)):
        if events or events & ~(EVENT_READ | EVENT_WRITE):
            raise ValueError('Invalid events: {!r}'.format(events))
        key = SelectorKey(fileobj, self._fileobj_lookup(fileobj), events, data)
        if key.fd in self._fd_to_key:
            raise KeyError('{!r} (FD {}) is already registered'.format(fileobj, key.fd))
        self._fd_to_key[key.fd] = key
        return key

    
    def unregister(self, fileobj):
        key = self._fd_to_key.pop(self._fileobj_lookup(fileobj))
        return key
    # WARNING: Decompyle incomplete

    
    def modify(self, fileobj, events, data = (None,)):
        key = self._fd_to_key[self._fileobj_lookup(fileobj)]
        if events != key.events:
            self.unregister(fileobj)
            key = self.register(fileobj, events, data)
            return key
        if None != key.data:
            key = key._replace(data = data)
            self._fd_to_key[key.fd] = key
        return key
    # WARNING: Decompyle incomplete

    
    def close(self):
        self._fd_to_key.clear()
        self._map = None

    
    def get_map(self):
        return self._map

    
    def _key_from_fd(self, fd):
        '''Return the key associated to a given file descriptor.

        Parameters:
        fd -- file descriptor

        Returns:
        corresponding key, or None if not found
        '''
        return self._fd_to_key[fd]
    # WARNING: Decompyle incomplete



class SelectSelector(_BaseSelectorImpl):
    pass
# WARNING: Decompyle incomplete


class _PollLikeSelector(_BaseSelectorImpl):
    pass
# WARNING: Decompyle incomplete

if hasattr(select, 'poll'):
    
    class PollSelector(_PollLikeSelector):
        '''Poll-based selector.'''
        _selector_cls = select.poll
        _EVENT_READ = select.POLLIN
        _EVENT_WRITE = select.POLLOUT

if hasattr(select, 'epoll'):
    
    class EpollSelector(_PollLikeSelector):
        pass
    # WARNING: Decompyle incomplete

if hasattr(select, 'devpoll'):
    
    class DevpollSelector(_PollLikeSelector):
        pass
    # WARNING: Decompyle incomplete

if hasattr(select, 'kqueue'):
    
    class KqueueSelector(_BaseSelectorImpl):
        pass
    # WARNING: Decompyle incomplete


def _can_use(method):
    '''Check if we can use the selector depending upon the
    operating system. '''
    selector = getattr(select, method, None)
# WARNING: Decompyle incomplete

if _can_use('kqueue'):
    DefaultSelector = KqueueSelector
    return None
if _can_use('epoll'):
    DefaultSelector = EpollSelector
    return None
if _can_use('devpoll'):
    DefaultSelector = DevpollSelector
    return None
if _can_use('poll'):
    DefaultSelector = PollSelector
    return None
DefaultSelector = SelectSelector
