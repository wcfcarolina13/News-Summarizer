# Source Generated with Decompyle++
# File: gettext.pyc (Python 3.12)

__doc__ = 'Internationalization and localization support.\n\nThis module provides internationalization (I18N) and localization (L10N)\nsupport for your Python programs by providing an interface to the GNU gettext\nmessage catalog library.\n\nI18N refers to the operation by which a program is made aware of multiple\nlanguages.  L10N refers to the adaptation of your program, once\ninternationalized, to the local language and cultural habits.\n\n'
import os
import re
import sys
__all__ = [
    'NullTranslations',
    'GNUTranslations',
    'Catalog',
    'bindtextdomain',
    'find',
    'translation',
    'install',
    'textdomain',
    'dgettext',
    'dngettext',
    'gettext',
    'ngettext',
    'pgettext',
    'dpgettext',
    'npgettext',
    'dnpgettext']
_default_localedir = os.path.join(sys.base_prefix, 'share', 'locale')
_token_pattern = re.compile('\n        (?P<WHITESPACES>[ \\t]+)                    | # spaces and horizontal tabs\n        (?P<NUMBER>[0-9]+\\b)                       | # decimal integer\n        (?P<NAME>n\\b)                              | # only n is allowed\n        (?P<PARENTHESIS>[()])                      |\n        (?P<OPERATOR>[-*/%+?:]|[><!]=?|==|&&|\\|\\|) | # !, *, /, %, +, -, <, >,\n                                                     # <=, >=, ==, !=, &&, ||,\n                                                     # ? :\n                                                     # unary and bitwise ops\n                                                     # not allowed\n        (?P<INVALID>\\w+|.)                           # invalid token\n    ', re.VERBOSE | re.DOTALL)

def _tokenize(plural):
    pass
# WARNING: Decompyle incomplete


def _error(value):
    if value:
        return ValueError('unexpected token in plural form: %s' % value)
    return None('unexpected end of plural form')

_binary_ops = (('||',), ('&&',), ('==', '!='), ('<', '>', '<=', '>='), ('+', '-'), ('*', '/', '%'))
# WARNING: Decompyle incomplete
