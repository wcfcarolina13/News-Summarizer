# Source Generated with Decompyle++
# File: dataclasses.pyc (Python 3.12)

import re
import sys
import copy
import types
import inspect
import keyword
import functools
import itertools
import abc
import _thread
from types import FunctionType, GenericAlias
__all__ = [
    'dataclass',
    'field',
    'Field',
    'FrozenInstanceError',
    'InitVar',
    'KW_ONLY',
    'MISSING',
    'fields',
    'asdict',
    'astuple',
    'make_dataclass',
    'replace',
    'is_dataclass']

class FrozenInstanceError(AttributeError):
    pass


class _HAS_DEFAULT_FACTORY_CLASS:
    
    def __repr__(self):
        return '<factory>'


_HAS_DEFAULT_FACTORY = _HAS_DEFAULT_FACTORY_CLASS()

class _MISSING_TYPE:
    pass

MISSING = _MISSING_TYPE()

class _KW_ONLY_TYPE:
    pass

KW_ONLY = _KW_ONLY_TYPE()
_EMPTY_METADATA = types.MappingProxyType({ })

class _FIELD_BASE:
    
    def __init__(self, name):
        self.name = name

    
    def __repr__(self):
        return self.name


_FIELD = _FIELD_BASE('_FIELD')
_FIELD_CLASSVAR = _FIELD_BASE('_FIELD_CLASSVAR')
_FIELD_INITVAR = _FIELD_BASE('_FIELD_INITVAR')
_FIELDS = '__dataclass_fields__'
_PARAMS = '__dataclass_params__'
_POST_INIT_NAME = '__post_init__'
_MODULE_IDENTIFIER_RE = re.compile('^(?:\\s*(\\w+)\\s*\\.)?\\s*(\\w+)')
_ATOMIC_TYPES = frozenset({
    types.NoneType,
    bool,
    int,
    float,
    str,
    complex,
    bytes,
    types.EllipsisType,
    types.NotImplementedType,
    types.CodeType,
    types.BuiltinFunctionType,
    types.FunctionType,
    type,
    range,
    property})

def _recursive_repr(user_function):
    pass
# WARNING: Decompyle incomplete


class InitVar:
    __slots__ = ('type',)
    
    def __init__(self, type):
        self.type = type

    
    def __repr__(self):
        if isinstance(self.type, type):
            type_name = self.type.__name__
        else:
            type_name = repr(self.type)
        return f'''dataclasses.InitVar[{type_name}]'''

    
    def __class_getitem__(cls, type):
        return InitVar(type)



class Field:
    __slots__ = ('name', 'type', 'default', 'default_factory', 'repr', 'hash', 'init', 'compare', 'metadata', 'kw_only', '_field_type')
    
    def __init__(self, default, default_factory, init, repr, hash, compare, metadata, kw_only):
        self.name = None
        self.type = None
        self.default = default
        self.default_factory = default_factory
        self.init = init
        self.repr = repr
        self.hash = hash
        self.compare = compare
    # WARNING: Decompyle incomplete

    __repr__ = (lambda self: f'''Field(name={self.name!r},type={self.type!r},default={self.default!r},default_factory={self.default_factory!r},init={self.init!r},repr={self.repr!r},hash={self.hash!r},compare={self.compare!r},metadata={self.metadata!r},kw_only={self.kw_only!r},_field_type={self._field_type})''')()
    
    def __set_name__(self, owner, name):
        func = getattr(type(self.default), '__set_name__', None)
        if func:
            func(self.default, owner, name)
            return None

    __class_getitem__ = classmethod(GenericAlias)


class _DataclassParams:
    __slots__ = ('init', 'repr', 'eq', 'order', 'unsafe_hash', 'frozen', 'match_args', 'kw_only', 'slots', 'weakref_slot')
    
    def __init__(self, init, repr, eq, order, unsafe_hash, frozen, match_args, kw_only, slots, weakref_slot):
        self.init = init
        self.repr = repr
        self.eq = eq
        self.order = order
        self.unsafe_hash = unsafe_hash
        self.frozen = frozen
        self.match_args = match_args
        self.kw_only = kw_only
        self.slots = slots
        self.weakref_slot = weakref_slot

    
    def __repr__(self):
        return f'''_DataclassParams(init={self.init!r},repr={self.repr!r},eq={self.eq!r},order={self.order!r},unsafe_hash={self.unsafe_hash!r},frozen={self.frozen!r},match_args={self.match_args!r},kw_only={self.kw_only!r},slots={self.slots!r},weakref_slot={self.weakref_slot!r})'''



def field(*, default, default_factory, init, repr, hash, compare, metadata, kw_only):
    """Return an object to identify dataclass fields.

    default is the default value of the field.  default_factory is a
    0-argument function called to initialize a field's value.  If init
    is true, the field will be a parameter to the class's __init__()
    function.  If repr is true, the field will be included in the
    object's repr().  If hash is true, the field will be included in the
    object's hash().  If compare is true, the field will be used in
    comparison functions.  metadata, if specified, must be a mapping
    which is stored but not otherwise examined by dataclass.  If kw_only
    is true, the field will become a keyword-only parameter to
    __init__().

    It is an error to specify both default and default_factory.
    """
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError('cannot specify both default and default_factory')
    return Field(default, default_factory, init, repr, hash, compare, metadata, kw_only)


def _fields_in_init_order(fields):
    return (tuple, (lambda .0: pass# WARNING: Decompyle incomplete
)(fields()))


def _tuple_str(obj_name, fields):
    if not fields:
        return '()'
# WARNING: Decompyle incomplete


def _create_fn(name, args = None, body = {
    'globals': None,
    'locals': None,
    'return_type': MISSING }, *, globals, locals, return_type):
    pass
# WARNING: Decompyle incomplete


def _field_assign(frozen, name, value, self_name):
    if frozen:
        return f'''__dataclass_builtins_object__.__setattr__({self_name},{name!r},{value})'''
    return f'''{None}.{name}={value}'''


def _field_init(f, frozen, globals, self_name, slots):
    default_name = f'''__dataclass_dflt_{f.name}__'''
    if f.default_factory is not MISSING:
        if f.init:
            globals[default_name] = f.default_factory
            value = f'''{default_name}() if {f.name} is __dataclass_HAS_DEFAULT_FACTORY__ else {f.name}'''
        else:
            globals[default_name] = f.default_factory
            value = f'''{default_name}()'''
    elif f.init:
        if f.default is MISSING:
            value = f.name
        elif f.default is not MISSING:
            globals[default_name] = f.default
            value = f.name
        elif slots and f.default is not MISSING:
            globals[default_name] = f.default
            value = default_name
        else:
            return None
    if f._field_type is _FIELD_INITVAR:
        return None
# WARNING: Decompyle incomplete


def _init_param(f):
    if f.default is MISSING and f.default_factory is MISSING:
        default = ''
    elif f.default is not MISSING:
        default = f'''=__dataclass_dflt_{f.name}__'''
    elif f.default_factory is not MISSING:
        default = '=__dataclass_HAS_DEFAULT_FACTORY__'
# WARNING: Decompyle incomplete


def _init_fn(fields, std_fields, kw_only_fields, frozen, has_post_init, self_name, globals, slots):
    seen_default = False
    for f in std_fields:
        if not f.init:
            continue
        if not f.default is MISSING or f.default_factory is MISSING:
            seen_default = True
            continue
        if not seen_default:
            continue
        raise TypeError(f'''non-default argument {f.name!r} follows default argument''')
# WARNING: Decompyle incomplete


def _repr_fn(fields, globals):
    pass
# WARNING: Decompyle incomplete


def _frozen_get_del_attr(cls, fields, globals):
    locals = {
        'cls': cls,
        'FrozenInstanceError': FrozenInstanceError }
    condition = 'type(self) is cls'
    if fields:
        None += ', '.join + (lambda .0: pass# WARNING: Decompyle incomplete
)(fields()) + '}'
    return (_create_fn('__setattr__', ('self', 'name', 'value'), (f'''if {condition}:''', ' raise FrozenInstanceError(f"cannot assign to field {name!r}")', 'super(cls, self).__setattr__(name, value)'), locals = locals, globals = globals), _create_fn('__delattr__', ('self', 'name'), (f'''if {condition}:''', ' raise FrozenInstanceError(f"cannot delete field {name!r}")', 'super(cls, self).__delattr__(name)'), locals = locals, globals = globals))


def _cmp_fn(name, op, self_tuple, other_tuple, globals):
    return _create_fn(name, ('self', 'other'), [
        'if other.__class__ is self.__class__:',
        f''' return {self_tuple}{op}{other_tuple}''',
        'return NotImplemented'], globals = globals)


def _hash_fn(fields, globals):
    self_tuple = _tuple_str('self', fields)
    return _create_fn('__hash__', ('self',), [
        f'''return hash({self_tuple})'''], globals = globals)


def _is_classvar(a_type, typing):
    if not a_type is typing.ClassVar:
        a_type is typing.ClassVar
        if type(a_type) is typing._GenericAlias:
            type(a_type) is typing._GenericAlias
    return a_type.__origin__ is typing.ClassVar


def _is_initvar(a_type, dataclasses):
    if not a_type is dataclasses.InitVar:
        a_type is dataclasses.InitVar
    return type(a_type) is dataclasses.InitVar


def _is_kw_only(a_type, dataclasses):
    return a_type is dataclasses.KW_ONLY


def _is_type(annotation, cls, a_module, a_type, is_type_predicate):
    match = _MODULE_IDENTIFIER_RE.match(annotation)
    if match:
        ns = None
        module_name = match.group(1)
        if not module_name:
            ns = sys.modules.get(cls.__module__).__dict__
        else:
            module = sys.modules.get(cls.__module__)
            if module and module.__dict__.get(module_name) is a_module:
                ns = sys.modules.get(a_type.__module__).__dict__
        if ns and is_type_predicate(ns.get(match.group(2)), a_module):
            return True
    return False


def _get_field(cls, a_name, a_type, default_kw_only):
    default = getattr(cls, a_name, MISSING)
    if isinstance(default, Field):
        f = default
    elif isinstance(default, types.MemberDescriptorType):
        default = MISSING
    f = field(default = default)
    f.name = a_name
    f.type = a_type
    f._field_type = _FIELD
    typing = sys.modules.get('typing')
    if typing:
        if (_is_classvar(a_type, typing) or isinstance(f.type, str)) and _is_type(f.type, cls, typing, typing.ClassVar, _is_classvar):
            f._field_type = _FIELD_CLASSVAR
    if f._field_type is _FIELD:
        dataclasses = sys.modules[__name__]
        if (_is_initvar(a_type, dataclasses) or isinstance(f.type, str)) and _is_type(f.type, cls, dataclasses, dataclasses.InitVar, _is_initvar):
            f._field_type = _FIELD_INITVAR
    if f._field_type in (_FIELD_CLASSVAR, _FIELD_INITVAR) and f.default_factory is not MISSING:
        raise TypeError(f'''field {f.name} cannot have a default factory''')
    if f._field_type in (_FIELD, _FIELD_INITVAR) or f.kw_only is MISSING:
        f.kw_only = default_kw_only
# WARNING: Decompyle incomplete


def _set_qualname(cls, value):
    if isinstance(value, FunctionType):
        value.__qualname__ = f'''{cls.__qualname__}.{value.__name__}'''
    return value


def _set_new_attribute(cls, name, value):
    if name in cls.__dict__:
        return True
    _set_qualname(cls, value)
    setattr(cls, name, value)
    return False


def _hash_set_none(cls, fields, globals):
    pass


def _hash_add(cls, fields, globals):
    pass
# WARNING: Decompyle incomplete


def _hash_exception(cls, fields, globals):
    raise TypeError(f'''Cannot overwrite attribute __hash__ in class {cls.__name__}''')

# WARNING: Decompyle incomplete
