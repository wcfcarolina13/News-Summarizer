# Source Generated with Decompyle++
# File: random.pyc (Python 3.12)

__doc__ = 'Random variable generators.\n\n    bytes\n    -----\n           uniform bytes (values between 0 and 255)\n\n    integers\n    --------\n           uniform within range\n\n    sequences\n    ---------\n           pick random element\n           pick random sample\n           pick weighted random sample\n           generate random permutation\n\n    distributions on the real line:\n    ------------------------------\n           uniform\n           triangular\n           normal (Gaussian)\n           lognormal\n           negative exponential\n           gamma\n           beta\n           pareto\n           Weibull\n\n    distributions on the circle (angles 0 to 2pi)\n    ---------------------------------------------\n           circular uniform\n           von Mises\n\n    discrete distributions\n    ----------------------\n           binomial\n\n\nGeneral notes on the underlying Mersenne Twister core generator:\n\n* The period is 2**19937-1.\n* It is one of the most extensively tested generators in existence.\n* The random() method is implemented in C, executes in a single Python step,\n  and is, therefore, threadsafe.\n\n'
from warnings import warn as _warn
from math import log as _log, exp as _exp, pi as _pi, e as _e, ceil as _ceil
from math import sqrt as _sqrt, acos as _acos, cos as _cos, sin as _sin
from math import tau as TWOPI, floor as _floor, isfinite as _isfinite
from math import lgamma as _lgamma, fabs as _fabs, log2 as _log2
from os import urandom as _urandom
from _collections_abc import Sequence as _Sequence
from operator import index as _index
from itertools import accumulate as _accumulate, repeat as _repeat
from bisect import bisect as _bisect
import os as _os
import _random
from _sha512 import sha512 as _sha512
__all__ = [
    'Random',
    'SystemRandom',
    'betavariate',
    'binomialvariate',
    'choice',
    'choices',
    'expovariate',
    'gammavariate',
    'gauss',
    'getrandbits',
    'getstate',
    'lognormvariate',
    'normalvariate',
    'paretovariate',
    'randbytes',
    'randint',
    'random',
    'randrange',
    'sample',
    'seed',
    'setstate',
    'shuffle',
    'triangular',
    'uniform',
    'vonmisesvariate',
    'weibullvariate']
NV_MAGICCONST = 4 * _exp(-0.5) / _sqrt(2)
LOG4 = _log(4)
SG_MAGICCONST = 1 + _log(4.5)
BPF = 53
RECIP_BPF = 2 ** (-BPF)
_ONE = 1

class Random(_random.Random):
    pass
# WARNING: Decompyle incomplete


class SystemRandom(Random):
    '''Alternate random number generator using sources provided
    by the operating system (such as /dev/urandom on Unix or
    CryptGenRandom on Windows).

     Not available on all systems (see os.urandom() for details).

    '''
    
    def random(self):
        '''Get the next random number in the range 0.0 <= X < 1.0.'''
        return (int.from_bytes(_urandom(7)) >> 3) * RECIP_BPF

    
    def getrandbits(self, k):
        '''getrandbits(k) -> x.  Generates an int with k random bits.'''
        if k < 0:
            raise ValueError('number of bits must be non-negative')
        numbytes = (k + 7) // 8
        x = int.from_bytes(_urandom(numbytes))
        return x >> numbytes * 8 - k

    
    def randbytes(self, n):
        '''Generate n random bytes.'''
        return _urandom(n)

    
    def seed(self, *args, **kwds):
        '''Stub method.  Not used for a system random number generator.'''
        pass

    
    def _notimplemented(self, *args, **kwds):
        '''Method should not be called for a system random number generator.'''
        raise NotImplementedError('System entropy source does not have state.')

    getstate = _notimplemented
    setstate = _notimplemented

_inst = Random()
seed = _inst.seed
random = _inst.random
uniform = _inst.uniform
triangular = _inst.triangular
randint = _inst.randint
choice = _inst.choice
randrange = _inst.randrange
sample = _inst.sample
shuffle = _inst.shuffle
choices = _inst.choices
normalvariate = _inst.normalvariate
lognormvariate = _inst.lognormvariate
expovariate = _inst.expovariate
vonmisesvariate = _inst.vonmisesvariate
gammavariate = _inst.gammavariate
gauss = _inst.gauss
betavariate = _inst.betavariate
binomialvariate = _inst.binomialvariate
paretovariate = _inst.paretovariate
weibullvariate = _inst.weibullvariate
getstate = _inst.getstate
setstate = _inst.setstate
getrandbits = _inst.getrandbits
randbytes = _inst.randbytes

def _test_generator(n, func, args):
    stdev = stdev
    mean = fmean
    import statistics
    perf_counter = perf_counter
    import time
    t0 = perf_counter()
# WARNING: Decompyle incomplete


def _test(N = (10000,)):
    _test_generator(N, random, ())
    _test_generator(N, normalvariate, (0, 1))
    _test_generator(N, lognormvariate, (0, 1))
    _test_generator(N, vonmisesvariate, (0, 1))
    _test_generator(N, binomialvariate, (15, 0.6))
    _test_generator(N, binomialvariate, (100, 0.75))
    _test_generator(N, gammavariate, (0.01, 1))
    _test_generator(N, gammavariate, (0.1, 1))
    _test_generator(N, gammavariate, (0.1, 2))
    _test_generator(N, gammavariate, (0.5, 1))
    _test_generator(N, gammavariate, (0.9, 1))
    _test_generator(N, gammavariate, (1, 1))
    _test_generator(N, gammavariate, (2, 1))
    _test_generator(N, gammavariate, (20, 1))
    _test_generator(N, gammavariate, (200, 1))
    _test_generator(N, gauss, (0, 1))
    _test_generator(N, betavariate, (3, 3))
    _test_generator(N, triangular, (0, 1, 0.333333))

if hasattr(_os, 'fork'):
    _os.register_at_fork(after_in_child = _inst.seed)
if __name__ == '__main__':
    _test()
    return None
return None
# WARNING: Decompyle incomplete
