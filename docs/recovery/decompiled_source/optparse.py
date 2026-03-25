# Source Generated with Decompyle++
# File: optparse.pyc (Python 3.12)

__doc__ = 'A powerful, extensible, and easy-to-use option parser.\n\nBy Greg Ward <gward@python.net>\n\nOriginally distributed as Optik.\n\nFor support, use the optik-users@lists.sourceforge.net mailing list\n(http://lists.sourceforge.net/lists/listinfo/optik-users).\n\nSimple usage example:\n\n   from optparse import OptionParser\n\n   parser = OptionParser()\n   parser.add_option("-f", "--file", dest="filename",\n                     help="write report to FILE", metavar="FILE")\n   parser.add_option("-q", "--quiet",\n                     action="store_false", dest="verbose", default=True,\n                     help="don\'t print status messages to stdout")\n\n   (options, args) = parser.parse_args()\n'
__version__ = '1.5.3'
__all__ = [
    'Option',
    'make_option',
    'SUPPRESS_HELP',
    'SUPPRESS_USAGE',
    'Values',
    'OptionContainer',
    'OptionGroup',
    'OptionParser',
    'HelpFormatter',
    'IndentedHelpFormatter',
    'TitledHelpFormatter',
    'OptParseError',
    'OptionError',
    'OptionConflictError',
    'OptionValueError',
    'BadOptionError',
    'check_choice']
__copyright__ = '\nCopyright (c) 2001-2006 Gregory P. Ward.  All rights reserved.\nCopyright (c) 2002-2006 Python Software Foundation.  All rights reserved.\n\nRedistribution and use in source and binary forms, with or without\nmodification, are permitted provided that the following conditions are\nmet:\n\n  * Redistributions of source code must retain the above copyright\n    notice, this list of conditions and the following disclaimer.\n\n  * Redistributions in binary form must reproduce the above copyright\n    notice, this list of conditions and the following disclaimer in the\n    documentation and/or other materials provided with the distribution.\n\n  * Neither the name of the author nor the names of its\n    contributors may be used to endorse or promote products derived from\n    this software without specific prior written permission.\n\nTHIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS\nIS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED\nTO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A\nPARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR\nCONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,\nEXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,\nPROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR\nPROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF\nLIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING\nNEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS\nSOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.\n'
import sys
import os
import textwrap

def _repr(self):
    return '<%s at 0x%x: %s>' % (self.__class__.__name__, id(self), self)

from gettext import gettext, ngettext
_ = gettext

class OptParseError(Exception):
    
    def __init__(self, msg):
        self.msg = msg

    
    def __str__(self):
        return self.msg



class OptionError(OptParseError):
    '''
    Raised if an Option instance is created with invalid or
    inconsistent arguments.
    '''
    
    def __init__(self, msg, option):
        self.msg = msg
        self.option_id = str(option)

    
    def __str__(self):
        if self.option_id:
            return f'''option {self.option_id!s}: {self.msg!s}'''
        return None.msg



class OptionConflictError(OptionError):
    '''
    Raised if conflicting options are added to an OptionParser.
    '''
    pass


class OptionValueError(OptParseError):
    '''
    Raised if an invalid option value is encountered on the command
    line.
    '''
    pass


class BadOptionError(OptParseError):
    '''
    Raised if an invalid option is seen on the command line.
    '''
    
    def __init__(self, opt_str):
        self.opt_str = opt_str

    
    def __str__(self):
        return _('no such option: %s') % self.opt_str



class AmbiguousOptionError(BadOptionError):
    '''
    Raised if an ambiguous option is seen on the command line.
    '''
    
    def __init__(self, opt_str, possibilities):
        BadOptionError.__init__(self, opt_str)
        self.possibilities = possibilities

    
    def __str__(self):
        return _('ambiguous option: %s (%s?)') % (self.opt_str, ', '.join(self.possibilities))



class HelpFormatter:
    '''
    Abstract base class for formatting option help.  OptionParser
    instances should use one of the HelpFormatter subclasses for
    formatting help; by default IndentedHelpFormatter is used.

    Instance attributes:
      parser : OptionParser
        the controlling OptionParser instance
      indent_increment : int
        the number of columns to indent per nesting level
      max_help_position : int
        the maximum starting column for option help text
      help_position : int
        the calculated starting column for option help text;
        initially the same as the maximum
      width : int
        total number of columns for output (pass None to constructor for
        this value to be taken from the $COLUMNS environment variable)
      level : int
        current indentation level
      current_indent : int
        current indentation level (in columns)
      help_width : int
        number of columns available for option help text (calculated)
      default_tag : str
        text to replace with each option\'s default value, "%default"
        by default.  Set to false value to disable default value expansion.
      option_strings : { Option : str }
        maps Option instances to the snippet of help text explaining
        the syntax of that option, e.g. "-h, --help" or
        "-fFILE, --file=FILE"
      _short_opt_fmt : str
        format string controlling how short options with values are
        printed in help text.  Must be either "%s%s" ("-fFILE") or
        "%s %s" ("-f FILE"), because those are the two syntaxes that
        Optik supports.
      _long_opt_fmt : str
        similar but for long options; must be either "%s %s" ("--file FILE")
        or "%s=%s" ("--file=FILE").
    '''
    NO_DEFAULT_VALUE = 'none'
    
    def __init__(self, indent_increment, max_help_position, width, short_first):
        self.parser = None
        self.indent_increment = indent_increment
    # WARNING: Decompyle incomplete

    
    def set_parser(self, parser):
        self.parser = parser

    
    def set_short_opt_delimiter(self, delim):
        if delim not in ('', ' '):
            raise ValueError('invalid metavar delimiter for short options: %r' % delim)
        self._short_opt_fmt = '%s' + delim + '%s'

    
    def set_long_opt_delimiter(self, delim):
        if delim not in ('=', ' '):
            raise ValueError('invalid metavar delimiter for long options: %r' % delim)
        self._long_opt_fmt = '%s' + delim + '%s'

    
    def indent(self):
        pass

    
    def dedent(self):
        pass
    # WARNING: Decompyle incomplete

    
    def format_usage(self, usage):
        raise NotImplementedError('subclasses must implement')

    
    def format_heading(self, heading):
        raise NotImplementedError('subclasses must implement')

    
    def _format_text(self, text):
        '''
        Format a paragraph of free-form text for inclusion in the
        help output at the current indentation level.
        '''
        text_width = max(self.width - self.current_indent, 11)
        indent = ' ' * self.current_indent
        return textwrap.fill(text, text_width, initial_indent = indent, subsequent_indent = indent)

    
    def format_description(self, description):
        if description:
            return self._format_text(description) + '\n'

    
    def format_epilog(self, epilog):
        if epilog:
            return '\n' + self._format_text(epilog) + '\n'

    
    def expand_default(self, option):
        pass
    # WARNING: Decompyle incomplete

    
    def format_option(self, option):
        result = []
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = '%*s%s\n' % (self.current_indent, '', opts)
            indent_first = self.help_position
        else:
            opts = '%*s%-*s  ' % (self.current_indent, '', opt_width, opts)
            indent_first = 0
        result.append(opts)
    # WARNING: Decompyle incomplete

    
    def store_option_strings(self, parser):
        self.indent()
        max_len = 0
        for opt in parser.option_list:
            strings = self.format_option_strings(opt)
            self.option_strings[opt] = strings
            max_len = max(max_len, len(strings) + self.current_indent)
        self.indent()
        for group in parser.option_groups:
            for opt in group.option_list:
                strings = self.format_option_strings(opt)
                self.option_strings[opt] = strings
                max_len = max(max_len, len(strings) + self.current_indent)
        self.dedent()
        self.dedent()
        self.help_position = min(max_len + 2, self.max_help_position)
        self.help_width = max(self.width - self.help_position, 11)

    
    def format_option_strings(self, option):
        '''Return a comma-separated list of option strings & metavariables.'''
        pass
    # WARNING: Decompyle incomplete



class IndentedHelpFormatter(HelpFormatter):
    '''Format help with indented section bodies.
    '''
    
    def __init__(self, indent_increment, max_help_position, width, short_first = (2, 24, None, 1)):
        HelpFormatter.__init__(self, indent_increment, max_help_position, width, short_first)

    
    def format_usage(self, usage):
        return _('Usage: %s\n') % usage

    
    def format_heading(self, heading):
        return '%*s%s:\n' % (self.current_indent, '', heading)



class TitledHelpFormatter(HelpFormatter):
    '''Format help with underlined section headers.
    '''
    
    def __init__(self, indent_increment, max_help_position, width, short_first = (0, 24, None, 0)):
        HelpFormatter.__init__(self, indent_increment, max_help_position, width, short_first)

    
    def format_usage(self, usage):
        return f'''{self.format_heading(_('Usage'))!s}  {usage!s}\n'''

    
    def format_heading(self, heading):
        return f'''{heading!s}\n{'=-'[self.level] * len(heading)!s}\n'''



def _parse_num(val, type):
    if val[:2].lower() == '0x':
        radix = 16
    elif val[:2].lower() == '0b':
        radix = 2
        if not val[2:]:
            val[2:]
        val = '0'
    elif val[:1] == '0':
        radix = 8
    else:
        radix = 10
    return type(val, radix)


def _parse_int(val):
    return _parse_num(val, int)

_builtin_cvt = {
    'int': (_parse_int, _('integer')),
    'long': (_parse_int, _('integer')),
    'float': (float, _('floating-point')),
    'complex': (complex, _('complex')) }

def check_builtin(option, opt, value):
    (cvt, what) = _builtin_cvt[option.type]
    return cvt(value)
# WARNING: Decompyle incomplete


def check_choice(option, opt, value):
    if value in option.choices:
        return value
    choices = None.join(map(repr, option.choices))
    raise OptionValueError(_('option %s: invalid choice: %r (choose from %s)') % (opt, value, choices))

NO_DEFAULT = ('NO', 'DEFAULT')

class Option:
    '''
    Instance attributes:
      _short_opts : [string]
      _long_opts : [string]

      action : string
      type : string
      dest : string
      default : any
      nargs : int
      const : any
      choices : [string]
      callback : function
      callback_args : (any*)
      callback_kwargs : { string : any }
      help : string
      metavar : string
    '''
    ATTRS = [
        'action',
        'type',
        'dest',
        'default',
        'nargs',
        'const',
        'choices',
        'callback',
        'callback_args',
        'callback_kwargs',
        'help',
        'metavar']
    ACTIONS = ('store', 'store_const', 'store_true', 'store_false', 'append', 'append_const', 'count', 'callback', 'help', 'version')
    STORE_ACTIONS = ('store', 'store_const', 'store_true', 'store_false', 'append', 'append_const', 'count')
    TYPED_ACTIONS = ('store', 'append', 'callback')
    ALWAYS_TYPED_ACTIONS = ('store', 'append')
    CONST_ACTIONS = ('store_const', 'append_const')
    TYPES = ('string', 'int', 'long', 'float', 'complex', 'choice')
    TYPE_CHECKER = {
        'int': check_builtin,
        'long': check_builtin,
        'float': check_builtin,
        'complex': check_builtin,
        'choice': check_choice }
    CHECK_METHODS = None
    
    def __init__(self, *opts, **attrs):
        self._short_opts = []
        self._long_opts = []
        opts = self._check_opt_strings(opts)
        self._set_opt_strings(opts)
        self._set_attrs(attrs)
        for checker in self.CHECK_METHODS:
            checker(self)

    
    def _check_opt_strings(self, opts):
        pass
    # WARNING: Decompyle incomplete

    
    def _set_opt_strings(self, opts):
        for opt in opts:
            if len(opt) < 2:
                raise OptionError('invalid option string %r: must be at least two characters long' % opt, self)
            if len(opt) == 2:
                if not opt[0] == '-' or opt[1] != '-':
                    raise OptionError('invalid short option string %r: must be of the form -x, (x any non-dash char)' % opt, self)
                self._short_opts.append(opt)
                continue
            if not opt[0:2] == '--' or opt[2] != '-':
                raise OptionError('invalid long option string %r: must start with --, followed by non-dash' % opt, self)
            self._long_opts.append(opt)

    
    def _set_attrs(self, attrs):
        for attr in self.ATTRS:
            if attr in attrs:
                setattr(self, attr, attrs[attr])
                del attrs[attr]
                continue
            if attr == 'default':
                setattr(self, attr, NO_DEFAULT)
                continue
            setattr(self, attr, None)
        if attrs:
            attrs = sorted(attrs.keys())
            raise OptionError('invalid keyword arguments: %s' % ', '.join(attrs), self)

    
    def _check_action(self):
        pass
    # WARNING: Decompyle incomplete

    
    def _check_type(self):
        pass
    # WARNING: Decompyle incomplete

    
    def _check_choice(self):
        pass
    # WARNING: Decompyle incomplete

    
    def _check_dest(self):
        if not self.action in self.STORE_ACTIONS:
            self.action in self.STORE_ACTIONS
        takes_value = self.type is not None
    # WARNING: Decompyle incomplete

    
    def _check_const(self):
        pass
    # WARNING: Decompyle incomplete

    
    def _check_nargs(self):
        pass
    # WARNING: Decompyle incomplete

    
    def _check_callback(self):
        pass
    # WARNING: Decompyle incomplete

    CHECK_METHODS = [
        _check_action,
        _check_type,
        _check_choice,
        _check_dest,
        _check_const,
        _check_nargs,
        _check_callback]
    
    def __str__(self):
        return '/'.join(self._short_opts + self._long_opts)

    __repr__ = _repr
    
    def takes_value(self):
        return self.type is not None

    
    def get_opt_string(self):
        if self._long_opts:
            return self._long_opts[0]
        return None._short_opts[0]

    
    def check_value(self, opt, value):
        checker = self.TYPE_CHECKER.get(self.type)
    # WARNING: Decompyle incomplete

    
    def convert_value(self, opt, value):
        pass
    # WARNING: Decompyle incomplete

    
    def process(self, opt, value, values, parser):
        value = self.convert_value(opt, value)
        return self.take_action(self.action, self.dest, opt, value, values, parser)

    
    def take_action(self, action, dest, opt, value, values, parser):
        if action == 'store':
            setattr(values, dest, value)
            return 1
        if action == 'store_const':
            setattr(values, dest, self.const)
            return 1
        if action == 'store_true':
            setattr(values, dest, True)
            return 1
        if action == 'store_false':
            setattr(values, dest, False)
            return 1
        if action == 'append':
            values.ensure_value(dest, []).append(value)
            return 1
        if action == 'append_const':
            values.ensure_value(dest, []).append(self.const)
            return 1
        if action == 'count':
            setattr(values, dest, values.ensure_value(dest, 0) + 1)
            return 1
    # WARNING: Decompyle incomplete


SUPPRESS_HELP = 'SUPPRESSHELP'
SUPPRESS_USAGE = 'SUPPRESSUSAGE'

class Values:
    
    def __init__(self, defaults = (None,)):
        if defaults:
            for attr, val in defaults.items():
                setattr(self, attr, val)
            return None

    
    def __str__(self):
        return str(self.__dict__)

    __repr__ = _repr
    
    def __eq__(self, other):
        if isinstance(other, Values):
            return self.__dict__ == other.__dict__
        if None(other, dict):
            return self.__dict__ == other

    
    def _update_careful(self, dict):
        '''
        Update the option values from an arbitrary dictionary, but only
        use keys from dict that already have a corresponding attribute
        in self.  Any keys in dict without a corresponding attribute
        are silently ignored.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _update_loose(self, dict):
        '''
        Update the option values from an arbitrary dictionary,
        using all keys from the dictionary regardless of whether
        they have a corresponding attribute in self or not.
        '''
        self.__dict__.update(dict)

    
    def _update(self, dict, mode):
        if mode == 'careful':
            self._update_careful(dict)
            return None
        if mode == 'loose':
            self._update_loose(dict)
            return None
        raise ValueError('invalid update mode: %r' % mode)

    
    def read_module(self, modname, mode = ('careful',)):
        __import__(modname)
        mod = sys.modules[modname]
        self._update(vars(mod), mode)

    
    def read_file(self, filename, mode = ('careful',)):
        vars = { }
        exec(open(filename).read(), vars)
        self._update(vars, mode)

    
    def ensure_value(self, attr, value):
        pass
    # WARNING: Decompyle incomplete



class OptionContainer:
    '''
    Abstract base class.

    Class attributes:
      standard_option_list : [Option]
        list of standard options that will be accepted by all instances
        of this parser class (intended to be overridden by subclasses).

    Instance attributes:
      option_list : [Option]
        the list of Option objects contained by this OptionContainer
      _short_opt : { string : Option }
        dictionary mapping short option strings, eg. "-f" or "-X",
        to the Option instances that implement them.  If an Option
        has multiple short option strings, it will appear in this
        dictionary multiple times. [1]
      _long_opt : { string : Option }
        dictionary mapping long option strings, eg. "--file" or
        "--exclude", to the Option instances that implement them.
        Again, a given Option can occur multiple times in this
        dictionary. [1]
      defaults : { string : any }
        dictionary mapping option destination names to default
        values for each destination [1]

    [1] These mappings are common to (shared by) all components of the
        controlling OptionParser, where they are initially created.

    '''
    
    def __init__(self, option_class, conflict_handler, description):
        self._create_option_list()
        self.option_class = option_class
        self.set_conflict_handler(conflict_handler)
        self.set_description(description)

    
    def _create_option_mappings(self):
        self._short_opt = { }
        self._long_opt = { }
        self.defaults = { }

    
    def _share_option_mappings(self, parser):
        self._short_opt = parser._short_opt
        self._long_opt = parser._long_opt
        self.defaults = parser.defaults

    
    def set_conflict_handler(self, handler):
        if handler not in ('error', 'resolve'):
            raise ValueError('invalid conflict_resolution value %r' % handler)
        self.conflict_handler = handler

    
    def set_description(self, description):
        self.description = description

    
    def get_description(self):
        return self.description

    
    def destroy(self):
        '''see OptionParser.destroy().'''
        del self._short_opt
        del self._long_opt
        del self.defaults

    
    def _check_conflict(self, option):
        conflict_opts = []
        for opt in option._short_opts:
            if not opt in self._short_opt:
                continue
            conflict_opts.append((opt, self._short_opt[opt]))
        for opt in option._long_opts:
            if not opt in self._long_opt:
                continue
            conflict_opts.append((opt, self._long_opt[opt]))
    # WARNING: Decompyle incomplete

    
    def add_option(self, *args, **kwargs):
        '''add_option(Option)
           add_option(opt_str, ..., kwarg=val, ...)
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def add_options(self, option_list):
        for option in option_list:
            self.add_option(option)

    
    def get_option(self, opt_str):
        if not self._short_opt.get(opt_str):
            self._short_opt.get(opt_str)
        return self._long_opt.get(opt_str)

    
    def has_option(self, opt_str):
        if not opt_str in self._short_opt:
            opt_str in self._short_opt
        return opt_str in self._long_opt

    
    def remove_option(self, opt_str):
        option = self._short_opt.get(opt_str)
    # WARNING: Decompyle incomplete

    
    def format_option_help(self, formatter):
        if not self.option_list:
            return ''
        result = []
        for option in self.option_list:
            if not option.help is not SUPPRESS_HELP:
                continue
            result.append(formatter.format_option(option))
        return ''.join(result)

    
    def format_description(self, formatter):
        return formatter.format_description(self.get_description())

    
    def format_help(self, formatter):
        result = []
        if self.description:
            result.append(self.format_description(formatter))
        if self.option_list:
            result.append(self.format_option_help(formatter))
        return '\n'.join(result)



class OptionGroup(OptionContainer):
    
    def __init__(self, parser, title, description = (None,)):
        self.parser = parser
        OptionContainer.__init__(self, parser.option_class, parser.conflict_handler, description)
        self.title = title

    
    def _create_option_list(self):
        self.option_list = []
        self._share_option_mappings(self.parser)

    
    def set_title(self, title):
        self.title = title

    
    def destroy(self):
        '''see OptionParser.destroy().'''
        OptionContainer.destroy(self)
        del self.option_list

    
    def format_help(self, formatter):
        result = formatter.format_heading(self.title)
        formatter.indent()
        result += OptionContainer.format_help(self, formatter)
        formatter.dedent()
        return result



class OptionParser(OptionContainer):
    '''
    Class attributes:
      standard_option_list : [Option]
        list of standard options that will be accepted by all instances
        of this parser class (intended to be overridden by subclasses).

    Instance attributes:
      usage : string
        a usage string for your program.  Before it is displayed
        to the user, "%prog" will be expanded to the name of
        your program (self.prog or os.path.basename(sys.argv[0])).
      prog : string
        the name of the current program (to override
        os.path.basename(sys.argv[0])).
      description : string
        A paragraph of text giving a brief overview of your program.
        optparse reformats this paragraph to fit the current terminal
        width and prints it when the user requests help (after usage,
        but before the list of options).
      epilog : string
        paragraph of help text to print after option help

      option_groups : [OptionGroup]
        list of option groups in this parser (option groups are
        irrelevant for parsing the command-line, but very useful
        for generating help)

      allow_interspersed_args : bool = true
        if true, positional arguments may be interspersed with options.
        Assuming -a and -b each take a single argument, the command-line
          -ablah foo bar -bboo baz
        will be interpreted the same as
          -ablah -bboo -- foo bar baz
        If this flag were false, that command line would be interpreted as
          -ablah -- foo bar -bboo baz
        -- ie. we stop processing options as soon as we see the first
        non-option argument.  (This is the tradition followed by
        Python\'s getopt module, Perl\'s Getopt::Std, and other argument-
        parsing libraries, but it is generally annoying to users.)

      process_default_values : bool = true
        if true, option default values are processed similarly to option
        values from the command line: that is, they are passed to the
        type-checking function for the option\'s type (as long as the
        default value is a string).  (This really only matters if you
        have defined custom types; see SF bug #955889.)  Set it to false
        to restore the behaviour of Optik 1.4.1 and earlier.

      rargs : [string]
        the argument list currently being parsed.  Only set when
        parse_args() is active, and continually trimmed down as
        we consume arguments.  Mainly there for the benefit of
        callback options.
      largs : [string]
        the list of leftover arguments that we have skipped while
        parsing options.  If allow_interspersed_args is false, this
        list is always empty.
      values : Values
        the set of option values currently being accumulated.  Only
        set when parse_args() is active.  Also mainly for callbacks.

    Because of the \'rargs\', \'largs\', and \'values\' attributes,
    OptionParser is not thread-safe.  If, for some perverse reason, you
    need to parse command-line arguments simultaneously in different
    threads, use different OptionParser instances.

    '''
    standard_option_list = []
    
    def __init__(self, usage, option_list, option_class, version, conflict_handler, description, formatter, add_help_option, prog, epilog = (None, None, Option, None, 'error', None, None, True, None, None)):
        OptionContainer.__init__(self, option_class, conflict_handler, description)
        self.set_usage(usage)
        self.prog = prog
        self.version = version
        self.allow_interspersed_args = True
        self.process_default_values = True
    # WARNING: Decompyle incomplete

    
    def destroy(self):
        '''
        Declare that you are done with this OptionParser.  This cleans up
        reference cycles so the OptionParser (and all objects referenced by
        it) can be garbage-collected promptly.  After calling destroy(), the
        OptionParser is unusable.
        '''
        OptionContainer.destroy(self)
        for group in self.option_groups:
            group.destroy()
        del self.option_list
        del self.option_groups
        del self.formatter

    
    def _create_option_list(self):
        self.option_list = []
        self.option_groups = []
        self._create_option_mappings()

    
    def _add_help_option(self):
        self.add_option('-h', '--help', action = 'help', help = _('show this help message and exit'))

    
    def _add_version_option(self):
        self.add_option('--version', action = 'version', help = _("show program's version number and exit"))

    
    def _populate_option_list(self, option_list, add_help = (True,)):
        if self.standard_option_list:
            self.add_options(self.standard_option_list)
        if option_list:
            self.add_options(option_list)
        if self.version:
            self._add_version_option()
        if add_help:
            self._add_help_option()
            return None

    
    def _init_parsing_state(self):
        self.rargs = None
        self.largs = None
        self.values = None

    
    def set_usage(self, usage):
        pass
    # WARNING: Decompyle incomplete

    
    def enable_interspersed_args(self):
        '''Set parsing to not stop on the first non-option, allowing
        interspersing switches with command arguments. This is the
        default behavior. See also disable_interspersed_args() and the
        class documentation description of the attribute
        allow_interspersed_args.'''
        self.allow_interspersed_args = True

    
    def disable_interspersed_args(self):
        """Set parsing to stop on the first non-option. Use this if
        you have a command processor which runs another command that
        has options of its own and you want to make sure these options
        don't get confused.
        """
        self.allow_interspersed_args = False

    
    def set_process_default_values(self, process):
        self.process_default_values = process

    
    def set_default(self, dest, value):
        self.defaults[dest] = value

    
    def set_defaults(self, **kwargs):
        self.defaults.update(kwargs)

    
    def _get_all_options(self):
        options = self.option_list[:]
        for group in self.option_groups:
            options.extend(group.option_list)
        return options

    
    def get_default_values(self):
        if not self.process_default_values:
            return Values(self.defaults)
        defaults = None.defaults.copy()
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if not isinstance(default, str):
                continue
            opt_str = option.get_opt_string()
            defaults[option.dest] = option.check_value(opt_str, default)
        return Values(defaults)

    
    def add_option_group(self, *args, **kwargs):
        pass
    # WARNING: Decompyle incomplete

    
    def get_option_group(self, opt_str):
        if not self._short_opt.get(opt_str):
            self._short_opt.get(opt_str)
        option = self._long_opt.get(opt_str)
        if option and option.container is not self:
            return option.container

    
    def _get_args(self, args):
        pass
    # WARNING: Decompyle incomplete

    
    def parse_args(self, args, values = (None, None)):
        """
        parse_args(args : [string] = sys.argv[1:],
                   values : Values = None)
        -> (values : Values, args : [string])

        Parse the command-line options found in 'args' (default:
        sys.argv[1:]).  Any errors result in a call to 'error()', which
        by default prints the usage message to stderr and calls
        sys.exit() with an error message.  On success returns a pair
        (values, args) where 'values' is a Values instance (with all
        your option values) and 'args' is the list of arguments left
        over after parsing options.
        """
        rargs = self._get_args(args)
    # WARNING: Decompyle incomplete

    
    def check_values(self, values, args):
        '''
        check_values(values : Values, args : [string])
        -> (values : Values, args : [string])

        Check that the supplied option values and leftover arguments are
        valid.  Returns the option values and leftover arguments
        (possibly adjusted, possibly completely new -- whatever you
        like).  Default implementation just returns the passed-in
        values; subclasses may override as desired.
        '''
        return (values, args)

    
    def _process_args(self, largs, rargs, values):
        """_process_args(largs : [string],
                         rargs : [string],
                         values : Values)

        Process command-line arguments and populate 'values', consuming
        options and arguments from 'rargs'.  If 'allow_interspersed_args' is
        false, stop at the first non-option argument.  If true, accumulate any
        interspersed non-option arguments in 'largs'.
        """
        if rargs:
            arg = rargs[0]
            if arg == '--':
                del rargs[0]
                return None
            if arg[0:2] == '--':
                self._process_long_opt(rargs, values)
            elif arg[:1] == '-' and len(arg) > 1:
                self._process_short_opts(rargs, values)
            elif self.allow_interspersed_args:
                largs.append(arg)
                del rargs[0]
            else:
                return None
            if rargs:
                continue
            return None

    
    def _match_long_opt(self, opt):
        """_match_long_opt(opt : string) -> string

        Determine which long option string 'opt' matches, ie. which one
        it is an unambiguous abbreviation for.  Raises BadOptionError if
        'opt' doesn't unambiguously match any long option string.
        """
        return _match_abbrev(opt, self._long_opt)

    
    def _process_long_opt(self, rargs, values):
        arg = rargs.pop(0)
        if '=' in arg:
            (opt, next_arg) = arg.split('=', 1)
            rargs.insert(0, next_arg)
            had_explicit_value = True
        else:
            opt = arg
            had_explicit_value = False
        opt = self._match_long_opt(opt)
        option = self._long_opt[opt]
        if option.takes_value():
            nargs = option.nargs
            if len(rargs) < nargs:
                self.error(ngettext('%(option)s option requires %(number)d argument', '%(option)s option requires %(number)d arguments', nargs) % {
                    'option': opt,
                    'number': nargs })
            elif nargs == 1:
                value = rargs.pop(0)
            else:
                value = tuple(rargs[0:nargs])
                del rargs[0:nargs]
        elif had_explicit_value:
            self.error(_('%s option does not take a value') % opt)
        else:
            value = None
    # WARNING: Decompyle incomplete

    
    def _process_short_opts(self, rargs, values):
        arg = rargs.pop(0)
        stop = False
        i = 1
    # WARNING: Decompyle incomplete

    
    def get_prog_name(self):
        pass
    # WARNING: Decompyle incomplete

    
    def expand_prog_name(self, s):
        return s.replace('%prog', self.get_prog_name())

    
    def get_description(self):
        return self.expand_prog_name(self.description)

    
    def exit(self, status, msg = (0, None)):
        if msg:
            sys.stderr.write(msg)
        sys.exit(status)

    
    def error(self, msg):
        """error(msg : string)

        Print a usage message incorporating 'msg' to stderr and exit.
        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(sys.stderr)
        self.exit(2, f'''{self.get_prog_name()!s}: error: {msg!s}\n''')

    
    def get_usage(self):
        if self.usage:
            return self.formatter.format_usage(self.expand_prog_name(self.usage))

    
    def print_usage(self, file = (None,)):
        '''print_usage(file : file = stdout)

        Print the usage message for the current program (self.usage) to
        \'file\' (default stdout).  Any occurrence of the string "%prog" in
        self.usage is replaced with the name of the current program
        (basename of sys.argv[0]).  Does nothing if self.usage is empty
        or not defined.
        '''
        if self.usage:
            print(self.get_usage(), file = file)
            return None

    
    def get_version(self):
        if self.version:
            return self.expand_prog_name(self.version)

    
    def print_version(self, file = (None,)):
        '''print_version(file : file = stdout)

        Print the version message for this program (self.version) to
        \'file\' (default stdout).  As with print_usage(), any occurrence
        of "%prog" in self.version is replaced by the current program\'s
        name.  Does nothing if self.version is empty or undefined.
        '''
        if self.version:
            print(self.get_version(), file = file)
            return None

    
    def format_option_help(self, formatter = (None,)):
        pass
    # WARNING: Decompyle incomplete

    
    def format_epilog(self, formatter):
        return formatter.format_epilog(self.epilog)

    
    def format_help(self, formatter = (None,)):
        pass
    # WARNING: Decompyle incomplete

    
    def print_help(self, file = (None,)):
        """print_help(file : file = stdout)

        Print an extended help message, listing all options and any
        help text provided with them, to 'file' (default stdout).
        """
        pass
    # WARNING: Decompyle incomplete



def _match_abbrev(s, wordmap):
    """_match_abbrev(s : string, wordmap : {string : Option}) -> string

    Return the string key in 'wordmap' for which 's' is an unambiguous
    abbreviation.  If 's' is found to be ambiguous or doesn't match any of
    'words', raise BadOptionError.
    """
    if s in wordmap:
        return s
# WARNING: Decompyle incomplete

make_option = Option
return None
# WARNING: Decompyle incomplete
