# Source Generated with Decompyle++
# File: typing.pyc (Python 3.12)

__doc__ = '\nThe typing module: Support for gradual typing as defined by PEP 484 and subsequent PEPs.\n\nAmong other things, the module includes the following:\n* Generic, Protocol, and internal machinery to support generic aliases.\n  All subscripted types like X[int], Union[int, str] are generic aliases.\n* Various "special forms" that have unique meanings in type annotations:\n  NoReturn, Never, ClassVar, Self, Concatenate, Unpack, and others.\n* Classes whose instances can be type arguments to generic classes and functions:\n  TypeVar, ParamSpec, TypeVarTuple.\n* Public helper functions: get_type_hints, overload, cast, final, and others.\n* Several protocols to support duck-typing:\n  SupportsFloat, SupportsIndex, SupportsAbs, and others.\n* Special types: NewType, NamedTuple, TypedDict.\n* Deprecated wrapper submodules for re and io related types.\n* Deprecated aliases for builtin types and collections.abc ABCs.\n\nAny name not present in __all__ is an implementation detail\nthat may be changed without notice. Use at your own risk!\n'
from abc import abstractmethod, ABCMeta
import collections
from collections import defaultdict
import collections.abc as collections
import copyreg
import contextlib
import functools
import operator
import re as stdlib_re
import sys
import types
import warnings
from types import WrapperDescriptorType, MethodWrapperType, MethodDescriptorType, GenericAlias
from _typing import _idfunc, TypeVar, ParamSpec, TypeVarTuple, ParamSpecArgs, ParamSpecKwargs, TypeAliasType, Generic
__all__ = [
    'Annotated',
    'Any',
    'Callable',
    'ClassVar',
    'Concatenate',
    'Final',
    'ForwardRef',
    'Generic',
    'Literal',
    'Optional',
    'ParamSpec',
    'Protocol',
    'Tuple',
    'Type',
    'TypeVar',
    'TypeVarTuple',
    'Union',
    'AbstractSet',
    'ByteString',
    'Container',
    'ContextManager',
    'Hashable',
    'ItemsView',
    'Iterable',
    'Iterator',
    'KeysView',
    'Mapping',
    'MappingView',
    'MutableMapping',
    'MutableSequence',
    'MutableSet',
    'Sequence',
    'Sized',
    'ValuesView',
    'Awaitable',
    'AsyncIterator',
    'AsyncIterable',
    'Coroutine',
    'Collection',
    'AsyncGenerator',
    'AsyncContextManager',
    'Reversible',
    'SupportsAbs',
    'SupportsBytes',
    'SupportsComplex',
    'SupportsFloat',
    'SupportsIndex',
    'SupportsInt',
    'SupportsRound',
    'ChainMap',
    'Counter',
    'Deque',
    'Dict',
    'DefaultDict',
    'List',
    'OrderedDict',
    'Set',
    'FrozenSet',
    'NamedTuple',
    'TypedDict',
    'Generator',
    'BinaryIO',
    'IO',
    'Match',
    'Pattern',
    'TextIO',
    'AnyStr',
    'assert_type',
    'assert_never',
    'cast',
    'clear_overloads',
    'dataclass_transform',
    'final',
    'get_args',
    'get_origin',
    'get_overloads',
    'get_type_hints',
    'is_typeddict',
    'LiteralString',
    'Never',
    'NewType',
    'no_type_check',
    'no_type_check_decorator',
    'NoReturn',
    'NotRequired',
    'overload',
    'override',
    'ParamSpecArgs',
    'ParamSpecKwargs',
    'Required',
    'reveal_type',
    'runtime_checkable',
    'Self',
    'Text',
    'TYPE_CHECKING',
    'TypeAlias',
    'TypeGuard',
    'TypeAliasType',
    'Unpack']

def _type_convert(arg = None, module = (None,), *, allow_special_forms):
    '''For converting None to type(None), and strings to ForwardRef.'''
    pass
# WARNING: Decompyle incomplete


def _type_check(arg, msg = None, is_argument = (True, None), module = {
    'allow_special_forms': False }, *, allow_special_forms):
    '''Check that the argument is a type, and return it (internal helper).

    As a special case, accept None and return type(None) instead. Also wrap strings
    into ForwardRef instances. Consider several corner cases, for example plain
    special forms like Union are not valid, while Union[int, str] is OK, etc.
    The msg argument is a human-readable error message, e.g.::

        "Union[arg, ...]: arg should be a type."

    We append the repr() of the actual value (truncated to 100 chars).
    '''
    invalid_generic_forms = (Generic, Protocol)
    if not allow_special_forms:
        invalid_generic_forms += (ClassVar,)
        if is_argument:
            invalid_generic_forms += (Final,)
    arg = _type_convert(arg, module = module, allow_special_forms = allow_special_forms)
    if isinstance(arg, _GenericAlias) and arg.__origin__ in invalid_generic_forms:
        raise TypeError(f'''{arg} is not valid as type argument''')
    if arg in (Any, LiteralString, NoReturn, Never, Self, TypeAlias):
        return arg
    if None and arg in (ClassVar, Final):
        return arg
    if None(arg, _SpecialForm) or arg in (Generic, Protocol):
        raise TypeError(f'''Plain {arg} is not valid as type argument''')
    if type(arg) is tuple:
        raise TypeError(f'''{msg} Got {arg!r:.100}.''')
    return arg


def _is_param_expr(arg):
    if not arg is ...:
        arg is ...
    return isinstance(arg, (tuple, list, ParamSpec, _ConcatenateGenericAlias))


def _should_unflatten_callable_args(typ, args):
    """Internal helper for munging collections.abc.Callable's __args__.

    The canonical representation for a Callable's __args__ flattens the
    argument types, see https://github.com/python/cpython/issues/86361.

    For example::

        assert collections.abc.Callable[[int, int], str].__args__ == (int, int, str)
        assert collections.abc.Callable[ParamSpec, str].__args__ == (ParamSpec, str)

    As a result, if we need to reconstruct the Callable from its __args__,
    we need to unflatten it.
    """
    if typ.__origin__ is collections.abc.Callable:
        typ.__origin__ is collections.abc.Callable
        if len(args) == 2:
            len(args) == 2
    return not _is_param_expr(args[0])


def _type_repr(obj):
    '''Return the repr() of an object, special-casing types (internal helper).

    If obj is a type, we return a shorter version than the default
    type.__repr__, based on the module and qualified name, which is
    typically enough to uniquely identify a type.  For everything
    else, we fall back on repr(obj).
    '''
    if isinstance(obj, type):
        if obj.__module__ == 'builtins':
            return obj.__qualname__
        return f'''{None.__module__}.{obj.__qualname__}'''
    if None is ...:
        return '...'
    if isinstance(obj, types.FunctionType):
        return obj.__name__
    if None(obj, tuple):
        return ', '.join + (lambda .0: pass# WARNING: Decompyle incomplete
)(obj()) + ']'
    return None(obj)


def _collect_parameters(args):
    '''Collect all type variables and parameter specifications in args
    in order of first appearance (lexicographic order).

    For example::

        assert _collect_parameters((T, Callable[P, T])) == (T, P)
    '''
    parameters = []
    for t in args:
        if isinstance(t, type):
            continue
        if isinstance(t, tuple):
            for x in t:
                for collected in _collect_parameters([
                    x]):
                    if not collected not in parameters:
                        continue
                    parameters.append(collected)
            continue
        if hasattr(t, '__typing_subst__'):
            if not t not in parameters:
                continue
            parameters.append(t)
            continue
        for x in getattr(t, '__parameters__', ()):
            if not x not in parameters:
                continue
            parameters.append(x)
    return tuple(parameters)


def _check_generic(cls, parameters, elen):
    '''Check correct count for parameters of a generic cls (internal helper).

    This gives a nice error message in case of count mismatch.
    '''
    if not elen:
        raise TypeError(f'''{cls} is not a generic class''')
    alen = len(parameters)
    if alen != elen:
        raise TypeError(f'''Too {'many' if alen > elen else 'few'} arguments for {cls}; actual {alen}, expected {elen}''')


def _unpack_args(args):
    newargs = []
# WARNING: Decompyle incomplete


def _deduplicate(params):
    all_params = set(params)
# WARNING: Decompyle incomplete


def _remove_dups_flatten(parameters):
    '''Internal helper for Union creation and substitution.

    Flatten Unions among parameters, then remove duplicates.
    '''
    params = []
    for p in parameters:
        if isinstance(p, (_UnionGenericAlias, types.UnionType)):
            params.extend(p.__args__)
            continue
        params.append(p)
    return tuple(_deduplicate(params))


def _flatten_literal_params(parameters):
    '''Internal helper for Literal creation: flatten Literals among parameters.'''
    params = []
    for p in parameters:
        if isinstance(p, _LiteralGenericAlias):
            params.extend(p.__args__)
            continue
        params.append(p)
    return tuple(params)

_cleanups = []
_caches = { }

def _tp_cache(func = None, *, typed):
    '''Internal wrapper caching __getitem__ of generic types.

    For non-hashable arguments, the original function is used as a fallback.
    '''
    pass
# WARNING: Decompyle incomplete


def _eval_type(t, globalns, localns, recursive_guard = (frozenset(),)):
    '''Evaluate all forward references in the given type t.

    For use of globalns and localns see the docstring for get_type_hints().
    recursive_guard is used to prevent infinite recursion with a recursive
    ForwardRef.
    '''
    pass
# WARNING: Decompyle incomplete


class _Final:
    '''Mixin to prohibit subclassing.'''
    __slots__ = ('__weakref__',)
    
    def __init_subclass__(cls, *args, **kwds):
        if '_root' not in kwds:
            raise TypeError('Cannot subclass special typing classes')



class _NotIterable:
    '''Mixin to prevent iteration, without being compatible with Iterable.

    That is, we could do::

        def __iter__(self): raise TypeError()

    But this would make users of this mixin duck type-compatible with
    collections.abc.Iterable - isinstance(foo, Iterable) would be True.

    Luckily, we can instead prevent iteration by setting __iter__ to None, which
    is treated specially.
    '''
    __slots__ = ()
    __iter__ = None


def _SpecialForm():
    '''_SpecialForm'''
    __slots__ = ('_name', '__doc__', '_getitem')
    
    def __init__(self, getitem):
        self._getitem = getitem
        self._name = getitem.__name__
        self.__doc__ = getitem.__doc__

    
    def __getattr__(self, item):
        if item in frozenset({'__name__', '__qualname__'}):
            return self._name
        raise None(item)

    
    def __mro_entries__(self, bases):
        raise TypeError(f'''Cannot subclass {self!r}''')

    
    def __repr__(self):
        return 'typing.' + self._name

    
    def __reduce__(self):
        return self._name

    
    def __call__(self, *args, **kwds):
        raise TypeError(f'''Cannot instantiate {self!r}''')

    
    def __or__(self, other):
        return Union[(self, other)]

    
    def __ror__(self, other):
        return Union[(other, self)]

    
    def __instancecheck__(self, obj):
        raise TypeError(f'''{self} cannot be used with isinstance()''')

    
    def __subclasscheck__(self, cls):
        raise TypeError(f'''{self} cannot be used with issubclass()''')

    __getitem__ = (lambda self, parameters: self._getitem(self, parameters))()

_SpecialForm = <NODE:27>(_SpecialForm, '_SpecialForm', _Final, _NotIterable, _root = True)

def _LiteralSpecialForm():
    '''_LiteralSpecialForm'''
    
    def __getitem__(self, parameters):
        if not isinstance(parameters, tuple):
            parameters = (parameters,)
    # WARNING: Decompyle incomplete


_LiteralSpecialForm = <NODE:27>(_LiteralSpecialForm, '_LiteralSpecialForm', _SpecialForm, _root = True)

class _AnyMeta(type):
    pass
# WARNING: Decompyle incomplete


def Any():
    '''Any'''
    pass
# WARNING: Decompyle incomplete

Any = <NODE:27>(Any, 'Any', metaclass = _AnyMeta)
NoReturn = (lambda self, parameters: raise TypeError(f'''{self} is not subscriptable'''))()
Never = (lambda self, parameters: raise TypeError(f'''{self} is not subscriptable'''))()
Self = (lambda self, parameters: raise TypeError(f'''{self} is not subscriptable'''))()
LiteralString = (lambda self, parameters: raise TypeError(f'''{self} is not subscriptable'''))()
ClassVar = (lambda self, parameters: item = _type_check(parameters, f'''{self} accepts only single type.''')_GenericAlias(self, (item,)))()
Final = (lambda self, parameters: item = _type_check(parameters, f'''{self} accepts only single type.''')_GenericAlias(self, (item,)))()
Union = (lambda self, parameters: pass# WARNING: Decompyle incomplete
)()

def _make_union(left, right):
    '''Used from the C implementation of TypeVar.

    TypeVar.__or__ calls this instead of returning types.UnionType
    because we want to allow unions between TypeVars and strings
    (forward references).
    '''
    return Union[(left, right)]

Optional = (lambda self, parameters: arg = _type_check(parameters, f'''{self} requires a single type.''')Union[(arg, type(None))])()
Literal = (lambda self: parameters = _flatten_literal_params(parameters)parameters = (lambda .0: pass# WARNING: Decompyle incomplete
)(_deduplicate(list(_value_and_type_iter(parameters)))())
    return _LiteralGenericAlias(self, parameters)
# WARNING: Decompyle incomplete
)()()
TypeAlias = (lambda self, parameters: raise TypeError(f'''{self} is not subscriptable'''))()
Concatenate = (lambda self, parameters: pass# WARNING: Decompyle incomplete
)()
TypeGuard = (lambda self, parameters: item = _type_check(parameters, f'''{self} accepts only single type.''')_GenericAlias(self, (item,)))()

def ForwardRef():
    '''ForwardRef'''
    __doc__ = 'Internal wrapper to hold a forward reference.'
    __slots__ = ('__forward_arg__', '__forward_code__', '__forward_evaluated__', '__forward_value__', '__forward_is_argument__', '__forward_is_class__', '__forward_module__')
    
    def __init__(self, arg = None, is_argument = (True, None), module = {
        'is_class': False }, *, is_class):
        if not isinstance(arg, str):
            raise TypeError(f'''Forward reference must be a string -- got {arg!r}''')
        if arg[0] == '*':
            arg_to_compile = f'''({arg},)[0]'''
        else:
            arg_to_compile = arg
        code = compile(arg_to_compile, '<string>', 'eval')
        self.__forward_arg__ = arg
        self.__forward_code__ = code
        self.__forward_evaluated__ = False
        self.__forward_value__ = None
        self.__forward_is_argument__ = is_argument
        self.__forward_is_class__ = is_class
        self.__forward_module__ = module
        return None
    # WARNING: Decompyle incomplete

    
    def _evaluate(self, globalns, localns, recursive_guard):
        if self.__forward_arg__ in recursive_guard:
            return self
    # WARNING: Decompyle incomplete

    
    def __eq__(self, other):
        if not isinstance(other, ForwardRef):
            return NotImplemented
        if None.__forward_evaluated__ and other.__forward_evaluated__:
            if self.__forward_arg__ == other.__forward_arg__:
                self.__forward_arg__ == other.__forward_arg__
            return self.__forward_value__ == other.__forward_value__
        if None.__forward_arg__ == other.__forward_arg__:
            None.__forward_arg__ == other.__forward_arg__
        return self.__forward_module__ == other.__forward_module__

    
    def __hash__(self):
        return hash((self.__forward_arg__, self.__forward_module__))

    
    def __or__(self, other):
        return Union[(self, other)]

    
    def __ror__(self, other):
        return Union[(other, self)]

    
    def __repr__(self):
        pass
    # WARNING: Decompyle incomplete


ForwardRef = <NODE:27>(ForwardRef, 'ForwardRef', _Final, _root = True)

def _is_unpacked_typevartuple(x = _SpecialForm):
    if not isinstance(x, type):
        not isinstance(x, type)
    return getattr(x, '__typing_is_unpacked_typevartuple__', False)


def _is_typevar_like(x = _SpecialForm):
    if not isinstance(x, (TypeVar, ParamSpec)):
        isinstance(x, (TypeVar, ParamSpec))
    return _is_unpacked_typevartuple(x)


class _PickleUsingNameMixin:
    '''Mixin enabling pickling based on self.__name__.'''
    
    def __reduce__(self):
        return self.__name__



def _typevar_subst(self, arg):
    msg = 'Parameters to generic types must be types.'
    arg = _type_check(arg, msg, is_argument = True)
    if (isinstance(arg, _GenericAlias) or arg.__origin__ is Unpack or isinstance(arg, GenericAlias)) and getattr(arg, '__unpacked__', False):
        raise TypeError(f'''{arg} is not valid as type argument''')
    return arg


def _typevartuple_prepare_subst(self, alias, args):
    params = alias.__parameters__
    typevartuple_index = params.index(self)
    for param in params[typevartuple_index + 1:]:
        if not isinstance(param, TypeVarTuple):
            continue
        raise TypeError(f'''More than one TypeVarTuple parameter in {alias}''')
    alen = len(args)
    plen = len(params)
    left = typevartuple_index
    right = plen - typevartuple_index - 1
    var_tuple_index = None
    fillarg = None
# WARNING: Decompyle incomplete


def _paramspec_subst(self, arg):
    if isinstance(arg, (list, tuple)):
        arg = (lambda .0: pass# WARNING: Decompyle incomplete
)(arg())
        return arg
    if not None(arg):
        raise TypeError(f'''Expected a list of types, an ellipsis, ParamSpec, or Concatenate. Got {arg}''')
    return arg


def _paramspec_prepare_subst(self, alias, args):
    params = alias.__parameters__
    i = params.index(self)
    if i >= len(args):
        raise TypeError(f'''Too few arguments for {alias}''')
# WARNING: Decompyle incomplete

_generic_class_getitem = (lambda cls, params: if not isinstance(params, tuple):
params = (params,)params = (lambda .0: pass# WARNING: Decompyle incomplete
)(params())
    is_generic_or_protocol = cls in (Generic, Protocol)
    if is_generic_or_protocol:
        if not params:
            raise TypeError(f'''Parameter list to {cls.__qualname__}[...] cannot be empty''')
        if not (lambda .0: pass# WARNING: Decompyle incomplete
)(params()):
            raise TypeError(f'''Parameters to {cls.__name__}[...] must all be type variables or parameter specification variables.''')
        if len(set(params)) != len(params):
            raise TypeError(f'''Parameters to {cls.__name__}[...] must all be unique''')
# WARNING: Decompyle incomplete
)()

def _generic_init_subclass(cls, *args, **kwargs):
    pass
# WARNING: Decompyle incomplete


def _is_dunder(attr):
    if attr.startswith('__'):
        attr.startswith('__')
    return attr.endswith('__')


def _BaseGenericAlias():
    '''_BaseGenericAlias'''
    pass
# WARNING: Decompyle incomplete

_BaseGenericAlias = <NODE:27>(_BaseGenericAlias, '_BaseGenericAlias', _Final, _root = True)

def _GenericAlias():
    '''_GenericAlias'''
    pass
# WARNING: Decompyle incomplete

_GenericAlias = <NODE:27>(_GenericAlias, '_GenericAlias', _BaseGenericAlias, _root = True)

def _SpecialGenericAlias():
    '''_SpecialGenericAlias'''
    pass
# WARNING: Decompyle incomplete

_SpecialGenericAlias = <NODE:27>(_SpecialGenericAlias, '_SpecialGenericAlias', _NotIterable, _BaseGenericAlias, _root = True)

def _DeprecatedGenericAlias():
    '''_DeprecatedGenericAlias'''
    pass
# WARNING: Decompyle incomplete

_DeprecatedGenericAlias = <NODE:27>(_DeprecatedGenericAlias, '_DeprecatedGenericAlias', _SpecialGenericAlias, _root = True)

def _CallableGenericAlias():
    '''_CallableGenericAlias'''
    pass
# WARNING: Decompyle incomplete

_CallableGenericAlias = <NODE:27>(_CallableGenericAlias, '_CallableGenericAlias', _NotIterable, _GenericAlias, _root = True)

def _CallableType():
    '''_CallableType'''
    
    def copy_with(self, params):
        return _CallableGenericAlias(self.__origin__, params, name = self._name, inst = self._inst)

    
    def __getitem__(self, params):
        if isinstance(params, tuple) or len(params) != 2:
            raise TypeError('Callable must be used as Callable[[arg, ...], result].')
        (args, result) = params
        if isinstance(args, list):
            params = (tuple(args), result)
        else:
            params = (args, result)
        return self.__getitem_inner__(params)

    __getitem_inner__ = (lambda self, params: (args, result) = paramsmsg = 'Callable[args, result]: result must be a type.'result = _type_check(result, msg)if args is Ellipsis:
self.copy_with((_TypingEllipsis, result))if not None(args, tuple):
args = (args,)args = (lambda .0: pass# WARNING: Decompyle incomplete
)(args())
        params = args + (result,)
        return self.copy_with(params)
)()

_CallableType = <NODE:27>(_CallableType, '_CallableType', _SpecialGenericAlias, _root = True)

def _TupleType():
    '''_TupleType'''
    __getitem__ = (lambda self, params: pass# WARNING: Decompyle incomplete
)()

_TupleType = <NODE:27>(_TupleType, '_TupleType', _SpecialGenericAlias, _root = True)

def _UnionGenericAlias():
    '''_UnionGenericAlias'''
    pass
# WARNING: Decompyle incomplete

_UnionGenericAlias = <NODE:27>(_UnionGenericAlias, '_UnionGenericAlias', _NotIterable, _GenericAlias, _root = True)

def _value_and_type_iter(parameters):
    return parameters()


def _LiteralGenericAlias():
    '''_LiteralGenericAlias'''
    
    def __eq__(self, other):
        if not isinstance(other, _LiteralGenericAlias):
            return NotImplemented
        return None(_value_and_type_iter(self.__args__)) == set(_value_and_type_iter(other.__args__))

    
    def __hash__(self):
        return hash(frozenset(_value_and_type_iter(self.__args__)))


_LiteralGenericAlias = <NODE:27>(_LiteralGenericAlias, '_LiteralGenericAlias', _GenericAlias, _root = True)

def _ConcatenateGenericAlias():
    '''_ConcatenateGenericAlias'''
    pass
# WARNING: Decompyle incomplete

_ConcatenateGenericAlias = <NODE:27>(_ConcatenateGenericAlias, '_ConcatenateGenericAlias', _GenericAlias, _root = True)
Unpack = (lambda self, parameters: item = _type_check(parameters, f'''{self} accepts only single type.''')_UnpackGenericAlias(origin = self, args = (item,)))()

def _UnpackGenericAlias():
    '''_UnpackGenericAlias'''
    pass
# WARNING: Decompyle incomplete

_UnpackGenericAlias = <NODE:27>(_UnpackGenericAlias, '_UnpackGenericAlias', _GenericAlias, _root = True)

class _TypingEllipsis:
    '''Internal placeholder for ... (ellipsis).'''
    pass

_TYPING_INTERNALS = frozenset({
    '_is_protocol',
    '__orig_bases__',
    '__orig_class__',
    '__parameters__',
    '__type_params__',
    '__protocol_attrs__',
    '_is_runtime_protocol',
    '__callable_proto_members_only__'})
_SPECIAL_NAMES = frozenset({
    '__doc__',
    '__new__',
    '__dict__',
    '__init__',
    '__slots__',
    '__module__',
    '__weakref__',
    '__annotations__',
    '__subclasshook__',
    '__class_getitem__',
    '__abstractmethods__'})
EXCLUDED_ATTRIBUTES = _TYPING_INTERNALS | _SPECIAL_NAMES | {
    '_MutableMapping__marker'}

def _get_protocol_attrs(cls):
