# Source Generated with Decompyle++
# File: six.pyc (Python 3.12)

__doc__ = 'Utilities for writing code that runs on Python 2 and 3'
from __future__ import absolute_import
import functools
import itertools
import operator
import sys
import types
__author__ = 'Benjamin Peterson <benjamin@python.org>'
__version__ = '1.17.0'
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
PY34 = sys.version_info[0:2] >= (3, 4)

def _add_doc(func, doc):
    '''Add documentation to a function.'''
    func.__doc__ = doc


def _import_module(name):
    '''Import module, returning the module after the last dot.'''
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):
    
    def __init__(self, name):
        self.name = name

    
    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        delattr(obj.__class__, self.name)
        return result
    # WARNING: Decompyle incomplete



class MovedModule(_LazyDescr):
    pass
# WARNING: Decompyle incomplete


class _LazyModule(types.ModuleType):
    pass
# WARNING: Decompyle incomplete


class MovedAttribute(_LazyDescr):
    pass
# WARNING: Decompyle incomplete


class _SixMetaPathImporter(object):
    '''
    A meta path importer to import six.moves and its submodules.

    This class implements a PEP302 finder and loader. It should be compatible
    with Python 2.5 and all existing versions of Python3
    '''
    
    def __init__(self, six_module_name):
        self.name = six_module_name
        self.known_modules = { }

    
    def _add_module(self, mod, *fullnames):
        for fullname in fullnames:
            self.known_modules[self.name + '.' + fullname] = mod

    
    def _get_module(self, fullname):
        return self.known_modules[self.name + '.' + fullname]

    
    def find_module(self, fullname, path = (None,)):
        if fullname in self.known_modules:
            return self

    
    def find_spec(self, fullname, path, target = (None,)):
        if fullname in self.known_modules:
            return spec_from_loader(fullname, self)

    
    def _SixMetaPathImporter__get_module(self, fullname):
        return self.known_modules[fullname]
    # WARNING: Decompyle incomplete

    
    def load_module(self, fullname):
        return sys.modules[fullname]
    # WARNING: Decompyle incomplete

    
    def is_package(self, fullname):
        '''
        Return true, if the named module is a package.

        We need this method to get correct spec objects with
        Python 3.4 (see PEP451)
        '''
        return hasattr(self._SixMetaPathImporter__get_module(fullname), '__path__')

    
    def get_code(self, fullname):
        '''Return None

        Required, if is_package is implemented'''
        self._SixMetaPathImporter__get_module(fullname)

    get_source = get_code
    
    def create_module(self, spec):
        return self.load_module(spec.name)

    
    def exec_module(self, module):
        pass


_importer = _SixMetaPathImporter(__name__)

class _MovedItems(_LazyModule):
    '''Lazy loading of moved objects'''
    __path__ = []

_moved_attributes = [][MovedAttribute('cStringIO', 'cStringIO', 'io', 'StringIO')][MovedAttribute('filter', 'itertools', 'builtins', 'ifilter', 'filter')][MovedAttribute('filterfalse', 'itertools', 'itertools', 'ifilterfalse', 'filterfalse')][MovedAttribute('input', '__builtin__', 'builtins', 'raw_input', 'input')][MovedAttribute('intern', '__builtin__', 'sys')][MovedAttribute('map', 'itertools', 'builtins', 'imap', 'map')][MovedAttribute('getcwd', 'os', 'os', 'getcwdu', 'getcwd')][MovedAttribute('getcwdb', 'os', 'os', 'getcwd', 'getcwdb')][MovedAttribute('getoutput', 'commands', 'subprocess')][MovedAttribute('range', '__builtin__', 'builtins', 'xrange', 'range')][MovedAttribute('reload_module', '__builtin__', 'importlib' if PY34 else 'imp', 'reload')][MovedAttribute('reduce', '__builtin__', 'functools')][MovedAttribute('shlex_quote', 'pipes', 'shlex', 'quote')][MovedAttribute('StringIO', 'StringIO', 'io')][MovedAttribute('UserDict', 'UserDict', 'collections', 'IterableUserDict', 'UserDict')][MovedAttribute('UserList', 'UserList', 'collections')][MovedAttribute('UserString', 'UserString', 'collections')][MovedAttribute('xrange', '__builtin__', 'builtins', 'xrange', 'range')][MovedAttribute('zip', 'itertools', 'builtins', 'izip', 'zip')][MovedAttribute('zip_longest', 'itertools', 'itertools', 'izip_longest', 'zip_longest')][MovedModule('builtins', '__builtin__')][MovedModule('configparser', 'ConfigParser')][MovedModule('collections_abc', 'collections', 'collections.abc' if sys.version_info >= (3, 3) else 'collections')][MovedModule('copyreg', 'copy_reg')][MovedModule('dbm_gnu', 'gdbm', 'dbm.gnu')][MovedModule('dbm_ndbm', 'dbm', 'dbm.ndbm')][MovedModule('_dummy_thread', 'dummy_thread', '_dummy_thread' if sys.version_info < (3, 9) else '_thread')][MovedModule('http_cookiejar', 'cookielib', 'http.cookiejar')][MovedModule('http_cookies', 'Cookie', 'http.cookies')][MovedModule('html_entities', 'htmlentitydefs', 'html.entities')][MovedModule('html_parser', 'HTMLParser', 'html.parser')][MovedModule('http_client', 'httplib', 'http.client')][MovedModule('email_mime_base', 'email.MIMEBase', 'email.mime.base')][MovedModule('email_mime_image', 'email.MIMEImage', 'email.mime.image')][MovedModule('email_mime_multipart', 'email.MIMEMultipart', 'email.mime.multipart')][MovedModule('email_mime_nonmultipart', 'email.MIMENonMultipart', 'email.mime.nonmultipart')][MovedModule('email_mime_text', 'email.MIMEText', 'email.mime.text')][MovedModule('BaseHTTPServer', 'BaseHTTPServer', 'http.server')][MovedModule('CGIHTTPServer', 'CGIHTTPServer', 'http.server')][MovedModule('SimpleHTTPServer', 'SimpleHTTPServer', 'http.server')][MovedModule('cPickle', 'cPickle', 'pickle')][MovedModule('queue', 'Queue')][MovedModule('reprlib', 'repr')][MovedModule('socketserver', 'SocketServer')][MovedModule('_thread', 'thread', '_thread')][MovedModule('tkinter', 'Tkinter')][MovedModule('tkinter_dialog', 'Dialog', 'tkinter.dialog')][MovedModule('tkinter_filedialog', 'FileDialog', 'tkinter.filedialog')][MovedModule('tkinter_scrolledtext', 'ScrolledText', 'tkinter.scrolledtext')][MovedModule('tkinter_simpledialog', 'SimpleDialog', 'tkinter.simpledialog')][MovedModule('tkinter_tix', 'Tix', 'tkinter.tix')][MovedModule('tkinter_ttk', 'ttk', 'tkinter.ttk')][MovedModule('tkinter_constants', 'Tkconstants', 'tkinter.constants')][MovedModule('tkinter_dnd', 'Tkdnd', 'tkinter.dnd')][MovedModule('tkinter_colorchooser', 'tkColorChooser', 'tkinter.colorchooser')][MovedModule('tkinter_commondialog', 'tkCommonDialog', 'tkinter.commondialog')][MovedModule('tkinter_tkfiledialog', 'tkFileDialog', 'tkinter.filedialog')][MovedModule('tkinter_font', 'tkFont', 'tkinter.font')][MovedModule('tkinter_messagebox', 'tkMessageBox', 'tkinter.messagebox')][MovedModule('tkinter_tksimpledialog', 'tkSimpleDialog', 'tkinter.simpledialog')][MovedModule('urllib_parse', __name__ + '.moves.urllib_parse', 'urllib.parse')][MovedModule('urllib_error', __name__ + '.moves.urllib_error', 'urllib.error')][MovedModule('urllib', __name__ + '.moves.urllib', __name__ + '.moves.urllib')][MovedModule('urllib_robotparser', 'robotparser', 'urllib.robotparser')][MovedModule('xmlrpc_client', 'xmlrpclib', 'xmlrpc.client')][MovedModule('xmlrpc_server', 'SimpleXMLRPCServer', 'xmlrpc.server')]
if sys.platform == 'win32':
    _moved_attributes += [
        MovedModule('winreg', '_winreg')]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
    if not isinstance(attr, MovedModule):
        continue
    _importer._add_module(attr, 'moves.' + attr.name)
del attr
_MovedItems._moved_attributes = _moved_attributes
moves = _MovedItems(__name__ + '.moves')
_importer._add_module(moves, 'moves')

class Module_six_moves_urllib_parse(_LazyModule):
    '''Lazy loading of moved objects in six.moves.urllib_parse'''
    pass

_urllib_parse_moved_attributes = [
    MovedAttribute('ParseResult', 'urlparse', 'urllib.parse'),
    MovedAttribute('SplitResult', 'urlparse', 'urllib.parse'),
    MovedAttribute('parse_qs', 'urlparse', 'urllib.parse'),
    MovedAttribute('parse_qsl', 'urlparse', 'urllib.parse'),
    MovedAttribute('urldefrag', 'urlparse', 'urllib.parse'),
    MovedAttribute('urljoin', 'urlparse', 'urllib.parse'),
    MovedAttribute('urlparse', 'urlparse', 'urllib.parse'),
    MovedAttribute('urlsplit', 'urlparse', 'urllib.parse'),
    MovedAttribute('urlunparse', 'urlparse', 'urllib.parse'),
    MovedAttribute('urlunsplit', 'urlparse', 'urllib.parse'),
    MovedAttribute('quote', 'urllib', 'urllib.parse'),
    MovedAttribute('quote_plus', 'urllib', 'urllib.parse'),
    MovedAttribute('unquote', 'urllib', 'urllib.parse'),
    MovedAttribute('unquote_plus', 'urllib', 'urllib.parse'),
    MovedAttribute('unquote_to_bytes', 'urllib', 'urllib.parse', 'unquote', 'unquote_to_bytes'),
    MovedAttribute('urlencode', 'urllib', 'urllib.parse'),
    MovedAttribute('splitquery', 'urllib', 'urllib.parse'),
    MovedAttribute('splittag', 'urllib', 'urllib.parse'),
    MovedAttribute('splituser', 'urllib', 'urllib.parse'),
    MovedAttribute('splitvalue', 'urllib', 'urllib.parse'),
    MovedAttribute('uses_fragment', 'urlparse', 'urllib.parse'),
    MovedAttribute('uses_netloc', 'urlparse', 'urllib.parse'),
    MovedAttribute('uses_params', 'urlparse', 'urllib.parse'),
    MovedAttribute('uses_query', 'urlparse', 'urllib.parse'),
    MovedAttribute('uses_relative', 'urlparse', 'urllib.parse')]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr
Module_six_moves_urllib_parse._moved_attributes = _urllib_parse_moved_attributes
_importer._add_module(Module_six_moves_urllib_parse(__name__ + '.moves.urllib_parse'), 'moves.urllib_parse', 'moves.urllib.parse')

class Module_six_moves_urllib_error(_LazyModule):
    '''Lazy loading of moved objects in six.moves.urllib_error'''
    pass

_urllib_error_moved_attributes = [
    MovedAttribute('URLError', 'urllib2', 'urllib.error'),
    MovedAttribute('HTTPError', 'urllib2', 'urllib.error'),
    MovedAttribute('ContentTooShortError', 'urllib', 'urllib.error')]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr
Module_six_moves_urllib_error._moved_attributes = _urllib_error_moved_attributes
_importer._add_module(Module_six_moves_urllib_error(__name__ + '.moves.urllib.error'), 'moves.urllib_error', 'moves.urllib.error')

class Module_six_moves_urllib_request(_LazyModule):
    '''Lazy loading of moved objects in six.moves.urllib_request'''
    pass

_urllib_request_moved_attributes = [][MovedAttribute('urlopen', 'urllib2', 'urllib.request')][MovedAttribute('install_opener', 'urllib2', 'urllib.request')][MovedAttribute('build_opener', 'urllib2', 'urllib.request')][MovedAttribute('pathname2url', 'urllib', 'urllib.request')][MovedAttribute('url2pathname', 'urllib', 'urllib.request')][MovedAttribute('getproxies', 'urllib', 'urllib.request')][MovedAttribute('Request', 'urllib2', 'urllib.request')][MovedAttribute('OpenerDirector', 'urllib2', 'urllib.request')][MovedAttribute('HTTPDefaultErrorHandler', 'urllib2', 'urllib.request')][MovedAttribute('HTTPRedirectHandler', 'urllib2', 'urllib.request')][MovedAttribute('HTTPCookieProcessor', 'urllib2', 'urllib.request')][MovedAttribute('ProxyHandler', 'urllib2', 'urllib.request')][MovedAttribute('BaseHandler', 'urllib2', 'urllib.request')][MovedAttribute('HTTPPasswordMgr', 'urllib2', 'urllib.request')][MovedAttribute('HTTPPasswordMgrWithDefaultRealm', 'urllib2', 'urllib.request')][MovedAttribute('AbstractBasicAuthHandler', 'urllib2', 'urllib.request')][MovedAttribute('HTTPBasicAuthHandler', 'urllib2', 'urllib.request')][MovedAttribute('ProxyBasicAuthHandler', 'urllib2', 'urllib.request')][MovedAttribute('AbstractDigestAuthHandler', 'urllib2', 'urllib.request')][MovedAttribute('HTTPDigestAuthHandler', 'urllib2', 'urllib.request')][MovedAttribute('ProxyDigestAuthHandler', 'urllib2', 'urllib.request')][MovedAttribute('HTTPHandler', 'urllib2', 'urllib.request')][MovedAttribute('HTTPSHandler', 'urllib2', 'urllib.request')][MovedAttribute('FileHandler', 'urllib2', 'urllib.request')][MovedAttribute('FTPHandler', 'urllib2', 'urllib.request')][MovedAttribute('CacheFTPHandler', 'urllib2', 'urllib.request')][MovedAttribute('UnknownHandler', 'urllib2', 'urllib.request')][MovedAttribute('HTTPErrorProcessor', 'urllib2', 'urllib.request')][MovedAttribute('urlretrieve', 'urllib', 'urllib.request')][MovedAttribute('urlcleanup', 'urllib', 'urllib.request')][MovedAttribute('proxy_bypass', 'urllib', 'urllib.request')][MovedAttribute('parse_http_list', 'urllib2', 'urllib.request')][MovedAttribute('parse_keqv_list', 'urllib2', 'urllib.request')]
if sys.version_info[:2] < (3, 14):
    _urllib_request_moved_attributes.extend([
        MovedAttribute('URLopener', 'urllib', 'urllib.request'),
        MovedAttribute('FancyURLopener', 'urllib', 'urllib.request')])
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr
Module_six_moves_urllib_request._moved_attributes = _urllib_request_moved_attributes
_importer._add_module(Module_six_moves_urllib_request(__name__ + '.moves.urllib.request'), 'moves.urllib_request', 'moves.urllib.request')

class Module_six_moves_urllib_response(_LazyModule):
    '''Lazy loading of moved objects in six.moves.urllib_response'''
    pass

_urllib_response_moved_attributes = [
    MovedAttribute('addbase', 'urllib', 'urllib.response'),
    MovedAttribute('addclosehook', 'urllib', 'urllib.response'),
    MovedAttribute('addinfo', 'urllib', 'urllib.response'),
    MovedAttribute('addinfourl', 'urllib', 'urllib.response')]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr
Module_six_moves_urllib_response._moved_attributes = _urllib_response_moved_attributes
_importer._add_module(Module_six_moves_urllib_response(__name__ + '.moves.urllib.response'), 'moves.urllib_response', 'moves.urllib.response')

class Module_six_moves_urllib_robotparser(_LazyModule):
    '''Lazy loading of moved objects in six.moves.urllib_robotparser'''
    pass

_urllib_robotparser_moved_attributes = [
    MovedAttribute('RobotFileParser', 'robotparser', 'urllib.robotparser')]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr
Module_six_moves_urllib_robotparser._moved_attributes = _urllib_robotparser_moved_attributes
_importer._add_module(Module_six_moves_urllib_robotparser(__name__ + '.moves.urllib.robotparser'), 'moves.urllib_robotparser', 'moves.urllib.robotparser')

class Module_six_moves_urllib(types.ModuleType):
    '''Create a six.moves.urllib namespace that resembles the Python 3 namespace'''
    __path__ = []
    parse = _importer._get_module('moves.urllib_parse')
    error = _importer._get_module('moves.urllib_error')
    request = _importer._get_module('moves.urllib_request')
    response = _importer._get_module('moves.urllib_response')
    robotparser = _importer._get_module('moves.urllib_robotparser')
    
    def __dir__(self):
        return [
            'parse',
            'error',
            'request',
            'response',
            'robotparser']


_importer._add_module(Module_six_moves_urllib(__name__ + '.moves.urllib'), 'moves.urllib')

def add_move(move):
    '''Add an item to six.moves.'''
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    '''Remove item from six.moves.'''
    delattr(_MovedItems, name)
    return None
# WARNING: Decompyle incomplete

advance_iterator = next
next = advance_iterator
callable = callable
_add_doc(get_unbound_function, 'Get the function out of a possibly unbound function')
get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)
_add_doc(iterkeys, 'Return an iterator over the keys of a dictionary.')
_add_doc(itervalues, 'Return an iterator over the values of a dictionary.')
_add_doc(iteritems, 'Return an iterator over the (key, value) pairs of a dictionary.')
_add_doc(iterlists, 'Return an iterator over the (key, [values]) pairs of a dictionary.')
_add_doc(b, 'Byte literal')
_add_doc(u, 'Text literal')

def assertCountEqual(self, *args, **kwargs):
    pass
# WARNING: Decompyle incomplete


def assertRaisesRegex(self, *args, **kwargs):
    pass
# WARNING: Decompyle incomplete


def assertRegex(self, *args, **kwargs):
    pass
# WARNING: Decompyle incomplete


def assertNotRegex(self, *args, **kwargs):
    pass
# WARNING: Decompyle incomplete

print_ = getattr(moves.builtins, 'print', None)
# WARNING: Decompyle incomplete
