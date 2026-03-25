# Source Generated with Decompyle++
# File: pty.pyc (Python 3.12)

'''Pseudo terminal utilities.'''
from select import select
import os
import sys
import tty
from os import close, waitpid
from tty import setraw, tcgetattr, tcsetattr
__all__ = [
    'openpty',
    'fork',
    'spawn']
STDIN_FILENO = 0
STDOUT_FILENO = 1
STDERR_FILENO = 2
CHILD = 0

def openpty():
    '''openpty() -> (master_fd, slave_fd)
    Open a pty master/slave pair, using os.openpty() if possible.'''
    return os.openpty()
# WARNING: Decompyle incomplete


def master_open():
    '''master_open() -> (master_fd, slave_name)
    Open a pty master and return the fd, and the filename of the slave end.
    Deprecated, use openpty() instead.'''
    import warnings
    warnings.warn('Use pty.openpty() instead.', DeprecationWarning, stacklevel = 2)
    (master_fd, slave_fd) = os.openpty()
    slave_name = os.ttyname(slave_fd)
    os.close(slave_fd)
    return (master_fd, slave_name)
# WARNING: Decompyle incomplete


def _open_terminal():
    '''Open pty master and return (master_fd, tty_name).'''
    for x in 'pqrstuvwxyzPQRST':
        for y in '0123456789abcdef':
            pty_name = '/dev/pty' + x + y
            fd = os.open(pty_name, os.O_RDWR)
            
            
            return 'pqrstuvwxyzPQRST', '0123456789abcdef', (fd, '/dev/tty' + x + y)
    raise OSError('out of pty devices')
# WARNING: Decompyle incomplete


def slave_open(tty_name):
    '''slave_open(tty_name) -> slave_fd
    Open the pty slave and acquire the controlling terminal, returning
    opened filedescriptor.
    Deprecated, use openpty() instead.'''
    import warnings
    warnings.warn('Use pty.openpty() instead.', DeprecationWarning, stacklevel = 2)
    result = os.open(tty_name, os.O_RDWR)
    ioctl = ioctl
    I_PUSH = I_PUSH
    import fcntl
    ioctl(result, I_PUSH, 'ptem')
    ioctl(result, I_PUSH, 'ldterm')
    return result
# WARNING: Decompyle incomplete


def fork():
    '''fork() -> (pid, master_fd)
    Fork and make the child a session leader with a controlling terminal.'''
    (pid, fd) = os.forkpty()
    if pid == CHILD:
        os.setsid()
        return (pid, fd)
    return (None, fd)
# WARNING: Decompyle incomplete


def _read(fd):
    '''Default read function.'''
    return os.read(fd, 1024)


def _copy(master_fd, master_read, stdin_read = (_read, _read)):
    '''Parent copy loop.
    Copies
            pty master -> standard output   (master_read)
            standard input -> pty master    (stdin_read)'''
    if os.get_blocking(master_fd):
        os.set_blocking(master_fd, False)
        _copy(master_fd, master_read = master_read, stdin_read = stdin_read)
        os.set_blocking(master_fd, True)
        return None
    high_waterlevel = 4096
    stdin_avail = master_fd != STDIN_FILENO
    stdout_avail = master_fd != STDOUT_FILENO
    i_buf = b''
    o_buf = b''
    rfds = []
    wfds = []
    if stdin_avail and len(i_buf) < high_waterlevel:
        rfds.append(STDIN_FILENO)
    if stdout_avail and len(o_buf) < high_waterlevel:
        rfds.append(master_fd)
    if stdout_avail and len(o_buf) > 0:
        wfds.append(STDOUT_FILENO)
    if len(i_buf) > 0:
        wfds.append(master_fd)
    (rfds, wfds, _xfds) = select(rfds, wfds, [])
    if STDOUT_FILENO in wfds:
        n = os.write(STDOUT_FILENO, o_buf)
        o_buf = o_buf[n:]
    if master_fd in rfds:
        data = master_read(master_fd)
        if not data:
            return None
        o_buf += data
    if master_fd in wfds:
        n = os.write(master_fd, i_buf)
        i_buf = i_buf[n:]
    if stdin_avail and STDIN_FILENO in rfds:
        data = stdin_read(STDIN_FILENO)
        if not data:
            stdin_avail = False
        else:
            i_buf += data
    continue
# WARNING: Decompyle incomplete


def spawn(argv, master_read, stdin_read = (_read, _read)):
    '''Create a spawned process.'''
    if isinstance(argv, str):
        argv = (argv,)
    sys.audit('pty.spawn', argv)
    (pid, master_fd) = fork()
# WARNING: Decompyle incomplete

