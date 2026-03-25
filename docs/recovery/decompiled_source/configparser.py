# Source Generated with Decompyle++
# File: configparser.pyc (Python 3.12)

'''Configuration file parser.

A configuration file consists of sections, lead by a "[section]" header,
and followed by "name: value" entries, with continuations and such in
the style of RFC 822.

Intrinsic defaults can be specified by passing them into the
ConfigParser constructor as a dictionary.

class:

ConfigParser -- responsible for parsing a list of
                    configuration files, and managing the parsed database.

    methods:

    __init__(defaults=None, dict_type=_default_dict, allow_no_value=False,
             delimiters=(\'=\', \':\'), comment_prefixes=(\'#\', \';\'),
             inline_comment_prefixes=None, strict=True,
             empty_lines_in_values=True, default_section=\'DEFAULT\',
             interpolation=<unset>, converters=<unset>):

        Create the parser. When `defaults` is given, it is initialized into the
        dictionary or intrinsic defaults. The keys must be strings, the values
        must be appropriate for %()s string interpolation.

        When `dict_type` is given, it will be used to create the dictionary
        objects for the list of sections, for the options within a section, and
        for the default values.

        When `delimiters` is given, it will be used as the set of substrings
        that divide keys from values.

        When `comment_prefixes` is given, it will be used as the set of
        substrings that prefix comments in empty lines. Comments can be
        indented.

        When `inline_comment_prefixes` is given, it will be used as the set of
        substrings that prefix comments in non-empty lines.

        When `strict` is True, the parser won\'t allow for any section or option
        duplicates while reading from a single source (file, string or
        dictionary). Default is True.

        When `empty_lines_in_values` is False (default: True), each empty line
        marks the end of an option. Otherwise, internal empty lines of
        a multiline option are kept as part of the value.

        When `allow_no_value` is True (default: False), options without
        values are accepted; the value presented for these is None.

        When `default_section` is given, the name of the special section is
        named accordingly. By default it is called ``"DEFAULT"`` but this can
        be customized to point to any other valid section name. Its current
        value can be retrieved using the ``parser_instance.default_section``
        attribute and may be modified at runtime.

        When `interpolation` is given, it should be an Interpolation subclass
        instance. It will be used as the handler for option value
        pre-processing when using getters. RawConfigParser objects don\'t do
        any sort of interpolation, whereas ConfigParser uses an instance of
        BasicInterpolation. The library also provides a ``zc.buildout``
        inspired ExtendedInterpolation implementation.

        When `converters` is given, it should be a dictionary where each key
        represents the name of a type converter and each value is a callable
        implementing the conversion from string to the desired datatype. Every
        converter gets its corresponding get*() method on the parser object and
        section proxies.

    sections()
        Return all the configuration section names, sans DEFAULT.

    has_section(section)
        Return whether the given section exists.

    has_option(section, option)
        Return whether the given option exists in the given section.

    options(section)
        Return list of configuration options for the named section.

    read(filenames, encoding=None)
        Read and parse the iterable of named configuration files, given by
        name.  A single filename is also allowed.  Non-existing files
        are ignored.  Return list of successfully read files.

    read_file(f, filename=None)
        Read and parse one configuration file, given as a file object.
        The filename defaults to f.name; it is only used in error
        messages (if f has no `name` attribute, the string `<???>` is used).

    read_string(string)
        Read configuration from a given string.

    read_dict(dictionary)
        Read configuration from a dictionary. Keys are section names,
        values are dictionaries with keys and values that should be present
        in the section. If the used dictionary type preserves order, sections
        and their keys will be added in order. Values are automatically
        converted to strings.

    get(section, option, raw=False, vars=None, fallback=_UNSET)
        Return a string value for the named option.  All % interpolations are
        expanded in the return values, based on the defaults passed into the
        constructor and the DEFAULT section.  Additional substitutions may be
        provided using the `vars` argument, which must be a dictionary whose
        contents override any pre-existing defaults. If `option` is a key in
        `vars`, the value from `vars` is used.

    getint(section, options, raw=False, vars=None, fallback=_UNSET)
        Like get(), but convert value to an integer.

    getfloat(section, options, raw=False, vars=None, fallback=_UNSET)
        Like get(), but convert value to a float.

    getboolean(section, options, raw=False, vars=None, fallback=_UNSET)
        Like get(), but convert value to a boolean (currently case
        insensitively defined as 0, false, no, off for False, and 1, true,
        yes, on for True).  Returns False or True.

    items(section=_UNSET, raw=False, vars=None)
        If section is given, return a list of tuples with (name, value) for
        each option in the section. Otherwise, return a list of tuples with
        (section_name, section_proxy) for each section, including DEFAULTSECT.

    remove_section(section)
        Remove the given file section and all its options.

    remove_option(section, option)
        Remove the given option from the given section.

    set(section, option, value)
        Set the given option.

    write(fp, space_around_delimiters=True)
        Write the configuration state in .ini format. If
        `space_around_delimiters` is True (the default), delimiters
        between keys and values are surrounded by spaces.
'''
from collections.abc import MutableMapping
from collections import ChainMap as _ChainMap
import functools
import io
import itertools
import os
import re
import sys
import warnings
__all__ = ('NoSectionError', 'DuplicateOptionError', 'DuplicateSectionError', 'NoOptionError', 'InterpolationError', 'InterpolationDepthError', 'InterpolationMissingOptionError', 'InterpolationSyntaxError', 'ParsingError', 'MissingSectionHeaderError', 'ConfigParser', 'RawConfigParser', 'Interpolation', 'BasicInterpolation', 'ExtendedInterpolation', 'LegacyInterpolation', 'SectionProxy', 'ConverterMapping', 'DEFAULTSECT', 'MAX_INTERPOLATION_DEPTH')
_default_dict = dict
DEFAULTSECT = 'DEFAULT'
MAX_INTERPOLATION_DEPTH = 10

class Error(Exception):
    '''Base class for ConfigParser exceptions.'''
    
    def __init__(self, msg = ('',)):
        self.message = msg
        Exception.__init__(self, msg)

    
    def __repr__(self):
        return self.message

    __str__ = __repr__


class NoSectionError(Error):
    '''Raised when no section matches a requested option.'''
    
    def __init__(self, section):
        Error.__init__(self, f'''No section: {section!r}''')
        self.section = section
        self.args = (section,)



class DuplicateSectionError(Error):
    '''Raised when a section is repeated in an input source.

    Possible repetitions that raise this exception are: multiple creation
    using the API or in strict parsers when a section is found more than once
    in a single input file, string or dictionary.
    '''
    
    def __init__(self, section, source, lineno = (None, None)):
        msg = [
            repr(section),
            ' already exists']
    # WARNING: Decompyle incomplete



class DuplicateOptionError(Error):
    '''Raised by strict parsers when an option is repeated in an input source.

    Current implementation raises this exception only when an option is found
    more than once in a single file, string or dictionary.
    '''
    
    def __init__(self, section, option, source, lineno = (None, None)):
        msg = [
            repr(option),
            ' in section ',
            repr(section),
            ' already exists']
    # WARNING: Decompyle incomplete



class NoOptionError(Error):
    '''A requested option was not found.'''
    
    def __init__(self, option, section):
        Error.__init__(self, f'''No option {option!r} in section: {section!r}''')
        self.option = option
        self.section = section
        self.args = (option, section)



class InterpolationError(Error):
    '''Base class for interpolation-related exceptions.'''
    
    def __init__(self, option, section, msg):
        Error.__init__(self, msg)
        self.option = option
        self.section = section
        self.args = (option, section, msg)



class InterpolationMissingOptionError(InterpolationError):
    '''A string substitution required a setting which was not available.'''
    
    def __init__(self, option, section, rawval, reference):
        msg = 'Bad value substitution: option {!r} in section {!r} contains an interpolation key {!r} which is not a valid option name. Raw value: {!r}'.format(option, section, reference, rawval)
        InterpolationError.__init__(self, option, section, msg)
        self.reference = reference
        self.args = (option, section, rawval, reference)



class InterpolationSyntaxError(InterpolationError):
    '''Raised when the source text contains invalid syntax.

    Current implementation raises this exception when the source text into
    which substitutions are made does not conform to the required syntax.
    '''
    pass


class InterpolationDepthError(InterpolationError):
    '''Raised when substitutions are nested too deeply.'''
    
    def __init__(self, option, section, rawval):
        msg = 'Recursion limit exceeded in value substitution: option {!r} in section {!r} contains an interpolation key which cannot be substituted in {} steps. Raw value: {!r}'.format(option, section, MAX_INTERPOLATION_DEPTH, rawval)
        InterpolationError.__init__(self, option, section, msg)
        self.args = (option, section, rawval)



class ParsingError(Error):
    pass
# WARNING: Decompyle incomplete


class MissingSectionHeaderError(ParsingError):
    '''Raised when a key-value pair is found before any section header.'''
    
    def __init__(self, filename, lineno, line):
        Error.__init__(self, 'File contains no section headers.\nfile: %r, line: %d\n%r' % (filename, lineno, line))
        self.source = filename
        self.lineno = lineno
        self.line = line
        self.args = (filename, lineno, line)


_UNSET = object()

class Interpolation:
    '''Dummy interpolation that passes the value through with no changes.'''
    
    def before_get(self, parser, section, option, value, defaults):
        return value

    
    def before_set(self, parser, section, option, value):
        return value

    
    def before_read(self, parser, section, option, value):
        return value

    
    def before_write(self, parser, section, option, value):
        return value



class BasicInterpolation(Interpolation):
    '''Interpolation as implemented in the classic ConfigParser.

    The option values can contain format strings which refer to other values in
    the same section, or values in the special default section.

    For example:

        something: %(dir)s/whatever

    would resolve the "%(dir)s" to the value of dir.  All reference
    expansions are done late, on demand. If a user needs to use a bare % in
    a configuration file, she can escape it by writing %%. Other % usage
    is considered a user error and raises `InterpolationSyntaxError`.'''
    _KEYCRE = re.compile('%\\(([^)]+)\\)s')
    
    def before_get(self, parser, section, option, value, defaults):
        L = []
        self._interpolate_some(parser, option, L, value, section, defaults, 1)
        return ''.join(L)

    
    def before_set(self, parser, section, option, value):
        tmp_value = value.replace('%%', '')
        tmp_value = self._KEYCRE.sub('', tmp_value)
        if '%' in tmp_value:
            raise ValueError('invalid interpolation syntax in %r at position %d' % (value, tmp_value.find('%')))
        return value

    
    def _interpolate_some(self, parser, option, accum, rest, section, map, depth):
        rawval = parser.get(section, option, raw = True, fallback = rest)
        if depth > MAX_INTERPOLATION_DEPTH:
            raise InterpolationDepthError(option, section, rawval)
    # WARNING: Decompyle incomplete



class ExtendedInterpolation(Interpolation):
    '''Advanced variant of interpolation, supports the syntax used by
    `zc.buildout`. Enables interpolation between sections.'''
    _KEYCRE = re.compile('\\$\\{([^}]+)\\}')
    
    def before_get(self, parser, section, option, value, defaults):
        L = []
        self._interpolate_some(parser, option, L, value, section, defaults, 1)
        return ''.join(L)

    
    def before_set(self, parser, section, option, value):
        tmp_value = value.replace('$$', '')
        tmp_value = self._KEYCRE.sub('', tmp_value)
        if '$' in tmp_value:
            raise ValueError('invalid interpolation syntax in %r at position %d' % (value, tmp_value.find('$')))
        return value

    
    def _interpolate_some(self, parser, option, accum, rest, section, map, depth):
        rawval = parser.get(section, option, raw = True, fallback = rest)
        if depth > MAX_INTERPOLATION_DEPTH:
            raise InterpolationDepthError(option, section, rawval)
    # WARNING: Decompyle incomplete



class LegacyInterpolation(Interpolation):
    pass
# WARNING: Decompyle incomplete


class RawConfigParser(MutableMapping):
    pass
# WARNING: Decompyle incomplete


class ConfigParser(RawConfigParser):
    pass
# WARNING: Decompyle incomplete


class SectionProxy(MutableMapping):
    '''A proxy for a single section from a parser.'''
    
    def __init__(self, parser, name):
        '''Creates a view on a section of the specified `name` in `parser`.'''
        self._parser = parser
        self._name = name
        for conv in parser.converters:
            key = 'get' + conv
            getter = functools.partial(self.get, _impl = getattr(parser, key))
            setattr(self, key, getter)

    
    def __repr__(self):
        return '<Section: {}>'.format(self._name)

    
    def __getitem__(self, key):
        if not self._parser.has_option(self._name, key):
            raise KeyError(key)
        return self._parser.get(self._name, key)

    
    def __setitem__(self, key, value):
        self._parser._validate_value_types(option = key, value = value)
        return self._parser.set(self._name, key, value)

    
    def __delitem__(self, key):
        if not self._parser.has_option(self._name, key) or self._parser.remove_option(self._name, key):
            raise KeyError(key)

    
    def __contains__(self, key):
        return self._parser.has_option(self._name, key)

    
    def __len__(self):
        return len(self._options())

    
    def __iter__(self):
        return self._options().__iter__()

    
    def _options(self):
        if self._name != self._parser.default_section:
            return self._parser.options(self._name)
        return None._parser.defaults()

    parser = (lambda self: self._parser)()
    name = (lambda self: self._name)()
    
    def get(self = property, option = (None,), fallback = {
        'raw': False,
        'vars': None,
        '_impl': None }, *, raw, vars, _impl, **kwargs):
        '''Get an option value.

        Unless `fallback` is provided, `None` will be returned if the option
        is not found.

        '''
        if not _impl:
            _impl = self._parser.get
    # WARNING: Decompyle incomplete



class ConverterMapping(MutableMapping):
    '''Enables reuse of get*() methods between the parser and section proxies.

    If a parser class implements a getter directly, the value for the given
    key will be ``None``. The presence of the converter name here enables
    section proxies to find and use the implementation on the parser class.
    '''
    GETTERCRE = re.compile('^get(?P<name>.+)$')
    
    def __init__(self, parser):
        self._parser = parser
        self._data = { }
        for getter in dir(self._parser):
            m = self.GETTERCRE.match(getter)
            if not m or callable(getattr(self._parser, getter)):
                continue
            self._data[m.group('name')] = None

    
    def __getitem__(self, key):
        return self._data[key]

    
    def __setitem__(self, key, value):
        k = 'get' + key
        if k == 'get':
            raise ValueError('Incompatible key: cannot use "" as a name')
        self._data[key] = value
        func = functools.partial(self._parser._get_conv, conv = value)
        func.converter = value
        setattr(self._parser, k, func)
        for proxy in self._parser.values():
            getter = functools.partial(proxy.get, _impl = func)
            setattr(proxy, k, getter)
        return None
    # WARNING: Decompyle incomplete

    
    def __delitem__(self, key):
        if not key:
            key
        k = 'get' + None
        del self._data[key]
        for inst in itertools.chain((self._parser,), self._parser.values()):
            delattr(inst, k)
        return None
    # WARNING: Decompyle incomplete

    
    def __iter__(self):
        return iter(self._data)

    
    def __len__(self):
        return len(self._data)


