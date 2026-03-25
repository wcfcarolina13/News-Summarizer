# Source Generated with Decompyle++
# File: inspect.pyc (Python 3.12)

"""Get useful information from live Python objects.

This module encapsulates the interface provided by the internal special
attributes (co_*, im_*, tb_*, etc.) in a friendlier fashion.
It also provides some help for examining source code and class layout.

Here are some of the useful functions provided by this module:

    ismodule(), isclass(), ismethod(), isfunction(), isgeneratorfunction(),
        isgenerator(), istraceback(), isframe(), iscode(), isbuiltin(),
        isroutine() - check object types
    getmembers() - get members of an object that satisfy a given condition

    getfile(), getsourcefile(), getsource() - find an object's source code
    getdoc(), getcomments() - get documentation on an object
    getmodule() - determine the module that an object came from
    getclasstree() - arrange classes so as to represent their hierarchy

    getargvalues(), getcallargs() - get info about function arguments
    getfullargspec() - same, with support for Python 3 features
    formatargvalues() - format an argument spec
    getouterframes(), getinnerframes() - get info about frames
    currentframe() - get the current stack frame
    stack(), trace() - get info about frames on the stack or in a traceback

    signature() - get a Signature object for the callable

    get_annotations() - safely compute an object's annotations
"""
__author__ = ('Ka-Ping Yee <ping@lfw.org>', 'Yury Selivanov <yselivanov@sprymix.com>')
__all__ = [
    'AGEN_CLOSED',
    'AGEN_CREATED',
    'AGEN_RUNNING',
    'AGEN_SUSPENDED',
    'ArgInfo',
    'Arguments',
    'Attribute',
    'BlockFinder',
    'BoundArguments',
    'BufferFlags',
    'CORO_CLOSED',
    'CORO_CREATED',
    'CORO_RUNNING',
    'CORO_SUSPENDED',
    'CO_ASYNC_GENERATOR',
    'CO_COROUTINE',
    'CO_GENERATOR',
    'CO_ITERABLE_COROUTINE',
    'CO_NESTED',
    'CO_NEWLOCALS',
    'CO_NOFREE',
    'CO_OPTIMIZED',
    'CO_VARARGS',
    'CO_VARKEYWORDS',
    'ClassFoundException',
    'ClosureVars',
    'EndOfBlock',
    'FrameInfo',
    'FullArgSpec',
    'GEN_CLOSED',
    'GEN_CREATED',
    'GEN_RUNNING',
    'GEN_SUSPENDED',
    'Parameter',
    'Signature',
    'TPFLAGS_IS_ABSTRACT',
    'Traceback',
    'classify_class_attrs',
    'cleandoc',
    'currentframe',
    'findsource',
    'formatannotation',
    'formatannotationrelativeto',
    'formatargvalues',
    'get_annotations',
    'getabsfile',
    'getargs',
    'getargvalues',
    'getasyncgenlocals',
    'getasyncgenstate',
    'getattr_static',
    'getblock',
    'getcallargs',
    'getclasstree',
    'getclosurevars',
    'getcomments',
    'getcoroutinelocals',
    'getcoroutinestate',
    'getdoc',
    'getfile',
    'getframeinfo',
    'getfullargspec',
    'getgeneratorlocals',
    'getgeneratorstate',
    'getinnerframes',
    'getlineno',
    'getmembers',
    'getmembers_static',
    'getmodule',
    'getmodulename',
    'getmro',
    'getouterframes',
    'getsource',
    'getsourcefile',
    'getsourcelines',
    'indentsize',
    'isabstract',
    'isasyncgen',
    'isasyncgenfunction',
    'isawaitable',
    'isbuiltin',
    'isclass',
    'iscode',
    'iscoroutine',
    'iscoroutinefunction',
    'isdatadescriptor',
    'isframe',
    'isfunction',
    'isgenerator',
    'isgeneratorfunction',
    'isgetsetdescriptor',
    'ismemberdescriptor',
    'ismethod',
    'ismethoddescriptor',
    'ismethodwrapper',
    'ismodule',
    'isroutine',
    'istraceback',
    'markcoroutinefunction',
    'signature',
    'stack',
    'trace',
    'unwrap',
    'walktree']
import abc
import ast
import dis
import collections.abc as collections
import enum
import importlib.machinery as importlib
import itertools
import linecache
import os
import re
import sys
import tokenize
import token
import types
import functools
import builtins
from keyword import iskeyword
from operator import attrgetter
from collections import namedtuple, OrderedDict
mod_dict = globals()
for k, v in dis.COMPILER_FLAG_NAMES.items():
    mod_dict['CO_' + v] = k
del k
del v
del mod_dict
TPFLAGS_IS_ABSTRACT = 1048576

def get_annotations(obj = None, *, globals, locals, eval_str):
    '''Compute the annotations dict for an object.

    obj may be a callable, class, or module.
    Passing in an object of any other type raises TypeError.

    Returns a dict.  get_annotations() returns a new dict every time
    it\'s called; calling it twice on the same object will return two
    different but equivalent dicts.

    This function handles several details for you:

      * If eval_str is true, values of type str will
        be un-stringized using eval().  This is intended
        for use with stringized annotations
        ("from __future__ import annotations").
      * If obj doesn\'t have an annotations dict, returns an
        empty dict.  (Functions and methods always have an
        annotations dict; classes, modules, and other types of
        callables may not.)
      * Ignores inherited annotations on classes.  If a class
        doesn\'t have its own annotations dict, returns an empty dict.
      * All accesses to object members and dict values are done
        using getattr() and dict.get() for safety.
      * Always, always, always returns a freshly-created dict.

    eval_str controls whether or not values of type str are replaced
    with the result of calling eval() on those values:

      * If eval_str is true, eval() is called on values of type str.
      * If eval_str is false (the default), values of type str are unchanged.

    globals and locals are passed in to eval(); see the documentation
    for eval() for more information.  If either globals or locals is
    None, this function may replace that value with a context-specific
    default, contingent on type(obj):

      * If obj is a module, globals defaults to obj.__dict__.
      * If obj is a class, globals defaults to
        sys.modules[obj.__module__].__dict__ and locals
        defaults to the obj class namespace.
      * If obj is a callable, globals defaults to obj.__globals__,
        although if obj is a wrapped function (using
        functools.update_wrapper()) it is first unwrapped.
    '''
    if isinstance(obj, type):
        obj_dict = getattr(obj, '__dict__', None)
        if obj_dict and hasattr(obj_dict, 'get'):
            ann = obj_dict.get('__annotations__', None)
            if isinstance(ann, types.GetSetDescriptorType):
                ann = None
            else:
                ann = None
        obj_globals = None
        module_name = getattr(obj, '__module__', None)
        if module_name:
            module = sys.modules.get(module_name, None)
            if module:
                obj_globals = getattr(module, '__dict__', None)
        obj_locals = dict(vars(obj))
        unwrap = obj
    elif isinstance(obj, types.ModuleType):
        ann = getattr(obj, '__annotations__', None)
        obj_globals = getattr(obj, '__dict__')
        obj_locals = None
        unwrap = None
    elif callable(obj):
        ann = getattr(obj, '__annotations__', None)
        obj_globals = getattr(obj, '__globals__', None)
        obj_locals = None
        unwrap = obj
    else:
        raise TypeError(f'''{obj!r} is not a module, class, or callable.''')
# WARNING: Decompyle incomplete


def ismodule(object):
    '''Return true if the object is a module.'''
    return isinstance(object, types.ModuleType)


def isclass(object):
    '''Return true if the object is a class.'''
    return isinstance(object, type)


def ismethod(object):
    '''Return true if the object is an instance method.'''
    return isinstance(object, types.MethodType)


def ismethoddescriptor(object):
    '''Return true if the object is a method descriptor.

    But not if ismethod() or isclass() or isfunction() are true.

    This is new in Python 2.2, and, for example, is true of int.__add__.
    An object passing this test has a __get__ attribute but not a __set__
    attribute, but beyond that the set of attributes varies.  __name__ is
    usually sensible, and __doc__ often is.

    Methods implemented via descriptors that also pass one of the other
    tests return false from the ismethoddescriptor() test, simply because
    the other tests promise more -- you can, e.g., count on having the
    __func__ attribute (etc) when an object passes ismethod().'''
    if isclass(object) and ismethod(object) or isfunction(object):
        return False
    tp = type(object)
    if hasattr(tp, '__get__'):
        hasattr(tp, '__get__')
    return not hasattr(tp, '__set__')


def isdatadescriptor(object):
    '''Return true if the object is a data descriptor.

    Data descriptors have a __set__ or a __delete__ attribute.  Examples are
    properties (defined in Python) and getsets and members (defined in C).
    Typically, data descriptors will also have __name__ and __doc__ attributes
    (properties, getsets, and members have both of these attributes), but this
    is not guaranteed.'''
    if isclass(object) and ismethod(object) or isfunction(object):
        return False
    tp = type(object)
    if not hasattr(tp, '__set__'):
        hasattr(tp, '__set__')
    return hasattr(tp, '__delete__')

if hasattr(types, 'MemberDescriptorType'):
    
    def ismemberdescriptor(object):
        '''Return true if the object is a member descriptor.

        Member descriptors are specialized descriptors defined in extension
        modules.'''
        return isinstance(object, types.MemberDescriptorType)

else:
    
    def ismemberdescriptor(object):
        '''Return true if the object is a member descriptor.

        Member descriptors are specialized descriptors defined in extension
        modules.'''
        return False

if hasattr(types, 'GetSetDescriptorType'):
    
    def isgetsetdescriptor(object):
        '''Return true if the object is a getset descriptor.

        getset descriptors are specialized descriptors defined in extension
        modules.'''
        return isinstance(object, types.GetSetDescriptorType)

else:
    
    def isgetsetdescriptor(object):
        '''Return true if the object is a getset descriptor.

        getset descriptors are specialized descriptors defined in extension
        modules.'''
        return False


def isfunction(object):
    '''Return true if the object is a user-defined function.

    Function objects provide these attributes:
        __doc__         documentation string
        __name__        name with which this function was defined
        __code__        code object containing compiled function bytecode
        __defaults__    tuple of any default values for arguments
        __globals__     global namespace in which this function was defined
        __annotations__ dict of parameter annotations
        __kwdefaults__  dict of keyword only parameters with defaults'''
    return isinstance(object, types.FunctionType)


def _has_code_flag(f, flag):
    '''Return true if ``f`` is a function (or a method or functools.partial
    wrapper wrapping a function) whose code object has the given ``flag``
    set in its flags.'''
    if ismethod(f):
        f = f.__func__
        if ismethod(f):
            continue
    f = functools._unwrap_partial(f)
    if not isfunction(f) and _signature_is_functionlike(f):
        return False
    return bool(f.__code__.co_flags & flag)


def isgeneratorfunction(obj):
    '''Return true if the object is a user-defined generator function.

    Generator function objects provide the same attributes as functions.
    See help(isfunction) for a list of attributes.'''
    return _has_code_flag(obj, CO_GENERATOR)

_is_coroutine_marker = object()

def _has_coroutine_mark(f):
    if ismethod(f):
        f = f.__func__
        if ismethod(f):
            continue
    f = functools._unwrap_partial(f)
    return getattr(f, '_is_coroutine_marker', None) is _is_coroutine_marker


def markcoroutinefunction(func):
    '''
    Decorator to ensure callable is recognised as a coroutine function.
    '''
    if hasattr(func, '__func__'):
        func = func.__func__
    func._is_coroutine_marker = _is_coroutine_marker
    return func


def iscoroutinefunction(obj):
    '''Return true if the object is a coroutine function.

    Coroutine functions are normally defined with "async def" syntax, but may
    be marked via markcoroutinefunction.
    '''
    if not _has_code_flag(obj, CO_COROUTINE):
        _has_code_flag(obj, CO_COROUTINE)
    return _has_coroutine_mark(obj)


def isasyncgenfunction(obj):
    '''Return true if the object is an asynchronous generator function.

    Asynchronous generator functions are defined with "async def"
    syntax and have "yield" expressions in their body.
    '''
    return _has_code_flag(obj, CO_ASYNC_GENERATOR)


def isasyncgen(object):
    '''Return true if the object is an asynchronous generator.'''
    return isinstance(object, types.AsyncGeneratorType)


def isgenerator(object):
    '''Return true if the object is a generator.

    Generator objects provide these attributes:
        __iter__        defined to support iteration over container
        close           raises a new GeneratorExit exception inside the
                        generator to terminate the iteration
        gi_code         code object
        gi_frame        frame object or possibly None once the generator has
                        been exhausted
        gi_running      set to 1 when generator is executing, 0 otherwise
        next            return the next item from the container
        send            resumes the generator and "sends" a value that becomes
                        the result of the current yield-expression
        throw           used to raise an exception inside the generator'''
    return isinstance(object, types.GeneratorType)


def iscoroutine(object):
    '''Return true if the object is a coroutine.'''
    return isinstance(object, types.CoroutineType)


def isawaitable(object):
    '''Return true if object can be passed to an ``await`` expression.'''
    if not isinstance(object, types.CoroutineType):
        isinstance(object, types.CoroutineType)
        if isinstance(object, types.GeneratorType):
            isinstance(object, types.GeneratorType)
        if not bool(object.gi_code.co_flags & CO_ITERABLE_COROUTINE):
            bool(object.gi_code.co_flags & CO_ITERABLE_COROUTINE)
    return isinstance(object, collections.abc.Awaitable)


def istraceback(object):
    '''Return true if the object is a traceback.

    Traceback objects provide these attributes:
        tb_frame        frame object at this level
        tb_lasti        index of last attempted instruction in bytecode
        tb_lineno       current line number in Python source code
        tb_next         next inner traceback object (called by this level)'''
    return isinstance(object, types.TracebackType)


def isframe(object):
    """Return true if the object is a frame object.

    Frame objects provide these attributes:
        f_back          next outer frame object (this frame's caller)
        f_builtins      built-in namespace seen by this frame
        f_code          code object being executed in this frame
        f_globals       global namespace seen by this frame
        f_lasti         index of last attempted instruction in bytecode
        f_lineno        current line number in Python source code
        f_locals        local namespace seen by this frame
        f_trace         tracing function for this frame, or None"""
    return isinstance(object, types.FrameType)


def iscode(object):
    '''Return true if the object is a code object.

    Code objects provide these attributes:
        co_argcount         number of arguments (not including *, ** args
                            or keyword only arguments)
        co_code             string of raw compiled bytecode
        co_cellvars         tuple of names of cell variables
        co_consts           tuple of constants used in the bytecode
        co_filename         name of file in which this code object was created
        co_firstlineno      number of first line in Python source code
        co_flags            bitmap: 1=optimized | 2=newlocals | 4=*arg | 8=**arg
                            | 16=nested | 32=generator | 64=nofree | 128=coroutine
                            | 256=iterable_coroutine | 512=async_generator
        co_freevars         tuple of names of free variables
        co_posonlyargcount  number of positional only arguments
        co_kwonlyargcount   number of keyword only arguments (not including ** arg)
        co_lnotab           encoded mapping of line numbers to bytecode indices
        co_name             name with which this code object was defined
        co_names            tuple of names other than arguments and function locals
        co_nlocals          number of local variables
        co_stacksize        virtual machine stack space required
        co_varnames         tuple of names of arguments and local variables'''
    return isinstance(object, types.CodeType)


def isbuiltin(object):
    '''Return true if the object is a built-in function or method.

    Built-in functions and methods provide these attributes:
        __doc__         documentation string
        __name__        original name of this function or method
        __self__        instance to which a method is bound, or None'''
    return isinstance(object, types.BuiltinFunctionType)


def ismethodwrapper(object):
    '''Return true if the object is a method wrapper.'''
    return isinstance(object, types.MethodWrapperType)


def isroutine(object):
    '''Return true if the object is any kind of function or method.'''
    if not isbuiltin(object):
        isbuiltin(object)
        if not isfunction(object):
            isfunction(object)
            if not ismethod(object):
                ismethod(object)
                if not ismethoddescriptor(object):
                    ismethoddescriptor(object)
    return ismethodwrapper(object)


def isabstract(object):
    '''Return true if the object is an abstract base class (ABC).'''
    if not isinstance(object, type):
        return False
    if object.__flags__ & TPFLAGS_IS_ABSTRACT:
        return True
    if not issubclass(type(object), abc.ABCMeta):
        return False
    if hasattr(object, '__abstractmethods__'):
        return False
    for name, value in object.__dict__.items():
        if not getattr(value, '__isabstractmethod__', False):
            continue
        object.__dict__.items()
        return True
    for base in object.__bases__:
        for name in getattr(base, '__abstractmethods__', ()):
            value = getattr(object, name, None)
            if not getattr(value, '__isabstractmethod__', False):
                continue
            getattr(base, '__abstractmethods__', ())
            object.__bases__
            return True
    return False


def _getmembers(object, predicate, getter):
    results = []
    processed = set()
    names = dir(object)
    if isclass(object):
        mro = getmro(object)
        for base in object.__bases__:
            for k, v in base.__dict__.items():
                if not isinstance(v, types.DynamicClassAttribute):
                    continue
                names.append(k)
    else:
        mro = ()
    for key in names:
        value = getter(object, key)
        if key in processed:
            raise AttributeError
        if predicate or predicate(value):
            results.append((key, value))
        processed.add(key)
    results.sort(key = (lambda pair: pair[0]))
    return results
# WARNING: Decompyle incomplete


def getmembers(object, predicate = (None,)):
    '''Return all members of an object as (name, value) pairs sorted by name.
    Optionally, only return members that satisfy a given predicate.'''
    return _getmembers(object, predicate, getattr)


def getmembers_static(object, predicate = (None,)):
    """Return all members of an object as (name, value) pairs sorted by name
    without triggering dynamic lookup via the descriptor protocol,
    __getattr__ or __getattribute__. Optionally, only return members that
    satisfy a given predicate.

    Note: this function may not be able to retrieve all members
       that getmembers can fetch (like dynamically created attributes)
       and may find members that getmembers can't (like descriptors
       that raise AttributeError). It can also return descriptor objects
       instead of instance members in some cases.
    """
    return _getmembers(object, predicate, getattr_static)

Attribute = namedtuple('Attribute', 'name kind defining_class object')

def classify_class_attrs(cls):
    """Return list of attribute-descriptor tuples.

    For each name in dir(cls), the return list contains a 4-tuple
    with these elements:

        0. The name (a string).

        1. The kind of attribute this is, one of these strings:
               'class method'    created via classmethod()
               'static method'   created via staticmethod()
               'property'        created via property()
               'method'          any other flavor of method or descriptor
               'data'            not a method

        2. The class which defined this attribute (a class).

        3. The object as obtained by calling getattr; if this fails, or if the
           resulting object does not live anywhere in the class' mro (including
           metaclasses) then the object is looked up in the defining class's
           dict (found by walking the mro).

    If one of the items in dir(cls) is stored in the metaclass it will now
    be discovered and not have None be listed as the class in which it was
    defined.  Any items whose home class cannot be discovered are skipped.
    """
    mro = getmro(cls)
    metamro = getmro(type(cls))
    metamro = (lambda .0: pass# WARNING: Decompyle incomplete
)(metamro())
    class_bases = (cls,) + mro
    all_bases = class_bases + metamro
    names = dir(cls)
# WARNING: Decompyle incomplete


def getmro(cls):
    '''Return tuple of base classes (including cls) in method resolution order.'''
    return cls.__mro__


def unwrap(func = None, *, stop):
    '''Get the object wrapped by *func*.

   Follows the chain of :attr:`__wrapped__` attributes returning the last
   object in the chain.

   *stop* is an optional callback accepting an object in the wrapper chain
   as its sole argument that allows the unwrapping to be terminated early if
   the callback returns a true value. If the callback never returns a true
   value, the last object in the chain is returned as usual. For example,
   :func:`signature` uses this to stop unwrapping if any object in the
   chain has a ``__signature__`` attribute defined.

   :exc:`ValueError` is raised if a cycle is encountered.

    '''
    pass
# WARNING: Decompyle incomplete


def indentsize(line):
    '''Return the indent size, in spaces, at the start of a line of text.'''
    expline = line.expandtabs()
    return len(expline) - len(expline.lstrip())


def _findclass(func):
    cls = sys.modules.get(func.__module__)
# WARNING: Decompyle incomplete


def _finddoc(obj):
    pass
# WARNING: Decompyle incomplete


def getdoc(object):
    '''Get the documentation string for an object.

    All tabs are expanded to spaces.  To clean up docstrings that are
    indented to line up with blocks of code, any whitespace than can be
    uniformly removed from the second line onwards is removed.'''
    doc = object.__doc__
# WARNING: Decompyle incomplete


def cleandoc(doc):
    '''Clean up indentation from docstrings.

    Any whitespace that can be uniformly removed from the second line
    onwards is removed.'''
    lines = doc.expandtabs().split('\n')
    margin = sys.maxsize
    for line in lines[1:]:
        content = len(line.lstrip())
        if not content:
            continue
        indent = len(line) - content
        margin = min(margin, indent)
    if lines:
        lines[0] = lines[0].lstrip()
    if margin < sys.maxsize:
        for i in range(1, len(lines)):
            lines[i] = lines[i][margin:]
    if not lines and lines[-1]:
        lines.pop()
        if not lines and lines[-1]:
            continue
    if not lines and lines[0]:
        lines.pop(0)
        if not lines and lines[0]:
            continue
    return '\n'.join(lines)
# WARNING: Decompyle incomplete


def getfile(object):
    '''Work out which source or compiled file an object was defined in.'''
    if ismodule(object):
        if getattr(object, '__file__', None):
            return object.__file__
        raise None('{!r} is a built-in module'.format(object))
    if isclass(object):
        if hasattr(object, '__module__'):
            module = sys.modules.get(object.__module__)
            if getattr(module, '__file__', None):
                return module.__file__
            if None.__module__ == '__main__':
                raise OSError('source code not available')
        raise TypeError('{!r} is a built-in class'.format(object))
    if ismethod(object):
        object = object.__func__
    if isfunction(object):
        object = object.__code__
    if istraceback(object):
        object = object.tb_frame
    if isframe(object):
        object = object.f_code
    if iscode(object):
        return object.co_filename
    raise None('module, class, method, function, traceback, frame, or code object was expected, got {}'.format(type(object).__name__))


def getmodulename(path):
    '''Return the module name for a given file, or None.'''
    fname = os.path.basename(path)
# WARNING: Decompyle incomplete


def getsourcefile(object):
    """Return the filename that can be used to locate an object's source.
    Return None if no way can be identified to get the source.
    """
    pass
# WARNING: Decompyle incomplete


def getabsfile(object, _filename = (None,)):
    '''Return an absolute path to the source or compiled file for an object.

    The idea is for each object to have a unique origin, so this routine
    normalizes the result as much as possible.'''
    pass
# WARNING: Decompyle incomplete

modulesbyfile = { }
_filesbymodname = { }

def getmodule(object, _filename = (None,)):
    '''Return the module an object was defined in, or None if not found.'''
    if ismodule(object):
        return object
    if None(object, '__module__'):
        return sys.modules.get(object.__module__)
# WARNING: Decompyle incomplete


class ClassFoundException(Exception):
    pass


class _ClassFinder(ast.NodeVisitor):
    
    def __init__(self, qualname):
        self.stack = []
        self.qualname = qualname

    
    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.stack.append('<locals>')
        self.generic_visit(node)
        self.stack.pop()
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef
    
    def visit_ClassDef(self, node):
        self.stack.append(node.name)
        if self.qualname == '.'.join(self.stack):
            if node.decorator_list:
                line_number = node.decorator_list[0].lineno
            else:
                line_number = node.lineno
            line_number -= 1
            raise ClassFoundException(line_number)
        self.generic_visit(node)
        self.stack.pop()



def findsource(object):
    '''Return the entire source file and starting line number for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a list of all the lines
    in the file and the line number indexes a line in that list.  An OSError
    is raised if the source code cannot be retrieved.'''
    file = getsourcefile(object)
    if file:
        linecache.checkcache(file)
    else:
        file = getfile(object)
        if not file.startswith('<') or file.endswith('>'):
            raise OSError('source code not available')
    module = getmodule(object, file)
    if module:
        lines = linecache.getlines(file, module.__dict__)
    else:
        lines = linecache.getlines(file)
    if not lines:
        raise OSError('could not get source code')
    if ismodule(object):
        return (lines, 0)
    if None(object):
        qualname = object.__qualname__
        source = ''.join(lines)
        tree = ast.parse(source)
        class_finder = _ClassFinder(qualname)
        class_finder.visit(tree)
        raise OSError('could not find class definition')
    if ismethod(object):
        object = object.__func__
    if isfunction(object):
        object = object.__code__
    if istraceback(object):
        object = object.tb_frame
    if isframe(object):
        object = object.f_code
    if iscode(object):
        if not hasattr(object, 'co_firstlineno'):
            raise OSError('could not find function definition')
        lnum = object.co_firstlineno - 1
        pat = re.compile('^(\\s*def\\s)|(\\s*async\\s+def\\s)|(.*(?<!\\w)lambda(:|\\s))|^(\\s*@)')
        if lnum > 0:
            line = lines[lnum]
            if pat.match(line):
                return (lines, lnum)
            lnum = None - 1
            if lnum > 0:
                continue
        return (lines, lnum)
    raise None('could not find code object')
# WARNING: Decompyle incomplete


def getcomments(object):
    """Get lines of comments immediately preceding an object's source code.

    Returns None when source can't be found.
    """
    (lines, lnum) = findsource(object)
    if ismodule(object):
        start = 0
        if lines and lines[0][:2] == '#!':
            start = 1
        if start < len(lines) and lines[start].strip() in ('', '#'):
            start = start + 1
            if start < len(lines) and lines[start].strip() in ('', '#'):
                continue
        if start < len(lines):
            if lines[start][:1] == '#':
                comments = []
                end = start
                if end < len(lines) and lines[end][:1] == '#':
                    comments.append(lines[end].expandtabs())
                    end = end + 1
                    if end < len(lines) and lines[end][:1] == '#':
                        continue
                return ''.join(comments)
        return None
    if lnum > 0:
        indent = indentsize(lines[lnum])
        end = lnum - 1
        if end >= 0:
            if lines[end].lstrip()[:1] == '#':
                if indentsize(lines[end]) == indent:
                    comments = [
                        lines[end].expandtabs().lstrip()]
                    if end > 0:
                        end = end - 1
                        comment = lines[end].expandtabs().lstrip()
                        if comment[:1] == '#' and indentsize(lines[end]) == indent:
                            comments[:0] = [
                                comment]
                            end = end - 1
                            if end < 0:
                                pass
                            else:
                                comment = lines[end].expandtabs().lstrip()
                                if comment[:1] == '#' and indentsize(lines[end]) == indent:
                                    continue
                    if comments and comments[0].strip() == '#':
                        comments[:1] = []
                        if comments and comments[0].strip() == '#':
                            continue
                    if comments and comments[-1].strip() == '#':
                        comments[-1:] = []
                        if comments and comments[-1].strip() == '#':
                            continue
                    return ''.join(comments)
            return None
        return None
    return None
# WARNING: Decompyle incomplete


class EndOfBlock(Exception):
    pass


class BlockFinder:
    '''Provide a tokeneater() method to detect the end of a code block.'''
    
    def __init__(self):
        self.indent = 0
        self.islambda = False
        self.started = False
        self.passline = False
        self.indecorator = False
        self.last = 1
        self.body_col0 = None

    
    def tokeneater(self, type, token, srowcol, erowcol, line):
        if not self.started and self.indecorator:
            if token == '@':
                self.indecorator = True
                self.passline = True
                return None
            if token in ('def', 'class', 'lambda'):
                if token == 'lambda':
                    self.islambda = True
                self.started = True
            self.passline = True
            return None
        if type == tokenize.NEWLINE:
            self.passline = False
            self.last = srowcol[0]
            if self.islambda:
                raise EndOfBlock
            if self.indecorator:
                self.indecorator = False
                return None
            return None
        if self.passline:
            return None
    # WARNING: Decompyle incomplete



def getblock(lines):
    '''Extract the block of code at the top of the given list of lines.'''
    blockfinder = BlockFinder()
    tokens = tokenize.generate_tokens(iter(lines).__next__)
# WARNING: Decompyle incomplete


def getsourcelines(object):
    '''Return a list of source lines and starting line number for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a list of the lines
    corresponding to the object and the line number indicates where in the
    original source file the first line of code was found.  An OSError is
    raised if the source code cannot be retrieved.'''
    object = unwrap(object)
    (lines, lnum) = findsource(object)
    if istraceback(object):
        object = object.tb_frame
    if (ismodule(object) or isframe(object)) and object.f_code.co_name == '<module>':
        return (lines, 0)
    return (None(lines[lnum:]), lnum + 1)


def getsource(object):
    '''Return the text of the source code for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a single string.  An
    OSError is raised if the source code cannot be retrieved.'''
    (lines, lnum) = getsourcelines(object)
    return ''.join(lines)


def walktree(classes, children, parent):
    '''Recursive helper function for getclasstree().'''
    results = []
    classes.sort(key = attrgetter('__module__', '__name__'))
    for c in classes:
        results.append((c, c.__bases__))
        if not c in children:
            continue
        results.append(walktree(children[c], children, c))
    return results


def getclasstree(classes, unique = (False,)):
    """Arrange the given list of classes into a hierarchy of nested lists.

    Where a nested list appears, it contains classes derived from the class
    whose entry immediately precedes the list.  Each entry is a 2-tuple
    containing a class and a tuple of its base classes.  If the 'unique'
    argument is true, exactly one entry appears in the returned structure
    for each class in the given list.  Otherwise, classes using multiple
    inheritance and their descendants will appear multiple times."""
    children = { }
    roots = []
    for c in classes:
        if c.__bases__:
            for parent in c.__bases__:
                if parent not in children:
                    children[parent] = []
                if c not in children[parent]:
                    children[parent].append(c)
                if not unique:
                    continue
                if not parent in classes:
                    continue
                c.__bases__
            continue
        if not c not in roots:
            continue
        roots.append(c)
    for parent in children:
        if not parent not in classes:
            continue
        roots.append(parent)
    return walktree(roots, children, None)

Arguments = namedtuple('Arguments', 'args, varargs, varkw')

def getargs(co):
    """Get information about the arguments accepted by a code object.

    Three things are returned: (args, varargs, varkw), where
    'args' is the list of argument names. Keyword-only arguments are
    appended. 'varargs' and 'varkw' are the names of the * and **
    arguments or None."""
    if not iscode(co):
        raise TypeError('{!r} is not a code object'.format(co))
    names = co.co_varnames
    nargs = co.co_argcount
    nkwargs = co.co_kwonlyargcount
    args = list(names[:nargs])
    kwonlyargs = list(names[nargs:nargs + nkwargs])
    nargs += nkwargs
    varargs = None
    if co.co_flags & CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs = nargs + 1
    varkw = None
    if co.co_flags & CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]
    return Arguments(args + kwonlyargs, varargs, varkw)

FullArgSpec = namedtuple('FullArgSpec', 'args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations')

def getfullargspec(func):
    '''Get the names and default values of a callable object\'s parameters.

    A tuple of seven things is returned:
    (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations).
    \'args\' is a list of the parameter names.
    \'varargs\' and \'varkw\' are the names of the * and ** parameters or None.
    \'defaults\' is an n-tuple of the default values of the last n parameters.
    \'kwonlyargs\' is a list of keyword-only parameter names.
    \'kwonlydefaults\' is a dictionary mapping names from kwonlyargs to defaults.
    \'annotations\' is a dictionary mapping parameter names to annotations.

    Notable differences from inspect.signature():
      - the "self" parameter is always reported, even for bound methods
      - wrapper chains defined by __wrapped__ *not* unwrapped automatically
    '''
    sig = _signature_from_callable(func, follow_wrapper_chains = False, skip_bound_arg = False, sigcls = Signature, eval_str = False)
    args = []
    varargs = None
    varkw = None
    posonlyargs = []
    kwonlyargs = []
    annotations = { }
    defaults = ()
    kwdefaults = { }
    if sig.return_annotation is not sig.empty:
        annotations['return'] = sig.return_annotation
    for param in sig.parameters.values():
        kind = param.kind
        name = param.name
        if kind is _POSITIONAL_ONLY:
            posonlyargs.append(name)
            if param.default is not param.empty:
                defaults += (param.default,)
            elif kind is _POSITIONAL_OR_KEYWORD:
                args.append(name)
                if param.default is not param.empty:
                    defaults += (param.default,)
                elif kind is _VAR_POSITIONAL:
                    varargs = name
                elif kind is _KEYWORD_ONLY:
                    kwonlyargs.append(name)
                    if param.default is not param.empty:
                        kwdefaults[name] = param.default
                    elif kind is _VAR_KEYWORD:
                        varkw = name
        if not param.annotation is not param.empty:
            continue
        annotations[name] = param.annotation
    if not kwdefaults:
        kwdefaults = None
    if not defaults:
        defaults = None
    return FullArgSpec(posonlyargs + args, varargs, varkw, defaults, kwonlyargs, kwdefaults, annotations)
# WARNING: Decompyle incomplete

ArgInfo = namedtuple('ArgInfo', 'args varargs keywords locals')

def getargvalues(frame):
    """Get information about arguments passed into a particular frame.

    A tuple of four things is returned: (args, varargs, varkw, locals).
    'args' is a list of the argument names.
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'locals' is the locals dictionary of the given frame."""
    (args, varargs, varkw) = getargs(frame.f_code)
    return ArgInfo(args, varargs, varkw, frame.f_locals)


def formatannotation(annotation, base_module = (None,)):
    if getattr(annotation, '__module__', None) == 'typing':
        
        def repl(match):
            text = match.group()
            return text.removeprefix('typing.')

        return re.sub('[\\w\\.]+', repl, repr(annotation))
    if None(annotation, types.GenericAlias):
        return str(annotation)
    if None(annotation, type):
        if annotation.__module__ in ('builtins', base_module):
            return annotation.__qualname__
        return None.__module__ + '.' + annotation.__qualname__
    return None(annotation)


def formatannotationrelativeto(object):
    pass
# WARNING: Decompyle incomplete


def formatargvalues(args, varargs, varkw, locals, formatarg, formatvarargs, formatvarkw, formatvalue = (str, (lambda name: '*' + name), (lambda name: '**' + name), (lambda value: '=' + repr(value)))):
    '''Format an argument spec from the 4 values returned by getargvalues.

    The first four arguments are (args, varargs, varkw, locals).  The
    next four arguments are the corresponding optional formatting functions
    that are called to turn names and values into strings.  The ninth
    argument is an optional function to format the sequence of arguments.'''
    
    def convert(name, locals, formatarg, formatvalue = (locals, formatarg, formatvalue)):
        return formatarg(name) + formatvalue(locals[name])

    specs = []
    for i in range(len(args)):
        specs.append(convert(args[i]))
    if varargs:
        specs.append(formatvarargs(varargs) + formatvalue(locals[varargs]))
    if varkw:
        specs.append(formatvarkw(varkw) + formatvalue(locals[varkw]))
    return '(' + ', '.join(specs) + ')'


def _missing_arguments(f_name, argnames, pos, values):
    pass
# WARNING: Decompyle incomplete


def _too_many(f_name, args, kwonly, varargs, defcount, given, values):
    atleast = len(args) - defcount
# WARNING: Decompyle incomplete


def getcallargs(func, *positional, **named):
    """Get the mapping of arguments to values.

    A dict is returned, with keys the function argument names (including the
    names of the * and ** arguments, if any), and values the respective bound
    values from 'positional' and 'named'."""
    spec = getfullargspec(func)
    (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, ann) = spec
    f_name = func.__name__
    arg2value = { }
# WARNING: Decompyle incomplete

ClosureVars = namedtuple('ClosureVars', 'nonlocals globals builtins unbound')

def getclosurevars(func):
    '''
    Get the mapping of free variables to their current values.

    Returns a named tuple of dicts mapping the current nonlocal, global
    and builtin references as seen by the body of the function. A final
    set of unbound names that could not be resolved is also provided.
    '''
    if ismethod(func):
        func = func.__func__
    if not isfunction(func):
        raise TypeError('{!r} is not a Python function'.format(func))
    code = func.__code__
# WARNING: Decompyle incomplete

_Traceback = namedtuple('_Traceback', 'filename lineno function code_context index')

class Traceback(_Traceback):
    pass
# WARNING: Decompyle incomplete


def _get_code_position_from_tb(tb):
    instruction_index = tb.tb_lasti
    code = tb.tb_frame.f_code
    return _get_code_position(code, instruction_index)


def _get_code_position(code, instruction_index):
    if instruction_index < 0:
        return (None, None, None, None)
    positions_gen = code.co_positions()
    return next(itertools.islice(positions_gen, instruction_index // 2, None))


def getframeinfo(frame, context = (1,)):
    '''Get information about a frame or traceback object.

    A tuple of five things is returned: the filename, the line number of
    the current line, the function name, a list of lines of context from
    the source code, and the index of the current line within that list.
    The optional second argument specifies the number of lines of context
    to return, which are centered around the current line.'''
    if istraceback(frame):
        positions = _get_code_position_from_tb(frame)
        lineno = frame.tb_lineno
        frame = frame.tb_frame
    else:
        lineno = frame.f_lineno
        positions = _get_code_position(frame.f_code, frame.f_lasti)
# WARNING: Decompyle incomplete


def getlineno(frame):
    '''Get the line number from a frame object, allowing for optimization.'''
    return frame.f_lineno

_FrameInfo = namedtuple('_FrameInfo', ('frame',) + Traceback._fields)

class FrameInfo(_FrameInfo):
    pass
# WARNING: Decompyle incomplete


def getouterframes(frame, context = (1,)):
    '''Get a list of records for a frame and all higher (calling) frames.

    Each record contains a frame object, filename, line number, function
    name, a list of lines of context, and index within the context.'''
    framelist = []
# WARNING: Decompyle incomplete


def getinnerframes(tb, context = (1,)):
    """Get a list of records for a traceback's frame and all lower frames.

    Each record contains a frame object, filename, line number, function
    name, a list of lines of context, and index within the context."""
    framelist = []
# WARNING: Decompyle incomplete


def currentframe():
    '''Return the frame of the caller or None if this is not possible.'''
    if hasattr(sys, '_getframe'):
        return sys._getframe(1)


def stack(context = (1,)):
    """Return a list of records for the stack above the caller's frame."""
    return getouterframes(sys._getframe(1), context)


def trace(context = (1,)):
    '''Return a list of records for the stack below the current exception.'''
    exc = sys.exception()
# WARNING: Decompyle incomplete

_sentinel = object()
_static_getmro = type.__dict__['__mro__'].__get__
_get_dunder_dict_of_class = type.__dict__['__dict__'].__get__

def _check_instance(obj, attr):
    instance_dict = { }
    instance_dict = object.__getattribute__(obj, '__dict__')
    return dict.get(instance_dict, attr, _sentinel)
# WARNING: Decompyle incomplete


def _check_class(klass, attr):
    for entry in _static_getmro(klass):
        if not _shadowed_dict(type(entry)) is _sentinel:
            continue
        if not attr in entry.__dict__:
            continue
        
        return _static_getmro(klass), entry.__dict__[attr]
    return _sentinel

_shadowed_dict_from_mro_tuple = (lambda mro: for entry in mro:
dunder_dict = _get_dunder_dict_of_class(entry)if not '__dict__' in dunder_dict:
continueclass_dict = dunder_dict['__dict__']if type(class_dict) is types.GetSetDescriptorType and class_dict.__name__ == '__dict__' and class_dict.__objclass__ is entry:
continuemro, class_dict_sentinel)()

def _shadowed_dict(klass):
    return _shadowed_dict_from_mro_tuple(_static_getmro(klass))


def getattr_static(obj, attr, default = (_sentinel,)):
    """Retrieve attributes without triggering dynamic lookup via the
       descriptor protocol,  __getattr__ or __getattribute__.

       Note: this function may not be able to retrieve all attributes
       that getattr can fetch (like dynamically created attributes)
       and may find attributes that getattr can't (like descriptors
       that raise AttributeError). It can also return descriptor objects
       instead of instance members in some cases. See the
       documentation for details.
    """
    instance_result = _sentinel
    objtype = type(obj)
    if type not in _static_getmro(objtype):
        klass = objtype
        dict_attr = _shadowed_dict(klass)
        if dict_attr is _sentinel or type(dict_attr) is types.MemberDescriptorType:
            instance_result = _check_instance(obj, attr)
        else:
            klass = obj
    klass_result = _check_class(klass, attr)
    if instance_result is not _sentinel and klass_result is not _sentinel and _check_class(type(klass_result), '__get__') is not _sentinel:
        if _check_class(type(klass_result), '__set__') is not _sentinel or _check_class(type(klass_result), '__delete__') is not _sentinel:
            return klass_result
        if None is not _sentinel:
            return instance_result
        if None is not _sentinel:
            return klass_result
        if None is klass:
            for entry in _static_getmro(type(klass)):
                if not _shadowed_dict(type(entry)) is _sentinel:
                    continue
                if not attr in entry.__dict__:
                    continue
                
                return _static_getmro(type(klass)), entry.__dict__[attr]
    if default is not _sentinel:
        return default
    raise None(attr)

GEN_CREATED = 'GEN_CREATED'
GEN_RUNNING = 'GEN_RUNNING'
GEN_SUSPENDED = 'GEN_SUSPENDED'
GEN_CLOSED = 'GEN_CLOSED'

def getgeneratorstate(generator):
    '''Get current state of a generator-iterator.

    Possible states are:
      GEN_CREATED: Waiting to start execution.
      GEN_RUNNING: Currently being executed by the interpreter.
      GEN_SUSPENDED: Currently suspended at a yield expression.
      GEN_CLOSED: Execution has completed.
    '''
    if generator.gi_running:
        return GEN_RUNNING
    if None.gi_suspended:
        return GEN_SUSPENDED
# WARNING: Decompyle incomplete


def getgeneratorlocals(generator):
    '''
    Get the mapping of generator local variables to their current values.

    A dict is returned, with the keys the local variable names and values the
    bound values.'''
    if not isgenerator(generator):
        raise TypeError('{!r} is not a Python generator'.format(generator))
    frame = getattr(generator, 'gi_frame', None)
# WARNING: Decompyle incomplete

CORO_CREATED = 'CORO_CREATED'
CORO_RUNNING = 'CORO_RUNNING'
CORO_SUSPENDED = 'CORO_SUSPENDED'
CORO_CLOSED = 'CORO_CLOSED'

def getcoroutinestate(coroutine):
    '''Get current state of a coroutine object.

    Possible states are:
      CORO_CREATED: Waiting to start execution.
      CORO_RUNNING: Currently being executed by the interpreter.
      CORO_SUSPENDED: Currently suspended at an await expression.
      CORO_CLOSED: Execution has completed.
    '''
    if coroutine.cr_running:
        return CORO_RUNNING
    if None.cr_suspended:
        return CORO_SUSPENDED
# WARNING: Decompyle incomplete


def getcoroutinelocals(coroutine):
    '''
    Get the mapping of coroutine local variables to their current values.

    A dict is returned, with the keys the local variable names and values the
    bound values.'''
    frame = getattr(coroutine, 'cr_frame', None)
# WARNING: Decompyle incomplete

AGEN_CREATED = 'AGEN_CREATED'
AGEN_RUNNING = 'AGEN_RUNNING'
AGEN_SUSPENDED = 'AGEN_SUSPENDED'
AGEN_CLOSED = 'AGEN_CLOSED'

def getasyncgenstate(agen):
    '''Get current state of an asynchronous generator object.

    Possible states are:
      AGEN_CREATED: Waiting to start execution.
      AGEN_RUNNING: Currently being executed by the interpreter.
      AGEN_SUSPENDED: Currently suspended at a yield expression.
      AGEN_CLOSED: Execution has completed.
    '''
    if agen.ag_running:
        return AGEN_RUNNING
    if None.ag_suspended:
        return AGEN_SUSPENDED
# WARNING: Decompyle incomplete


def getasyncgenlocals(agen):
    '''
    Get the mapping of asynchronous generator local variables to their current
    values.

    A dict is returned, with the keys the local variable names and values the
    bound values.'''
    if not isasyncgen(agen):
        raise TypeError(f'''{agen!r} is not a Python async generator''')
    frame = getattr(agen, 'ag_frame', None)
# WARNING: Decompyle incomplete

_NonUserDefinedCallables = (types.WrapperDescriptorType, types.MethodWrapperType, types.ClassMethodDescriptorType, types.BuiltinFunctionType)

def _signature_get_user_defined_method(cls, method_name):
    '''Private helper. Checks if ``cls`` has an attribute
    named ``method_name`` and returns it only if it is a
    pure python function.
    '''
    meth = getattr(cls, method_name)
    if not isinstance(meth, _NonUserDefinedCallables):
        return meth
# WARNING: Decompyle incomplete


def _signature_get_partial(wrapped_sig, partial, extra_args = ((),)):
    """Private helper to calculate how 'wrapped_sig' signature will
    look like after applying a 'functools.partial' object (or alike)
    on it.
    """
    old_params = wrapped_sig.parameters
    new_params = OrderedDict(old_params.items())
    if not partial.args:
        partial.args
    partial_args = ()
    if not partial.keywords:
        partial.keywords
    partial_keywords = { }
    if extra_args:
        partial_args = extra_args + partial_args
# WARNING: Decompyle incomplete


def _signature_bound_method(sig):
    '''Private helper to transform signatures for unbound
    functions to bound methods.
    '''
    params = tuple(sig.parameters.values())
    if params or params[0].kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
        raise ValueError('invalid method signature')
    kind = params[0].kind
    if kind in (_POSITIONAL_OR_KEYWORD, _POSITIONAL_ONLY):
        params = params[1:]
    elif kind is not _VAR_POSITIONAL:
        raise ValueError('invalid argument type')
    return sig.replace(parameters = params)


def _signature_is_builtin(obj):
    """Private helper to test if `obj` is a callable that might
    support Argument Clinic's __text_signature__ protocol.
    """
    if not isbuiltin(obj):
        isbuiltin(obj)
        if not ismethoddescriptor(obj):
            ismethoddescriptor(obj)
            if not isinstance(obj, _NonUserDefinedCallables):
                isinstance(obj, _NonUserDefinedCallables)
    return obj in (type, object)


def _signature_is_functionlike(obj):
    '''Private helper to test if `obj` is a duck type of FunctionType.
    A good example of such objects are functions compiled with
    Cython, which have all attributes that a pure Python function
    would have, but have their code statically compiled.
    '''
    if callable(obj) or isclass(obj):
        return False
    name = getattr(obj, '__name__', None)
    code = getattr(obj, '__code__', None)
    defaults = getattr(obj, '__defaults__', _void)
    kwdefaults = getattr(obj, '__kwdefaults__', _void)
    annotations = getattr(obj, '__annotations__', None)
    if isinstance(code, types.CodeType):
        isinstance(code, types.CodeType)
        if isinstance(name, str):
            isinstance(name, str)
            if not defaults is None:
                defaults is None
            if isinstance(defaults, tuple):
                isinstance(defaults, tuple)
                if not kwdefaults is None:
                    kwdefaults is None
                if isinstance(kwdefaults, dict):
                    isinstance(kwdefaults, dict)
                    if not isinstance(annotations, dict):
                        isinstance(annotations, dict)
    return annotations is None


def _signature_strip_non_python_syntax(signature):
    '''
    Private helper function. Takes a signature in Argument Clinic\'s
    extended signature format.

    Returns a tuple of two things:
      * that signature re-rendered in standard Python syntax, and
      * the index of the "self" parameter (generally 0), or None if
        the function does not have a "self" parameter.
    '''
    if not signature:
        return (signature, None)
    self_parameter = None
# WARNING: Decompyle incomplete


def _signature_fromstr(cls, obj, s, skip_bound_arg = (True,)):
    """Private helper to parse content of '__text_signature__'
    and return a Signature based on it.
    """
    pass
# WARNING: Decompyle incomplete


def _signature_from_builtin(cls, func, skip_bound_arg = (True,)):
    '''Private helper function to get signature for
    builtin callables.
    '''
    if not _signature_is_builtin(func):
        raise TypeError('{!r} is not a Python builtin function'.format(func))
    s = getattr(func, '__text_signature__', None)
    if not s:
        raise ValueError('no signature found for builtin {!r}'.format(func))
    return _signature_fromstr(cls, func, s, skip_bound_arg)


def _signature_from_function(cls, func, skip_bound_arg, globals, locals, eval_str = (True, None, None, False)):
    '''Private helper: constructs Signature for the given python function.'''
    is_duck_function = False
    if not isfunction(func):
        if _signature_is_functionlike(func):
            is_duck_function = True
        else:
            raise TypeError('{!r} is not a Python function'.format(func))
    s = getattr(func, '__text_signature__', None)
    if s:
        return _signature_fromstr(cls, func, s, skip_bound_arg)
    Parameter = None._parameter_cls
    func_code = func.__code__
    pos_count = func_code.co_argcount
    arg_names = func_code.co_varnames
    posonly_count = func_code.co_posonlyargcount
    positional = arg_names[:pos_count]
    keyword_only_count = func_code.co_kwonlyargcount
    keyword_only = arg_names[pos_count:pos_count + keyword_only_count]
    annotations = get_annotations(func, globals = globals, locals = locals, eval_str = eval_str)
    defaults = func.__defaults__
    kwdefaults = func.__kwdefaults__
    if defaults:
        pos_default_count = len(defaults)
    else:
        pos_default_count = 0
    parameters = []
    non_default_count = pos_count - pos_default_count
    posonly_left = posonly_count
    for name in positional[:non_default_count]:
        kind = _POSITIONAL_ONLY if posonly_left else _POSITIONAL_OR_KEYWORD
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation = annotation, kind = kind))
        if not posonly_left:
            continue
        posonly_left -= 1
    for offset, name in enumerate(positional[non_default_count:]):
        kind = _POSITIONAL_ONLY if posonly_left else _POSITIONAL_OR_KEYWORD
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation = annotation, kind = kind, default = defaults[offset]))
        if not posonly_left:
            continue
        posonly_left -= 1
    if func_code.co_flags & CO_VARARGS:
        name = arg_names[pos_count + keyword_only_count]
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation = annotation, kind = _VAR_POSITIONAL))
# WARNING: Decompyle incomplete


def _signature_from_callable(obj = functools.lru_cache(), *, follow_wrapper_chains, skip_bound_arg, globals, locals, eval_str, sigcls):
    '''Private helper function to get signature for arbitrary
    callable objects.
    '''
    _get_signature_of = functools.partial(_signature_from_callable, follow_wrapper_chains = follow_wrapper_chains, skip_bound_arg = skip_bound_arg, globals = globals, locals = locals, sigcls = sigcls, eval_str = eval_str)
    if not callable(obj):
        raise TypeError('{!r} is not a callable object'.format(obj))
    if isinstance(obj, types.MethodType):
        sig = _get_signature_of(obj.__func__)
        if skip_bound_arg:
            return _signature_bound_method(sig)
        return None
# WARNING: Decompyle incomplete


class _void:
    '''A private marker - used in Parameter & Signature.'''
    pass


class _empty:
    '''Marker object for Signature.empty and Parameter.empty.'''
    pass


class _ParameterKind(enum.IntEnum):
    POSITIONAL_ONLY = 'positional-only'
    POSITIONAL_OR_KEYWORD = 'positional or keyword'
    VAR_POSITIONAL = 'variadic positional'
    KEYWORD_ONLY = 'keyword-only'
    VAR_KEYWORD = 'variadic keyword'
    
    def __new__(cls, description):
        value = len(cls.__members__)
        member = int.__new__(cls, value)
        member._value_ = value
        member.description = description
        return member

    
    def __str__(self):
        return self.name


_POSITIONAL_ONLY = _ParameterKind.POSITIONAL_ONLY
_POSITIONAL_OR_KEYWORD = _ParameterKind.POSITIONAL_OR_KEYWORD
_VAR_POSITIONAL = _ParameterKind.VAR_POSITIONAL
_KEYWORD_ONLY = _ParameterKind.KEYWORD_ONLY
_VAR_KEYWORD = _ParameterKind.VAR_KEYWORD

class Parameter:
    '''Represents a parameter in a function signature.

    Has the following public attributes:

    * name : str
        The name of the parameter as a string.
    * default : object
        The default value for the parameter if specified.  If the
        parameter has no default value, this attribute is set to
        `Parameter.empty`.
    * annotation
        The annotation for the parameter if specified.  If the
        parameter has no annotation, this attribute is set to
        `Parameter.empty`.
    * kind : str
        Describes how argument values are bound to the parameter.
        Possible values: `Parameter.POSITIONAL_ONLY`,
        `Parameter.POSITIONAL_OR_KEYWORD`, `Parameter.VAR_POSITIONAL`,
        `Parameter.KEYWORD_ONLY`, `Parameter.VAR_KEYWORD`.
    '''
    __slots__ = ('_name', '_kind', '_default', '_annotation')
    POSITIONAL_ONLY = _POSITIONAL_ONLY
    POSITIONAL_OR_KEYWORD = _POSITIONAL_OR_KEYWORD
    VAR_POSITIONAL = _VAR_POSITIONAL
    KEYWORD_ONLY = _KEYWORD_ONLY
    VAR_KEYWORD = _VAR_KEYWORD
    empty = _empty
    
    def __init__(self, name = None, kind = {
        'default': _empty,
        'annotation': _empty }, *, default, annotation):
        self._kind = _ParameterKind(kind)
        if default is not _empty and self._kind in (_VAR_POSITIONAL, _VAR_KEYWORD):
            msg = '{} parameters cannot have default values'
            msg = msg.format(self._kind.description)
            raise ValueError(msg)
        self._default = default
        self._annotation = annotation
        if name is _empty:
            raise ValueError('name is a required attribute for Parameter')
        if not isinstance(name, str):
            msg = 'name must be a str, not a {}'.format(type(name).__name__)
            raise TypeError(msg)
        if name[0] == '.' and name[1:].isdigit():
            if self._kind != _POSITIONAL_OR_KEYWORD:
                msg = 'implicit arguments must be passed as positional or keyword arguments, not {}'
                msg = msg.format(self._kind.description)
                raise ValueError(msg)
            self._kind = _POSITIONAL_ONLY
            name = 'implicit{}'.format(name[1:])
        if iskeyword(name):
            iskeyword(name)
        is_keyword = self._kind is not _POSITIONAL_ONLY
        if not is_keyword or name.isidentifier():
            raise ValueError('{!r} is not a valid parameter name'.format(name))
        self._name = name
        return None
    # WARNING: Decompyle incomplete

    
    def __reduce__(self):
        return (type(self), (self._name, self._kind), {
            '_default': self._default,
            '_annotation': self._annotation })

    
    def __setstate__(self, state):
        self._default = state['_default']
        self._annotation = state['_annotation']

    name = (lambda self: self._name)()
    default = (lambda self: self._default)()
    annotation = (lambda self: self._annotation)()
    kind = (lambda self: self._kind)()
    
    def replace(self = property, *, name, kind, annotation, default):
        '''Creates a customized copy of the Parameter.'''
        if name is _void:
            name = self._name
        if kind is _void:
            kind = self._kind
        if annotation is _void:
            annotation = self._annotation
        if default is _void:
            default = self._default
        return type(self)(name, kind, default = default, annotation = annotation)

    
    def __str__(self):
        kind = self.kind
        formatted = self._name
        if self._annotation is not _empty:
            formatted = '{}: {}'.format(formatted, formatannotation(self._annotation))
        if self._default is not _empty:
            if self._annotation is not _empty:
                formatted = '{} = {}'.format(formatted, repr(self._default))
            else:
                formatted = '{}={}'.format(formatted, repr(self._default))
        if kind == _VAR_POSITIONAL:
            formatted = '*' + formatted
            return formatted
        if None == _VAR_KEYWORD:
            formatted = '**' + formatted
        return formatted

    
    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self)

    
    def __hash__(self):
        return hash((self._name, self._kind, self._annotation, self._default))

    
    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Parameter):
            return NotImplemented
        if None._name == other._name:
            None._name == other._name
            if self._kind == other._kind:
                self._kind == other._kind
                if self._default == other._default:
                    self._default == other._default
        return self._annotation == other._annotation



class BoundArguments:
    """Result of `Signature.bind` call.  Holds the mapping of arguments
    to the function's parameters.

    Has the following public attributes:

    * arguments : dict
        An ordered mutable mapping of parameters' names to arguments' values.
        Does not contain arguments' default values.
    * signature : Signature
        The Signature object that created this instance.
    * args : tuple
        Tuple of positional arguments values.
    * kwargs : dict
        Dict of keyword arguments values.
    """
    __slots__ = ('arguments', '_signature', '__weakref__')
    
    def __init__(self, signature, arguments):
        self.arguments = arguments
        self._signature = signature

    signature = (lambda self: self._signature)()
    args = (lambda self: args = []for param_name, param in self._signature.parameters.items():
if param.kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
self._signature.parameters.items()tuple(args)arg = self.arguments[param_name]if param.kind == _VAR_POSITIONAL:
args.extend(arg)continueargs.append(arg)tuple(args)# WARNING: Decompyle incomplete
)()
    kwargs = (lambda self: kwargs = { }kwargs_started = Falsefor param_name, param in self._signature.parameters.items():
if not kwargs_started:
if param.kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
kwargs_started = Trueelif param_name not in self.arguments:
kwargs_started = Truecontinueif not kwargs_started:
continuearg = self.arguments[param_name]if param.kind == _VAR_KEYWORD:
kwargs.update(arg)continuekwargs[param_name] = argkwargs# WARNING: Decompyle incomplete
)()
    
    def apply_defaults(self):
        '''Set default values for missing arguments.

        For variable-positional arguments (*args) the default is an
        empty tuple.

        For variable-keyword arguments (**kwargs) the default is an
        empty dict.
        '''
        arguments = self.arguments
        new_arguments = []
        for name, param in self._signature.parameters.items():
            new_arguments.append((name, arguments[name]))
        self.arguments = dict(new_arguments)
        return None
    # WARNING: Decompyle incomplete

    
    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, BoundArguments):
            return NotImplemented
        if None.signature == other.signature:
            None.signature == other.signature
        return self.arguments == other.arguments

    
    def __setstate__(self, state):
        self._signature = state['_signature']
        self.arguments = state['arguments']

    
    def __getstate__(self):
        return {
            '_signature': self._signature,
            'arguments': self.arguments }

    
    def __repr__(self):
        args = []
        for arg, value in self.arguments.items():
            args.append('{}={!r}'.format(arg, value))
        return '<{} ({})>'.format(self.__class__.__name__, ', '.join(args))



class Signature:
    """A Signature object represents the overall signature of a function.
    It stores a Parameter object for each parameter accepted by the
    function, as well as information specific to the function itself.

    A Signature object has the following public attributes and methods:

    * parameters : OrderedDict
        An ordered mapping of parameters' names to the corresponding
        Parameter objects (keyword-only arguments are in the same order
        as listed in `code.co_varnames`).
    * return_annotation : object
        The annotation for the return type of the function if specified.
        If the function has no annotation for its return type, this
        attribute is set to `Signature.empty`.
    * bind(*args, **kwargs) -> BoundArguments
        Creates a mapping from positional and keyword arguments to
        parameters.
    * bind_partial(*args, **kwargs) -> BoundArguments
        Creates a partial mapping from positional and keyword arguments
        to parameters (simulating 'functools.partial' behavior.)
    """
    __slots__ = ('_return_annotation', '_parameters')
    _parameter_cls = Parameter
    _bound_arguments_cls = BoundArguments
    empty = _empty
    
    def __init__(self = None, parameters = (None,), *, return_annotation, __validate_parameters__):
        """Constructs Signature from the given list of Parameter
        objects and 'return_annotation'.  All arguments are optional.
        """
        pass
    # WARNING: Decompyle incomplete

    from_callable = (lambda cls = classmethod, obj = {
        'follow_wrapped': True,
        'globals': None,
        'locals': None,
        'eval_str': False }, *, follow_wrapped, globals: _signature_from_callable(obj, sigcls = cls, follow_wrapper_chains = follow_wrapped, globals = globals, locals = locals, eval_str = eval_str))()
    parameters = (lambda self: self._parameters)()
    return_annotation = (lambda self: self._return_annotation)()
    
    def replace(self = property, *, parameters, return_annotation):
        """Creates a customized copy of the Signature.
        Pass 'parameters' and/or 'return_annotation' arguments
        to override them in the new copy.
        """
        if parameters is _void:
            parameters = self.parameters.values()
        if return_annotation is _void:
            return_annotation = self._return_annotation
        return type(self)(parameters, return_annotation = return_annotation)

    
    def _hash_basis(self):
        params = (lambda .0: pass# WARNING: Decompyle incomplete
)(self.parameters.values()())
    # WARNING: Decompyle incomplete

    
    def __hash__(self):
        (params, kwo_params, return_annotation) = self._hash_basis()
        kwo_params = frozenset(kwo_params.values())
        return hash((params, kwo_params, return_annotation))

    
    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Signature):
            return NotImplemented
        return None._hash_basis() == other._hash_basis()

    
    def _bind(self, args = property, kwargs = {
        'partial': False }, *, partial):
        """Private method. Don't use directly."""
        arguments = { }
        parameters = iter(self.parameters.values())
        parameters_ex = ()
        arg_vals = iter(args)
        arg_val = next(arg_vals)
        param = next(parameters)
        if param.kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
            raise TypeError('too many positional arguments'), None
        if param.kind == _VAR_POSITIONAL:
            values = [
                arg_val]
            values.extend(arg_vals)
            arguments[param.name] = tuple(values)
        elif param.name in kwargs and param.kind != _POSITIONAL_ONLY:
            raise TypeError('multiple values for argument {arg!r}'.format(arg = param.name)), None
        arguments[param.name] = arg_val
        continue
        kwargs_param = None
        for param in itertools.chain(parameters_ex, parameters):
            if param.kind == _VAR_KEYWORD:
                kwargs_param = param
                continue
            if param.kind == _VAR_POSITIONAL:
                continue
            param_name = param.name
            arg_val = kwargs.pop(param_name)
            if param.kind == _POSITIONAL_ONLY:
                raise TypeError('{arg!r} parameter is positional only, but was passed as a keyword'.format(arg = param.name))
            arguments[param_name] = arg_val
    # WARNING: Decompyle incomplete

    
    def bind(self, *args, **kwargs):
        """Get a BoundArguments object, that maps the passed `args`
        and `kwargs` to the function's signature.  Raises `TypeError`
        if the passed arguments can not be bound.
        """
        return self._bind(args, kwargs)

    
    def bind_partial(self, *args, **kwargs):
        """Get a BoundArguments object, that partially maps the
        passed `args` and `kwargs` to the function's signature.
        Raises `TypeError` if the passed arguments can not be bound.
        """
        return self._bind(args, kwargs, partial = True)

    
    def __reduce__(self):
        return (type(self), (tuple(self._parameters.values()),), {
            '_return_annotation': self._return_annotation })

    
    def __setstate__(self, state):
        self._return_annotation = state['_return_annotation']

    
    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self)

    
    def __str__(self):
        result = []
        render_pos_only_separator = False
        render_kw_only_separator = True
        for param in self.parameters.values():
            formatted = str(param)
            kind = param.kind
            if kind == _POSITIONAL_ONLY:
                render_pos_only_separator = True
            elif render_pos_only_separator:
                result.append('/')
                render_pos_only_separator = False
            if kind == _VAR_POSITIONAL:
                render_kw_only_separator = False
            elif kind == _KEYWORD_ONLY and render_kw_only_separator:
                result.append('*')
                render_kw_only_separator = False
            result.append(formatted)
        if render_pos_only_separator:
            result.append('/')
        rendered = '({})'.format(', '.join(result))
        if self.return_annotation is not _empty:
            anno = formatannotation(self.return_annotation)
            rendered += ' -> {}'.format(anno)
        return rendered



def signature(obj = None, *, follow_wrapped, globals, locals, eval_str):
    '''Get a signature object for the passed callable.'''
    return Signature.from_callable(obj, follow_wrapped = follow_wrapped, globals = globals, locals = locals, eval_str = eval_str)


class BufferFlags(enum.IntFlag):
    SIMPLE = 0
    WRITABLE = 1
    FORMAT = 4
    ND = 8
    STRIDES = 16 | ND
    C_CONTIGUOUS = 32 | STRIDES
    F_CONTIGUOUS = 64 | STRIDES
    ANY_CONTIGUOUS = 128 | STRIDES
    INDIRECT = 256 | STRIDES
    CONTIG = ND | WRITABLE
    CONTIG_RO = ND
    STRIDED = STRIDES | WRITABLE
    STRIDED_RO = STRIDES
    RECORDS = STRIDES | WRITABLE | FORMAT
    RECORDS_RO = STRIDES | FORMAT
    FULL = INDIRECT | WRITABLE | FORMAT
    FULL_RO = INDIRECT | FORMAT
    READ = 256
    WRITE = 512


def _main():
    ''' Logic for inspecting an object given at command line '''
    import argparse
    import importlib
    parser = argparse.ArgumentParser()
    parser.add_argument('object', help = "The object to be analysed. It supports the 'module:qualname' syntax")
    parser.add_argument('-d', '--details', action = 'store_true', help = 'Display info about the module rather than its source code')
    args = parser.parse_args()
    target = args.object
    (mod_name, has_attrs, attrs) = target.partition(':')
    obj = importlib.import_module(mod_name)
    module = importlib.import_module(mod_name)
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    _main()
    return None
