# Source Generated with Decompyle++
# File: typing_extensions.pyc (Python 3.12)

import abc
import builtins
import collections
import collections.abc as collections
import contextlib
import enum
import functools
import inspect
import keyword
import operator
import sys
import types as _types
import typing
import warnings
__all__ = [
    'Any',
    'ClassVar',
    'Concatenate',
    'Final',
    'LiteralString',
    'ParamSpec',
    'ParamSpecArgs',
    'ParamSpecKwargs',
    'Self',
    'Type',
    'TypeVar',
    'TypeVarTuple',
    'Unpack',
    'Awaitable',
    'AsyncIterator',
    'AsyncIterable',
    'Coroutine',
    'AsyncGenerator',
    'AsyncContextManager',
    'Buffer',
    'ChainMap',
    'ContextManager',
    'Counter',
    'Deque',
    'DefaultDict',
    'NamedTuple',
    'OrderedDict',
    'TypedDict',
    'SupportsAbs',
    'SupportsBytes',
    'SupportsComplex',
    'SupportsFloat',
    'SupportsIndex',
    'SupportsInt',
    'SupportsRound',
    'Annotated',
    'assert_never',
    'assert_type',
    'clear_overloads',
    'dataclass_transform',
    'deprecated',
    'Doc',
    'evaluate_forward_ref',
    'get_overloads',
    'final',
    'Format',
    'get_annotations',
    'get_args',
    'get_origin',
    'get_original_bases',
    'get_protocol_members',
    'get_type_hints',
    'IntVar',
    'is_protocol',
    'is_typeddict',
    'Literal',
    'NewType',
    'overload',
    'override',
    'Protocol',
    'reveal_type',
    'runtime',
    'runtime_checkable',
    'Text',
    'TypeAlias',
    'TypeAliasType',
    'TypeForm',
    'TypeGuard',
    'TypeIs',
    'TYPE_CHECKING',
    'Never',
    'NoReturn',
    'ReadOnly',
    'Required',
    'NotRequired',
    'NoDefault',
    'NoExtraItems',
    'AbstractSet',
    'AnyStr',
    'BinaryIO',
    'Callable',
    'Collection',
    'Container',
    'Dict',
    'ForwardRef',
    'FrozenSet',
    'Generator',
    'Generic',
    'Hashable',
    'IO',
    'ItemsView',
    'Iterable',
    'Iterator',
    'KeysView',
    'List',
    'Mapping',
    'MappingView',
    'Match',
    'MutableMapping',
    'MutableSequence',
    'MutableSet',
    'Optional',
    'Pattern',
    'Reversible',
    'Sequence',
    'Set',
    'Sized',
    'TextIO',
    'Tuple',
    'Union',
    'ValuesView',
    'cast',
    'no_type_check',
    'no_type_check_decorator']
PEP_560 = True
GenericMeta = type
_PEP_696_IMPLEMENTED = sys.version_info >= (3, 13, 0, 'beta')
_FORWARD_REF_HAS_CLASS = '__forward_is_class__' in typing.ForwardRef.__slots__

class _Sentinel:
    
    def __repr__(self):
        return '<sentinel>'


_marker = _Sentinel()
if sys.version_info >= (3, 10):
    
    def _should_collect_from_parameters(t):
        return isinstance(t, (typing._GenericAlias, _types.GenericAlias, _types.UnionType))

elif sys.version_info >= (3, 9):
    
    def _should_collect_from_parameters(t):
        return isinstance(t, (typing._GenericAlias, _types.GenericAlias))

else:
    
    def _should_collect_from_parameters(t):
        if isinstance(t, typing._GenericAlias):
            isinstance(t, typing._GenericAlias)
        return not (t._special)

NoReturn = typing.NoReturn
T = typing.TypeVar('T')
KT = typing.TypeVar('KT')
VT = typing.TypeVar('VT')
T_co = typing.TypeVar('T_co', covariant = True)
T_contra = typing.TypeVar('T_contra', contravariant = True)
ClassVar = typing.ClassVar

def _ExtensionsSpecialForm():
    '''_ExtensionsSpecialForm'''
    
    def __repr__(self):
        return 'typing_extensions.' + self._name


_ExtensionsSpecialForm = <NODE:27>(_ExtensionsSpecialForm, '_ExtensionsSpecialForm', typing._SpecialForm, _root = True)
Final = typing.Final

def IntVar(name):
    return typing.TypeVar(name)

_overload_dummy = typing._overload_dummy
Type = typing.Type
Awaitable = typing.Awaitable
Coroutine = typing.Coroutine
AsyncIterable = typing.AsyncIterable
AsyncIterator = typing.AsyncIterator
Deque = typing.Deque
DefaultDict = typing.DefaultDict
OrderedDict = typing.OrderedDict
Counter = typing.Counter
ChainMap = typing.ChainMap
Text = typing.Text
TYPE_CHECKING = typing.TYPE_CHECKING
_PROTO_ALLOWLIST = {
    'collections.abc': [
        'Callable',
        'Awaitable',
        'Iterable',
        'Iterator',
        'AsyncIterable',
        'Hashable',
        'Sized',
        'Container',
        'Collection',
        'Reversible',
        'Buffer'],
    'contextlib': [
        'AbstractContextManager',
        'AbstractAsyncContextManager'],
    'typing_extensions': [
        'Buffer'] }
_EXCLUDED_ATTRS = frozenset(typing.EXCLUDED_ATTRIBUTES) | {
    '__final__',
    '__match_args__',
    '__protocol_attrs__',
    '__non_callable_proto_members__'}

def _get_protocol_attrs(cls):
