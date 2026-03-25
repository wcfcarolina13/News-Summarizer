# Source Generated with Decompyle++
# File: cgi.pyc (Python 3.12)

'''Support module for CGI (Common Gateway Interface) scripts.

This module defines a number of utilities for use by CGI scripts
written in Python.

The global variable maxlen can be set to an integer indicating the maximum size
of a POST request. POST requests larger than this size will result in a
ValueError being raised during parsing. The default value of this variable is 0,
meaning the request size is unlimited.
'''
__version__ = '2.6'
from io import StringIO, BytesIO, TextIOWrapper
from collections.abc import Mapping
import sys
import os
import urllib.parse as urllib
from email.parser import FeedParser
from email.message import Message
import html
import locale
import tempfile
import warnings
__all__ = [
    'MiniFieldStorage',
    'FieldStorage',
    'parse',
    'parse_multipart',
    'parse_header',
    'test',
    'print_exception',
    'print_environ',
    'print_form',
    'print_directory',
    'print_arguments',
    'print_environ_usage']
warnings._deprecated(__name__, remove = (3, 13))
logfile = ''
logfp = None

def initlog(*allargs):
    '''Write a log message, if there is a log file.

    Even though this function is called initlog(), you should always
    use log(); log is a variable that is set either to initlog
    (initially), to dolog (once the log file has been opened), or to
    nolog (when logging is disabled).

    The first argument is a format string; the remaining arguments (if
    any) are arguments to the % operator, so e.g.
        log("%s: %s", "a", "b")
    will write "a: b" to the log file, followed by a newline.

    If the global logfp is not None, it should be a file object to
    which log data is written.

    If the global logfp is None, the global logfile may be a string
    giving a filename to open, in append mode.  This file should be
    world writable!!!  If the file can\'t be opened, logging is
    silently disabled (since there is no safe place where we could
    send an error message).

    '''
    global logfp, log, log
    warnings.warn('cgi.log() is deprecated as of 3.10. Use logging instead', DeprecationWarning, stacklevel = 2)
    if not logfile and logfp:
        logfp = open(logfile, 'a', encoding = 'locale')
    if not logfp:
        log = nolog
    else:
        log = dolog
# WARNING: Decompyle incomplete


def dolog(fmt, *args):
    '''Write a log message to the log file.  See initlog() for docs.'''
    logfp.write(fmt % args + '\n')


def nolog(*allargs):
    '''Dummy function, assigned to log when logging is disabled.'''
    pass


def closelog():
    '''Close the log file.'''
    global logfile, logfp, log
    logfile = ''
    if logfp:
        logfp.close()
        logfp = None
    log = initlog

log = initlog
maxlen = 0

def parse(fp, environ, keep_blank_values, strict_parsing, separator = (None, os.environ, 0, 0, '&')):
    '''Parse a query in the environment or from a file (default stdin)

        Arguments, all optional:

        fp              : file pointer; default: sys.stdin.buffer

        environ         : environment dictionary; default: os.environ

        keep_blank_values: flag indicating whether blank values in
            percent-encoded forms should be treated as blank strings.
            A true value indicates that blanks should be retained as
            blank strings.  The default false value indicates that
            blank values are to be ignored and treated as if they were
            not included.

        strict_parsing: flag indicating what to do with parsing errors.
            If false (the default), errors are silently ignored.
            If true, errors raise a ValueError exception.

        separator: str. The symbol to use for separating the query arguments.
            Defaults to &.
    '''
    pass
# WARNING: Decompyle incomplete


def parse_multipart(fp, pdict, encoding, errors, separator = ('utf-8', 'replace', '&')):
    '''Parse multipart input.

    Arguments:
    fp   : input file
    pdict: dictionary containing other parameters of content-type header
    encoding, errors: request encoding and error handler, passed to
        FieldStorage

    Returns a dictionary just like parse_qs(): keys are the field names, each
    value is a list of values for that field. For non-file fields, the value
    is a list of strings.
    '''
    boundary = pdict['boundary'].decode('ascii')
    ctype = 'multipart/form-data; boundary={}'.format(boundary)
    headers = Message()
    headers.set_type(ctype)
    headers['Content-Length'] = pdict['CONTENT-LENGTH']
    fs = FieldStorage(fp, headers = headers, encoding = encoding, errors = errors, environ = {
        'REQUEST_METHOD': 'POST' }, separator = separator)
# WARNING: Decompyle incomplete


def _parseparam(s):
    pass
# WARNING: Decompyle incomplete


def parse_header(line):
    '''Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    '''
    parts = _parseparam(';' + line)
    key = parts.__next__()
    pdict = { }
    for p in parts:
        i = p.find('=')
        if not i >= 0:
            continue
        name = p[:i].strip().lower()
        value = p[i + 1:].strip()
        pdict[name] = value
    return (key, pdict)


class MiniFieldStorage:
    '''Like FieldStorage, for use when no file uploads are possible.'''
    filename = None
    list = None
    type = None
    file = None
    type_options = { }
    disposition = None
    disposition_options = { }
    headers = { }
    
    def __init__(self, name, value):
        '''Constructor from field name and value.'''
        self.name = name
        self.value = value

    
    def __repr__(self):
        '''Return printable representation.'''
        return f'''MiniFieldStorage({self.name!r}, {self.value!r})'''



class FieldStorage:
    """Store a sequence of fields, reading multipart/form-data.

    This class provides naming, typing, files stored on disk, and
    more.  At the top level, it is accessible like a dictionary, whose
    keys are the field names.  (Note: None can occur as a field name.)
    The items are either a Python list (if there's multiple values) or
    another FieldStorage or MiniFieldStorage object.  If it's a single
    object, it has the following attributes:

    name: the field name, if specified; otherwise None

    filename: the filename, if specified; otherwise None; this is the
        client side filename, *not* the file name on which it is
        stored (that's a temporary file you don't deal with)

    value: the value as a *string*; for file uploads, this
        transparently reads the file every time you request the value
        and returns *bytes*

    file: the file(-like) object from which you can read the data *as
        bytes* ; None if the data is stored a simple string

    type: the content-type, or None if not specified

    type_options: dictionary of options specified on the content-type
        line

    disposition: content-disposition, or None if not specified

    disposition_options: dictionary of corresponding options

    headers: a dictionary(-like) object (sometimes email.message.Message or a
        subclass thereof) containing *all* headers

    The class is subclassable, mostly for the purpose of overriding
    the make_file() method, which is called internally to come up with
    a file open for reading and writing.  This makes it possible to
    override the default choice of storing all files in a temporary
    directory and unlinking them as soon as they have been opened.

    """
    
    def __init__(self, fp, headers, outerboundary, environ, keep_blank_values, strict_parsing, limit, encoding, errors, max_num_fields, separator = (None, None, b'', os.environ, 0, 0, None, 'utf-8', 'replace', None, '&')):
        '''Constructor.  Read multipart/* until last part.

        Arguments, all optional:

        fp              : file pointer; default: sys.stdin.buffer
            (not used when the request method is GET)
            Can be :
            1. a TextIOWrapper object
            2. an object whose read() and readline() methods return bytes

        headers         : header dictionary-like object; default:
            taken from environ as per CGI spec

        outerboundary   : terminating multipart boundary
            (for internal use only)

        environ         : environment dictionary; default: os.environ

        keep_blank_values: flag indicating whether blank values in
            percent-encoded forms should be treated as blank strings.
            A true value indicates that blanks should be retained as
            blank strings.  The default false value indicates that
            blank values are to be ignored and treated as if they were
            not included.

        strict_parsing: flag indicating what to do with parsing errors.
            If false (the default), errors are silently ignored.
            If true, errors raise a ValueError exception.

        limit : used internally to read parts of multipart/form-data forms,
            to exit from the reading loop when reached. It is the difference
            between the form content-length and the number of bytes already
            read

        encoding, errors : the encoding and error handler used to decode the
            binary stream to strings. Must be the same as the charset defined
            for the page sending the form (content-type : meta http-equiv or
            header)

        max_num_fields: int. If set, then __init__ throws a ValueError
            if there are more than n fields read by parse_qsl().

        '''
        method = 'GET'
        self.keep_blank_values = keep_blank_values
        self.strict_parsing = strict_parsing
        self.max_num_fields = max_num_fields
        self.separator = separator
        if 'REQUEST_METHOD' in environ:
            method = environ['REQUEST_METHOD'].upper()
        self.qs_on_post = None
    # WARNING: Decompyle incomplete

    
    def __del__(self):
        self.file.close()
        return None
    # WARNING: Decompyle incomplete

    
    def __enter__(self):
        return self

    
    def __exit__(self, *args):
        self.file.close()

    
    def __repr__(self):
        '''Return a printable representation.'''
        return f'''FieldStorage({self.name!r}, {self.filename!r}, {self.value!r})'''

    
    def __iter__(self):
        return iter(self.keys())

    
    def __getattr__(self, name):
        if name != 'value':
            raise AttributeError(name)
        if self.file:
            self.file.seek(0)
            value = self.file.read()
            self.file.seek(0)
            return value
    # WARNING: Decompyle incomplete

    
    def __getitem__(self, key):
        '''Dictionary style indexing.'''
        pass
    # WARNING: Decompyle incomplete

    
    def getvalue(self, key, default = (None,)):
        """Dictionary style get() method, including 'value' lookup."""
        pass
    # WARNING: Decompyle incomplete

    
    def getfirst(self, key, default = (None,)):
        ''' Return the first value received.'''
        if key in self:
            value = self[key]
            if isinstance(value, list):
                return value[0].value
            return None.value

    
    def getlist(self, key):
        ''' Return list of received values.'''
        pass
    # WARNING: Decompyle incomplete

    
    def keys(self):
        '''Dictionary style keys() method.'''
        pass
    # WARNING: Decompyle incomplete

    
    def __contains__(self, key):
        '''Dictionary style __contains__ method.'''
        pass
    # WARNING: Decompyle incomplete

    
    def __len__(self):
        '''Dictionary style len(x) support.'''
        return len(self.keys())

    
    def __bool__(self):
        pass
    # WARNING: Decompyle incomplete

    
    def read_urlencoded(self):
        '''Internal: read data in query string format.'''
        qs = self.fp.read(self.length)
        if not isinstance(qs, bytes):
            raise ValueError(f'''{self.fp!s} should return bytes, got {type(qs).__name__!s}''')
        qs = qs.decode(self.encoding, self.errors)
        if self.qs_on_post:
            qs += '&' + self.qs_on_post
        query = urllib.parse.parse_qsl(qs, self.keep_blank_values, self.strict_parsing, encoding = self.encoding, errors = self.errors, max_num_fields = self.max_num_fields, separator = self.separator)
    # WARNING: Decompyle incomplete

    FieldStorageClass = None
    
    def read_multi(self, environ, keep_blank_values, strict_parsing):
        '''Internal: read a part that is itself multipart.'''
        ib = self.innerboundary
        if not valid_boundary(ib):
            raise ValueError(f'''Invalid boundary in multipart form: {ib!r}''')
        self.list = []
        if self.qs_on_post:
            query = urllib.parse.parse_qsl(self.qs_on_post, self.keep_blank_values, self.strict_parsing, encoding = self.encoding, errors = self.errors, max_num_fields = self.max_num_fields, separator = self.separator)
            (lambda .0: pass# WARNING: Decompyle incomplete
)(query())
        if not self.FieldStorageClass:
            self.FieldStorageClass
        klass = self.__class__
        first_line = self.fp.readline()
        if not isinstance(first_line, bytes):
            raise ValueError(f'''{self.fp!s} should return bytes, got {type(first_line).__name__!s}''')
        if first_line.strip() != b'--' + self.innerboundary and first_line:
            self.fp.readline() = self, self.bytes_read += len(first_line), .bytes_read
            if first_line.strip() != b'--' + self.innerboundary and first_line:
                continue
        self.max_num_fields = self, self.bytes_read += len(first_line), .bytes_read
    # WARNING: Decompyle incomplete

    
    def read_single(self):
        '''Internal: read an atomic part.'''
        if self.length >= 0:
            self.read_binary()
            self.skip_lines()
        else:
            self.read_lines()
        self.file.seek(0)

    bufsize = 8192
    
    def read_binary(self):
        '''Internal: read binary data.'''
        self.file = self.make_file()
        todo = self.length
        if todo >= 0:
            if todo > 0:
                data = self.fp.read(min(todo, self.bufsize))
                if not isinstance(data, bytes):
                    raise ValueError(f'''{self.fp!s} should return bytes, got {type(data).__name__!s}''')
                if not data:
                    -1 = self, self.bytes_read += len(data), .bytes_read
                    return None
                self.file.write(data)
                todo = todo - len(data)
                if todo > 0:
                    continue
                return None
            return None

    
    def read_lines(self):
        '''Internal: read lines until EOF or outerboundary.'''
        if self._binary_file:
            self.file = BytesIO()
            self._FieldStorage__file = BytesIO()
        else:
            self.file = StringIO()
            self._FieldStorage__file = StringIO()
        if self.outerboundary:
            self.read_lines_to_outerboundary()
            return None
        self.read_lines_to_eof()

    
    def __write(self, line):
        '''line is always bytes, not string'''
        pass
    # WARNING: Decompyle incomplete

    
    def read_lines_to_eof(self):
        '''Internal: read lines until EOF.'''
        line = self.fp.readline(65536)
        if not line:
            -1 = self, self.bytes_read += len(line), .bytes_read
            return None
        self.__write(line)
        continue

    
    def read_lines_to_outerboundary(self):
        '''Internal: read lines until outerboundary.
        Data is read as bytes: boundaries and line ends must be converted
        to bytes for comparisons.
        '''
        next_boundary = b'--' + self.outerboundary
        last_boundary = next_boundary + b'--'
        delim = b''
        last_line_lfend = True
        _read = 0
    # WARNING: Decompyle incomplete

    
    def skip_lines(self):
        '''Internal: skip lines until outer boundary if defined.'''
        if self.outerboundary or self.done:
            return None
        next_boundary = b'--' + self.outerboundary
        last_boundary = next_boundary + b'--'
        last_line_lfend = True
        line = self.fp.readline(65536)
        if not line:
            -1 = self, self.bytes_read += len(line), .bytes_read
            return None
        if line.endswith(b'--') and last_line_lfend:
            strippedline = line.strip()
            if strippedline == next_boundary:
                return None
            if strippedline == last_boundary:
                self.done = 1
                return None
        last_line_lfend = line.endswith(b'\n')
        continue

    
    def make_file(self):
        """Overridable: return a readable & writable file.

        The file will be used as follows:
        - data is written to it
        - seek(0)
        - data is read from it

        The file is opened in binary mode for files, in text mode
        for other fields

        This version opens a temporary file for reading and writing,
        and immediately deletes (unlinks) it.  The trick (on Unix!) is
        that the file can still be used, but it can't be opened by
        another process, and it will automatically be deleted when it
        is closed or when the current process terminates.

        If you want a more permanent file, you derive a class which
        overrides this method.  If you want a visible temporary file
        that is nevertheless automatically deleted when the script
        terminates, try defining a __del__ method in a derived class
        which unlinks the temporary files you have created.

        """
        if self._binary_file:
            return tempfile.TemporaryFile('wb+')
        return None.TemporaryFile('w+', encoding = self.encoding, newline = '\n')



def test(environ = (os.environ,)):
    '''Robust test CGI script, usable as main program.

    Write minimal HTTP headers and dump all information provided to
    the script in HTML form.

    '''
    global maxlen
    print('Content-type: text/html')
    print()
    sys.stderr = sys.stdout
    form = FieldStorage()
    print_directory()
    print_arguments()
    print_form(form)
    print_environ(environ)
    print_environ_usage()
    
    def f():
        exec('testing print_exception() -- <I>italics?</I>')

    
    def g(f = (f,)):
        f()

    print('<H3>What follows is a test, not an actual exception:</H3>')
    g()
    print('<H1>Second try with a small maxlen...</H1>')
    maxlen = 50
    form = FieldStorage()
    print_directory()
    print_arguments()
    print_form(form)
    print_environ(environ)
    return None
# WARNING: Decompyle incomplete


def print_exception(type, value, tb, limit = (None, None, None, None)):
    pass
# WARNING: Decompyle incomplete


def print_environ(environ = (os.environ,)):
    '''Dump the shell environment as HTML.'''
    keys = sorted(environ.keys())
    print()
    print('<H3>Shell Environment:</H3>')
    print('<DL>')
    for key in keys:
        print('<DT>', html.escape(key), '<DD>', html.escape(environ[key]))
    print('</DL>')
    print()


def print_form(form):
    '''Dump the contents of a form as HTML.'''
    keys = sorted(form.keys())
    print()
    print('<H3>Form Contents:</H3>')
    if not keys:
        print('<P>No form fields.')
    print('<DL>')
    for key in keys:
        print('<DT>' + html.escape(key) + ':', end = ' ')
        value = form[key]
        print('<i>' + html.escape(repr(type(value))) + '</i>')
        print('<DD>' + html.escape(repr(value)))
    print('</DL>')
    print()


def print_directory():
    '''Dump the current directory as HTML.'''
    print()
    print('<H3>Current Working Directory:</H3>')
    pwd = os.getcwd()
    print(html.escape(pwd))
    print()
    return None
# WARNING: Decompyle incomplete


def print_arguments():
    print()
    print('<H3>Command Line Arguments:</H3>')
    print()
    print(sys.argv)
    print()


def print_environ_usage():
    '''Dump a list of environment variables used by CGI as HTML.'''
    print('\n<H3>These environment variables could have been set:</H3>\n<UL>\n<LI>AUTH_TYPE\n<LI>CONTENT_LENGTH\n<LI>CONTENT_TYPE\n<LI>DATE_GMT\n<LI>DATE_LOCAL\n<LI>DOCUMENT_NAME\n<LI>DOCUMENT_ROOT\n<LI>DOCUMENT_URI\n<LI>GATEWAY_INTERFACE\n<LI>LAST_MODIFIED\n<LI>PATH\n<LI>PATH_INFO\n<LI>PATH_TRANSLATED\n<LI>QUERY_STRING\n<LI>REMOTE_ADDR\n<LI>REMOTE_HOST\n<LI>REMOTE_IDENT\n<LI>REMOTE_USER\n<LI>REQUEST_METHOD\n<LI>SCRIPT_NAME\n<LI>SERVER_NAME\n<LI>SERVER_PORT\n<LI>SERVER_PROTOCOL\n<LI>SERVER_ROOT\n<LI>SERVER_SOFTWARE\n</UL>\nIn addition, HTTP headers sent by the server may be passed in the\nenvironment as well.  Here are some common variable names:\n<UL>\n<LI>HTTP_ACCEPT\n<LI>HTTP_CONNECTION\n<LI>HTTP_HOST\n<LI>HTTP_PRAGMA\n<LI>HTTP_REFERER\n<LI>HTTP_USER_AGENT\n</UL>\n')


def valid_boundary(s):
    import re
    if isinstance(s, bytes):
        _vb_pattern = b'^[ -~]{0,200}[!-~]$'
    else:
        _vb_pattern = '^[ -~]{0,200}[!-~]$'
    return re.match(_vb_pattern, s)

if __name__ == '__main__':
    test()
    return None
