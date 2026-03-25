# Source Generated with Decompyle++
# File: doctest.pyc (Python 3.12)

'''Module doctest -- a framework for running examples in docstrings.

In simplest use, end each module M to be tested with:

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

Then running the module as a script will cause the examples in the
docstrings to get executed and verified:

python M.py

This won\'t display anything unless an example fails, in which case the
failing example(s) and the cause(s) of the failure(s) are printed to stdout
(why not stderr? because stderr is a lame hack <0.2 wink>), and the final
line of output is "Test failed.".

Run it with the -v switch instead:

python M.py -v

and a detailed report of all examples tried is printed to stdout, along
with assorted summaries at the end.

You can force verbose mode by passing "verbose=True" to testmod, or prohibit
it by passing "verbose=False".  In either of those cases, sys.argv is not
examined by testmod.

There are a variety of other ways to run doctests, including integration
with the unittest framework, and support for running non-Python text
files containing doctests.  There are also many ways to override parts
of doctest\'s default behaviors.  See the Library Reference Manual for
details.
'''
__docformat__ = 'reStructuredText en'
__all__ = [
    'register_optionflag',
    'DONT_ACCEPT_TRUE_FOR_1',
    'DONT_ACCEPT_BLANKLINE',
    'NORMALIZE_WHITESPACE',
    'ELLIPSIS',
    'SKIP',
    'IGNORE_EXCEPTION_DETAIL',
    'COMPARISON_FLAGS',
    'REPORT_UDIFF',
    'REPORT_CDIFF',
    'REPORT_NDIFF',
    'REPORT_ONLY_FIRST_FAILURE',
    'REPORTING_FLAGS',
    'FAIL_FAST',
    'Example',
    'DocTest',
    'DocTestParser',
    'DocTestFinder',
    'DocTestRunner',
    'OutputChecker',
    'DocTestFailure',
    'UnexpectedException',
    'DebugRunner',
    'testmod',
    'testfile',
    'run_docstring_examples',
    'DocTestSuite',
    'DocFileSuite',
    'set_unittest_reportflags',
    'script_from_examples',
    'testsource',
    'debug_src',
    'debug']
import __future__
import difflib
import inspect
import linecache
import os
import pdb
import re
import sys
import traceback
import unittest
from io import StringIO, IncrementalNewlineDecoder
from collections import namedtuple
TestResults = namedtuple('TestResults', 'failed attempted')
OPTIONFLAGS_BY_NAME = { }

def register_optionflag(name):
    return OPTIONFLAGS_BY_NAME.setdefault(name, 1 << len(OPTIONFLAGS_BY_NAME))

DONT_ACCEPT_TRUE_FOR_1 = register_optionflag('DONT_ACCEPT_TRUE_FOR_1')
DONT_ACCEPT_BLANKLINE = register_optionflag('DONT_ACCEPT_BLANKLINE')
NORMALIZE_WHITESPACE = register_optionflag('NORMALIZE_WHITESPACE')
ELLIPSIS = register_optionflag('ELLIPSIS')
SKIP = register_optionflag('SKIP')
IGNORE_EXCEPTION_DETAIL = register_optionflag('IGNORE_EXCEPTION_DETAIL')
COMPARISON_FLAGS = DONT_ACCEPT_TRUE_FOR_1 | DONT_ACCEPT_BLANKLINE | NORMALIZE_WHITESPACE | ELLIPSIS | SKIP | IGNORE_EXCEPTION_DETAIL
REPORT_UDIFF = register_optionflag('REPORT_UDIFF')
REPORT_CDIFF = register_optionflag('REPORT_CDIFF')
REPORT_NDIFF = register_optionflag('REPORT_NDIFF')
REPORT_ONLY_FIRST_FAILURE = register_optionflag('REPORT_ONLY_FIRST_FAILURE')
FAIL_FAST = register_optionflag('FAIL_FAST')
REPORTING_FLAGS = REPORT_UDIFF | REPORT_CDIFF | REPORT_NDIFF | REPORT_ONLY_FIRST_FAILURE | FAIL_FAST
BLANKLINE_MARKER = '<BLANKLINE>'
ELLIPSIS_MARKER = '...'

def _extract_future_flags(globs):
    '''
    Return the compiler-flags associated with the future features that
    have been imported into the given namespace (globs).
    '''
    flags = 0
    for fname in __future__.all_feature_names:
        feature = globs.get(fname, None)
        if not feature is getattr(__future__, fname):
            continue
        flags |= feature.compiler_flag
    return flags


def _normalize_module(module, depth = (2,)):
    '''
    Return the module specified by `module`.  In particular:
      - If `module` is a module, then return module.
      - If `module` is a string, then import and return the
        module with that name.
      - If `module` is None, then return the calling module.
        The calling module is assumed to be the module of
        the stack frame at the given depth in the call stack.
    '''
    if inspect.ismodule(module):
        return module
    if None(module, str):
        return __import__(module, globals(), locals(), [
            '*'])
# WARNING: Decompyle incomplete


def _newline_convert(data):
    return IncrementalNewlineDecoder(None, True).decode(data, True)


def _load_testfile(filename, package, module_relative, encoding):
    pass
# WARNING: Decompyle incomplete


def _indent(s, indent = (4,)):
    '''
    Add the given number of space characters to the beginning of
    every non-blank line in `s`, and return the result.
    '''
    return re.sub('(?m)^(?!$)', indent * ' ', s)


def _exception_traceback(exc_info):
    '''
    Return a string containing a traceback message for the given
    exc_info tuple (as returned by sys.exc_info()).
    '''
    excout = StringIO()
    (exc_type, exc_val, exc_tb) = exc_info
    traceback.print_exception(exc_type, exc_val, exc_tb, file = excout)
    return excout.getvalue()


class _SpoofOut(StringIO):
    
    def getvalue(self):
        result = StringIO.getvalue(self)
        if not result and result.endswith('\n'):
            result += '\n'
        return result

    
    def truncate(self, size = (None,)):
        self.seek(size)
        StringIO.truncate(self)



def _ellipsis_match(want, got):
    """
    Essentially the only subtle case:
    >>> _ellipsis_match('aa...aa', 'aaa')
    False
    """
    if ELLIPSIS_MARKER not in want:
        return want == got
    ws = None.split(ELLIPSIS_MARKER)
# WARNING: Decompyle incomplete


def _comment_line(line):
    '''Return a commented form of the given line'''
    line = line.rstrip()
    if line:
        return '# ' + line


def _strip_exception_details(msg):
    end = len(msg)
    start = 0
    i = msg.find('\n')
    if i >= 0:
        end = i
    i = msg.find(':', 0, end)
    if i >= 0:
        end = i
    i = msg.rfind('.', 0, end)
    if i >= 0:
        start = i + 1
    return msg[start:end]


class _OutputRedirectingPdb(pdb.Pdb):
    '''
    A specialized version of the python debugger that redirects stdout
    to a given stream when interacting with the user.  Stdout is *not*
    redirected when traced code is executed.
    '''
    
    def __init__(self, out):
        self._OutputRedirectingPdb__out = out
        self._OutputRedirectingPdb__debugger_used = False
        pdb.Pdb.__init__(self, stdout = out, nosigint = True)
        self.use_rawinput = 1

    
    def set_trace(self, frame = (None,)):
        self._OutputRedirectingPdb__debugger_used = True
    # WARNING: Decompyle incomplete

    
    def set_continue(self):
        if self._OutputRedirectingPdb__debugger_used:
            pdb.Pdb.set_continue(self)
            return None

    
    def trace_dispatch(self, *args):
        save_stdout = sys.stdout
        sys.stdout = self._OutputRedirectingPdb__out
    # WARNING: Decompyle incomplete



def _module_relative_path(module, test_path):
    if not inspect.ismodule(module):
        raise TypeError('Expected a module: %r' % module)
    if test_path.startswith('/'):
        raise ValueError('Module-relative files may not have absolute paths')
# WARNING: Decompyle incomplete


class Example:
    """
    A single doctest example, consisting of source code and expected
    output.  `Example` defines the following attributes:

      - source: A single Python statement, always ending with a newline.
        The constructor adds a newline if needed.

      - want: The expected output from running the source code (either
        from stdout, or a traceback in case of exception).  `want` ends
        with a newline unless it's empty, in which case it's an empty
        string.  The constructor adds a newline if needed.

      - exc_msg: The exception message generated by the example, if
        the example is expected to generate an exception; or `None` if
        it is not expected to generate an exception.  This exception
        message is compared against the return value of
        `traceback.format_exception_only()`.  `exc_msg` ends with a
        newline unless it's `None`.  The constructor adds a newline
        if needed.

      - lineno: The line number within the DocTest string containing
        this Example where the Example begins.  This line number is
        zero-based, with respect to the beginning of the DocTest.

      - indent: The example's indentation in the DocTest string.
        I.e., the number of space characters that precede the
        example's first prompt.

      - options: A dictionary mapping from option flags to True or
        False, which is used to override default options for this
        example.  Any option flags not contained in this dictionary
        are left at their default value (as specified by the
        DocTestRunner's optionflags).  By default, no options are set.
    """
    
    def __init__(self, source, want, exc_msg, lineno, indent, options = (None, 0, 0, None)):
        if not source.endswith('\n'):
            source += '\n'
        if not want and want.endswith('\n'):
            want += '\n'
    # WARNING: Decompyle incomplete

    
    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        if None.source == other.source:
            None.source == other.source
            if self.want == other.want:
                self.want == other.want
                if self.lineno == other.lineno:
                    self.lineno == other.lineno
                    if self.indent == other.indent:
                        self.indent == other.indent
                        if self.options == other.options:
                            self.options == other.options
        return self.exc_msg == other.exc_msg

    
    def __hash__(self):
        return hash((self.source, self.want, self.lineno, self.indent, self.exc_msg))



class DocTest:
    '''
    A collection of doctest examples that should be run in a single
    namespace.  Each `DocTest` defines the following attributes:

      - examples: the list of examples.

      - globs: The namespace (aka globals) that the examples should
        be run in.

      - name: A name identifying the DocTest (typically, the name of
        the object whose docstring this DocTest was extracted from).

      - filename: The name of the file that this DocTest was extracted
        from, or `None` if the filename is unknown.

      - lineno: The line number within filename where this DocTest
        begins, or `None` if the line number is unavailable.  This
        line number is zero-based, with respect to the beginning of
        the file.

      - docstring: The string that the examples were extracted from,
        or `None` if the string is unavailable.
    '''
    
    def __init__(self, examples, globs, name, filename, lineno, docstring):
        """
        Create a new DocTest containing the given examples.  The
        DocTest's globals are initialized with a copy of `globs`.
        """
        pass
    # WARNING: Decompyle incomplete

    
    def __repr__(self):
        if len(self.examples) == 0:
            examples = 'no examples'
        elif len(self.examples) == 1:
            examples = '1 example'
        else:
            examples = '%d examples' % len(self.examples)
        return f'''<{self.__class__.__name__!s} {self.name!s} from {self.filename!s}:{self.lineno!s} ({examples!s})>'''

    
    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        if None.examples == other.examples:
            None.examples == other.examples
            if self.docstring == other.docstring:
                self.docstring == other.docstring
                if self.globs == other.globs:
                    self.globs == other.globs
                    if self.name == other.name:
                        self.name == other.name
                        if self.filename == other.filename:
                            self.filename == other.filename
        return self.lineno == other.lineno

    
    def __hash__(self):
        return hash((self.docstring, self.name, self.filename, self.lineno))

    
    def __lt__(self, other):
        if not isinstance(other, DocTest):
            return NotImplemented
        return (None.name, self.filename, self.lineno, id(self)) < (other.name, other.filename, other.lineno, id(other))



class DocTestParser:
    '''
    A class used to parse strings containing doctest examples.
    '''
    _EXAMPLE_RE = re.compile('\n        # Source consists of a PS1 line followed by zero or more PS2 lines.\n        (?P<source>\n            (?:^(?P<indent> [ ]*) >>>    .*)    # PS1 line\n            (?:\\n           [ ]*  \\.\\.\\. .*)*)  # PS2 lines\n        \\n?\n        # Want consists of any non-blank lines that do not start with PS1.\n        (?P<want> (?:(?![ ]*$)    # Not a blank line\n                     (?![ ]*>>>)  # Not a line starting with PS1\n                     .+$\\n?       # But any other line\n                  )*)\n        ', re.MULTILINE | re.VERBOSE)
    _EXCEPTION_RE = re.compile("\n        # Grab the traceback header.  Different versions of Python have\n        # said different things on the first traceback line.\n        ^(?P<hdr> Traceback\\ \\(\n            (?: most\\ recent\\ call\\ last\n            |   innermost\\ last\n            ) \\) :\n        )\n        \\s* $                # toss trailing whitespace on the header.\n        (?P<stack> .*?)      # don't blink: absorb stuff until...\n        ^ (?P<msg> \\w+ .*)   #     a line *starts* with alphanum.\n        ", re.VERBOSE | re.MULTILINE | re.DOTALL)
    _IS_BLANK_OR_COMMENT = re.compile('^[ ]*(#.*)?$').match
    
    def parse(self, string, name = ('<string>',)):
        '''
        Divide the given string into examples and intervening text,
        and return them as a list of alternating Examples and strings.
        Line numbers for the Examples are 0-based.  The optional
        argument `name` is a name identifying this string, and is only
        used for error messages.
        '''
        string = string.expandtabs()
        min_indent = self._min_indent(string)
    # WARNING: Decompyle incomplete

    
    def get_doctest(self, string, globs, name, filename, lineno):
        '''
        Extract all doctest examples from the given string, and
        collect them into a `DocTest` object.

        `globs`, `name`, `filename`, and `lineno` are attributes for
        the new `DocTest` object.  See the documentation for `DocTest`
        for more information.
        '''
        return DocTest(self.get_examples(string, name), globs, name, filename, lineno, string)

    
    def get_examples(self, string, name = ('<string>',)):
        '''
        Extract all doctest examples from the given string, and return
        them as a list of `Example` objects.  Line numbers are
        0-based, because it\'s most common in doctests that nothing
        interesting appears on the same line as opening triple-quote,
        and so the first interesting line is called "line 1" then.

        The optional argument `name` is a name identifying this
        string, and is only used for error messages.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _parse_example(self, m, name, lineno):
        """
        Given a regular expression match from `_EXAMPLE_RE` (`m`),
        return a pair `(source, want)`, where `source` is the matched
        example's source code (with prompts and indentation stripped);
        and `want` is the example's expected output (with indentation
        stripped).

        `name` is the string's name, and `lineno` is the line number
        where the example starts; both are used for error messages.
        """
        indent = len(m.group('indent'))
        source_lines = m.group('source').split('\n')
        self._check_prompt_blank(source_lines, indent, name, lineno)
        self._check_prefix(source_lines[1:], ' ' * indent + '.', name, lineno)
    # WARNING: Decompyle incomplete

    _OPTION_DIRECTIVE_RE = re.compile('#\\s*doctest:\\s*([^\\n\\\'"]*)$', re.MULTILINE)
    
    def _find_options(self, source, name, lineno):
        """
        Return a dictionary containing option overrides extracted from
        option directives in the given source string.

        `name` is the string's name, and `lineno` is the line number
        where the example starts; both are used for error messages.
        """
        options = { }
        for m in self._OPTION_DIRECTIVE_RE.finditer(source):
            option_strings = m.group(1).replace(',', ' ').split()
            for option in option_strings:
                if option[0] not in '+-' or option[1:] not in OPTIONFLAGS_BY_NAME:
                    raise ValueError(f'''line {lineno + 1!r} of the doctest for {name!s} has an invalid option: {option!r}''')
                flag = OPTIONFLAGS_BY_NAME[option[1:]]
                options[flag] = option[0] == '+'
        if options and self._IS_BLANK_OR_COMMENT(source):
            raise ValueError(f'''line {lineno!r} of the doctest for {name!s} has an option directive on a line with no example: {source!r}''')
        return options

    _INDENT_RE = re.compile('^([ ]*)(?=\\S)', re.MULTILINE)
    
    def _min_indent(self, s):
        '''Return the minimum indentation of any non-blank line in `s`'''
        pass
    # WARNING: Decompyle incomplete

    
    def _check_prompt_blank(self, lines, indent, name, lineno):
        '''
        Given the lines of a source string (including prompts and
        leading indentation), check to make sure that every prompt is
        followed by a space character.  If any line is not followed by
        a space character, then raise ValueError.
        '''
        for i, line in enumerate(lines):
            if not len(line) >= indent + 4:
                continue
            if not line[indent + 3] != ' ':
                continue
            raise ValueError(f'''line {lineno + i + 1!r} of the docstring for {name!s} lacks blank after {line[indent:indent + 3]!s}: {line!r}''')

    
    def _check_prefix(self, lines, prefix, name, lineno):
        '''
        Check that every line in the given list starts with the given
        prefix; if any line does not, then raise a ValueError.
        '''
        for i, line in enumerate(lines):
            if not line:
                continue
            if line.startswith(prefix):
                continue
            raise ValueError(f'''line {lineno + i + 1!r} of the docstring for {name!s} has inconsistent leading whitespace: {line!r}''')



class DocTestFinder:
    '''
    A class used to extract the DocTests that are relevant to a given
    object, from its docstring and the docstrings of its contained
    objects.  Doctests can currently be extracted from the following
    object types: modules, functions, classes, methods, staticmethods,
    classmethods, and properties.
    '''
    
    def __init__(self, verbose, parser, recurse, exclude_empty = (False, DocTestParser(), True, True)):
        '''
        Create a new doctest finder.

        The optional argument `parser` specifies a class or
        function that should be used to create new DocTest objects (or
        objects that implement the same interface as DocTest).  The
        signature for this factory function should match the signature
        of the DocTest constructor.

        If the optional argument `recurse` is false, then `find` will
        only examine the given object, and not any contained objects.

        If the optional argument `exclude_empty` is false, then `find`
        will include tests for objects with empty docstrings.
        '''
        self._parser = parser
        self._verbose = verbose
        self._recurse = recurse
        self._exclude_empty = exclude_empty

    
    def find(self, obj, name, module, globs, extraglobs = (None, None, None, None)):
        """
        Return a list of the DocTests that are defined by the given
        object's docstring, or by any of its contained objects'
        docstrings.

        The optional parameter `module` is the module that contains
        the given object.  If the module is not specified or is None, then
        the test finder will attempt to automatically determine the
        correct module.  The object's module is used:

            - As a default namespace, if `globs` is not specified.
            - To prevent the DocTestFinder from extracting DocTests
              from objects that are imported from other modules.
            - To find the name of the file containing the object.
            - To help find the line number of the object within its
              file.

        Contained objects whose module does not match `module` are ignored.

        If `module` is False, no attempt to find the module will be made.
        This is obscure, of use mostly in tests:  if `module` is False, or
        is None but cannot be found automatically, then all objects are
        considered to belong to the (non-existent) module, so all contained
        objects will (recursively) be searched for doctests.

        The globals for each DocTest is formed by combining `globs`
        and `extraglobs` (bindings in `extraglobs` override bindings
        in `globs`).  A new copy of the globals dictionary is created
        for each DocTest.  If `globs` is not specified, then it
        defaults to the module's `__dict__`, if specified, or {}
        otherwise.  If `extraglobs` is not specified, then it defaults
        to {}.

        """
        pass
    # WARNING: Decompyle incomplete

    
    def _from_module(self, module, object):
        '''
        Return true if the given object is defined in the given
        module.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _is_routine(self, obj):
        '''
        Safely unwrap objects and determine if they are functions.
        '''
        maybe_routine = obj
        maybe_routine = inspect.unwrap(maybe_routine)
        return inspect.isroutine(maybe_routine)
    # WARNING: Decompyle incomplete

    
    def _find(self, tests, obj, name, module, source_lines, globs, seen):
        '''
        Find tests for the given object and any contained objects, and
        add them to `tests`.
        '''
        if self._verbose:
            print('Finding tests in %s' % name)
        if id(obj) in seen:
            return None
        seen[id(obj)] = 1
        test = self._get_test(obj, name, module, globs, source_lines)
    # WARNING: Decompyle incomplete

    
    def _get_test(self, obj, name, module, globs, source_lines):
        '''
        Return a DocTest for the given object, if it defines a docstring;
        otherwise, return None.
        '''
        if isinstance(obj, str):
            docstring = obj
    # WARNING: Decompyle incomplete

    
    def _find_lineno(self, obj, source_lines):
        """
        Return a line number of the given object's docstring.

        Returns `None` if the given object does not have a docstring.
        """
        lineno = None
        docstring = getattr(obj, '__doc__', None)
    # WARNING: Decompyle incomplete



class DocTestRunner:
    """
    A class used to run DocTest test cases, and accumulate statistics.
    The `run` method is used to process a single DocTest case.  It
    returns a tuple `(f, t)`, where `t` is the number of test cases
    tried, and `f` is the number of test cases that failed.

        >>> tests = DocTestFinder().find(_TestClass)
        >>> runner = DocTestRunner(verbose=False)
        >>> tests.sort(key = lambda test: test.name)
        >>> for test in tests:
        ...     print(test.name, '->', runner.run(test))
        _TestClass -> TestResults(failed=0, attempted=2)
        _TestClass.__init__ -> TestResults(failed=0, attempted=2)
        _TestClass.get -> TestResults(failed=0, attempted=2)
        _TestClass.square -> TestResults(failed=0, attempted=1)

    The `summarize` method prints a summary of all the test cases that
    have been run by the runner, and returns an aggregated `(f, t)`
    tuple:

        >>> runner.summarize(verbose=1)
        4 items passed all tests:
           2 tests in _TestClass
           2 tests in _TestClass.__init__
           2 tests in _TestClass.get
           1 tests in _TestClass.square
        7 tests in 4 items.
        7 passed and 0 failed.
        Test passed.
        TestResults(failed=0, attempted=7)

    The aggregated number of tried examples and failed examples is
    also available via the `tries` and `failures` attributes:

        >>> runner.tries
        7
        >>> runner.failures
        0

    The comparison between expected outputs and actual outputs is done
    by an `OutputChecker`.  This comparison may be customized with a
    number of option flags; see the documentation for `testmod` for
    more information.  If the option flags are insufficient, then the
    comparison may also be customized by passing a subclass of
    `OutputChecker` to the constructor.

    The test runner's display output can be controlled in two ways.
    First, an output function (`out) can be passed to
    `TestRunner.run`; this function will be called with strings that
    should be displayed.  It defaults to `sys.stdout.write`.  If
    capturing the output is not sufficient, then the display output
    can be also customized by subclassing DocTestRunner, and
    overriding the methods `report_start`, `report_success`,
    `report_unexpected_exception`, and `report_failure`.
    """
    DIVIDER = '**********************************************************************'
    
    def __init__(self, checker, verbose, optionflags = (None, None, 0)):
        """
        Create a new test runner.

        Optional keyword arg `checker` is the `OutputChecker` that
        should be used to compare the expected outputs and actual
        outputs of doctest examples.

        Optional keyword arg 'verbose' prints lots of stuff if true,
        only failures if false; by default, it's true iff '-v' is in
        sys.argv.

        Optional argument `optionflags` can be used to control how the
        test runner compares expected output to actual output, and how
        it displays failures.  See the documentation for `testmod` for
        more information.
        """
        if not checker:
            checker
        self._checker = OutputChecker()
    # WARNING: Decompyle incomplete

    
    def report_start(self, out, test, example):
        '''
        Report that the test runner is about to process the given
        example.  (Only displays a message if verbose=True)
        '''
        if self._verbose:
            if example.want:
                out('Trying:\n' + _indent(example.source) + 'Expecting:\n' + _indent(example.want))
                return None
            out('Trying:\n' + _indent(example.source) + 'Expecting nothing\n')
            return None

    
    def report_success(self, out, test, example, got):
        '''
        Report that the given example ran successfully.  (Only
        displays a message if verbose=True)
        '''
        if self._verbose:
            out('ok\n')
            return None

    
    def report_failure(self, out, test, example, got):
        '''
        Report that the given example failed.
        '''
        out(self._failure_header(test, example) + self._checker.output_difference(example, got, self.optionflags))

    
    def report_unexpected_exception(self, out, test, example, exc_info):
        '''
        Report that the given example raised an unexpected exception.
        '''
        out(self._failure_header(test, example) + 'Exception raised:\n' + _indent(_exception_traceback(exc_info)))

    
    def _failure_header(self, test, example):
        out = [
            self.DIVIDER]
    # WARNING: Decompyle incomplete

    
    def __run(self, test, compileflags, out):
        '''
        Run the examples in `test`.  Write the outcome of each example
        with one of the `DocTestRunner.report_*` methods, using the
        writer function `out`.  `compileflags` is the set of compiler
        flags that should be used to execute examples.  Return a tuple
        `(f, t)`, where `t` is the number of examples tried, and `f`
        is the number of examples that failed.  The examples are run
        in the namespace `test.globs`.
        '''
        failures = 0
        tries = 0
        original_optionflags = self.optionflags
        (SUCCESS, FAILURE, BOOM) = range(3)
        check = self._checker.check_output
    # WARNING: Decompyle incomplete

    
    def __record_outcome(self, test, f, t):
        '''
        Record the fact that the given DocTest (`test`) generated `f`
        failures out of `t` tried examples.
        '''
        (f2, t2) = self._name2ft.get(test.name, (0, 0))
        self._name2ft[test.name] = (f + f2, t + t2)

    __LINECACHE_FILENAME_RE = re.compile('<doctest (?P<name>.+)\\[(?P<examplenum>\\d+)\\]>$')
    
    def __patched_linecache_getlines(self, filename, module_globals = (None,)):
        m = self.__LINECACHE_FILENAME_RE.match(filename)
        if m and m.group('name') == self.test.name:
            example = self.test.examples[int(m.group('examplenum'))]
            return example.source.splitlines(keepends = True)
        return None.save_linecache_getlines(filename, module_globals)

    
    def run(self, test, compileflags, out, clear_globs = (None, None, True)):
        '''
        Run the examples in `test`, and display the results using the
        writer function `out`.

        The examples are run in the namespace `test.globs`.  If
        `clear_globs` is true (the default), then this namespace will
        be cleared after the test runs, to help with garbage
        collection.  If you would like to examine the namespace after
        the test completes, then use `clear_globs=False`.

        `compileflags` gives the set of flags that should be used by
        the Python compiler when running the examples.  If not
        specified, then it will default to the set of future-import
        flags that apply to `globs`.

        The output of each example is checked using
        `DocTestRunner.check_output`, and the results are formatted by
        the `DocTestRunner.report_*` methods.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def summarize(self, verbose = (None,)):
        """
        Print a summary of all the test cases that have been run by
        this DocTestRunner, and return a tuple `(f, t)`, where `f` is
        the total number of failed examples, and `t` is the total
        number of tried examples.

        The optional `verbose` argument controls how detailed the
        summary is.  If the verbosity is not specified, then the
        DocTestRunner's verbosity is used.
        """
        pass
    # WARNING: Decompyle incomplete

    
    def merge(self, other):
        d = self._name2ft
        for f, t in other._name2ft.items():
            if name in d:
                (f2, t2) = d[name]
                f = f + f2
                t = t + t2
            d[name] = (f, t)



class OutputChecker:
    '''
    A class used to check the whether the actual output from a doctest
    example matches the expected output.  `OutputChecker` defines two
    methods: `check_output`, which compares a given pair of outputs,
    and returns true if they match; and `output_difference`, which
    returns a string describing the differences between two outputs.
    '''
    
    def _toAscii(self, s):
        '''
        Convert string to hex-escaped ASCII string.
        '''
        return str(s.encode('ASCII', 'backslashreplace'), 'ASCII')

    
    def check_output(self, want, got, optionflags):
        '''
        Return True iff the actual output from an example (`got`)
        matches the expected output (`want`).  These strings are
        always considered to match if they are identical; but
        depending on what option flags the test runner is using,
        several non-exact match types are also possible.  See the
        documentation for `TestRunner` for more information about
        option flags.
        '''
        got = self._toAscii(got)
        want = self._toAscii(want)
        if got == want:
            return True
        if not optionflags & DONT_ACCEPT_TRUE_FOR_1:
            if (got, want) == ('True\n', '1\n'):
                return True
            if (got, want) == ('False\n', '0\n'):
                return True
        if not optionflags & DONT_ACCEPT_BLANKLINE:
            want = re.sub('(?m)^%s\\s*?$' % re.escape(BLANKLINE_MARKER), '', want)
            got = re.sub('(?m)^[^\\S\\n]+$', '', got)
            if got == want:
                return True
        if optionflags & NORMALIZE_WHITESPACE:
            got = ' '.join(got.split())
            want = ' '.join(want.split())
            if got == want:
                return True
        if optionflags & ELLIPSIS and _ellipsis_match(want, got):
            return True
        return False

    
    def _do_a_fancy_diff(self, want, got, optionflags):
        if not optionflags & (REPORT_UDIFF | REPORT_CDIFF | REPORT_NDIFF):
            return False
        if optionflags & REPORT_NDIFF:
            return True
        if want.count('\n') > 2:
            want.count('\n') > 2
        return got.count('\n') > 2

    
    def output_difference(self, example, got, optionflags):
        '''
        Return a string describing the differences between the
        expected output for a given example (`example`) and the actual
        output (`got`).  `optionflags` is the set of option flags used
        to compare `want` and `got`.
        '''
        want = example.want
        if not optionflags & DONT_ACCEPT_BLANKLINE:
            got = re.sub('(?m)^[ ]*(?=\n)', BLANKLINE_MARKER, got)
    # WARNING: Decompyle incomplete



class DocTestFailure(Exception):
    '''A DocTest example has failed in debugging mode.

    The exception instance has variables:

    - test: the DocTest object being run

    - example: the Example object that failed

    - got: the actual output
    '''
    
    def __init__(self, test, example, got):
        self.test = test
        self.example = example
        self.got = got

    
    def __str__(self):
        return str(self.test)



class UnexpectedException(Exception):
    '''A DocTest example has encountered an unexpected exception

    The exception instance has variables:

    - test: the DocTest object being run

    - example: the Example object that failed

    - exc_info: the exception info
    '''
    
    def __init__(self, test, example, exc_info):
        self.test = test
        self.example = example
        self.exc_info = exc_info

    
    def __str__(self):
        return str(self.test)



class DebugRunner(DocTestRunner):
    """Run doc tests but raise an exception as soon as there is a failure.

       If an unexpected exception occurs, an UnexpectedException is raised.
       It contains the test, the example, and the original exception:

         >>> runner = DebugRunner(verbose=False)
         >>> test = DocTestParser().get_doctest('>>> raise KeyError\\n42',
         ...                                    {}, 'foo', 'foo.py', 0)
         >>> try:
         ...     runner.run(test)
         ... except UnexpectedException as f:
         ...     failure = f

         >>> failure.test is test
         True

         >>> failure.example.want
         '42\\n'

         >>> exc_info = failure.exc_info
         >>> raise exc_info[1] # Already has the traceback
         Traceback (most recent call last):
         ...
         KeyError

       We wrap the original exception to give the calling application
       access to the test and example information.

       If the output doesn't match, then a DocTestFailure is raised:

         >>> test = DocTestParser().get_doctest('''
         ...      >>> x = 1
         ...      >>> x
         ...      2
         ...      ''', {}, 'foo', 'foo.py', 0)

         >>> try:
         ...    runner.run(test)
         ... except DocTestFailure as f:
         ...    failure = f

       DocTestFailure objects provide access to the test:

         >>> failure.test is test
         True

       As well as to the example:

         >>> failure.example.want
         '2\\n'

       and the actual output:

         >>> failure.got
         '1\\n'

       If a failure or error occurs, the globals are left intact:

         >>> del test.globs['__builtins__']
         >>> test.globs
         {'x': 1}

         >>> test = DocTestParser().get_doctest('''
         ...      >>> x = 2
         ...      >>> raise KeyError
         ...      ''', {}, 'foo', 'foo.py', 0)

         >>> runner.run(test)
         Traceback (most recent call last):
         ...
         doctest.UnexpectedException: <DocTest foo from foo.py:0 (2 examples)>

         >>> del test.globs['__builtins__']
         >>> test.globs
         {'x': 2}

       But the globals are cleared if there is no error:

         >>> test = DocTestParser().get_doctest('''
         ...      >>> x = 2
         ...      ''', {}, 'foo', 'foo.py', 0)

         >>> runner.run(test)
         TestResults(failed=0, attempted=1)

         >>> test.globs
         {}

       """
    
    def run(self, test, compileflags, out, clear_globs = (None, None, True)):
        r = DocTestRunner.run(self, test, compileflags, out, False)
        if clear_globs:
            test.globs.clear()
        return r

    
    def report_unexpected_exception(self, out, test, example, exc_info):
        raise UnexpectedException(test, example, exc_info)

    
    def report_failure(self, out, test, example, got):
        raise DocTestFailure(test, example, got)


master = None

def testmod(m, name, globs, verbose, report, optionflags, extraglobs, raise_on_error, exclude_empty = (None, None, None, None, True, 0, None, False, False)):
    '''m=None, name=None, globs=None, verbose=None, report=True,
       optionflags=0, extraglobs=None, raise_on_error=False,
       exclude_empty=False

    Test examples in docstrings in functions and classes reachable
    from module m (or the current module if m is not supplied), starting
    with m.__doc__.

    Also test examples reachable from dict m.__test__ if it exists and is
    not None.  m.__test__ maps names to functions, classes and strings;
    function and class docstrings are tested even if the name is private;
    strings are tested directly, as if they were docstrings.

    Return (#failures, #tests).

    See help(doctest) for an overview.

    Optional keyword arg "name" gives the name of the module; by default
    use m.__name__.

    Optional keyword arg "globs" gives a dict to be used as the globals
    when executing examples; by default, use m.__dict__.  A copy of this
    dict is actually used for each docstring, so that each docstring\'s
    examples start with a clean slate.

    Optional keyword arg "extraglobs" gives a dictionary that should be
    merged into the globals that are used to execute examples.  By
    default, no extra globals are used.  This is new in 2.4.

    Optional keyword arg "verbose" prints lots of stuff if true, prints
    only failures if false; by default, it\'s true iff "-v" is in sys.argv.

    Optional keyword arg "report" prints a summary at the end when true,
    else prints nothing at the end.  In verbose mode, the summary is
    detailed, else very brief (in fact, empty if all tests passed).

    Optional keyword arg "optionflags" or\'s together module constants,
    and defaults to 0.  This is new in 2.3.  Possible values (see the
    docs for details):

        DONT_ACCEPT_TRUE_FOR_1
        DONT_ACCEPT_BLANKLINE
        NORMALIZE_WHITESPACE
        ELLIPSIS
        SKIP
        IGNORE_EXCEPTION_DETAIL
        REPORT_UDIFF
        REPORT_CDIFF
        REPORT_NDIFF
        REPORT_ONLY_FIRST_FAILURE

    Optional keyword arg "raise_on_error" raises an exception on the
    first unexpected exception or failure. This allows failures to be
    post-mortem debugged.

    Advanced tomfoolery:  testmod runs methods of a local instance of
    class doctest.Tester, then merges the results into (or creates)
    global Tester instance doctest.master.  Methods of doctest.master
    can be called directly too, if you want to do something unusual.
    Passing report=0 to testmod is especially useful then, to delay
    displaying a summary.  Invoke doctest.master.summarize(verbose)
    when you\'re done fiddling.
    '''
    pass
# WARNING: Decompyle incomplete


def testfile(filename, module_relative, name, package, globs, verbose, report, optionflags, extraglobs, raise_on_error, parser, encoding = (True, None, None, None, None, True, 0, None, False, DocTestParser(), None)):
    '''
    Test examples in the given file.  Return (#failures, #tests).

    Optional keyword arg "module_relative" specifies how filenames
    should be interpreted:

      - If "module_relative" is True (the default), then "filename"
         specifies a module-relative path.  By default, this path is
         relative to the calling module\'s directory; but if the
         "package" argument is specified, then it is relative to that
         package.  To ensure os-independence, "filename" should use
         "/" characters to separate path segments, and should not
         be an absolute path (i.e., it may not begin with "/").

      - If "module_relative" is False, then "filename" specifies an
        os-specific path.  The path may be absolute or relative (to
        the current working directory).

    Optional keyword arg "name" gives the name of the test; by default
    use the file\'s basename.

    Optional keyword argument "package" is a Python package or the
    name of a Python package whose directory should be used as the
    base directory for a module relative filename.  If no package is
    specified, then the calling module\'s directory is used as the base
    directory for module relative filenames.  It is an error to
    specify "package" if "module_relative" is False.

    Optional keyword arg "globs" gives a dict to be used as the globals
    when executing examples; by default, use {}.  A copy of this dict
    is actually used for each docstring, so that each docstring\'s
    examples start with a clean slate.

    Optional keyword arg "extraglobs" gives a dictionary that should be
    merged into the globals that are used to execute examples.  By
    default, no extra globals are used.

    Optional keyword arg "verbose" prints lots of stuff if true, prints
    only failures if false; by default, it\'s true iff "-v" is in sys.argv.

    Optional keyword arg "report" prints a summary at the end when true,
    else prints nothing at the end.  In verbose mode, the summary is
    detailed, else very brief (in fact, empty if all tests passed).

    Optional keyword arg "optionflags" or\'s together module constants,
    and defaults to 0.  Possible values (see the docs for details):

        DONT_ACCEPT_TRUE_FOR_1
        DONT_ACCEPT_BLANKLINE
        NORMALIZE_WHITESPACE
        ELLIPSIS
        SKIP
        IGNORE_EXCEPTION_DETAIL
        REPORT_UDIFF
        REPORT_CDIFF
        REPORT_NDIFF
        REPORT_ONLY_FIRST_FAILURE

    Optional keyword arg "raise_on_error" raises an exception on the
    first unexpected exception or failure. This allows failures to be
    post-mortem debugged.

    Optional keyword arg "parser" specifies a DocTestParser (or
    subclass) that should be used to extract tests from the files.

    Optional keyword arg "encoding" specifies an encoding that should
    be used to convert the file to unicode.

    Advanced tomfoolery:  testmod runs methods of a local instance of
    class doctest.Tester, then merges the results into (or creates)
    global Tester instance doctest.master.  Methods of doctest.master
    can be called directly too, if you want to do something unusual.
    Passing report=0 to testmod is especially useful then, to delay
    displaying a summary.  Invoke doctest.master.summarize(verbose)
    when you\'re done fiddling.
    '''
    if not package and module_relative:
        raise ValueError('Package may only be specified for module-relative paths.')
    if not encoding:
        encoding
    (text, filename) = _load_testfile(filename, package, module_relative, 'utf-8')
# WARNING: Decompyle incomplete


def run_docstring_examples(f, globs, verbose, name, compileflags, optionflags = (False, 'NoName', None, 0)):
    """
    Test examples in the given object's docstring (`f`), using `globs`
    as globals.  Optional argument `name` is used in failure messages.
    If the optional argument `verbose` is true, then generate output
    even if there are no failures.

    `compileflags` gives the set of flags that should be used by the
    Python compiler when running the examples.  If not specified, then
    it will default to the set of future-import flags that apply to
    `globs`.

    Optional keyword arg `optionflags` specifies options for the
    testing and output.  See the documentation for `testmod` for more
    information.
    """
    finder = DocTestFinder(verbose = verbose, recurse = False)
    runner = DocTestRunner(verbose = verbose, optionflags = optionflags)
    for test in finder.find(f, name, globs = globs):
        runner.run(test, compileflags = compileflags)

_unittest_reportflags = 0

def set_unittest_reportflags(flags):
    """Sets the unittest option flags.

    The old flag is returned so that a runner could restore the old
    value if it wished to:

      >>> import doctest
      >>> old = doctest._unittest_reportflags
      >>> doctest.set_unittest_reportflags(REPORT_NDIFF |
      ...                          REPORT_ONLY_FIRST_FAILURE) == old
      True

      >>> doctest._unittest_reportflags == (REPORT_NDIFF |
      ...                                   REPORT_ONLY_FIRST_FAILURE)
      True

    Only reporting flags can be set:

      >>> doctest.set_unittest_reportflags(ELLIPSIS)
      Traceback (most recent call last):
      ...
      ValueError: ('Only reporting flags allowed', 8)

      >>> doctest.set_unittest_reportflags(old) == (REPORT_NDIFF |
      ...                                   REPORT_ONLY_FIRST_FAILURE)
      True
    """
    global _unittest_reportflags
    if flags & REPORTING_FLAGS != flags:
        raise ValueError('Only reporting flags allowed', flags)
    old = _unittest_reportflags
    _unittest_reportflags = flags
    return old


class DocTestCase(unittest.TestCase):
    
    def __init__(self, test, optionflags, setUp, tearDown, checker = (0, None, None, None)):
        unittest.TestCase.__init__(self)
        self._dt_optionflags = optionflags
        self._dt_checker = checker
        self._dt_globs = test.globs.copy()
        self._dt_test = test
        self._dt_setUp = setUp
        self._dt_tearDown = tearDown

    
    def setUp(self):
        test = self._dt_test
    # WARNING: Decompyle incomplete

    
    def tearDown(self):
        test = self._dt_test
    # WARNING: Decompyle incomplete

    
    def runTest(self):
        test = self._dt_test
        old = sys.stdout
        new = StringIO()
        optionflags = self._dt_optionflags
        if not optionflags & REPORTING_FLAGS:
            optionflags |= _unittest_reportflags
        runner = DocTestRunner(optionflags = optionflags, checker = self._dt_checker, verbose = False)
        runner.DIVIDER = '----------------------------------------------------------------------'
        (failures, tries) = runner.run(test, out = new.write, clear_globs = False)
        sys.stdout = old
        if failures:
            raise self.failureException(self.format_failure(new.getvalue()))
        return None
    # WARNING: Decompyle incomplete

    
    def format_failure(self, err):
        test = self._dt_test
    # WARNING: Decompyle incomplete

    
    def debug(self):
        """Run the test case without results and without catching exceptions

           The unit test framework includes a debug method on test cases
           and test suites to support post-mortem debugging.  The test code
           is run in such a way that errors are not caught.  This way a
           caller can catch the errors and initiate post-mortem debugging.

           The DocTestCase provides a debug method that raises
           UnexpectedException errors if there is an unexpected
           exception:

             >>> test = DocTestParser().get_doctest('>>> raise KeyError\\n42',
             ...                {}, 'foo', 'foo.py', 0)
             >>> case = DocTestCase(test)
             >>> try:
             ...     case.debug()
             ... except UnexpectedException as f:
             ...     failure = f

           The UnexpectedException contains the test, the example, and
           the original exception:

             >>> failure.test is test
             True

             >>> failure.example.want
             '42\\n'

             >>> exc_info = failure.exc_info
             >>> raise exc_info[1] # Already has the traceback
             Traceback (most recent call last):
             ...
             KeyError

           If the output doesn't match, then a DocTestFailure is raised:

             >>> test = DocTestParser().get_doctest('''
             ...      >>> x = 1
             ...      >>> x
             ...      2
             ...      ''', {}, 'foo', 'foo.py', 0)
             >>> case = DocTestCase(test)

             >>> try:
             ...    case.debug()
             ... except DocTestFailure as f:
             ...    failure = f

           DocTestFailure objects provide access to the test:

             >>> failure.test is test
             True

           As well as to the example:

             >>> failure.example.want
             '2\\n'

           and the actual output:

             >>> failure.got
             '1\\n'

           """
        self.setUp()
        runner = DebugRunner(optionflags = self._dt_optionflags, checker = self._dt_checker, verbose = False)
        runner.run(self._dt_test, clear_globs = False)
        self.tearDown()

    
    def id(self):
        return self._dt_test.name

    
    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        if None._dt_test == other._dt_test:
            None._dt_test == other._dt_test
            if self._dt_optionflags == other._dt_optionflags:
                self._dt_optionflags == other._dt_optionflags
                if self._dt_setUp == other._dt_setUp:
                    self._dt_setUp == other._dt_setUp
                    if self._dt_tearDown == other._dt_tearDown:
                        self._dt_tearDown == other._dt_tearDown
        return self._dt_checker == other._dt_checker

    
    def __hash__(self):
        return hash((self._dt_optionflags, self._dt_setUp, self._dt_tearDown, self._dt_checker))

    
    def __repr__(self):
        name = self._dt_test.name.split('.')
        return f'''{name[-1]!s} ({'.'.join(name[:-1])!s})'''

    __str__ = object.__str__
    
    def shortDescription(self):
        return 'Doctest: ' + self._dt_test.name



class SkipDocTestCase(DocTestCase):
    
    def __init__(self, module):
        self.module = module
        DocTestCase.__init__(self, None)

    
    def setUp(self):
        self.skipTest('DocTestSuite will not work with -O2 and above')

    
    def test_skip(self):
        pass

    
    def shortDescription(self):
        return 'Skipping tests from %s' % self.module.__name__

    __str__ = shortDescription


class _DocTestSuite(unittest.TestSuite):
    
    def _removeTestAtIndex(self, index):
        pass



def DocTestSuite(module, globs, extraglobs, test_finder = (None, None, None, None), **options):
    '''
    Convert doctest tests for a module to a unittest test suite.

    This converts each documentation string in a module that
    contains doctest tests to a unittest test case.  If any of the
    tests in a doc string fail, then the test case fails.  An exception
    is raised showing the name of the file containing the test and a
    (sometimes approximate) line number.

    The `module` argument provides the module to be tested.  The argument
    can be either a module or a module name.

    If no argument is given, the calling module is used.

    A number of options may be provided as keyword arguments:

    setUp
      A set-up function.  This is called before running the
      tests in each file. The setUp function will be passed a DocTest
      object.  The setUp function can access the test globals as the
      globs attribute of the test passed.

    tearDown
      A tear-down function.  This is called after running the
      tests in each file.  The tearDown function will be passed a DocTest
      object.  The tearDown function can access the test globals as the
      globs attribute of the test passed.

    globs
      A dictionary containing initial global variables for the tests.

    optionflags
       A set of doctest option flags expressed as an integer.
    '''
    pass
# WARNING: Decompyle incomplete


class DocFileCase(DocTestCase):
    
    def id(self):
        return '_'.join(self._dt_test.name.split('.'))

    
    def __repr__(self):
        return self._dt_test.filename

    
    def format_failure(self, err):
        return f'''Failed doctest test for {self._dt_test.name!s}\n  File "{self._dt_test.filename!s}", line 0\n\n{err!s}'''



def DocFileTest(path, module_relative, package, globs, parser, encoding = (True, None, None, DocTestParser(), None), **options):
    pass
# WARNING: Decompyle incomplete


def DocFileSuite(*paths, **kw):
    '''A unittest suite for one or more doctest files.

    The path to each doctest file is given as a string; the
    interpretation of that string depends on the keyword argument
    "module_relative".

    A number of options may be provided as keyword arguments:

    module_relative
      If "module_relative" is True, then the given file paths are
      interpreted as os-independent module-relative paths.  By
      default, these paths are relative to the calling module\'s
      directory; but if the "package" argument is specified, then
      they are relative to that package.  To ensure os-independence,
      "filename" should use "/" characters to separate path
      segments, and may not be an absolute path (i.e., it may not
      begin with "/").

      If "module_relative" is False, then the given file paths are
      interpreted as os-specific paths.  These paths may be absolute
      or relative (to the current working directory).

    package
      A Python package or the name of a Python package whose directory
      should be used as the base directory for module relative paths.
      If "package" is not specified, then the calling module\'s
      directory is used as the base directory for module relative
      filenames.  It is an error to specify "package" if
      "module_relative" is False.

    setUp
      A set-up function.  This is called before running the
      tests in each file. The setUp function will be passed a DocTest
      object.  The setUp function can access the test globals as the
      globs attribute of the test passed.

    tearDown
      A tear-down function.  This is called after running the
      tests in each file.  The tearDown function will be passed a DocTest
      object.  The tearDown function can access the test globals as the
      globs attribute of the test passed.

    globs
      A dictionary containing initial global variables for the tests.

    optionflags
      A set of doctest option flags expressed as an integer.

    parser
      A DocTestParser (or subclass) that should be used to extract
      tests from the files.

    encoding
      An encoding that will be used to convert the files to unicode.
    '''
    suite = _DocTestSuite()
    if kw.get('module_relative', True):
        kw['package'] = _normalize_module(kw.get('package'))
# WARNING: Decompyle incomplete


def script_from_examples(s):
    """Extract script from text with examples.

       Converts text with examples to a Python script.  Example input is
       converted to regular code.  Example output and all other words
       are converted to comments:

       >>> text = '''
       ...       Here are examples of simple math.
       ...
       ...           Python has super accurate integer addition
       ...
       ...           >>> 2 + 2
       ...           5
       ...
       ...           And very friendly error messages:
       ...
       ...           >>> 1/0
       ...           To Infinity
       ...           And
       ...           Beyond
       ...
       ...           You can use logic if you want:
       ...
       ...           >>> if 0:
       ...           ...    blah
       ...           ...    blah
       ...           ...
       ...
       ...           Ho hum
       ...           '''

       >>> print(script_from_examples(text))
       # Here are examples of simple math.
       #
       #     Python has super accurate integer addition
       #
       2 + 2
       # Expected:
       ## 5
       #
       #     And very friendly error messages:
       #
       1/0
       # Expected:
       ## To Infinity
       ## And
       ## Beyond
       #
       #     You can use logic if you want:
       #
       if 0:
          blah
          blah
       #
       #     Ho hum
       <BLANKLINE>
       """
    output = []
# WARNING: Decompyle incomplete


def testsource(module, name):
    '''Extract the test sources from a doctest docstring as a script.

    Provide the module (or dotted name of the module) containing the
    test to be debugged and the name (within the module) of the object
    with the doc string with tests to be debugged.
    '''
    module = _normalize_module(module)
    tests = DocTestFinder().find(module)
# WARNING: Decompyle incomplete


def debug_src(src, pm, globs = (False, None)):
    """Debug a single doctest docstring, in argument `src`'"""
    testsrc = script_from_examples(src)
    debug_script(testsrc, pm, globs)


def debug_script(src, pm, globs = (False, None)):
    '''Debug a test script.  `src` is the script, as a string.'''
    import pdb
    if globs:
        globs = globs.copy()
    else:
        globs = { }
    if pm:
        exec(src, globs, globs)
        return None
    pdb.Pdb(nosigint = True).run('exec(%r)' % src, globs, globs)
    return None
# WARNING: Decompyle incomplete


def debug(module, name, pm = (False,)):
    '''Debug a single doctest docstring.

    Provide the module (or dotted name of the module) containing the
    test to be debugged and the name (within the module) of the object
    with the docstring with tests to be debugged.
    '''
    module = _normalize_module(module)
    testsrc = testsource(module, name)
    debug_script(testsrc, pm, module.__dict__)


class _TestClass:
    """
    A pointless class, for sanity-checking of docstring testing.

    Methods:
        square()
        get()

    >>> _TestClass(13).get() + _TestClass(-12).get()
    1
    >>> hex(_TestClass(13).square().get())
    '0xa9'
    """
    
    def __init__(self, val):
        '''val -> _TestClass object with associated value val.

        >>> t = _TestClass(123)
        >>> print(t.get())
        123
        '''
        self.val = val

    
    def square(self):
        """square() -> square TestClass's associated value

        >>> _TestClass(13).square().get()
        169
        """
        self.val = self.val ** 2
        return self

    
    def get(self):
        """get() -> return TestClass's associated value.

        >>> x = _TestClass(-42)
        >>> print(x.get())
        -42
        """
        return self.val


__test__ = {
    '_TestClass': _TestClass,
    'string': '\n                      Example of a string object, searched as-is.\n                      >>> x = 1; y = 2\n                      >>> x + y, x * y\n                      (3, 2)\n                      ',
    'bool-int equivalence': '\n                                    In 2.2, boolean expressions displayed\n                                    0 or 1.  By default, we still accept\n                                    them.  This can be disabled by passing\n                                    DONT_ACCEPT_TRUE_FOR_1 to the new\n                                    optionflags argument.\n                                    >>> 4 == 4\n                                    1\n                                    >>> 4 == 4\n                                    True\n                                    >>> 4 > 4\n                                    0\n                                    >>> 4 > 4\n                                    False\n                                    ',
    'blank lines': "\n                Blank lines can be marked with <BLANKLINE>:\n                    >>> print('foo\\n\\nbar\\n')\n                    foo\n                    <BLANKLINE>\n                    bar\n                    <BLANKLINE>\n            ",
    'ellipsis': "\n                If the ellipsis flag is used, then '...' can be used to\n                elide substrings in the desired output:\n                    >>> print(list(range(1000))) #doctest: +ELLIPSIS\n                    [0, 1, 2, ..., 999]\n            ",
    'whitespace normalization': '\n                If the whitespace normalization flag is used, then\n                differences in whitespace are ignored.\n                    >>> print(list(range(30))) #doctest: +NORMALIZE_WHITESPACE\n                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,\n                     15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,\n                     27, 28, 29]\n            ' }

def _test():
    import argparse
    parser = argparse.ArgumentParser(description = 'doctest runner')
    parser.add_argument('-v', '--verbose', action = 'store_true', default = False, help = 'print very verbose output for all tests')
    parser.add_argument('-o', '--option', action = 'append', choices = OPTIONFLAGS_BY_NAME.keys(), default = [], help = 'specify a doctest option flag to apply to the test run; may be specified more than once to apply multiple options')
    parser.add_argument('-f', '--fail-fast', action = 'store_true', help = 'stop running tests after first failure (this is a shorthand for -o FAIL_FAST, and is in addition to any other -o options)')
    parser.add_argument('file', nargs = '+', help = 'file containing the tests to run')
    args = parser.parse_args()
    testfiles = args.file
    verbose = args.verbose
    options = 0
    for option in args.option:
        options |= OPTIONFLAGS_BY_NAME[option]
    if args.fail_fast:
        options |= FAIL_FAST
    for filename in testfiles:
        if not failures:
            continue
        None if filename.endswith('.py') else testfiles
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(_test())
    return None
