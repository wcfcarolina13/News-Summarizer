# Source Generated with Decompyle++
# File: statistics.pyc (Python 3.12)

__doc__ = '\nBasic statistics module.\n\nThis module provides functions for calculating statistics of data, including\naverages, variance, and standard deviation.\n\nCalculating averages\n--------------------\n\n==================  ==================================================\nFunction            Description\n==================  ==================================================\nmean                Arithmetic mean (average) of data.\nfmean               Fast, floating point arithmetic mean.\ngeometric_mean      Geometric mean of data.\nharmonic_mean       Harmonic mean of data.\nmedian              Median (middle value) of data.\nmedian_low          Low median of data.\nmedian_high         High median of data.\nmedian_grouped      Median, or 50th percentile, of grouped data.\nmode                Mode (most common value) of data.\nmultimode           List of modes (most common values of data).\nquantiles           Divide data into intervals with equal probability.\n==================  ==================================================\n\nCalculate the arithmetic mean ("the average") of data:\n\n>>> mean([-1.0, 2.5, 3.25, 5.75])\n2.625\n\n\nCalculate the standard median of discrete data:\n\n>>> median([2, 3, 4, 5])\n3.5\n\n\nCalculate the median, or 50th percentile, of data grouped into class intervals\ncentred on the data values provided. E.g. if your data points are rounded to\nthe nearest whole number:\n\n>>> median_grouped([2, 2, 3, 3, 3, 4])  #doctest: +ELLIPSIS\n2.8333333333...\n\nThis should be interpreted in this way: you have two data points in the class\ninterval 1.5-2.5, three data points in the class interval 2.5-3.5, and one in\nthe class interval 3.5-4.5. The median of these data points is 2.8333...\n\n\nCalculating variability or spread\n---------------------------------\n\n==================  =============================================\nFunction            Description\n==================  =============================================\npvariance           Population variance of data.\nvariance            Sample variance of data.\npstdev              Population standard deviation of data.\nstdev               Sample standard deviation of data.\n==================  =============================================\n\nCalculate the standard deviation of sample data:\n\n>>> stdev([2.5, 3.25, 5.5, 11.25, 11.75])  #doctest: +ELLIPSIS\n4.38961843444...\n\nIf you have previously calculated the mean, you can pass it as the optional\nsecond argument to the four "spread" functions to avoid recalculating it:\n\n>>> data = [1, 2, 2, 4, 4, 4, 5, 6]\n>>> mu = mean(data)\n>>> pvariance(data, mu)\n2.5\n\n\nStatistics for relations between two inputs\n-------------------------------------------\n\n==================  ====================================================\nFunction            Description\n==================  ====================================================\ncovariance          Sample covariance for two variables.\ncorrelation         Pearson\'s correlation coefficient for two variables.\nlinear_regression   Intercept and slope for simple linear regression.\n==================  ====================================================\n\nCalculate covariance, Pearson\'s correlation, and simple linear regression\nfor two inputs:\n\n>>> x = [1, 2, 3, 4, 5, 6, 7, 8, 9]\n>>> y = [1, 2, 3, 1, 2, 3, 1, 2, 3]\n>>> covariance(x, y)\n0.75\n>>> correlation(x, y)  #doctest: +ELLIPSIS\n0.31622776601...\n>>> linear_regression(x, y)  #doctest:\nLinearRegression(slope=0.1, intercept=1.5)\n\n\nExceptions\n----------\n\nA single exception is defined: StatisticsError is a subclass of ValueError.\n\n'
__all__ = [
    'NormalDist',
    'StatisticsError',
    'correlation',
    'covariance',
    'fmean',
    'geometric_mean',
    'harmonic_mean',
    'linear_regression',
    'mean',
    'median',
    'median_grouped',
    'median_high',
    'median_low',
    'mode',
    'multimode',
    'pstdev',
    'pvariance',
    'quantiles',
    'stdev',
    'variance']
import math
import numbers
import random
import sys
from fractions import Fraction
from decimal import Decimal
from itertools import count, groupby, repeat
from bisect import bisect_left, bisect_right
from math import hypot, sqrt, fabs, exp, erf, tau, log, fsum, sumprod
from functools import reduce
from operator import itemgetter
from collections import Counter, namedtuple, defaultdict
_SQRT2 = sqrt(2)

class StatisticsError(ValueError):
    pass


def _sum(data):
    '''_sum(data) -> (type, sum, count)

    Return a high-precision sum of the given numeric data as a fraction,
    together with the type to be converted to and the count of items.

    Examples
    --------

    >>> _sum([3, 2.25, 4.5, -0.5, 0.25])
    (<class \'float\'>, Fraction(19, 2), 5)

    Some sources of round-off error will be avoided:

    # Built-in sum returns zero.
    >>> _sum([1e50, 1, -1e50] * 1000)
    (<class \'float\'>, Fraction(1000, 1), 3000)

    Fractions and Decimals are also supported:

    >>> from fractions import Fraction as F
    >>> _sum([F(2, 3), F(7, 5), F(1, 4), F(5, 6)])
    (<class \'fractions.Fraction\'>, Fraction(63, 20), 4)

    >>> from decimal import Decimal as D
    >>> data = [D("0.1375"), D("0.2108"), D("0.3061"), D("0.0419")]
    >>> _sum(data)
    (<class \'decimal.Decimal\'>, Fraction(6963, 10000), 4)

    Mixed types are currently treated as an error, except that int is
    allowed.
    '''
    count = 0
    types = set()
    types_add = types.add
    partials = { }
    partials_get = partials.get
    for typ, values in groupby(data, type):
        types_add(typ)
        for n, d in map(_exact_ratio, values):
            count += 1
            partials[d] = partials_get(d, 0) + n
# WARNING: Decompyle incomplete


def _ss(data, c = (None,)):
    '''Return the exact mean and sum of square deviations of sequence data.

    Calculations are done in a single pass, allowing the input to be an iterator.

    If given *c* is used the mean; otherwise, it is calculated from the data.
    Use the *c* argument with care, as it can lead to garbage results.

    '''
    pass
# WARNING: Decompyle incomplete


def _isfinite(x):
    return x.is_finite()
# WARNING: Decompyle incomplete


def _coerce(T, S):
    '''Coerce types T and S to a common type, or raise TypeError.

    Coercion rules are currently an implementation detail. See the CoerceTest
    test class in test_statistics for details.
    '''
    pass
# WARNING: Decompyle incomplete


def _exact_ratio(x):
    '''Return Real number x to exact (numerator, denominator) pair.

    >>> _exact_ratio(0.25)
    (1, 4)

    x is expected to be an int, Fraction, Decimal or float.
    '''
    return x.as_integer_ratio()
# WARNING: Decompyle incomplete


def _convert(value, T):
    '''Convert value to given numeric type T.'''
    if type(value) is T:
        return value
    if None(T, int) and value.denominator != 1:
        T = float
    return T(value)
# WARNING: Decompyle incomplete


def _fail_neg(values, errmsg = ('negative value',)):
    '''Iterate over values, failing if any are less than zero.'''
    pass
# WARNING: Decompyle incomplete


def _rank(data = None, *, key, reverse, ties, start):
    """Rank order a dataset. The lowest value has rank 1.

    Ties are averaged so that equal values receive the same rank:

        >>> data = [31, 56, 31, 25, 75, 18]
        >>> _rank(data)
        [3.5, 5.0, 3.5, 2.0, 6.0, 1.0]

    The operation is idempotent:

        >>> _rank([3.5, 5.0, 3.5, 2.0, 6.0, 1.0])
        [3.5, 5.0, 3.5, 2.0, 6.0, 1.0]

    It is possible to rank the data in reverse order so that the
    highest value has rank 1.  Also, a key-function can extract
    the field to be ranked:

        >>> goals = [('eagles', 45), ('bears', 48), ('lions', 44)]
        >>> _rank(goals, key=itemgetter(1), reverse=True)
        [2.0, 1.0, 3.0]

    Ranks are conventionally numbered starting from one; however,
    setting *start* to zero allows the ranks to be used as array indices:

        >>> prize = ['Gold', 'Silver', 'Bronze', 'Certificate']
        >>> scores = [8.1, 7.3, 9.4, 8.3]
        >>> [prize[int(i)] for i in _rank(scores, start=0, reverse=True)]
        ['Bronze', 'Certificate', 'Gold', 'Silver']

    """
    if ties != 'average':
        raise ValueError(f'''Unknown tie resolution method: {ties!r}''')
# WARNING: Decompyle incomplete


def _integer_sqrt_of_frac_rto(n = None, m = None):
    '''Square root of n/m, rounded to the nearest integer using round-to-odd.'''
    a = math.isqrt(n // m)
    return a | (a * a * m != n)

_sqrt_bit_width: int = 2 * sys.float_info.mant_dig + 3

def _float_sqrt_of_frac(n = None, m = None):
    '''Square root of n/m as a float, correctly rounded.'''
    q = (n.bit_length() - m.bit_length() - _sqrt_bit_width) // 2
    if q >= 0:
        numerator = _integer_sqrt_of_frac_rto(n, m << 2 * q) << q
        denominator = 1
        return numerator / denominator
    numerator = None(n << -2 * q, m)
    denominator = 1 << -q
    return numerator / denominator


def _decimal_sqrt_of_frac(n = None, m = None):
    '''Square root of n/m as a Decimal, correctly rounded.'''
    if n <= 0:
        if not n:
            return Decimal('0.0')
        m = -m
        n = -None
    root = (Decimal(n) / Decimal(m)).sqrt()
    (nr, dr) = root.as_integer_ratio()
    plus = root.next_plus()
    (np, dp) = plus.as_integer_ratio()
    if 4 * n * (dr * dp) ** 2 > m * (dr * np + dp * nr) ** 2:
        return plus
    minus = None.next_minus()
    (nm, dm) = minus.as_integer_ratio()
    if 4 * n * (dr * dm) ** 2 < m * (dr * nm + dm * nr) ** 2:
        return minus


def mean(data):
    '''Return the sample arithmetic mean of data.

    >>> mean([1, 2, 3, 4, 4])
    2.8

    >>> from fractions import Fraction as F
    >>> mean([F(3, 7), F(1, 21), F(5, 3), F(1, 3)])
    Fraction(13, 21)

    >>> from decimal import Decimal as D
    >>> mean([D("0.5"), D("0.75"), D("0.625"), D("0.375")])
    Decimal(\'0.5625\')

    If ``data`` is empty, StatisticsError will be raised.
    '''
    (T, total, n) = _sum(data)
    if n < 1:
        raise StatisticsError('mean requires at least one data point')
    return _convert(total / n, T)


def fmean(data, weights = (None,)):
    '''Convert data to floats and compute the arithmetic mean.

    This runs faster than the mean() function and it always returns a float.
    If the input dataset is empty, it raises a StatisticsError.

    >>> fmean([3.5, 4.0, 5.25])
    4.25
    '''
    pass
# WARNING: Decompyle incomplete


def geometric_mean(data):
    '''Convert data to floats and compute the geometric mean.

    Raises a StatisticsError if the input dataset is empty,
    if it contains a zero, or if it contains a negative value.

    No special efforts are made to achieve exact results.
    (However, this may change in the future.)

    >>> round(geometric_mean([54, 24, 36]), 9)
    36.0
    '''
    return exp(fmean(map(log, data)))
# WARNING: Decompyle incomplete


def harmonic_mean(data, weights = (None,)):
    '''Return the harmonic mean of data.

    The harmonic mean is the reciprocal of the arithmetic mean of the
    reciprocals of the data.  It can be used for averaging ratios or
    rates, for example speeds.

    Suppose a car travels 40 km/hr for 5 km and then speeds-up to
    60 km/hr for another 5 km. What is the average speed?

        >>> harmonic_mean([40, 60])
        48.0

    Suppose a car travels 40 km/hr for 5 km, and when traffic clears,
    speeds-up to 60 km/hr for the remaining 30 km of the journey. What
    is the average speed?

        >>> harmonic_mean([40, 60], weights=[5, 30])
        56.0

    If ``data`` is empty, or any element is less than zero,
    ``harmonic_mean`` will raise ``StatisticsError``.
    '''
    if iter(data) is data:
        data = list(data)
    errmsg = 'harmonic mean does not support negative values'
    n = len(data)
    if n < 1:
        raise StatisticsError('harmonic_mean requires at least one data point')
# WARNING: Decompyle incomplete


def median(data):
    '''Return the median (middle value) of numeric data.

    When the number of data points is odd, return the middle data point.
    When the number of data points is even, the median is interpolated by
    taking the average of the two middle values:

    >>> median([1, 3, 5])
    3
    >>> median([1, 3, 5, 7])
    4.0

    '''
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError('no median for empty data')
    if n % 2 == 1:
        return data[n // 2]
    i = None // 2
    return (data[i - 1] + data[i]) / 2


def median_low(data):
    '''Return the low median of numeric data.

    When the number of data points is odd, the middle value is returned.
    When it is even, the smaller of the two middle values is returned.

    >>> median_low([1, 3, 5])
    3
    >>> median_low([1, 3, 5, 7])
    3

    '''
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError('no median for empty data')
    if n % 2 == 1:
        return data[n // 2]
    return None[n // 2 - 1]


def median_high(data):
    '''Return the high median of data.

    When the number of data points is odd, the middle value is returned.
    When it is even, the larger of the two middle values is returned.

    >>> median_high([1, 3, 5])
    3
    >>> median_high([1, 3, 5, 7])
    5

    '''
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError('no median for empty data')
    return data[n // 2]


def median_grouped(data, interval = (1,)):
    '''Estimates the median for numeric data binned around the midpoints
    of consecutive, fixed-width intervals.

    The *data* can be any iterable of numeric data with each value being
    exactly the midpoint of a bin.  At least one value must be present.

    The *interval* is width of each bin.

    For example, demographic information may have been summarized into
    consecutive ten-year age groups with each group being represented
    by the 5-year midpoints of the intervals:

        >>> demographics = Counter({
        ...    25: 172,   # 20 to 30 years old
        ...    35: 484,   # 30 to 40 years old
        ...    45: 387,   # 40 to 50 years old
        ...    55:  22,   # 50 to 60 years old
        ...    65:   6,   # 60 to 70 years old
        ... })

    The 50th percentile (median) is the 536th person out of the 1071
    member cohort.  That person is in the 30 to 40 year old age group.

    The regular median() function would assume that everyone in the
    tricenarian age group was exactly 35 years old.  A more tenable
    assumption is that the 484 members of that age group are evenly
    distributed between 30 and 40.  For that, we use median_grouped().

        >>> data = list(demographics.elements())
        >>> median(data)
        35
        >>> round(median_grouped(data, interval=10), 1)
        37.5

    The caller is responsible for making sure the data points are separated
    by exact multiples of *interval*.  This is essential for getting a
    correct result.  The function does not check this precondition.

    Inputs may be any numeric type that can be coerced to a float during
    the interpolation step.

    '''
    data = sorted(data)
    n = len(data)
    if not n:
        raise StatisticsError('no median for empty data')
    x = data[n // 2]
    i = bisect_left(data, x)
    j = bisect_right(data, x, lo = i)
    interval = float(interval)
    x = float(x)
    L = x - interval / 2
    cf = i
    f = j - i
    return L + interval * (n / 2 - cf) / f
# WARNING: Decompyle incomplete


def mode(data):
    '''Return the most common data point from discrete or nominal data.

    ``mode`` assumes discrete data, and returns a single value. This is the
    standard treatment of the mode as commonly taught in schools:

        >>> mode([1, 1, 2, 3, 3, 3, 3, 4])
        3

    This also works with nominal (non-numeric) data:

        >>> mode(["red", "blue", "blue", "red", "green", "red", "red"])
        \'red\'

    If there are multiple modes with same frequency, return the first one
    encountered:

        >>> mode([\'red\', \'red\', \'green\', \'blue\', \'blue\'])
        \'red\'

    If *data* is empty, ``mode``, raises StatisticsError.

    '''
    pairs = Counter(iter(data)).most_common(1)
    return pairs[0][0]
# WARNING: Decompyle incomplete


def multimode(data):
    """Return a list of the most frequently occurring values.

    Will return more than one result if there are multiple modes
    or an empty list if *data* is empty.

    >>> multimode('aabbbbbbbbcc')
    ['b']
    >>> multimode('aabbbbccddddeeffffgg')
    ['b', 'd', 'f']
    >>> multimode('')
    []
    """
    counts = Counter(iter(data))
    if not counts:
        return []
    maxcount = None(counts.values())
# WARNING: Decompyle incomplete


def quantiles(data = None, *, n, method):
    '''Divide *data* into *n* continuous intervals with equal probability.

    Returns a list of (n - 1) cut points separating the intervals.

    Set *n* to 4 for quartiles (the default).  Set *n* to 10 for deciles.
    Set *n* to 100 for percentiles which gives the 99 cuts points that
    separate *data* in to 100 equal sized groups.

    The *data* can be any iterable containing sample.
    The cut points are linearly interpolated between data points.

    If *method* is set to *inclusive*, *data* is treated as population
    data.  The minimum value is treated as the 0th percentile and the
    maximum value is treated as the 100th percentile.
    '''
    if n < 1:
        raise StatisticsError('n must be at least 1')
    data = sorted(data)
    ld = len(data)
    if ld < 2:
        raise StatisticsError('must have at least two data points')
    if method == 'inclusive':
        m = ld - 1
        result = []
        for i in range(1, n):
            (j, delta) = divmod(i * m, n)
            interpolated = (data[j] * (n - delta) + data[j + 1] * delta) / n
            result.append(interpolated)
        return result
    if None == 'exclusive':
        m = ld + 1
        result = []
        for i in range(1, n):
            j = i * m // n
            if j < 1:
                pass
            elif j > ld - 1:
                pass
            
            j = j
            delta = i * m - j * n
            interpolated = (data[j - 1] * (n - delta) + data[j] * delta) / n
            result.append(interpolated)
        return result
    raise None(f'''Unknown method: {method!r}''')


def variance(data, xbar = (None,)):
    '''Return the sample variance of data.

    data should be an iterable of Real-valued numbers, with at least two
    values. The optional argument xbar, if given, should be the mean of
    the data. If it is missing or None, the mean is automatically calculated.

    Use this function when your data is a sample from a population. To
    calculate the variance from the entire population, see ``pvariance``.

    Examples:

    >>> data = [2.75, 1.75, 1.25, 0.25, 0.5, 1.25, 3.5]
    >>> variance(data)
    1.3720238095238095

    If you have already calculated the mean of your data, you can pass it as
    the optional second argument ``xbar`` to avoid recalculating it:

    >>> m = mean(data)
    >>> variance(data, m)
    1.3720238095238095

    This function does not check that ``xbar`` is actually the mean of
    ``data``. Giving arbitrary values for ``xbar`` may lead to invalid or
    impossible results.

    Decimals and Fractions are supported:

    >>> from decimal import Decimal as D
    >>> variance([D("27.5"), D("30.25"), D("30.25"), D("34.5"), D("41.75")])
    Decimal(\'31.01875\')

    >>> from fractions import Fraction as F
    >>> variance([F(1, 6), F(1, 2), F(5, 3)])
    Fraction(67, 108)

    '''
    (T, ss, c, n) = _ss(data, xbar)
    if n < 2:
        raise StatisticsError('variance requires at least two data points')
    return _convert(ss / (n - 1), T)


def pvariance(data, mu = (None,)):
    '''Return the population variance of ``data``.

    data should be a sequence or iterable of Real-valued numbers, with at least one
    value. The optional argument mu, if given, should be the mean of
    the data. If it is missing or None, the mean is automatically calculated.

    Use this function to calculate the variance from the entire population.
    To estimate the variance from a sample, the ``variance`` function is
    usually a better choice.

    Examples:

    >>> data = [0.0, 0.25, 0.25, 1.25, 1.5, 1.75, 2.75, 3.25]
    >>> pvariance(data)
    1.25

    If you have already calculated the mean of the data, you can pass it as
    the optional second argument to avoid recalculating it:

    >>> mu = mean(data)
    >>> pvariance(data, mu)
    1.25

    Decimals and Fractions are supported:

    >>> from decimal import Decimal as D
    >>> pvariance([D("27.5"), D("30.25"), D("30.25"), D("34.5"), D("41.75")])
    Decimal(\'24.815\')

    >>> from fractions import Fraction as F
    >>> pvariance([F(1, 4), F(5, 4), F(1, 2)])
    Fraction(13, 72)

    '''
    (T, ss, c, n) = _ss(data, mu)
    if n < 1:
        raise StatisticsError('pvariance requires at least one data point')
    return _convert(ss / n, T)


def stdev(data, xbar = (None,)):
    '''Return the square root of the sample variance.

    See ``variance`` for arguments and other details.

    >>> stdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    1.0810874155219827

    '''
    (T, ss, c, n) = _ss(data, xbar)
    if n < 2:
        raise StatisticsError('stdev requires at least two data points')
    mss = ss / (n - 1)
    if issubclass(T, Decimal):
        return _decimal_sqrt_of_frac(mss.numerator, mss.denominator)
    return None(mss.numerator, mss.denominator)


def pstdev(data, mu = (None,)):
    '''Return the square root of the population variance.

    See ``pvariance`` for arguments and other details.

    >>> pstdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
    0.986893273527251

    '''
    (T, ss, c, n) = _ss(data, mu)
    if n < 1:
        raise StatisticsError('pstdev requires at least one data point')
    mss = ss / n
    if issubclass(T, Decimal):
        return _decimal_sqrt_of_frac(mss.numerator, mss.denominator)
    return None(mss.numerator, mss.denominator)


def _mean_stdev(data):
    '''In one pass, compute the mean and sample standard deviation as floats.'''
    (T, ss, xbar, n) = _ss(data)
    if n < 2:
        raise StatisticsError('stdev requires at least two data points')
    mss = ss / (n - 1)
    return (float(xbar), _float_sqrt_of_frac(mss.numerator, mss.denominator))
# WARNING: Decompyle incomplete


def covariance(x, y):
    '''Covariance

    Return the sample covariance of two inputs *x* and *y*. Covariance
    is a measure of the joint variability of two inputs.

    >>> x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    >>> y = [1, 2, 3, 1, 2, 3, 1, 2, 3]
    >>> covariance(x, y)
    0.75
    >>> z = [9, 8, 7, 6, 5, 4, 3, 2, 1]
    >>> covariance(x, z)
    -7.5
    >>> covariance(z, x)
    -7.5

    '''
    pass
# WARNING: Decompyle incomplete


def correlation(x = None, y = {
    'method': 'linear' }, *, method):
    '''Pearson\'s correlation coefficient

    Return the Pearson\'s correlation coefficient for two inputs. Pearson\'s
    correlation coefficient *r* takes values between -1 and +1. It measures
    the strength and direction of a linear relationship.

    >>> x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    >>> y = [9, 8, 7, 6, 5, 4, 3, 2, 1]
    >>> correlation(x, x)
    1.0
    >>> correlation(x, y)
    -1.0

    If *method* is "ranked", computes Spearman\'s rank correlation coefficient
    for two inputs.  The data is replaced by ranks.  Ties are averaged
    so that equal values receive the same rank.  The resulting coefficient
    measures the strength of a monotonic relationship.

    Spearman\'s rank correlation coefficient is appropriate for ordinal
    data or for continuous data that doesn\'t meet the linear proportion
    requirement for Pearson\'s correlation coefficient.
    '''
    n = len(x)
    if len(y) != n:
        raise StatisticsError('correlation requires that both inputs have same number of data points')
    if n < 2:
        raise StatisticsError('correlation requires at least two data points')
    if method not in frozenset({'linear', 'ranked'}):
        raise ValueError(f'''Unknown method: {method!r}''')
    if method == 'ranked':
        start = (n - 1) / -2
        x = _rank(x, start = start)
        y = _rank(y, start = start)
# WARNING: Decompyle incomplete

LinearRegression = namedtuple('LinearRegression', ('slope', 'intercept'))

def linear_regression(x = None, y = {
    'proportional': False }, *, proportional):
    '''Slope and intercept for simple linear regression.

    Return the slope and intercept of simple linear regression
    parameters estimated using ordinary least squares. Simple linear
    regression describes relationship between an independent variable
    *x* and a dependent variable *y* in terms of a linear function:

        y = slope * x + intercept + noise

    where *slope* and *intercept* are the regression parameters that are
    estimated, and noise represents the variability of the data that was
    not explained by the linear regression (it is equal to the
    difference between predicted and actual values of the dependent
    variable).

    The parameters are returned as a named tuple.

    >>> x = [1, 2, 3, 4, 5]
    >>> noise = NormalDist().samples(5, seed=42)
    >>> y = [3 * x[i] + 2 + noise[i] for i in range(5)]
    >>> linear_regression(x, y)  #doctest: +ELLIPSIS
    LinearRegression(slope=3.09078914170..., intercept=1.75684970486...)

    If *proportional* is true, the independent variable *x* and the
    dependent variable *y* are assumed to be directly proportional.
    The data is fit to a line passing through the origin.

    Since the *intercept* will always be 0.0, the underlying linear
    function simplifies to:

        y = slope * x + noise

    >>> y = [3 * x[i] + noise[i] for i in range(5)]
    >>> linear_regression(x, y, proportional=True)  #doctest: +ELLIPSIS
    LinearRegression(slope=3.02447542484..., intercept=0.0)

    '''
    pass
# WARNING: Decompyle incomplete


def _normal_dist_inv_cdf(p, mu, sigma):
    q = p - 0.5
    if fabs(q) <= 0.425:
        r = 0.180625 - q * q
        num = (((((((2509.08 * r + 33430.6) * r + 67265.8) * r + 45922) * r + 13731.7) * r + 1971.59) * r + 133.142) * r + 3.38713) * q
        den = ((((((5226.5 * r + 28729.1) * r + 39307.9) * r + 21213.8) * r + 5394.2) * r + 687.187) * r + 42.3133) * r + 1
        x = num / den
        return mu + x * sigma
    r = p if None <= 0 else 1 - p
    r = sqrt(-log(r))
    if r <= 5:
        r = r - 1.6
        num = ((((((0.000774545 * r + 0.0227238) * r + 0.241781) * r + 1.27046) * r + 3.64785) * r + 5.7695) * r + 4.63034) * r + 1.42344
        den = ((((((1.05075e-09 * r + 0.000547594) * r + 0.0151987) * r + 0.148104) * r + 0.689767) * r + 1.67638) * r + 2.05319) * r + 1
    else:
        r = r - 5
        num = ((((((2.01033e-07 * r + 2.71156e-05) * r + 0.00124266) * r + 0.0265322) * r + 0.296561) * r + 1.78483) * r + 5.46378) * r + 6.6579
        den = ((((((2.04426e-15 * r + 1.42151e-07) * r + 1.84632e-05) * r + 0.000786869) * r + 0.0148754) * r + 0.13693) * r + 0.599832) * r + 1
    x = num / den
    if q < 0:
        x = -x
    return mu + x * sigma

from _statistics import _normal_dist_inv_cdf

class NormalDist:
    '''Normal distribution of a random variable'''
    __slots__ = {
        '_mu': 'Arithmetic mean of a normal distribution',
        '_sigma': 'Standard deviation of a normal distribution' }
    
    def __init__(self, mu, sigma = (0, 1)):
        '''NormalDist where mu is the mean and sigma is the standard deviation.'''
        if sigma < 0:
            raise StatisticsError('sigma must be non-negative')
        self._mu = float(mu)
        self._sigma = float(sigma)

    from_samples = (lambda cls, data: pass# WARNING: Decompyle incomplete
)()
    
    def samples(self = classmethod, n = {
        'seed': None }, *, seed):
        '''Generate *n* samples for a given mean and standard deviation.'''
        pass
    # WARNING: Decompyle incomplete

    
    def pdf(self, x):
        '''Probability density function.  P(x <= X < x+dx) / dx'''
        variance = self._sigma * self._sigma
        if not variance:
            raise StatisticsError('pdf() not defined when sigma is zero')
        diff = x - self._mu
        return exp(diff * diff / (-2 * variance)) / sqrt(tau * variance)

    
    def cdf(self, x):
        '''Cumulative distribution function.  P(X <= x)'''
        if not self._sigma:
            raise StatisticsError('cdf() not defined when sigma is zero')
        return 0.5 * (1 + erf((x - self._mu) / (self._sigma * _SQRT2)))

    
    def inv_cdf(self, p):
        '''Inverse cumulative distribution function.  x : P(X <= x) = p

        Finds the value of the random variable such that the probability of
        the variable being less than or equal to that value equals the given
        probability.

        This function is also called the percent point function or quantile
        function.
        '''
        if p <= 0 or p >= 1:
            raise StatisticsError('p must be in the range 0.0 < p < 1.0')
        return _normal_dist_inv_cdf(p, self._mu, self._sigma)

    
    def quantiles(self, n = (4,)):
        '''Divide into *n* continuous intervals with equal probability.

        Returns a list of (n - 1) cut points separating the intervals.

        Set *n* to 4 for quartiles (the default).  Set *n* to 10 for deciles.
        Set *n* to 100 for percentiles which gives the 99 cuts points that
        separate the normal distribution in to 100 equal sized groups.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def overlap(self, other):
        '''Compute the overlapping coefficient (OVL) between two normal distributions.

        Measures the agreement between two normal probability distributions.
        Returns a value between 0.0 and 1.0 giving the overlapping area in
        the two underlying probability density functions.

            >>> N1 = NormalDist(2.4, 1.6)
            >>> N2 = NormalDist(3.2, 2.0)
            >>> N1.overlap(N2)
            0.8035050657330205
        '''
        if not isinstance(other, NormalDist):
            raise TypeError('Expected another NormalDist instance')
        Y = other
        X = self
        if (Y._sigma, Y._mu) < (X._sigma, X._mu):
            Y = X
            X = Y
        Y_var = Y.variance
        X_var = X.variance
        if not X_var or Y_var:
            raise StatisticsError('overlap() not defined when sigma is zero')
        dv = Y_var - X_var
        dm = fabs(Y._mu - X._mu)
        if not dv:
            return 1 - erf(dm / (2 * X._sigma * _SQRT2))
        a = None._mu * Y_var - Y._mu * X_var
        b = X._sigma * Y._sigma * sqrt(dm * dm + dv * log(Y_var / X_var))
        x1 = (a + b) / dv
        x2 = (a - b) / dv
        return 1 - (fabs(Y.cdf(x1) - X.cdf(x1)) + fabs(Y.cdf(x2) - X.cdf(x2)))

    
    def zscore(self, x):
        '''Compute the Standard Score.  (x - mean) / stdev

        Describes *x* in terms of the number of standard deviations
        above or below the mean of the normal distribution.
        '''
        if not self._sigma:
            raise StatisticsError('zscore() not defined when sigma is zero')
        return (x - self._mu) / self._sigma

    mean = (lambda self: self._mu)()
    median = (lambda self: self._mu)()
    mode = (lambda self: self._mu)()
    stdev = (lambda self: self._sigma)()
    variance = (lambda self: self._sigma * self._sigma)()
    
    def __add__(x1, x2):
        '''Add a constant or another NormalDist instance.

        If *other* is a constant, translate mu by the constant,
        leaving sigma unchanged.

        If *other* is a NormalDist, add both the means and the variances.
        Mathematically, this works only if the two distributions are
        independent or if they are jointly normally distributed.
        '''
        if isinstance(x2, NormalDist):
            return NormalDist(x1._mu + x2._mu, hypot(x1._sigma, x2._sigma))
        return None(x1._mu + x2, x1._sigma)

    
    def __sub__(x1, x2):
        '''Subtract a constant or another NormalDist instance.

        If *other* is a constant, translate by the constant mu,
        leaving sigma unchanged.

        If *other* is a NormalDist, subtract the means and add the variances.
        Mathematically, this works only if the two distributions are
        independent or if they are jointly normally distributed.
        '''
        if isinstance(x2, NormalDist):
            return NormalDist(x1._mu - x2._mu, hypot(x1._sigma, x2._sigma))
        return None(x1._mu - x2, x1._sigma)

    
    def __mul__(x1, x2):
        '''Multiply both mu and sigma by a constant.

        Used for rescaling, perhaps to change measurement units.
        Sigma is scaled with the absolute value of the constant.
        '''
        return NormalDist(x1._mu * x2, x1._sigma * fabs(x2))

    
    def __truediv__(x1, x2):
        '''Divide both mu and sigma by a constant.

        Used for rescaling, perhaps to change measurement units.
        Sigma is scaled with the absolute value of the constant.
        '''
        return NormalDist(x1._mu / x2, x1._sigma / fabs(x2))

    
    def __pos__(x1):
        '''Return a copy of the instance.'''
        return NormalDist(x1._mu, x1._sigma)

    
    def __neg__(x1):
        '''Negates mu while keeping sigma the same.'''
        return NormalDist(-(x1._mu), x1._sigma)

    __radd__ = __add__
    
    def __rsub__(x1, x2):
        '''Subtract a NormalDist from a constant or another NormalDist.'''
        return -(x1 - x2)

    __rmul__ = __mul__
    
    def __eq__(x1, x2):
        '''Two NormalDist objects are equal if their mu and sigma are both equal.'''
        if not isinstance(x2, NormalDist):
            return NotImplemented
        if None._mu == x2._mu:
            None._mu == x2._mu
        return x1._sigma == x2._sigma

    
    def __hash__(self):
        '''NormalDist objects hash equal if their mu and sigma are both equal.'''
        return hash((self._mu, self._sigma))

    
    def __repr__(self):
        return f'''{type(self).__name__}(mu={self._mu!r}, sigma={self._sigma!r})'''

    
    def __getstate__(self):
        return (self._mu, self._sigma)

    
    def __setstate__(self, state):
        (self._mu, self._sigma) = state


return None
# WARNING: Decompyle incomplete
