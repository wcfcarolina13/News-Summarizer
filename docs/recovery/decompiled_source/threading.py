# Source Generated with Decompyle++
# File: threading.pyc (Python 3.12)

__doc__ = "Thread module emulating a subset of Java's threading model."
import os as _os
import sys as _sys
import _thread
import functools
from time import monotonic as _time
from _weakrefset import WeakSet
from itertools import count as _count
from _collections import deque as _deque
__all__ = [
    'get_ident',
    'active_count',
    'Condition',
    'current_thread',
    'enumerate',
    'main_thread',
    'TIMEOUT_MAX',
    'Event',
    'Lock',
    'RLock',
    'Semaphore',
    'BoundedSemaphore',
    'Thread',
    'Barrier',
    'BrokenBarrierError',
    'Timer',
    'ThreadError',
    'setprofile',
    'settrace',
    'local',
    'stack_size',
    'excepthook',
    'ExceptHookArgs',
    'gettrace',
    'getprofile',
    'setprofile_all_threads',
    'settrace_all_threads']
_start_new_thread = _thread.start_new_thread
_daemon_threads_allowed = _thread.daemon_threads_allowed
_allocate_lock = _thread.allocate_lock
_set_sentinel = _thread._set_sentinel
get_ident = _thread.get_ident
get_native_id = _thread.get_native_id
_HAVE_THREAD_NATIVE_ID = True
__all__.append('get_native_id')
ThreadError = _thread.error
_CRLock = _thread.RLock
TIMEOUT_MAX = _thread.TIMEOUT_MAX
del _thread
_profile_hook = None
_trace_hook = None

def setprofile(func):
    '''Set a profile function for all threads started from the threading module.

    The func will be passed to sys.setprofile() for each thread, before its
    run() method is called.
    '''
    global _profile_hook
    _profile_hook = func


def setprofile_all_threads(func):
    '''Set a profile function for all threads started from the threading module
    and all Python threads that are currently executing.

    The func will be passed to sys.setprofile() for each thread, before its
    run() method is called.
    '''
    setprofile(func)
    _sys._setprofileallthreads(func)


def getprofile():
    '''Get the profiler function as set by threading.setprofile().'''
    return _profile_hook


def settrace(func):
    '''Set a trace function for all threads started from the threading module.

    The func will be passed to sys.settrace() for each thread, before its run()
    method is called.
    '''
    global _trace_hook
    _trace_hook = func


def settrace_all_threads(func):
    '''Set a trace function for all threads started from the threading module
    and all Python threads that are currently executing.

    The func will be passed to sys.settrace() for each thread, before its run()
    method is called.
    '''
    settrace(func)
    _sys._settraceallthreads(func)


def gettrace():
    '''Get the trace function as set by threading.settrace().'''
    return _trace_hook

Lock = _allocate_lock

def RLock(*args, **kwargs):
    '''Factory function that returns a new reentrant lock.

    A reentrant lock must be released by the thread that acquired it. Once a
    thread has acquired a reentrant lock, the same thread may acquire it again
    without blocking; the thread must release it once for each time it has
    acquired it.

    '''
    pass
# WARNING: Decompyle incomplete


class _RLock:
    '''This class implements reentrant lock objects.

    A reentrant lock must be released by the thread that acquired it. Once a
    thread has acquired a reentrant lock, the same thread may acquire it
    again without blocking; the thread must release it once for each time it
    has acquired it.

    '''
    
    def __init__(self):
        self._block = _allocate_lock()
        self._owner = None
        self._count = 0

    
    def __repr__(self):
        owner = self._owner
        owner = _active[owner].name
        return '<%s %s.%s object owner=%r count=%d at %s>' % ('locked' if self._block.locked() else 'unlocked', self.__class__.__module__, self.__class__.__qualname__, owner, self._count, hex(id(self)))
    # WARNING: Decompyle incomplete

    
    def _at_fork_reinit(self):
        self._block._at_fork_reinit()
        self._owner = None
        self._count = 0

    
    def acquire(self, blocking, timeout = (True, -1)):
        '''Acquire a lock, blocking or non-blocking.

        When invoked without arguments: if this thread already owns the lock,
        increment the recursion level by one, and return immediately. Otherwise,
        if another thread owns the lock, block until the lock is unlocked. Once
        the lock is unlocked (not owned by any thread), then grab ownership, set
        the recursion level to one, and return. If more than one thread is
        blocked waiting until the lock is unlocked, only one at a time will be
        able to grab ownership of the lock. There is no return value in this
        case.

        When invoked with the blocking argument set to true, do the same thing
        as when called without arguments, and return true.

        When invoked with the blocking argument set to false, do not block. If a
        call without an argument would block, return false immediately;
        otherwise, do the same thing as when called without arguments, and
        return true.

        When invoked with the floating-point timeout argument set to a positive
        value, block for at most the number of seconds specified by timeout
        and as long as the lock cannot be acquired.  Return true if the lock has
        been acquired, false if the timeout has elapsed.

        '''
        me = get_ident()
        if self._owner == me:
            return 1
        self._block.acquire(blocking, timeout) = self, self._count += 1, ._count
        if rc:
            self._owner = me
            self._count = 1
        return rc

    __enter__ = acquire
    
    def release(self):
        '''Release a lock, decrementing the recursion level.

        If after the decrement it is zero, reset the lock to unlocked (not owned
        by any thread), and if any other threads are blocked waiting for the
        lock to become unlocked, allow exactly one of them to proceed. If after
        the decrement the recursion level is still nonzero, the lock remains
        locked and owned by the calling thread.

        Only call this method when the calling thread owns the lock. A
        RuntimeError is raised if this method is called when the lock is
        unlocked.

        There is no return value.

        '''
        if self._owner != get_ident():
            raise RuntimeError('cannot release un-acquired lock')
        self._count = self._count - 1
        count = self._count - 1
        if not count:
            self._owner = None
            self._block.release()
            return None

    
    def __exit__(self, t, v, tb):
        self.release()

    
    def _acquire_restore(self, state):
        self._block.acquire()
        (self._count, self._owner) = state

    
    def _release_save(self):
        if self._count == 0:
            raise RuntimeError('cannot release un-acquired lock')
        count = self._count
        self._count = 0
        owner = self._owner
        self._owner = None
        self._block.release()
        return (count, owner)

    
    def _is_owned(self):
        return self._owner == get_ident()


_PyRLock = _RLock

class Condition:
    '''Class that implements a condition variable.

    A condition variable allows one or more threads to wait until they are
    notified by another thread.

    If the lock argument is given and not None, it must be a Lock or RLock
    object, and it is used as the underlying lock. Otherwise, a new RLock object
    is created and used as the underlying lock.

    '''
    
    def __init__(self, lock = (None,)):
        pass
    # WARNING: Decompyle incomplete

    
    def _at_fork_reinit(self):
        self._lock._at_fork_reinit()
        self._waiters.clear()

    
    def __enter__(self):
        return self._lock.__enter__()

    
    def __exit__(self, *args):
        pass
    # WARNING: Decompyle incomplete

    
    def __repr__(self):
        return '<Condition(%s, %d)>' % (self._lock, len(self._waiters))

    
    def _release_save(self):
        self._lock.release()

    
    def _acquire_restore(self, x):
        self._lock.acquire()

    
    def _is_owned(self):
        if self._lock.acquire(False):
            self._lock.release()
            return False
        return True

    
    def wait(self, timeout = (None,)):
        '''Wait until notified or until a timeout occurs.

        If the calling thread has not acquired the lock when this method is
        called, a RuntimeError is raised.

        This method releases the underlying lock, and then blocks until it is
        awakened by a notify() or notify_all() call for the same condition
        variable in another thread, or until the optional timeout occurs. Once
        awakened or timed out, it re-acquires the lock and returns.

        When the timeout argument is present and not None, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        When the underlying lock is an RLock, it is not released using its
        release() method, since this may not actually unlock the lock when it
        was acquired multiple times recursively. Instead, an internal interface
        of the RLock class is used, which really unlocks it even when it has
        been recursively acquired several times. Another internal interface is
        then used to restore the recursion level when the lock is reacquired.

        '''
        if not self._is_owned():
            raise RuntimeError('cannot wait on un-acquired lock')
        waiter = _allocate_lock()
        waiter.acquire()
        self._waiters.append(waiter)
        saved_state = self._release_save()
        gotit = False
    # WARNING: Decompyle incomplete

    
    def wait_for(self, predicate, timeout = (None,)):
        '''Wait until a condition evaluates to True.

        predicate should be a callable which result will be interpreted as a
        boolean value.  A timeout may be provided giving the maximum time to
        wait.

        '''
        endtime = None
        waittime = timeout
        result = predicate()
    # WARNING: Decompyle incomplete

    
    def notify(self, n = (1,)):
        '''Wake up one or more threads waiting on this condition, if any.

        If the calling thread has not acquired the lock when this method is
        called, a RuntimeError is raised.

        This method wakes up at most n of the threads waiting for the condition
        variable; it is a no-op if no threads are waiting.

        '''
        if not self._is_owned():
            raise RuntimeError('cannot notify on un-acquired lock')
        waiters = self._waiters
        if waiters:
            if n > 0:
                waiter = waiters[0]
                waiter.release()
                n -= 1
                waiters.remove(waiter)
                if waiters:
                    if n > 0:
                        continue
                    return None
                return None
            return None
        return None
    # WARNING: Decompyle incomplete

    
    def notify_all(self):
        '''Wake up all threads waiting on this condition.

        If the calling thread has not acquired the lock when this method
        is called, a RuntimeError is raised.

        '''
        self.notify(len(self._waiters))

    
    def notifyAll(self):
        '''Wake up all threads waiting on this condition.

        This method is deprecated, use notify_all() instead.

        '''
        import warnings
        warnings.warn('notifyAll() is deprecated, use notify_all() instead', DeprecationWarning, stacklevel = 2)
        self.notify_all()



class Semaphore:
    '''This class implements semaphore objects.

    Semaphores manage a counter representing the number of release() calls minus
    the number of acquire() calls, plus an initial value. The acquire() method
    blocks if necessary until it can return without making the counter
    negative. If not given, value defaults to 1.

    '''
    
    def __init__(self, value = (1,)):
        if value < 0:
            raise ValueError('semaphore initial value must be >= 0')
        self._cond = Condition(Lock())
        self._value = value

    
    def __repr__(self):
        cls = self.__class__
        return f'''<{cls.__module__}.{cls.__qualname__} at {id(self):#x}: value={self._value}>'''

    
    def acquire(self, blocking, timeout = (True, None)):
        '''Acquire a semaphore, decrementing the internal counter by one.

        When invoked without arguments: if the internal counter is larger than
        zero on entry, decrement it by one and return immediately. If it is zero
        on entry, block, waiting until some other thread has called release() to
        make it larger than zero. This is done with proper interlocking so that
        if multiple acquire() calls are blocked, release() will wake exactly one
        of them up. The implementation may pick one at random, so the order in
        which blocked threads are awakened should not be relied on. There is no
        return value in this case.

        When invoked with blocking set to true, do the same thing as when called
        without arguments, and return true.

        When invoked with blocking set to false, do not block. If a call without
        an argument would block, return false immediately; otherwise, do the
        same thing as when called without arguments, and return true.

        When invoked with a timeout other than None, it will block for at
        most timeout seconds.  If acquire does not complete successfully in
        that interval, return false.  Return true otherwise.

        '''
        pass
    # WARNING: Decompyle incomplete

    __enter__ = acquire
    
    def release(self, n = (1,)):
        '''Release a semaphore, incrementing the internal counter by one or more.

        When the counter is zero on entry and another thread is waiting for it
        to become larger than zero again, wake up that thread.

        '''
        if n < 1:
            raise ValueError('n must be one or more')
    # WARNING: Decompyle incomplete

    
    def __exit__(self, t, v, tb):
        self.release()



class BoundedSemaphore(Semaphore):
    pass
# WARNING: Decompyle incomplete


class Event:
    '''Class implementing event objects.

    Events manage a flag that can be set to true with the set() method and reset
    to false with the clear() method. The wait() method blocks until the flag is
    true.  The flag is initially false.

    '''
    
    def __init__(self):
        self._cond = Condition(Lock())
        self._flag = False

    
    def __repr__(self):
        cls = self.__class__
        status = 'set' if self._flag else 'unset'
        return f'''<{cls.__module__}.{cls.__qualname__} at {id(self):#x}: {status}>'''

    
    def _at_fork_reinit(self):
        self._cond._at_fork_reinit()

    
    def is_set(self):
        '''Return true if and only if the internal flag is true.'''
        return self._flag

    
    def isSet(self):
        '''Return true if and only if the internal flag is true.

        This method is deprecated, use is_set() instead.

        '''
        import warnings
        warnings.warn('isSet() is deprecated, use is_set() instead', DeprecationWarning, stacklevel = 2)
        return self.is_set()

    
    def set(self):
        '''Set the internal flag to true.

        All threads waiting for it to become true are awakened. Threads
        that call wait() once the flag is true will not block at all.

        '''
        pass
    # WARNING: Decompyle incomplete

    
    def clear(self):
        '''Reset the internal flag to false.

        Subsequently, threads calling wait() will block until set() is called to
        set the internal flag to true again.

        '''
        pass
    # WARNING: Decompyle incomplete

    
    def wait(self, timeout = (None,)):
        '''Block until the internal flag is true.

        If the internal flag is true on entry, return immediately. Otherwise,
        block until another thread calls set() to set the flag to true, or until
        the optional timeout occurs.

        When the timeout argument is present and not None, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        This method returns the internal flag on exit, so it will always return
        True except if a timeout is given and the operation times out.

        '''
        pass
    # WARNING: Decompyle incomplete



class Barrier:
    """Implements a Barrier.

    Useful for synchronizing a fixed number of threads at known synchronization
    points.  Threads block on 'wait()' and are simultaneously awoken once they
    have all made that call.

    """
    
    def __init__(self, parties, action, timeout = (None, None)):
        """Create a barrier, initialised to 'parties' threads.

        'action' is a callable which, when supplied, will be called by one of
        the threads after they have all entered the barrier and just prior to
        releasing them all. If a 'timeout' is provided, it is used as the
        default for all subsequent 'wait()' calls.

        """
        self._cond = Condition(Lock())
        self._action = action
        self._timeout = timeout
        self._parties = parties
        self._state = 0
        self._count = 0

    
    def __repr__(self):
        cls = self.__class__
        if self.broken:
            return f'''<{cls.__module__}.{cls.__qualname__} at {id(self):#x}: broken>'''
        return f'''{cls.__module__}.{cls.__qualname__} at {id(self):#x}: waiters={self.n_waiting}/{self.parties}>'''

    
    def wait(self, timeout = (None,)):
        """Wait for the barrier.

        When the specified number of threads have started waiting, they are all
        simultaneously awoken. If an 'action' was provided for the barrier, one
        of the threads will have executed that callback prior to returning.
        Returns an individual index number from 0 to 'parties-1'.

        """
        pass
    # WARNING: Decompyle incomplete

    
    def _enter(self):
        if self._state in (-1, 1):
            self._cond.wait()
            if self._state in (-1, 1):
                continue
        if self._state < 0:
            raise BrokenBarrierError
    # WARNING: Decompyle incomplete

    
    def _release(self):
        if self._action:
            self._action()
        self._state = 1
        self._cond.notify_all()
        return None
    # WARNING: Decompyle incomplete

    
    def _wait(self, timeout):
        pass
    # WARNING: Decompyle incomplete

    
    def _exit(self):
        if self._count == 0:
            if self._state in (-1, 1):
                self._state = 0
                self._cond.notify_all()
                return None
            return None

    
    def reset(self):
        '''Reset the barrier to the initial state.

        Any threads currently waiting will get the BrokenBarrier exception
        raised.

        '''
        pass
    # WARNING: Decompyle incomplete

    
    def abort(self):
        """Place the barrier into a 'broken' state.

        Useful in case of error.  Any currently waiting threads and threads
        attempting to 'wait()' will have BrokenBarrierError raised.

        """
        pass
    # WARNING: Decompyle incomplete

    
    def _break(self):
        self._state = -2
        self._cond.notify_all()

    parties = (lambda self: self._parties)()
    n_waiting = (lambda self: if self._state == 0:
self._count)()
    broken = (lambda self: self._state == -2)()


class BrokenBarrierError(RuntimeError):
    pass

_counter = _count(1).__next__

def _newname(name_template):
    return name_template % _counter()

_active_limbo_lock = RLock()
_active = { }
_limbo = { }
_dangling = WeakSet()
_shutdown_locks_lock = _allocate_lock()
_shutdown_locks = set()

def _maintain_shutdown_locks():
    """
    Drop any shutdown locks that don't correspond to running threads anymore.

    Calling this from time to time avoids an ever-growing _shutdown_locks
    set when Thread objects are not joined explicitly. See bpo-37788.

    This must be called with _shutdown_locks_lock acquired.
    """
    pass
# WARNING: Decompyle incomplete


class Thread:
    '''A class that represents a thread of control.

    This class can be safely subclassed in a limited fashion. There are two ways
    to specify the activity: by passing a callable object to the constructor, or
    by overriding the run() method in a subclass.

    '''
    _initialized = False
    
    def __init__(self, group, target, name = None, args = (None, None, None, (), None), kwargs = {
        'daemon': None }, *, daemon):
        '''This constructor should always be called with keyword arguments. Arguments are:

        *group* should be None; reserved for future extension when a ThreadGroup
        class is implemented.

        *target* is the callable object to be invoked by the run()
        method. Defaults to None, meaning nothing is called.

        *name* is the thread name. By default, a unique name is constructed of
        the form "Thread-N" where N is a small decimal number.

        *args* is a list or tuple of arguments for the target invocation. Defaults to ().

        *kwargs* is a dictionary of keyword arguments for the target
        invocation. Defaults to {}.

        If a subclass overrides the constructor, it must make sure to invoke
        the base class constructor (Thread.__init__()) before doing anything
        else to the thread.

        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _reset_internal_locks(self, is_alive):
        self._started._at_fork_reinit()
    # WARNING: Decompyle incomplete

    
    def __repr__(self):
        pass
    # WARNING: Decompyle incomplete

    
    def start(self):
        """Start the thread's activity.

        It must be called at most once per thread object. It arranges for the
        object's run() method to be invoked in a separate thread of control.

        This method will raise a RuntimeError if called more than once on the
        same thread object.

        """
        if not self._initialized:
            raise RuntimeError('thread.__init__() not called')
        if self._started.is_set():
            raise RuntimeError('threads can only be started once')
    # WARNING: Decompyle incomplete

    
    def run(self):
        """Method representing the thread's activity.

        You may override this method in a subclass. The standard run() method
        invokes the callable object passed to the object's constructor as the
        target argument, if any, with sequential and keyword arguments taken
        from the args and kwargs arguments, respectively.

        """
        pass
    # WARNING: Decompyle incomplete

    
    def _bootstrap(self):
        self._bootstrap_inner()
        return None
    # WARNING: Decompyle incomplete

    
    def _set_ident(self):
        self._ident = get_ident()

    if _HAVE_THREAD_NATIVE_ID:
        
        def _set_native_id(self):
            self._native_id = get_native_id()

    
    def _set_tstate_lock(self):
        '''
        Set a lock object which will be released by the interpreter when
        the underlying thread state (see pystate.h) gets deleted.
        '''
        self._tstate_lock = _set_sentinel()
        self._tstate_lock.acquire()
    # WARNING: Decompyle incomplete

    
    def _bootstrap_inner(self):
        self._set_ident()
        self._set_tstate_lock()
        if _HAVE_THREAD_NATIVE_ID:
            self._set_native_id()
        self._started.set()
    # WARNING: Decompyle incomplete

    
    def _stop(self):
        lock = self._tstate_lock
    # WARNING: Decompyle incomplete

    
    def _delete(self):
        '''Remove current thread from the dict of currently running threads.'''
        pass
    # WARNING: Decompyle incomplete

    
    def join(self, timeout = (None,)):
        '''Wait until the thread terminates.

        This blocks the calling thread until the thread whose join() method is
        called terminates -- either normally or through an unhandled exception
        or until the optional timeout occurs.

        When the timeout argument is present and not None, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof). As join() always returns None, you must call
        is_alive() after join() to decide whether a timeout happened -- if the
        thread is still alive, the join() call timed out.

        When the timeout argument is not present or None, the operation will
        block until the thread terminates.

        A thread can be join()ed many times.

        join() raises a RuntimeError if an attempt is made to join the current
        thread as that would cause a deadlock. It is also an error to join() a
        thread before it has been started and attempts to do so raises the same
        exception.

        '''
        if not self._initialized:
            raise RuntimeError('Thread.__init__() not called')
        if not self._started.is_set():
            raise RuntimeError('cannot join thread before it is started')
        if self is current_thread():
            raise RuntimeError('cannot join current thread')
    # WARNING: Decompyle incomplete

    
    def _wait_for_tstate_lock(self, block, timeout = (True, -1)):
        lock = self._tstate_lock
    # WARNING: Decompyle incomplete

    name = (lambda self: pass# WARNING: Decompyle incomplete
)()
    name = (lambda self, name: pass# WARNING: Decompyle incomplete
)()
    ident = (lambda self: pass# WARNING: Decompyle incomplete
)()
    if _HAVE_THREAD_NATIVE_ID:
        native_id = (lambda self: pass# WARNING: Decompyle incomplete
)()
    
    def is_alive(self):
        '''Return whether the thread is alive.

        This method returns True just before the run() method starts until just
        after the run() method terminates. See also the module function
        enumerate().

        '''
        pass
    # WARNING: Decompyle incomplete

    daemon = (lambda self: pass# WARNING: Decompyle incomplete
)()
    daemon = (lambda self, daemonic: if not self._initialized:
raise RuntimeError('Thread.__init__() not called')if not daemonic and _daemon_threads_allowed():
raise RuntimeError('daemon threads are disabled in this interpreter')if self._started.is_set():
raise RuntimeError('cannot set daemon status of active thread')self._daemonic = daemonic)()
    
    def isDaemon(self):
        '''Return whether this thread is a daemon.

        This method is deprecated, use the daemon attribute instead.

        '''
        import warnings
        warnings.warn('isDaemon() is deprecated, get the daemon attribute instead', DeprecationWarning, stacklevel = 2)
        return self.daemon

    
    def setDaemon(self, daemonic):
        '''Set whether this thread is a daemon.

        This method is deprecated, use the .daemon property instead.

        '''
        import warnings
        warnings.warn('setDaemon() is deprecated, set the daemon attribute instead', DeprecationWarning, stacklevel = 2)
        self.daemon = daemonic

    
    def getName(self):
        '''Return a string used for identification purposes only.

        This method is deprecated, use the name attribute instead.

        '''
        import warnings
        warnings.warn('getName() is deprecated, get the name attribute instead', DeprecationWarning, stacklevel = 2)
        return self.name

    
    def setName(self, name):
        '''Set the name string for this thread.

        This method is deprecated, use the name attribute instead.

        '''
        import warnings
        warnings.warn('setName() is deprecated, set the name attribute instead', DeprecationWarning, stacklevel = 2)
        self.name = name


excepthook = _excepthook
from _thread import _ExceptHookArgs as ExceptHookArgs
__excepthook__ = excepthook

def _make_invoke_excepthook():
    pass
# WARNING: Decompyle incomplete


class Timer(Thread):
    """Call a function after a specified number of seconds:

            t = Timer(30.0, f, args=None, kwargs=None)
            t.start()
            t.cancel()     # stop the timer's action if it's still waiting

    """
    
    def __init__(self, interval, function, args, kwargs = (None, None)):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
    # WARNING: Decompyle incomplete

    
    def cancel(self):
        """Stop the timer if it hasn't finished yet."""
        self.finished.set()

    
    def run(self):
        self.finished.wait(self.interval)
    # WARNING: Decompyle incomplete



class _MainThread(Thread):
    
    def __init__(self):
        Thread.__init__(self, name = 'MainThread', daemon = False)
        self._set_tstate_lock()
        self._started.set()
        self._set_ident()
        if _HAVE_THREAD_NATIVE_ID:
            self._set_native_id()
    # WARNING: Decompyle incomplete



class _DummyThread(Thread):
    
    def __init__(self):
        Thread.__init__(self, name = _newname('Dummy-%d'), daemon = _daemon_threads_allowed())
        self._started.set()
        self._set_ident()
        if _HAVE_THREAD_NATIVE_ID:
            self._set_native_id()
    # WARNING: Decompyle incomplete

    
    def _stop(self):
        pass

    
    def is_alive(self):
        pass
    # WARNING: Decompyle incomplete

    
    def join(self, timeout = (None,)):
        pass
    # WARNING: Decompyle incomplete



def current_thread():
    """Return the current Thread object, corresponding to the caller's thread of control.

    If the caller's thread of control was not created through the threading
    module, a dummy thread object with limited functionality is returned.

    """
    return _active[get_ident()]
# WARNING: Decompyle incomplete


def currentThread():
    """Return the current Thread object, corresponding to the caller's thread of control.

    This function is deprecated, use current_thread() instead.

    """
    import warnings
    warnings.warn('currentThread() is deprecated, use current_thread() instead', DeprecationWarning, stacklevel = 2)
    return current_thread()


def active_count():
    '''Return the number of Thread objects currently alive.

    The returned count is equal to the length of the list returned by
    enumerate().

    '''
    pass
# WARNING: Decompyle incomplete


def activeCount():
    '''Return the number of Thread objects currently alive.

    This function is deprecated, use active_count() instead.

    '''
    import warnings
    warnings.warn('activeCount() is deprecated, use active_count() instead', DeprecationWarning, stacklevel = 2)
    return active_count()


def _enumerate():
    return list(_active.values()) + list(_limbo.values())


def enumerate():
    '''Return a list of all Thread objects currently alive.

    The list includes daemonic threads, dummy thread objects created by
    current_thread(), and the main thread. It excludes terminated threads and
    threads that have not yet been started.

    '''
    pass
# WARNING: Decompyle incomplete

_threading_atexits = []
_SHUTTING_DOWN = False

def _register_atexit(func, *arg, **kwargs):
    '''CPython internal: register *func* to be called before joining threads.

    The registered *func* is called with its arguments just before all
    non-daemon threads are joined in `_shutdown()`. It provides a similar
    purpose to `atexit.register()`, but its functions are called prior to
    threading shutdown instead of interpreter shutdown.

    For similarity to atexit, the registered functions are called in reverse.
    '''
    if _SHUTTING_DOWN:
        raise RuntimeError("can't register atexit after shutdown")
# WARNING: Decompyle incomplete

from _thread import stack_size
_main_thread = _MainThread()

def _shutdown():
    '''
    Wait until the Python thread state of all non-daemon threads get deleted.
    '''
    global _SHUTTING_DOWN
    if _main_thread._is_stopped:
        return None
    _SHUTTING_DOWN = True
    for atexit_call in reversed(_threading_atexits):
        atexit_call()
# WARNING: Decompyle incomplete


def main_thread():
    '''Return the main thread object.

    In normal conditions, the main thread is the thread from which the
    Python interpreter was started.
    '''
    return _main_thread

from _thread import _local as local

def _after_fork():
    '''
    Cleanup threading module state that should not exist after a fork.
    '''
    global _active_limbo_lock, _main_thread, _shutdown_locks_lock, _shutdown_locks
    _active_limbo_lock = RLock()
    new_active = { }
    current = _active[get_ident()]
    _main_thread = current
    _shutdown_locks_lock = _allocate_lock()
    _shutdown_locks = set()
# WARNING: Decompyle incomplete

if hasattr(_os, 'register_at_fork'):
    _os.register_at_fork(after_in_child = _after_fork)
    return None
return None
# WARNING: Decompyle incomplete
