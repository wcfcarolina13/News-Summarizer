# Source Generated with Decompyle++
# File: getpass.pyc (Python 3.12)

__doc__ = 'Utilities to get a password and/or the current user name.\n\ngetpass(prompt[, stream]) - Prompt for a password, with echo turned off.\ngetuser() - Get the user name from the environment or password database.\n\nGetPassWarning - This UserWarning is issued when getpass() cannot prevent\n                 echoing of the password contents while reading.\n\nOn Windows, the msvcrt module will be used.\n\n'
import contextlib
import io
import os
import sys
import warnings
__all__ = [
    'getpass',
    'getuser',
    'GetPassWarning']

class GetPassWarning(UserWarning):
    pass


def unix_getpass(prompt, stream = ('Password: ', None)):
    """Prompt for a password, with echo turned off.

    Args:
      prompt: Written on stream to ask for the input.  Default: 'Password: '
      stream: A writable file object to display the prompt.  Defaults to
              the tty.  If no tty is available defaults to sys.stderr.
    Returns:
      The seKr3t input.
    Raises:
      EOFError: If our input tty or stdin was closed.
      GetPassWarning: When we were unable to turn echo off on the input.

    Always restores terminal settings before returning.
    """
    passwd = None
# WARNING: Decompyle incomplete


def win_getpass(prompt, stream = ('Password: ', None)):
    '''Prompt for password with echo off, using Windows getwch().'''
    if sys.stdin is not sys.__stdin__:
        return fallback_getpass(prompt, stream)
    for c in None:
        msvcrt.putwch(c)
    pw = ''
    c = msvcrt.getwch()
    if c == '\r' or c == '\n':
        pass
    elif c == '\x03':
        raise KeyboardInterrupt
    if c == '\x08':
        pw = pw[:-1]
    else:
        pw = pw + c
    continue
    msvcrt.putwch('\r')
    msvcrt.putwch('\n')
    return pw


def fallback_getpass(prompt, stream = ('Password: ', None)):
    warnings.warn('Can not control echo on the terminal.', GetPassWarning, stacklevel = 2)
    if not stream:
        stream = sys.stderr
    print('Warning: Password input may be echoed.', file = stream)
    return _raw_input(prompt, stream)


def _raw_input(prompt, stream, input = ('', None, None)):
    if not stream:
        stream = sys.stderr
    if not input:
        input = sys.stdin
    prompt = str(prompt)
    if prompt:
        stream.write(prompt)
        stream.flush()
    line = input.readline()
    if not line:
        raise EOFError
    if line[-1] == '\n':
        line = line[:-1]
    return line
# WARNING: Decompyle incomplete


def getuser():
    '''Get the username from the environment or password database.

    First try various environment variables, then the password
    database.  This works on Windows as long as USERNAME is set.

    '''
    for name in ('LOGNAME', 'USER', 'LNAME', 'USERNAME'):
        user = os.environ.get(name)
        if not user:
            continue
        
        return ('LOGNAME', 'USER', 'LNAME', 'USERNAME'), user
    return pwd.getpwuid(os.getuid())[0]

import termios
(termios.tcgetattr, termios.tcsetattr)
getpass = unix_getpass
return None
# WARNING: Decompyle incomplete
