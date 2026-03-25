# Source Generated with Decompyle++
# File: subprocess.pyc (Python 3.12)

__doc__ = 'Subprocesses with accessible I/O streams\n\nThis module allows you to spawn processes, connect to their\ninput/output/error pipes, and obtain their return codes.\n\nFor a complete description of this module see the Python documentation.\n\nMain API\n========\nrun(...): Runs a command, waits for it to complete, then returns a\n          CompletedProcess instance.\nPopen(...): A class for flexibly executing a command in a new process\n\nConstants\n---------\nDEVNULL: Special value that indicates that os.devnull should be used\nPIPE:    Special value that indicates a pipe should be created\nSTDOUT:  Special value that indicates that stderr should go to stdout\n\n\nOlder API\n=========\ncall(...): Runs a command, waits for it to complete, then returns\n    the return code.\ncheck_call(...): Same as call() but raises CalledProcessError()\n    if return code is not 0\ncheck_output(...): Same as check_call() but returns the contents of\n    stdout instead of a return code\ngetoutput(...): Runs a command in the shell, waits for it to complete,\n    then returns the output\ngetstatusoutput(...): Runs a command in the shell, waits for it to complete,\n    then returns a (exitcode, output) tuple\n'
import builtins
import errno
import io
import locale
import os
import time
import signal
import sys
import threading
import warnings
import contextlib
from time import monotonic as _time
import types
import fcntl
__all__ = [
    'Popen',
    'PIPE',
    'STDOUT',
    'call',
    'check_call',
    'getstatusoutput',
    'getoutput',
    'check_output',
    'run',
    'CalledProcessError',
    'DEVNULL',
    'SubprocessError',
    'TimeoutExpired',
    'CompletedProcess']
import msvcrt
_mswindows = True
_can_fork_exec = sys.platform not in frozenset({'wasi', 'emscripten'})
if _mswindows:
    import _winapi
    from _winapi import CREATE_NEW_CONSOLE, CREATE_NEW_PROCESS_GROUP, STD_INPUT_HANDLE, STD_OUTPUT_HANDLE, STD_ERROR_HANDLE, SW_HIDE, STARTF_USESTDHANDLES, STARTF_USESHOWWINDOW, ABOVE_NORMAL_PRIORITY_CLASS, BELOW_NORMAL_PRIORITY_CLASS, HIGH_PRIORITY_CLASS, IDLE_PRIORITY_CLASS, NORMAL_PRIORITY_CLASS, REALTIME_PRIORITY_CLASS, CREATE_NO_WINDOW, DETACHED_PROCESS, CREATE_DEFAULT_ERROR_MODE, CREATE_BREAKAWAY_FROM_JOB
    __all__.extend([
        'CREATE_NEW_CONSOLE',
        'CREATE_NEW_PROCESS_GROUP',
        'STD_INPUT_HANDLE',
        'STD_OUTPUT_HANDLE',
        'STD_ERROR_HANDLE',
        'SW_HIDE',
        'STARTF_USESTDHANDLES',
        'STARTF_USESHOWWINDOW',
        'STARTUPINFO',
        'ABOVE_NORMAL_PRIORITY_CLASS',
        'BELOW_NORMAL_PRIORITY_CLASS',
        'HIGH_PRIORITY_CLASS',
        'IDLE_PRIORITY_CLASS',
        'NORMAL_PRIORITY_CLASS',
        'REALTIME_PRIORITY_CLASS',
        'CREATE_NO_WINDOW',
        'DETACHED_PROCESS',
        'CREATE_DEFAULT_ERROR_MODE',
        'CREATE_BREAKAWAY_FROM_JOB'])
elif _can_fork_exec:
    from _posixsubprocess import fork_exec as _fork_exec
    _waitpid = os.waitpid
    _waitstatus_to_exitcode = os.waitstatus_to_exitcode
    _WIFSTOPPED = os.WIFSTOPPED
    _WSTOPSIG = os.WSTOPSIG
    _WNOHANG = os.WNOHANG
else:
    _fork_exec = None
    _waitpid = None
    _waitstatus_to_exitcode = None
    _WIFSTOPPED = None
    _WSTOPSIG = None
    _WNOHANG = None
import select
import selectors

class SubprocessError(Exception):
    pass


class CalledProcessError(SubprocessError):
    '''Raised when run() is called with check=True and the process
    returns a non-zero exit status.

    Attributes:
      cmd, returncode, stdout, stderr, output
    '''
    
    def __init__(self, returncode, cmd, output, stderr = (None, None)):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
        self.stderr = stderr

    
    def __str__(self):
        if self.returncode and self.returncode < 0:
            return f'''Command \'{self.cmd!s}\' died with {signal.Signals(-(self.returncode))!r}.'''
        return None % (self.cmd, self.returncode)
    # WARNING: Decompyle incomplete

    stdout = (lambda self: self.output)()
    stdout = (lambda self, value: self.output = value)()


class TimeoutExpired(SubprocessError):
    '''This exception is raised when the timeout expires while waiting for a
    child process.

    Attributes:
        cmd, output, stdout, stderr, timeout
    '''
    
    def __init__(self, cmd, timeout, output, stderr = (None, None)):
        self.cmd = cmd
        self.timeout = timeout
        self.output = output
        self.stderr = stderr

    
    def __str__(self):
        return f'''Command \'{self.cmd!s}\' timed out after {self.timeout!s} seconds'''

    stdout = (lambda self: self.output)()
    stdout = (lambda self, value: self.output = value)()

PIPE = -1
STDOUT = -2
DEVNULL = -3

def _optim_args_from_interpreter_flags():
    '''Return a list of command-line arguments reproducing the current
    optimization settings in sys.flags.'''
    args = []
    value = sys.flags.optimize
    if value > 0:
        args.append('-' + 'O' * value)
    return args


def _args_from_interpreter_flags():
    '''Return a list of command-line arguments reproducing the current
    settings in sys.flags, sys.warnoptions and sys._xoptions.'''
    flag_opt_map = {
        'debug': 'd',
        'dont_write_bytecode': 'B',
        'no_site': 'S',
        'verbose': 'v',
        'bytes_warning': 'b',
        'quiet': 'q' }
    args = _optim_args_from_interpreter_flags()
    for flag, opt in flag_opt_map.items():
        v = getattr(sys.flags, flag)
        if not v > 0:
            continue
        args.append('-' + opt * v)
    if sys.flags.isolated:
        args.append('-I')
    elif sys.flags.ignore_environment:
        args.append('-E')
    if sys.flags.no_user_site:
        args.append('-s')
    if sys.flags.safe_path:
        args.append('-P')
    warnopts = sys.warnoptions[:]
    xoptions = getattr(sys, '_xoptions', { })
    bytes_warning = sys.flags.bytes_warning
    dev_mode = sys.flags.dev_mode
    if bytes_warning > 1:
        warnopts.remove('error::BytesWarning')
    elif bytes_warning:
        warnopts.remove('default::BytesWarning')
    if dev_mode:
        warnopts.remove('default')
    for opt in warnopts:
        args.append('-W' + opt)
    if dev_mode:
        args.extend(('-X', 'dev'))
    for opt in ('faulthandler', 'tracemalloc', 'importtime', 'frozen_modules', 'showrefcount', 'utf8'):
        if not opt in xoptions:
            continue
        value = xoptions[opt]
        args.extend(('-X', arg))
    return args


def _text_encoding():
    if sys.flags.warn_default_encoding:
        f = sys._getframe()
        filename = f.f_code.co_filename
        stacklevel = 2
        f = f.f_back
        if f.f_back:
            if f.f_code.co_filename != filename:
                pass
            else:
                stacklevel += 1
                f = f.f_back
                if f.f_back:
                    continue
        warnings.warn("'encoding' argument not specified.", EncodingWarning, stacklevel)
    if sys.flags.utf8_mode:
        return 'utf-8'
    return locale.getencoding()


def call(*, timeout, *popenargs, **kwargs):
    '''Run command with arguments.  Wait for command to complete or
    timeout, then return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    retcode = call(["ls", "-l"])
    '''
    pass
# WARNING: Decompyle incomplete


def check_call(*popenargs, **kwargs):
    '''Run command with arguments.  Wait for command to complete.  If
    the exit code was zero then return, otherwise raise
    CalledProcessError.  The CalledProcessError object will have the
    return code in the returncode attribute.

    The arguments are the same as for the call function.  Example:

    check_call(["ls", "-l"])
    '''
    pass
# WARNING: Decompyle incomplete


def check_output(*, timeout, *popenargs, **kwargs):
    '''Run command with arguments and return its output.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    >>> check_output(["ls", "-l", "/dev/null"])
    b\'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\\n\'

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.

    >>> check_output(["/bin/sh", "-c",
    ...               "ls -l non_existent_file ; exit 0"],
    ...              stderr=STDOUT)
    b\'ls: non_existent_file: No such file or directory\\n\'

    There is an additional optional argument, "input", allowing you to
    pass a string to the subprocess\'s stdin.  If you use this argument
    you may not also use the Popen constructor\'s "stdin" argument, as
    it too will be used internally.  Example:

    >>> check_output(["sed", "-e", "s/foo/bar/"],
    ...              input=b"when in the course of fooman events\\n")
    b\'when in the course of barman events\\n\'

    By default, all communication is in bytes, and therefore any "input"
    should be bytes, and the return value will be bytes.  If in text mode,
    any "input" should be a string, and the return value will be a string
    decoded according to locale encoding, or by "encoding" if set. Text mode
    is triggered by setting any of text, encoding, errors or universal_newlines.
    '''
    for kw in ('stdout', 'check'):
        if not kw in kwargs:
            continue
        raise ValueError(f'''{kw} argument not allowed, it will be overridden.''')
# WARNING: Decompyle incomplete


class CompletedProcess(object):
    '''A process that has finished running.

    This is returned by run().

    Attributes:
      args: The list or str args passed to run().
      returncode: The exit code of the process, negative for signals.
      stdout: The standard output (None if not captured).
      stderr: The standard error (None if not captured).
    '''
    
    def __init__(self, args, returncode, stdout, stderr = (None, None)):
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    
    def __repr__(self):
        args = [
            'args={!r}'.format(self.args),
            'returncode={!r}'.format(self.returncode)]
    # WARNING: Decompyle incomplete

    __class_getitem__ = classmethod(types.GenericAlias)
    
    def check_returncode(self):
        '''Raise CalledProcessError if the exit code is non-zero.'''
        if self.returncode:
            raise CalledProcessError(self.returncode, self.args, self.stdout, self.stderr)



def run(*, input, capture_output, timeout, check, *popenargs, **kwargs):
    '''Run command with arguments and return a CompletedProcess instance.

    The returned instance will have attributes args, returncode, stdout and
    stderr. By default, stdout and stderr are not captured, and those attributes
    will be None. Pass stdout=PIPE and/or stderr=PIPE in order to capture them,
    or pass capture_output=True to capture both.

    If check is True and the exit code was non-zero, it raises a
    CalledProcessError. The CalledProcessError object will have the return code
    in the returncode attribute, and output & stderr attributes if those streams
    were captured.

    If timeout is given, and the process takes too long, a TimeoutExpired
    exception will be raised.

    There is an optional argument "input", allowing you to
    pass bytes or a string to the subprocess\'s stdin.  If you use this argument
    you may not also use the Popen constructor\'s "stdin" argument, as
    it will be used internally.

    By default, all communication is in bytes, and therefore any "input" should
    be bytes, and the stdout and stderr will be bytes. If in text mode, any
    "input" should be a string, and stdout and stderr will be strings decoded
    according to locale encoding, or by "encoding" if set. Text mode is
    triggered by setting any of text, encoding, errors or universal_newlines.

    The other arguments are the same as for the Popen constructor.
    '''
    pass
# WARNING: Decompyle incomplete


def list2cmdline(seq):
    '''
    Translate a sequence of arguments into a command line
    string, using the same rules as the MS C runtime:

    1) Arguments are delimited by white space, which is either a
       space or a tab.

    2) A string surrounded by double quotation marks is
       interpreted as a single argument, regardless of white space
       contained within.  A quoted string can be embedded in an
       argument.

    3) A double quotation mark preceded by a backslash is
       interpreted as a literal double quotation mark.

    4) Backslashes are interpreted literally, unless they
       immediately precede a double quotation mark.

    5) If backslashes immediately precede a double quotation mark,
       every pair of backslashes is interpreted as a literal
       backslash.  If the number of backslashes is odd, the last
       backslash escapes the next double quotation mark as
       described in rule 3.
    '''
    result = []
    needquote = False
    for arg in map(os.fsdecode, seq):
        bs_buf = []
        if result:
            result.append(' ')
        if not ' ' in arg:
            ' ' in arg
            if not '\t' in arg:
                '\t' in arg
        needquote = not arg
        if needquote:
            result.append('"')
        for c in arg:
            if c == '\\':
                bs_buf.append(c)
                continue
            if c == '"':
                result.append('\\' * len(bs_buf) * 2)
                bs_buf = []
                result.append('\\"')
                continue
            if bs_buf:
                result.extend(bs_buf)
                bs_buf = []
            result.append(c)
        if bs_buf:
            result.extend(bs_buf)
        if not needquote:
            continue
        result.extend(bs_buf)
        result.append('"')
    return ''.join(result)


def getstatusoutput(cmd = None, *, encoding, errors):
    """Return (exitcode, output) of executing cmd in a shell.

    Execute the string 'cmd' in a shell with 'check_output' and
    return a 2-tuple (status, output). The locale encoding is used
    to decode the output and process newlines.

    A trailing newline is stripped from the output.
    The exit status for the command can be interpreted
    according to the rules for the function 'wait'. Example:

    >>> import subprocess
    >>> subprocess.getstatusoutput('ls /bin/ls')
    (0, '/bin/ls')
    >>> subprocess.getstatusoutput('cat /bin/junk')
    (1, 'cat: /bin/junk: No such file or directory')
    >>> subprocess.getstatusoutput('/bin/junk')
    (127, 'sh: /bin/junk: not found')
    >>> subprocess.getstatusoutput('/bin/kill $$')
    (-15, '')
    """
    data = check_output(cmd, shell = True, text = True, stderr = STDOUT, encoding = encoding, errors = errors)
    exitcode = 0
    if data[-1:] == '\n':
        data = data[:-1]
    return (exitcode, data)
# WARNING: Decompyle incomplete


def getoutput(cmd = None, *, encoding, errors):
    """Return output (stdout or stderr) of executing cmd in a shell.

    Like getstatusoutput(), except the exit status is ignored and the return
    value is a string containing the command's output.  Example:

    >>> import subprocess
    >>> subprocess.getoutput('ls /bin/ls')
    '/bin/ls'
    """
    return getstatusoutput(cmd, encoding = encoding, errors = errors)[1]


def _use_posix_spawn():
    '''Check if posix_spawn() can be used for subprocess.

    subprocess requires a posix_spawn() implementation that properly reports
    errors to the parent process, & sets errno on the following failures:

    * Process attribute actions failed.
    * File actions failed.
    * exec() failed.

    Prefer an implementation which can use vfork() in some cases for best
    performance.
    '''
    if not _mswindows or hasattr(os, 'posix_spawn'):
        return False
    if sys.platform in ('darwin', 'sunos5'):
        return True
    ver = os.confstr('CS_GNU_LIBC_VERSION')
    parts = ver.split(maxsplit = 1)
    if len(parts) != 2:
        raise ValueError
    libc = parts[0]
    version = tuple(map(int, parts[1].split('.')))
    if sys.platform == 'linux' and libc == 'glibc' and version >= (2, 24):
        return True
    return False
# WARNING: Decompyle incomplete

_USE_POSIX_SPAWN = _use_posix_spawn()
_USE_VFORK = True

class Popen:
    """ Execute a child program in a new process.

    For a complete description of the arguments see the Python documentation.

    Arguments:
      args: A string, or a sequence of program arguments.

      bufsize: supplied as the buffering argument to the open() function when
          creating the stdin/stdout/stderr pipe file objects

      executable: A replacement program to execute.

      stdin, stdout and stderr: These specify the executed programs' standard
          input, standard output and standard error file handles, respectively.

      preexec_fn: (POSIX only) An object to be called in the child process
          just before the child is executed.

      close_fds: Controls closing or inheriting of file descriptors.

      shell: If true, the command will be executed through the shell.

      cwd: Sets the current directory before the child is executed.

      env: Defines the environment variables for the new process.

      text: If true, decode stdin, stdout and stderr using the given encoding
          (if set) or the system default otherwise.

      universal_newlines: Alias of text, provided for backwards compatibility.

      startupinfo and creationflags (Windows only)

      restore_signals (POSIX only)

      start_new_session (POSIX only)

      process_group (POSIX only)

      group (POSIX only)

      extra_groups (POSIX only)

      user (POSIX only)

      umask (POSIX only)

      pass_fds (POSIX only)

      encoding and errors: Text mode encoding and error handling to use for
          file objects stdin, stdout and stderr.

    Attributes:
        stdin, stdout, stderr, pid, returncode
    """
    _child_created = False
    
    def __init__(self, args, bufsize, executable, stdin, stdout, stderr, preexec_fn, close_fds, shell, cwd, env, universal_newlines, startupinfo, creationflags, restore_signals = None, start_new_session = (-1, None, None, None, None, None, True, False, None, None, None, None, 0, True, False, ()), pass_fds = {
        'user': None,
        'group': None,
        'extra_groups': None,
        'encoding': None,
        'errors': None,
        'text': None,
        'umask': -1,
        'pipesize': -1,
        'process_group': None }, *, user, group, extra_groups, encoding, errors, text, umask, pipesize, process_group):
        '''Create new Popen instance.'''
        if not _can_fork_exec:
            raise OSError(errno.ENOTSUP, f'''{sys.platform} does not support processes.''')
        _cleanup()
        self._waitpid_lock = threading.Lock()
        self._input = None
        self._communication_started = False
    # WARNING: Decompyle incomplete

    
    def __repr__(self):
        obj_repr = f'''<{self.__class__.__name__}: returncode: {self.returncode} args: {self.args!r}>'''
        if len(obj_repr) > 80:
            obj_repr = obj_repr[:76] + '...>'
        return obj_repr

    __class_getitem__ = classmethod(types.GenericAlias)
    universal_newlines = (lambda self: self.text_mode)()
    universal_newlines = (lambda self, universal_newlines: self.text_mode = bool(universal_newlines))()
    
    def _translate_newlines(self, data, encoding, errors):
        data = data.decode(encoding, errors)
        return data.replace('\r\n', '\n').replace('\r', '\n')

    
    def __enter__(self):
        return self

    
    def __exit__(self, exc_type, value, traceback):
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()
        if self.stdin:
            self.stdin.close()
        if exc_type == KeyboardInterrupt:
            if self._sigint_wait_secs > 0:
                self._wait(timeout = self._sigint_wait_secs)
                self._sigint_wait_secs = 0
                return None
            self._sigint_wait_secs = 0
            return None
        self.wait()
        return None
    # WARNING: Decompyle incomplete

    
    def __del__(self, _maxsize, _warn = (sys.maxsize, warnings.warn)):
        if not self._child_created:
            return None
    # WARNING: Decompyle incomplete

    
    def _get_devnull(self):
        if not hasattr(self, '_devnull'):
            self._devnull = os.open(os.devnull, os.O_RDWR)
        return self._devnull

    
    def _stdin_write(self, input):
        if input:
            self.stdin.write(input)
        self.stdin.close()
        return None
    # WARNING: Decompyle incomplete

    
    def communicate(self, input, timeout = (None, None)):
        '''Interact with process: Send data to stdin and close it.
        Read data from stdout and stderr, until end-of-file is
        reached.  Wait for process to terminate.

        The optional "input" argument should be data to be sent to the
        child process, or None, if no data should be sent to the child.
        communicate() returns a tuple (stdout, stderr).

        By default, all communication is in bytes, and therefore any
        "input" should be bytes, and the (stdout, stderr) will be bytes.
        If in text mode (indicated by self.text_mode), any "input" should
        be a string, and (stdout, stderr) will be strings decoded
        according to locale encoding, or by "encoding" if set. Text mode
        is triggered by setting any of text, encoding, errors or
        universal_newlines.
        '''
        if self._communication_started and input:
            raise ValueError('Cannot send input after starting communication')
    # WARNING: Decompyle incomplete

    
    def poll(self):
        '''Check if child process has terminated. Set and return returncode
        attribute.'''
        return self._internal_poll()

    
    def _remaining_time(self, endtime):
        '''Convenience for _communicate when computing timeouts.'''
        pass
    # WARNING: Decompyle incomplete

    
    def _check_timeout(self, endtime, orig_timeout, stdout_seq, stderr_seq, skip_check_and_raise = (False,)):
        '''Convenience for checking if a timeout has expired.'''
        pass
    # WARNING: Decompyle incomplete

    
    def wait(self, timeout = (None,)):
        '''Wait for child process to terminate; returns self.returncode.'''
        pass
    # WARNING: Decompyle incomplete

    
    def _close_pipe_fds(self, p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite):
        devnull_fd = getattr(self, '_devnull', None)
    # WARNING: Decompyle incomplete

    _on_error_fd_closer = (lambda self: pass# WARNING: Decompyle incomplete
)()
    if _mswindows:
        
        def _get_handles(self, stdin, stdout, stderr):
            '''Construct and return tuple with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            '''
            pass
        # WARNING: Decompyle incomplete

        
        def _make_inheritable(self, handle):
            '''Return a duplicate of handle, which is inheritable'''
            h = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), handle, _winapi.GetCurrentProcess(), 0, 1, _winapi.DUPLICATE_SAME_ACCESS)
            return Handle(h)

        
        def _filter_handle_list(self, handle_list):
            '''Filter out console handles that can\'t be used
            in lpAttributeList["handle_list"] and make sure the list
            isn\'t empty. This also removes duplicate handles.'''
            pass
        # WARNING: Decompyle incomplete

        
        def _execute_child(self, args, executable, preexec_fn, close_fds, pass_fds, cwd, env, startupinfo, creationflags, shell, p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite, unused_restore_signals, unused_gid, unused_gids, unused_uid, unused_umask, unused_start_new_session, unused_process_group):
            '''Execute program (MS Windows version)'''
            pass
        # WARNING: Decompyle incomplete

        
        def _internal_poll(self, _deadstate, _WaitForSingleObject, _WAIT_OBJECT_0, _GetExitCodeProcess = (None, _winapi.WaitForSingleObject, _winapi.WAIT_OBJECT_0, _winapi.GetExitCodeProcess)):
            '''Check if child process has terminated.  Returns returncode
            attribute.

            This method is called by __del__, so it can only refer to objects
            in its local scope.

            '''
            pass
        # WARNING: Decompyle incomplete

        
        def _wait(self, timeout):
            '''Internal implementation of wait() on Windows.'''
            pass
        # WARNING: Decompyle incomplete

        
        def _readerthread(self, fh, buffer):
            buffer.append(fh.read())
            fh.close()

        
        def _communicate(self, input, endtime, orig_timeout):
            if not self.stdout and hasattr(self, '_stdout_buff'):
                self._stdout_buff = []
                self.stdout_thread = threading.Thread(target = self._readerthread, args = (self.stdout, self._stdout_buff))
                self.stdout_thread.daemon = True
                self.stdout_thread.start()
            if not self.stderr and hasattr(self, '_stderr_buff'):
                self._stderr_buff = []
                self.stderr_thread = threading.Thread(target = self._readerthread, args = (self.stderr, self._stderr_buff))
                self.stderr_thread.daemon = True
                self.stderr_thread.start()
            if self.stdin:
                self._stdin_write(input)
        # WARNING: Decompyle incomplete

        
        def send_signal(self, sig):
            '''Send a signal to the process.'''
            pass
        # WARNING: Decompyle incomplete

        
        def terminate(self):
            '''Terminates the process.'''
            pass
        # WARNING: Decompyle incomplete

        kill = terminate
        return None
    
    def _get_handles(self, stdin, stdout, stderr):
        '''Construct and return tuple with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            '''
        (p2cread, p2cwrite) = (-1, -1)
        (c2pread, c2pwrite) = (-1, -1)
        (errread, errwrite) = (-1, -1)
    # WARNING: Decompyle incomplete

    
    def _posix_spawn(self, args, executable, env, restore_signals, p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite):
        '''Execute program using os.posix_spawn().'''
        pass
    # WARNING: Decompyle incomplete

    
    def _execute_child(self, args, executable, preexec_fn, close_fds, pass_fds, cwd, env, startupinfo, creationflags, shell, p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite, restore_signals, gid, gids, uid, umask, start_new_session, process_group):
        '''Execute program (POSIX version)'''
        pass
    # WARNING: Decompyle incomplete

    
    def _handle_exitstatus(self, sts, _waitstatus_to_exitcode, _WIFSTOPPED, _WSTOPSIG = (_waitstatus_to_exitcode, _WIFSTOPPED, _WSTOPSIG)):
        '''All callers to this function MUST hold self._waitpid_lock.'''
        if _WIFSTOPPED(sts):
            self.returncode = -_WSTOPSIG(sts)
            return None
        self.returncode = _waitstatus_to_exitcode(sts)

    
    def _internal_poll(self, _deadstate, _waitpid, _WNOHANG, _ECHILD = (None, _waitpid, _WNOHANG, errno.ECHILD)):
        '''Check if child process has terminated.  Returns returncode
            attribute.

            This method is called by __del__, so it cannot reference anything
            outside of the local scope (nor can any methods it calls).

            '''
        pass
    # WARNING: Decompyle incomplete

    
    def _try_wait(self, wait_flags):
        '''All callers to this function MUST hold self._waitpid_lock.'''
        (pid, sts) = os.waitpid(self.pid, wait_flags)
        return (pid, sts)
    # WARNING: Decompyle incomplete

    
    def _wait(self, timeout):
        '''Internal implementation of wait() on POSIX.'''
        pass
    # WARNING: Decompyle incomplete

    
    def _communicate(self, input, endtime, orig_timeout):
        if not self.stdin and self._communication_started:
            self.stdin.flush()
            if not input:
                self.stdin.close()
        stdout = None
        stderr = None
        if not self._communication_started:
            self._fileobj2output = { }
            if self.stdout:
                self._fileobj2output[self.stdout] = []
            if self.stderr:
                self._fileobj2output[self.stderr] = []
        if self.stdout:
            stdout = self._fileobj2output[self.stdout]
        if self.stderr:
            stderr = self._fileobj2output[self.stderr]
        self._save_input(input)
        if self._input:
            input_view = memoryview(self._input)
    # WARNING: Decompyle incomplete

    
    def _save_input(self, input):
        pass
    # WARNING: Decompyle incomplete

    
    def send_signal(self, sig):
        '''Send a signal to the process.'''
        self.poll()
    # WARNING: Decompyle incomplete

    
    def terminate(self):
        '''Terminate the process with SIGTERM
            '''
        self.send_signal(signal.SIGTERM)

    
    def kill(self):
        '''Kill the process with SIGKILL
            '''
        self.send_signal(signal.SIGKILL)


return None
# WARNING: Decompyle incomplete
