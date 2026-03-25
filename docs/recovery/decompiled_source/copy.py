# Source Generated with Decompyle++
# File: copy.pyc (Python 3.12)

'''Generic (shallow and deep) copying operations.

Interface summary:

        import copy

        x = copy.copy(y)        # make a shallow copy of y
        x = copy.deepcopy(y)    # make a deep copy of y

For module specific errors, copy.Error is raised.

The difference between shallow and deep copying is only relevant for
compound objects (objects that contain other objects, like lists or
class instances).

- A shallow copy constructs a new compound object and then (to the
  extent possible) inserts *the same objects* into it that the
  original contains.

- A deep copy constructs a new compound object and then, recursively,
  inserts *copies* into it of the objects found in the original.

Two problems often exist with deep copy operations that don\'t exist
with shallow copy operations:

 a) recursive objects (compound objects that, directly or indirectly,
    contain a reference to themselves) may cause a recursive loop

 b) because deep copy copies *everything* it may copy too much, e.g.
    administrative data structures that should be shared even between
    copies

Python\'s deep copy operation avoids these problems by:

 a) keeping a table of objects already copied during the current
    copying pass

 b) letting user-defined classes override the copying operation or the
    set of components copied

This version does not copy types like module, class, function, method,
nor stack trace, stack frame, nor file, socket, window, nor any
similar types.

Classes can use the same interfaces to control copying that they use
to control pickling: they can define methods called __getinitargs__(),
__getstate__() and __setstate__().  See the documentation for module
"pickle" for information on these methods.
'''
import types
import weakref
from copyreg import dispatch_table

class Error(Exception):
    pass

error = Error
__all__ = [
    'Error',
    'copy',
    'deepcopy']

def copy(x):
    """Shallow copy operation on arbitrary Python objects.

    See the module's __doc__ string for more info.
    """
    cls = type(x)
    copier = _copy_dispatch.get(cls)
    if copier:
        return copier(x)
    if None(cls, type):
        return _copy_immutable(x)
    copier = None(cls, '__copy__', None)
# WARNING: Decompyle incomplete

_copy_dispatch = { }
d = { }

def _copy_immutable(x):
    return x

for t in (types.NoneType, int, float, bool, complex, str, tuple, bytes, frozenset, type, range, slice, property, types.BuiltinFunctionType, types.EllipsisType, types.NotImplementedType, types.FunctionType, types.CodeType, weakref.ref):
    d[t] = _copy_immutable
d[list] = list.copy
d[dict] = dict.copy
d[set] = set.copy
d[bytearray] = bytearray.copy
del d
del t

def deepcopy(x, memo, _nil = (None, [])):
    """Deep copy operation on arbitrary Python objects.

    See the module's __doc__ string for more info.
    """
    pass
# WARNING: Decompyle incomplete

_deepcopy_dispatch = { }
d = { }

def _deepcopy_atomic(x, memo):
    return x

d[types.NoneType] = _deepcopy_atomic
d[types.EllipsisType] = _deepcopy_atomic
d[types.NotImplementedType] = _deepcopy_atomic
d[int] = _deepcopy_atomic
d[float] = _deepcopy_atomic
d[bool] = _deepcopy_atomic
d[complex] = _deepcopy_atomic
d[bytes] = _deepcopy_atomic
d[str] = _deepcopy_atomic
d[types.CodeType] = _deepcopy_atomic
d[type] = _deepcopy_atomic
d[range] = _deepcopy_atomic
d[types.BuiltinFunctionType] = _deepcopy_atomic
d[types.FunctionType] = _deepcopy_atomic
d[weakref.ref] = _deepcopy_atomic
d[property] = _deepcopy_atomic

def _deepcopy_list(x, memo, deepcopy = (deepcopy,)):
    y = []
    memo[id(x)] = y
    append = y.append
    for a in x:
        append(deepcopy(a, memo))
    return y

d[list] = _deepcopy_list

def _deepcopy_tuple(x, memo, deepcopy = (deepcopy,)):
    pass
# WARNING: Decompyle incomplete

d[tuple] = _deepcopy_tuple

def _deepcopy_dict(x, memo, deepcopy = (deepcopy,)):
    y = { }
    memo[id(x)] = y
    for key, value in x.items():
        y[deepcopy(key, memo)] = deepcopy(value, memo)
    return y

d[dict] = _deepcopy_dict

def _deepcopy_method(x, memo):
    return type(x)(x.__func__, deepcopy(x.__self__, memo))

d[types.MethodType] = _deepcopy_method
del d

def _keep_alive(x, memo):
    '''Keeps a reference to the object x in the memo.

    Because we remember objects by their id, we have
    to assure that possibly temporary objects are kept
    alive by referencing them.
    We store a reference at the id of the memo, which should
    normally not be used unless someone tries to deepcopy
    the memo itself...
    '''
    memo[id(memo)].append(x)
    return None
# WARNING: Decompyle incomplete


def _reconstruct(x, memo, func, args, state = None, listiter = (None, None, None), dictiter = {
    'deepcopy': deepcopy }, *, deepcopy):
    pass
# WARNING: Decompyle incomplete

del types
del weakref
