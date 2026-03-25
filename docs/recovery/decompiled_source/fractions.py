# Source Generated with Decompyle++
# File: fractions.pyc (Python 3.12)

'''Fraction, infinite-precision, rational numbers.'''
from decimal import Decimal
import functools
import math
import numbers
import operator
import re
import sys
__all__ = [
    'Fraction']
_PyHASH_MODULUS = sys.hash_info.modulus
_PyHASH_INF = sys.hash_info.inf
_hash_algorithm = (lambda numerator, denominator: dinv = pow(denominator, -1, _PyHASH_MODULUS)hash_ = hash(hash(abs(numerator)) * dinv)result = hash_ if numerator >= 0 else -hash_if result == -1:
-2None# WARNING: Decompyle incomplete
)()
_RATIONAL_FORMAT = re.compile('\n    \\A\\s*                                 # optional whitespace at the start,\n    (?P<sign>[-+]?)                       # an optional sign, then\n    (?=\\d|\\.\\d)                           # lookahead for digit or .digit\n    (?P<num>\\d*|\\d+(_\\d+)*)               # numerator (possibly empty)\n    (?:                                   # followed by\n       (?:\\s*/\\s*(?P<denom>\\d+(_\\d+)*))?  # an optional denominator\n    |                                     # or\n       (?:\\.(?P<decimal>d*|\\d+(_\\d+)*))?  # an optional fractional part\n       (?:E(?P<exp>[-+]?\\d+(_\\d+)*))?     # and optional exponent\n    )\n    \\s*\\Z                                 # and optional whitespace to finish\n', re.VERBOSE | re.IGNORECASE)

def _round_to_exponent(n, d, exponent, no_neg_zero = (False,)):
    '''Round a rational number to the nearest multiple of a given power of 10.

    Rounds the rational number n/d to the nearest integer multiple of
    10**exponent, rounding to the nearest even integer multiple in the case of
    a tie. Returns a pair (sign: bool, significand: int) representing the
    rounded value (-1)**sign * significand * 10**exponent.

    If no_neg_zero is true, then the returned sign will always be False when
    the significand is zero. Otherwise, the sign reflects the sign of the
    input.

    d must be positive, but n and d need not be relatively prime.
    '''
    if exponent >= 0:
        d *= 10 ** exponent
    else:
        n *= 10 ** (-exponent)
    (q, r) = divmod(n + (d >> 1), d)
    if r == 0 and d & 1 == 0:
        q &= -2
    sign = q < 0 if no_neg_zero else n < 0
    return (sign, abs(q))


def _round_to_figures(n, d, figures):
    '''Round a rational number to a given number of significant figures.

    Rounds the rational number n/d to the given number of significant figures
    using the round-ties-to-even rule, and returns a triple
    (sign: bool, significand: int, exponent: int) representing the rounded
    value (-1)**sign * significand * 10**exponent.

    In the special case where n = 0, returns a significand of zero and
    an exponent of 1 - figures, for compatibility with formatting.
    Otherwise, the returned significand satisfies
    10**(figures - 1) <= significand < 10**figures.

    d must be positive, but n and d need not be relatively prime.
    figures must be positive.
    '''
    if n == 0:
        return (False, 0, 1 - figures)
    str_d = str(d)
    str_n = None(abs(n))
    m = (len(str_n) - len(str_d)) + (str_d <= str_n)
    exponent = m - figures
    (sign, significand) = _round_to_exponent(n, d, exponent)
    if len(str(significand)) == figures + 1:
        significand //= 10
        exponent += 1
    return (sign, significand, exponent)

_FLOAT_FORMAT_SPECIFICATION_MATCHER = re.compile("\n    (?:\n        (?P<fill>.)?\n        (?P<align>[<>=^])\n    )?\n    (?P<sign>[-+ ]?)\n    (?P<no_neg_zero>z)?\n    (?P<alt>\\#)?\n    # A '0' that's *not* followed by another digit is parsed as a minimum width\n    # rather than a zeropad flag.\n    (?P<zeropad>0(?=[0-9]))?\n    (?P<minimumwidth>0|[1-9][0-9]*)?\n    (?P<thousands_sep>[,_])?\n    (?:\\.(?P<precision>0|[1-9][0-9]*))?\n    (?P<presentation_type>[eEfFgG%])\n", re.DOTALL | re.VERBOSE).fullmatch

class Fraction(numbers.Rational):
    pass
# WARNING: Decompyle incomplete

