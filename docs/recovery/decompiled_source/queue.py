# Source Generated with Decompyle++
# File: queue.pyc (Python 3.12)

__doc__ = 'A multi-producer, multi-consumer queue.'
import threading
import types
from collections import deque
from heapq import heappush, heappop
from time import monotonic as time
from _queue import SimpleQueue
__all__ = [
    'Empty',
    'Full',
    'Queue',
    'PriorityQueue',
    'LifoQueue',
    'SimpleQueue']
from _queue import Empty

class Full(Exception):
    '''Exception raised by Queue.put(block=0)/put_nowait().'''
    pass


class Queue:
    '''Create a queue object with a given maximum size.

    If maxsize is <= 0, the queue size is infinite.
    '''
    
    def __init__(self, maxsize = (0,)):
        self.maxsize = maxsize
        self._init(maxsize)
        self.mutex = threading.Lock()
        self.not_empty = threading.Condition(self.mutex)
        self.not_full = threading.Condition(self.mutex)
        self.all_tasks_done = threading.Condition(self.mutex)
        self.unfinished_tasks = 0

    
    def task_done(self):
        '''Indicate that a formerly enqueued task is complete.

        Used by Queue consumer threads.  For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.

        If a join() is currently blocking, it will resume when all items
        have been processed (meaning that a task_done() call was received
        for every item that had been put() into the queue).

        Raises a ValueError if called more times than there were items
        placed in the queue.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def join(self):
        '''Blocks until all items in the Queue have been gotten and processed.

        The count of unfinished tasks goes up whenever an item is added to the
        queue. The count goes down whenever a consumer thread calls task_done()
        to indicate the item was retrieved and all work on it is complete.

        When the count of unfinished tasks drops to zero, join() unblocks.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def qsize(self):
        '''Return the approximate size of the queue (not reliable!).'''
        pass
    # WARNING: Decompyle incomplete

    
    def empty(self):
        '''Return True if the queue is empty, False otherwise (not reliable!).

        This method is likely to be removed at some point.  Use qsize() == 0
        as a direct substitute, but be aware that either approach risks a race
        condition where a queue can grow before the result of empty() or
        qsize() can be used.

        To create code that needs to wait for all queued tasks to be
        completed, the preferred technique is to use the join() method.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def full(self):
        '''Return True if the queue is full, False otherwise (not reliable!).

        This method is likely to be removed at some point.  Use qsize() >= n
        as a direct substitute, but be aware that either approach risks a race
        condition where a queue can shrink before the result of full() or
        qsize() can be used.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def put(self, item, block, timeout = (True, None)):
        """Put an item into the queue.

        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until a free slot is available. If 'timeout' is
        a non-negative number, it blocks at most 'timeout' seconds and raises
        the Full exception if no free slot was available within that time.
        Otherwise ('block' is false), put an item on the queue if a free slot
        is immediately available, else raise the Full exception ('timeout'
        is ignored in that case).
        """
        pass
    # WARNING: Decompyle incomplete

    
    def get(self, block, timeout = (True, None)):
        """Remove and return an item from the queue.

        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until an item is available. If 'timeout' is
        a non-negative number, it blocks at most 'timeout' seconds and raises
        the Empty exception if no item was available within that time.
        Otherwise ('block' is false), return an item if one is immediately
        available, else raise the Empty exception ('timeout' is ignored
        in that case).
        """
        pass
    # WARNING: Decompyle incomplete

    
    def put_nowait(self, item):
        '''Put an item into the queue without blocking.

        Only enqueue the item if a free slot is immediately available.
        Otherwise raise the Full exception.
        '''
        return self.put(item, block = False)

    
    def get_nowait(self):
        '''Remove and return an item from the queue without blocking.

        Only get an item if one is immediately available. Otherwise
        raise the Empty exception.
        '''
        return self.get(block = False)

    
    def _init(self, maxsize):
        self.queue = deque()

    
    def _qsize(self):
        return len(self.queue)

    
    def _put(self, item):
        self.queue.append(item)

    
    def _get(self):
        return self.queue.popleft()

    __class_getitem__ = classmethod(types.GenericAlias)


class PriorityQueue(Queue):
    '''Variant of Queue that retrieves open entries in priority order (lowest first).

    Entries are typically tuples of the form:  (priority number, data).
    '''
    
    def _init(self, maxsize):
        self.queue = []

    
    def _qsize(self):
        return len(self.queue)

    
    def _put(self, item):
        heappush(self.queue, item)

    
    def _get(self):
        return heappop(self.queue)



class LifoQueue(Queue):
    '''Variant of Queue that retrieves most recently added entries first.'''
    
    def _init(self, maxsize):
        self.queue = []

    
    def _qsize(self):
        return len(self.queue)

    
    def _put(self, item):
        self.queue.append(item)

    
    def _get(self):
        return self.queue.pop()



class _PySimpleQueue:
    '''Simple, unbounded FIFO queue.

    This pure Python implementation is not reentrant.
    '''
    
    def __init__(self):
        self._queue = deque()
        self._count = threading.Semaphore(0)

    
    def put(self, item, block, timeout = (True, None)):
        """Put the item on the queue.

        The optional 'block' and 'timeout' arguments are ignored, as this method
        never blocks.  They are provided for compatibility with the Queue class.
        """
        self._queue.append(item)
        self._count.release()

    
    def get(self, block, timeout = (True, None)):
        """Remove and return an item from the queue.

        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until an item is available. If 'timeout' is
        a non-negative number, it blocks at most 'timeout' seconds and raises
        the Empty exception if no item was available within that time.
        Otherwise ('block' is false), return an item if one is immediately
        available, else raise the Empty exception ('timeout' is ignored
        in that case).
        """
        pass
    # WARNING: Decompyle incomplete

    
    def put_nowait(self, item):
        '''Put an item into the queue without blocking.

        This is exactly equivalent to `put(item, block=False)` and is only provided
        for compatibility with the Queue class.
        '''
        return self.put(item, block = False)

    
    def get_nowait(self):
        '''Remove and return an item from the queue without blocking.

        Only get an item if one is immediately available. Otherwise
        raise the Empty exception.
        '''
        return self.get(block = False)

    
    def empty(self):
        '''Return True if the queue is empty, False otherwise (not reliable!).'''
        return len(self._queue) == 0

    
    def qsize(self):
        '''Return the approximate size of the queue (not reliable!).'''
        return len(self._queue)

    __class_getitem__ = classmethod(types.GenericAlias)

# WARNING: Decompyle incomplete
