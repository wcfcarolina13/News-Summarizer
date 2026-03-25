# Source Generated with Decompyle++
# File: argparse.pyc (Python 3.12)

"""Command-line parsing library

This module is an optparse-inspired command-line parsing library that:

    - handles both optional and positional arguments
    - produces highly informative usage messages
    - supports parsers that dispatch to sub-parsers

The following is a simple usage example that sums integers from the
command-line and writes the result to a file::

    parser = argparse.ArgumentParser(
        description='sum the integers at the command line')
    parser.add_argument(
        'integers', metavar='int', nargs='+', type=int,
        help='an integer to be summed')
    parser.add_argument(
        '--log', default=sys.stdout, type=argparse.FileType('w'),
        help='the file where the sum should be written')
    args = parser.parse_args()
    args.log.write('%s' % sum(args.integers))
    args.log.close()

The module contains the following public classes:

    - ArgumentParser -- The main entry point for command-line parsing. As the
        example above shows, the add_argument() method is used to populate
        the parser with actions for optional and positional arguments. Then
        the parse_args() method is invoked to convert the args at the
        command-line into an object with attributes.

    - ArgumentError -- The exception raised by ArgumentParser objects when
        there are errors with the parser's actions. Errors raised while
        parsing the command-line are caught by ArgumentParser and emitted
        as command-line messages.

    - FileType -- A factory for defining types of files to be created. As the
        example above shows, instances of FileType are typically passed as
        the type= argument of add_argument() calls.

    - Action -- The base class for parser actions. Typically actions are
        selected by passing strings like 'store_true' or 'append_const' to
        the action= argument of add_argument(). However, for greater
        customization of ArgumentParser actions, subclasses of Action may
        be defined and passed as the action= argument.

    - HelpFormatter, RawDescriptionHelpFormatter, RawTextHelpFormatter,
        ArgumentDefaultsHelpFormatter -- Formatter classes which
        may be passed as the formatter_class= argument to the
        ArgumentParser constructor. HelpFormatter is the default,
        RawDescriptionHelpFormatter and RawTextHelpFormatter tell the parser
        not to change the formatting for help text, and
        ArgumentDefaultsHelpFormatter adds information about argument defaults
        to the help.

All other classes in this module are considered implementation details.
(Also note that HelpFormatter and RawDescriptionHelpFormatter are only
considered public as object names -- the API of the formatter objects is
still considered an implementation detail.)
"""
__version__ = '1.1'
__all__ = [
    'ArgumentParser',
    'ArgumentError',
    'ArgumentTypeError',
    'BooleanOptionalAction',
    'FileType',
    'HelpFormatter',
    'ArgumentDefaultsHelpFormatter',
    'RawDescriptionHelpFormatter',
    'RawTextHelpFormatter',
    'MetavarTypeHelpFormatter',
    'Namespace',
    'Action',
    'ONE_OR_MORE',
    'OPTIONAL',
    'PARSER',
    'REMAINDER',
    'SUPPRESS',
    'ZERO_OR_MORE']
import os as _os
import re as _re
import sys as _sys
import warnings
from gettext import gettext as _, ngettext
SUPPRESS = '==SUPPRESS=='
OPTIONAL = '?'
ZERO_OR_MORE = '*'
ONE_OR_MORE = '+'
PARSER = 'A...'
REMAINDER = '...'
_UNRECOGNIZED_ARGS_ATTR = '_unrecognized_args'

class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format::
        ClassName(attr=name, attr=name, ...)
    The attributes are determined either by a class-level attribute,
    '_kwarg_names', or by inspecting the instance __dict__.
    """
    
    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = []
        star_args = { }
        for arg in self._get_args():
            arg_strings.append(repr(arg))
        for name, value in self._get_kwargs():
            if name.isidentifier():
                arg_strings.append(f'''{name!s}={value!r}''')
                continue
            star_args[name] = value
        if star_args:
            arg_strings.append('**%s' % repr(star_args))
        return f'''{type_name!s}({', '.join(arg_strings)!s})'''

    
    def _get_kwargs(self):
        return list(self.__dict__.items())

    
    def _get_args(self):
        return []



def _copy_items(items):
    pass
# WARNING: Decompyle incomplete


class HelpFormatter(object):
    '''Formatter for generating usage messages and argument help strings.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    '''
    
    def __init__(self, prog, indent_increment, max_help_position, width = (2, 24, None)):
        pass
    # WARNING: Decompyle incomplete

    
    def _indent(self):
        pass

    
    def _dedent(self):
        pass
    # WARNING: Decompyle incomplete

    
    class _Section(object):
        
        def __init__(self, formatter, parent, heading = (None,)):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        
        def format_help(self):
            pass
        # WARNING: Decompyle incomplete


    
    def _add_item(self, func, args):
        self._current_section.items.append((func, args))

    
    def start_section(self, heading):
        self._indent()
        section = self._Section(self, self._current_section, heading)
        self._add_item(section.format_help, [])
        self._current_section = section

    
    def end_section(self):
        self._current_section = self._current_section.parent
        self._dedent()

    
    def add_text(self, text):
        pass
    # WARNING: Decompyle incomplete

    
    def add_usage(self, usage, actions, groups, prefix = (None,)):
        if usage is not SUPPRESS:
            args = (usage, actions, groups, prefix)
            self._add_item(self._format_usage, args)
            return None

    
    def add_argument(self, action):
        if action.help is not SUPPRESS:
            get_invocation = self._format_action_invocation
            invocations = [
                get_invocation(action)]
            for subaction in self._iter_indented_subactions(action):
                invocations.append(get_invocation(subaction))
            invocation_length = max(map(len, invocations))
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length, action_length)
            self._add_item(self._format_action, [
                action])
            return None

    
    def add_arguments(self, actions):
        for action in actions:
            self.add_argument(action)

    
    def format_help(self):
        help = self._root_section.format_help()
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n') + '\n'
        return help

    
    def _join_parts(self, part_strings):
        pass
    # WARNING: Decompyle incomplete

    
    def _format_usage(self, usage, actions, groups, prefix):
        pass
    # WARNING: Decompyle incomplete

    
    def _format_actions_usage(self, actions, groups):
        group_actions = set()
        inserts = { }
        for group in groups:
            if not group._group_actions:
                raise ValueError(f'''empty group {group}''')
            start = actions.index(group._group_actions[0])
            group_action_count = len(group._group_actions)
            end = start + group_action_count
            if not actions[start:end] == group._group_actions:
                continue
            suppressed_actions_count = 0
            for action in group._group_actions:
                group_actions.add(action)
                if not action.help is SUPPRESS:
                    continue
                suppressed_actions_count += 1
            exposed_actions_count = group_action_count - suppressed_actions_count
            if not group.required:
                if start in inserts:
                    pass
                else:
                    '[' = None
                if end in inserts:
                    pass
                else:
                    ']' = None
            elif exposed_actions_count > 1:
                if start in inserts:
                    pass
                else:
                    '(' = None
                if end in inserts:
                    pass
                else:
                    ')' = None
            for i in range(start + 1, end):
                inserts[i] = '|'
        parts = []
        for i, action in enumerate(actions):
            if action.help is SUPPRESS:
                parts.append(None)
                if inserts.get(i) == '|':
                    inserts.pop(i)
                    continue
                if not inserts.get(i + 1) == '|':
                    continue
                inserts.pop(i + 1)
                continue
            if not action.option_strings:
                default = self._get_default_metavar_for_positional(action)
                part = self._format_args(action, default)
                if action in group_actions and part[0] == '[' and part[-1] == ']':
                    part = part[1:-1]
                parts.append(part)
                continue
            option_string = action.option_strings[0]
            if action.required and action not in group_actions:
                part = '[%s]' % part
            parts.append(part)
        for i in sorted(inserts, reverse = True):
            parts[i:i] = [
                inserts[i]]
    # WARNING: Decompyle incomplete

    
    def _format_text(self, text):
        if '%(prog)' in text:
            text = text % dict(prog = self._prog)
        text_width = max(self._width - self._current_indent, 11)
        indent = ' ' * self._current_indent
        return self._fill_text(text, text_width, indent) + '\n\n'

    
    def _format_action(self, action):
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)
        if not action.help:
            tup = (self._current_indent, '', action_header)
            action_header = '%*s%s\n' % tup
        elif len(action_header) <= action_width:
            tup = (self._current_indent, '', action_width, action_header)
            action_header = '%*s%-*s  ' % tup
            indent_first = 0
        else:
            tup = (self._current_indent, '', action_header)
            action_header = '%*s%s\n' % tup
            indent_first = help_position
        parts = [
            action_header]
    # WARNING: Decompyle incomplete

    
    def _format_action_invocation(self, action):
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            (metavar,) = self._metavar_formatter(action, default)(1)
            return metavar
        parts = None
        if action.nargs == 0:
            parts.extend(action.option_strings)
        else:
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            for option_string in action.option_strings:
                parts.append(f'''{option_string!s} {args_string!s}''')
        return ', '.join(parts)

    
    def _metavar_formatter(self, action, default_metavar):
        pass
    # WARNING: Decompyle incomplete

    
    def _format_args(self, action, default_metavar):
        get_metavar = self._metavar_formatter(action, default_metavar)
    # WARNING: Decompyle incomplete

    
    def _expand_help(self, action):
        params = dict(vars(action), prog = self._prog)
        for name in list(params):
            if not params[name] is SUPPRESS:
                continue
            del params[name]
        for name in list(params):
            if not hasattr(params[name], '__name__'):
                continue
            params[name] = params[name].__name__
    # WARNING: Decompyle incomplete

    
    def _iter_indented_subactions(self, action):
        pass
    # WARNING: Decompyle incomplete

    
    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        import textwrap
        return textwrap.wrap(text, width)

    
    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        import textwrap
        return textwrap.fill(text, width, initial_indent = indent, subsequent_indent = indent)

    
    def _get_help_string(self, action):
        return action.help

    
    def _get_default_metavar_for_optional(self, action):
        return action.dest.upper()

    
    def _get_default_metavar_for_positional(self, action):
        return action.dest



class RawDescriptionHelpFormatter(HelpFormatter):
    '''Help message formatter which retains any formatting in descriptions.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    '''
    
    def _fill_text(self, text, width, indent):
        pass
    # WARNING: Decompyle incomplete



class RawTextHelpFormatter(RawDescriptionHelpFormatter):
    '''Help message formatter which retains formatting of all help text.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    '''
    
    def _split_lines(self, text, width):
        return text.splitlines()



class ArgumentDefaultsHelpFormatter(HelpFormatter):
    '''Help message formatter which adds default values to argument help.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    '''
    
    def _get_help_string(self, action):
        """
        Add the default value to the option help message.

        ArgumentDefaultsHelpFormatter and BooleanOptionalAction when it isn't
        already present. This code will do that, detecting cornercases to
        prevent duplicates or cases where it wouldn't make sense to the end
        user.
        """
        help = action.help
    # WARNING: Decompyle incomplete



class MetavarTypeHelpFormatter(HelpFormatter):
    """Help message formatter which uses the argument 'type' as the default
    metavar value (instead of the argument 'dest')

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """
    
    def _get_default_metavar_for_optional(self, action):
        return action.type.__name__

    
    def _get_default_metavar_for_positional(self, action):
        return action.type.__name__



def _get_action_name(argument):
    pass
# WARNING: Decompyle incomplete


class ArgumentError(Exception):
    '''An error from creating or using an argument (optional or positional).

    The string value of this exception is the message, augmented with
    information about the argument that caused it.
    '''
    
    def __init__(self, argument, message):
        self.argument_name = _get_action_name(argument)
        self.message = message

    
    def __str__(self):
        pass
    # WARNING: Decompyle incomplete



class ArgumentTypeError(Exception):
    '''An error from trying to convert a command line string to a type.'''
    pass


class Action(_AttributeHolder):
    """Information about how to convert command line strings to Python objects.

    Action objects are used by an ArgumentParser to represent the information
    needed to parse a single argument from one or more strings from the
    command line. The keyword arguments to the Action constructor are also
    all attributes of Action instances.

    Keyword Arguments:

        - option_strings -- A list of command-line option strings which
            should be associated with this action.

        - dest -- The name of the attribute to hold the created object(s)

        - nargs -- The number of command-line arguments that should be
            consumed. By default, one argument will be consumed and a single
            value will be produced.  Other values include:
                - N (an integer) consumes N arguments (and produces a list)
                - '?' consumes zero or one arguments
                - '*' consumes zero or more arguments (and produces a list)
                - '+' consumes one or more arguments (and produces a list)
            Note that the difference between the default and nargs=1 is that
            with the default, a single value will be produced, while with
            nargs=1, a list containing a single value will be produced.

        - const -- The value to be produced if the option is specified and the
            option uses an action that takes no values.

        - default -- The value to be produced if the option is not specified.

        - type -- A callable that accepts a single string argument, and
            returns the converted value.  The standard Python types str, int,
            float, and complex are useful examples of such callables.  If None,
            str is used.

        - choices -- A container of values that should be allowed. If not None,
            after a command-line argument has been converted to the appropriate
            type, an exception will be raised if it is not a member of this
            collection.

        - required -- True if the action must always be specified at the
            command line. This is only meaningful for optional command-line
            arguments.

        - help -- The help string describing the argument.

        - metavar -- The name to be used for the option's argument with the
            help string. If None, the 'dest' value will be used as the name.
    """
    
    def __init__(self, option_strings, dest, nargs, const, default, type, choices, required, help, metavar = (None, None, None, None, None, False, None, None)):
        self.option_strings = option_strings
        self.dest = dest
        self.nargs = nargs
        self.const = const
        self.default = default
        self.type = type
        self.choices = choices
        self.required = required
        self.help = help
        self.metavar = metavar

    
    def _get_kwargs(self):
        names = [
            'option_strings',
            'dest',
            'nargs',
            'const',
            'default',
            'type',
            'choices',
            'required',
            'help',
            'metavar']
    # WARNING: Decompyle incomplete

    
    def format_usage(self):
        return self.option_strings[0]

    
    def __call__(self, parser, namespace, values, option_string = (None,)):
        raise NotImplementedError(_('.__call__() not defined'))


_deprecated_default = object()

class BooleanOptionalAction(Action):
    pass
# WARNING: Decompyle incomplete


class _StoreAction(Action):
    pass
# WARNING: Decompyle incomplete


class _StoreConstAction(Action):
    pass
# WARNING: Decompyle incomplete


class _StoreTrueAction(_StoreConstAction):
    pass
# WARNING: Decompyle incomplete


class _StoreFalseAction(_StoreConstAction):
    pass
# WARNING: Decompyle incomplete


class _AppendAction(Action):
    pass
# WARNING: Decompyle incomplete


class _AppendConstAction(Action):
    pass
# WARNING: Decompyle incomplete


class _CountAction(Action):
    pass
# WARNING: Decompyle incomplete


class _HelpAction(Action):
    pass
# WARNING: Decompyle incomplete


class _VersionAction(Action):
    pass
# WARNING: Decompyle incomplete


class _SubParsersAction(Action):
    pass
# WARNING: Decompyle incomplete


class _ExtendAction(_AppendAction):
    
    def __call__(self, parser, namespace, values, option_string = (None,)):
        items = getattr(namespace, self.dest, None)
        items = _copy_items(items)
        items.extend(values)
        setattr(namespace, self.dest, items)



class FileType(object):
    """Factory for creating file object types

    Instances of FileType are typically passed as type= arguments to the
    ArgumentParser add_argument() method.

    Keyword Arguments:
        - mode -- A string indicating how the file is to be opened. Accepts the
            same values as the builtin open() function.
        - bufsize -- The file's desired buffer size. Accepts the same values as
            the builtin open() function.
        - encoding -- The file's encoding. Accepts the same values as the
            builtin open() function.
        - errors -- A string indicating how encoding and decoding errors are to
            be handled. Accepts the same value as the builtin open() function.
    """
    
    def __init__(self, mode, bufsize, encoding, errors = ('r', -1, None, None)):
        self._mode = mode
        self._bufsize = bufsize
        self._encoding = encoding
        self._errors = errors

    
    def __call__(self, string):
        pass
    # WARNING: Decompyle incomplete

    
    def __repr__(self):
        args = (self._mode, self._bufsize)
        kwargs = [
            ('encoding', self._encoding),
            ('errors', self._errors)]
    # WARNING: Decompyle incomplete



class Namespace(_AttributeHolder):
    '''Simple object for storing attributes.

    Implements equality by attribute names and values, and provides a simple
    string representation.
    '''
    
    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    
    def __eq__(self, other):
        if not isinstance(other, Namespace):
            return NotImplemented
        return None(self) == vars(other)

    
    def __contains__(self, key):
        return key in self.__dict__



class _ActionsContainer(object):
    pass
# WARNING: Decompyle incomplete


class _ArgumentGroup(_ActionsContainer):
    pass
# WARNING: Decompyle incomplete


class _MutuallyExclusiveGroup(_ArgumentGroup):
    pass
# WARNING: Decompyle incomplete


class ArgumentParser(_ActionsContainer, _AttributeHolder):
    pass
# WARNING: Decompyle incomplete

