# Source Generated with Decompyle++
# File: bisect.pyc (Python 3.12)

__doc__ = 'Bisection algorithms.'

def insort_right(a, x = None, lo = (0, None), hi = {
    'key': None }, *, key):
    '''Insert item x in list a, and keep it sorted assuming a is sorted.

    If x is already in a, insert it to the right of the rightmost x.

    Optional args lo (default 0) and hi (default len(a)) bound the
    slice of a to be searched.

    A custom key function can be supplied to customize the sort order.
    '''
    pass
# WARNING: Decompyle incomplete


def bisect_right(a, x = None, lo = (0, None), hi = {
    'key': None }, *, key):
    '''Return the index where to insert item x in list a, assuming a is sorted.

    The return value i is such that all e in a[:i] have e <= x, and all e in
    a[i:] have e > x.  So if x already appears in the list, a.insert(i, x) will
    insert just after the rightmost x already there.

    Optional args lo (default 0) and hi (default len(a)) bound the
    slice of a to be searched.

    A custom key function can be supplied to customize the sort order.
    '''
    if lo < 0:
        raise ValueError('lo must be non-negative')
# WARNING: Decompyle incomplete


def insort_left(a, x = None, lo = (0, None), hi = {
    'key': None }, *, key):
    '''Insert item x in list a, and keep it sorted assuming a is sorted.

    If x is already in a, insert it to the left of the leftmost x.

    Optional args lo (default 0) and hi (default len(a)) bound the
    slice of a to be searched.

    A custom key function can be supplied to customize the sort order.
    '''
    pass
# WARNING: Decompyle incomplete


def bisect_left(a, x = None, lo = (0, None), hi = {
    'key': None }, *, key):
    '''Return the index where to insert item x in list a, assuming a is sorted.

    The return value i is such that all e in a[:i] have e < x, and all e in
    a[i:] have e >= x.  So if x already appears in the list, a.insert(i, x) will
    insert just before the leftmost x already there.

    Optional args lo (default 0) and hi (default len(a)) bound the
    slice of a to be searched.

    A custom key function can be supplied to customize the sort order.
    '''
    if lo < 0:
        raise ValueError('lo must be non-negative')
# WARNING: Decompyle incomplete

# WARNING: Decompyle incomplete
