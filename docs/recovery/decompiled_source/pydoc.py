# Source Generated with Decompyle++
# File: pydoc.pyc (Python 3.12)

'''Generate Python documentation in HTML or text for interactive use.

At the Python interactive prompt, calling help(thing) on a Python object
documents the object, and calling help() starts up an interactive
help session.

Or, at the shell command line outside of Python:

Run "pydoc <name>" to show documentation on something.  <name> may be
the name of a function, module, package, or a dotted reference to a
class or function within a module or module in a package.  If the
argument contains a path segment delimiter (e.g. slash on Unix,
backslash on Windows) it is treated as the path to a Python source file.

Run "pydoc -k <keyword>" to search for a keyword in the synopsis lines
of all available modules.

Run "pydoc -n <hostname>" to start an HTTP server with the given
hostname (default: localhost) on the local machine.

Run "pydoc -p <port>" to start an HTTP server on the given port on the
local machine.  Port number 0 can be used to get an arbitrary unused port.

Run "pydoc -b" to start an HTTP server on an arbitrary unused port and
open a web browser to interactively browse documentation.  Combine with
the -n and -p options to control the hostname and port used.

Run "pydoc -w <name>" to write out the HTML documentation for a module
to a file named "<name>.html".

Module docs for core modules are assumed to be in

    https://docs.python.org/X.Y/library/

This can be overridden by setting the PYTHONDOCS environment variable
to a different URL or to a local directory containing the Library
Reference Manual pages.
'''
__all__ = [
    'help']
__author__ = 'Ka-Ping Yee <ping@lfw.org>'
__date__ = '26 February 2001'
__credits__ = 'Guido van Rossum, for an excellent programming language.\nTommy Burnette, the original creator of manpy.\nPaul Prescod, for all his work on onlinehelp.\nRichard Chamberlain, for the first implementation of textdoc.\n'
import __future__
import builtins
import importlib._bootstrap as importlib
import importlib._bootstrap_external as importlib
import importlib.machinery as importlib
import importlib.util as importlib
import inspect
import io
import os
import pkgutil
import platform
import re
import sys
import sysconfig
import time
import tokenize
import urllib.parse as urllib
import warnings
from collections import deque
from reprlib import Repr
from traceback import format_exception_only

def pathdirs():
    '''Convert sys.path into a list of absolute, existing, unique paths.'''
    dirs = []
    normdirs = []
    for dir in sys.path:
        if not dir:
            dir
        dir = os.path.abspath('.')
        normdir = os.path.normcase(dir)
        if not normdir not in normdirs:
            continue
        if not os.path.isdir(dir):
            continue
        dirs.append(dir)
        normdirs.append(normdir)
    return dirs


def _findclass(func):
    cls = sys.modules.get(func.__module__)
# WARNING: Decompyle incomplete


def _finddoc(obj):
    if inspect.ismethod(obj):
        name = obj.__func__.__name__
        self = obj.__self__
        if inspect.isclass(self) and getattr(getattr(self, name, None), '__func__') is obj.__func__:
            cls = self
        else:
            cls = self.__class__
# WARNING: Decompyle incomplete


def _getowndoc(obj):
    '''Get the documentation string for an object if it is not
    inherited from its class.'''
    doc = object.__getattribute__(obj, '__doc__')
# WARNING: Decompyle incomplete


def _getdoc(object):
    '''Get the documentation string for an object.

    All tabs are expanded to spaces.  To clean up docstrings that are
    indented to line up with blocks of code, any whitespace than can be
    uniformly removed from the second line onwards is removed.'''
    doc = _getowndoc(object)
# WARNING: Decompyle incomplete


def getdoc(object):
    '''Get the doc string or comments for an object.'''
    if not _getdoc(object):
        _getdoc(object)
    result = inspect.getcomments(object)
    if result:
        result
    if not re.sub('^ *\n', '', result.rstrip()):
        re.sub('^ *\n', '', result.rstrip())
    return ''


def splitdoc(doc):
    '''Split a doc string into a synopsis line (if any) and the rest.'''
    lines = doc.strip().split('\n')
    if len(lines) == 1:
        return (lines[0], '')
    if not None(lines) >= 2 and lines[1].rstrip():
        return (lines[0], '\n'.join(lines[2:]))
    return (None, '\n'.join(lines))


def classname(object, modname):
    '''Get a class name and qualify it with a module name if necessary.'''
    name = object.__name__
    if object.__module__ != modname:
        name = object.__module__ + '.' + name
    return name


def isdata(object):
    """Check if an object is of a type that probably means it's data."""
    if not inspect.ismodule(object):
        inspect.ismodule(object)
        if not inspect.isclass(object):
            inspect.isclass(object)
            if not inspect.isroutine(object):
                inspect.isroutine(object)
                if not inspect.isframe(object):
                    inspect.isframe(object)
                    if not inspect.istraceback(object):
                        inspect.istraceback(object)
    return not inspect.iscode(object)


def replace(text, *pairs):
    '''Do a series of global replacements on a string.'''
    if pairs:
        text = pairs[1].join(text.split(pairs[0]))
        pairs = pairs[2:]
        if pairs:
            continue
    return text


def cram(text, maxlen):
    '''Omit part of a string if needed to make it fit in a maximum length.'''
    if len(text) > maxlen:
        pre = max(0, (maxlen - 3) // 2)
        post = max(0, maxlen - 3 - pre)
        return text[:pre] + '...' + text[len(text) - post:]

_re_stripid = re.compile(' at 0x[0-9a-f]{6,16}(>+)$', re.IGNORECASE)

def stripid(text):
    '''Remove the hexadecimal id from a Python object representation.'''
    return _re_stripid.sub('\\1', text)


def _is_bound_method(fn):
    '''
    Returns True if fn is a bound method, regardless of whether
    fn was implemented in Python or in C.
    '''
    if inspect.ismethod(fn):
        return True
    if inspect.isbuiltin(fn):
        self = getattr(fn, '__self__', None)
        if not inspect.ismodule(self):
            inspect.ismodule(self)
        return not (self is None)


def allmethods(cl):
    methods = { }
    for key, value in inspect.getmembers(cl, inspect.isroutine):
        methods[key] = 1
    for base in cl.__bases__:
        methods.update(allmethods(base))
    for key in methods.keys():
        methods[key] = getattr(cl, key)
    return methods


def _split_list(s, predicate):
    '''Split sequence s via predicate, and return pair ([true], [false]).

    The return value is a 2-tuple of lists,
        ([x for x in s if predicate(x)],
         [x for x in s if not predicate(x)])
    '''
    yes = []
    no = []
    for x in s:
        if predicate(x):
            yes.append(x)
            continue
        no.append(x)
    return (yes, no)

_future_feature_names = set(__future__.all_feature_names)

def visiblename(name, all, obj = (None, None)):
    '''Decide whether to show documentation on a variable.'''
    if name in frozenset({'__doc__', '__date__', '__file__', '__name__', '__path__', '__spec__', '__slots__', '__author__', '__cached__', '__loader__', '__module__', '__credits__', '__package__', '__version__', '__builtins__', '__qualname__'}):
        return 0
    if name.startswith('__') and name.endswith('__'):
        return 1
    if name.startswith('_') and hasattr(obj, '_fields'):
        return True
    if obj is not __future__ and name in _future_feature_names and isinstance(getattr(obj, name, None), __future__._Feature):
        return False
# WARNING: Decompyle incomplete


def classify_class_attrs(object):
    '''Wrap inspect.classify_class_attrs, with fixup for data descriptors.'''
    results = []
# WARNING: Decompyle incomplete


def sort_attributes(attrs, object):
    '''Sort the attrs list in-place by _fields and then alphabetically by name'''
    pass
# WARNING: Decompyle incomplete


def ispackage(path):
    '''Guess whether a path refers to a package directory.'''
    if os.path.isdir(path):
        for ext in ('.py', '.pyc'):
            if not os.path.isfile(os.path.join(path, '__init__' + ext)):
                continue
            ('.py', '.pyc')
            return True
    return False


def source_synopsis(file):
    line = file.readline()
    if not line[:1] == '#' or line.strip():
        line = file.readline()
        if not line:
            pass
        elif line[:1] == '#':
            continue
        if not line.strip():
            continue
    line = line.strip()
    if line[:4] == 'r"""':
        line = line[1:]
    if line[:3] == '"""':
        line = line[3:]
        if line[-1:] == '\\':
            line = line[:-1]
        if not line.strip():
            line = file.readline()
            if not line:
                pass
            elif not line.strip():
                continue
        result = line.split('"""')[0].strip()
        return result
    result = None
    return result


def synopsis(filename, cache = ({ },)):
    '''Get the one-line summary out of a module file.'''
    mtime = os.stat(filename).st_mtime
    (lastupdate, result) = cache.get(filename, (None, None))
# WARNING: Decompyle incomplete


class ErrorDuringImport(Exception):
    '''Errors that occurred while trying to import something to document it.'''
    
    def __init__(self, filename, exc_info):
        pass
    # WARNING: Decompyle incomplete

    
    def __str__(self):
        exc = self.exc.__name__
        return f'''problem in {self.filename!s} - {exc!s}: {self.value!s}'''



def importfile(path):
    '''Import a Python source file or compiled file given its path.'''
    magic = importlib.util.MAGIC_NUMBER
# WARNING: Decompyle incomplete


def safeimport(path, forceload, cache = (0, { })):
    """Import a module; handle errors; return None if the module isn't found.

    If the module *is* found but an exception occurs, it's wrapped in an
    ErrorDuringImport exception and reraised.  Unlike __import__, if a
    package path is specified, the module at the end of the path is returned,
    not the package at the beginning.  If the optional 'forceload' argument
    is 1, we reload the module from disk (unless it's a dynamic extension)."""
    pass
# WARNING: Decompyle incomplete


class Doc:
    PYTHONDOCS = os.environ.get('PYTHONDOCS', 'https://docs.python.org/%d.%d/library' % sys.version_info[:2])
    
    def document(self, object, name = (None,), *args):
        '''Generate documentation for an object.'''
        args = (object, name) + args
    # WARNING: Decompyle incomplete

    
    def fail(self, object, name = (None,), *args):
        '''Raise an exception for unimplemented types.'''
        if name:
            name
        message = f'''don\'t know how to document object{' ' + repr(name)!s} of type {type(object).__name__!s}'''
        raise TypeError(message)

    docmodule = fail
    docclass = fail
    docroutine = fail
    docother = fail
    docproperty = fail
    docdata = fail
    
    def getdocloc(self, object, basedir = (sysconfig.get_path('stdlib'),)):
        '''Return the location of module docs or None'''
        file = inspect.getabsfile(object)
        docloc = os.environ.get('PYTHONDOCS', self.PYTHONDOCS)
        basedir = os.path.normcase(basedir)
        if isinstance(object, type(os)):
            if (object.__name__ in ('errno', 'exceptions', 'gc', 'marshal', 'posix', 'signal', 'sys', '_thread', 'zipimport') or file.startswith(basedir)) and file.startswith(os.path.join(basedir, 'site-packages')) and object.__name__ not in ('xml.etree', 'test.pydoc_mod'):
                if docloc.startswith(('http://', 'https://')):
                    docloc = '{}/{}.html'.format(docloc.rstrip('/'), object.__name__.lower())
                    return docloc
                docloc = None.path.join(docloc, object.__name__.lower() + '.html')
                return docloc
            docloc = None
            return docloc
    # WARNING: Decompyle incomplete



class HTMLRepr(Repr):
    '''Class for safely making an HTML representation of a Python object.'''
    
    def __init__(self):
        Repr.__init__(self)
        self.maxlist = 20
        self.maxtuple = 20
        self.maxdict = 10
        self.maxstring = 100
        self.maxother = 100

    
    def escape(self, text):
        return replace(text, '&', '&amp;', '<', '&lt;', '>', '&gt;')

    
    def repr(self, object):
        return Repr.repr(self, object)

    
    def repr1(self, x, level):
