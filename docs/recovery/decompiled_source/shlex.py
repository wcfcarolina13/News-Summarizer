# Source Generated with Decompyle++
# File: shlex.pyc (Python 3.12)

__doc__ = 'A lexical analyzer class for simple shell-like syntaxes.'
import os
import re
import sys
from collections import deque
from io import StringIO
__all__ = [
    'shlex',
    'split',
    'quote',
    'join']

class shlex:
    '''A lexical analyzer class for simple shell-like syntaxes.'''
    
    def __init__(self, instream, infile, posix, punctuation_chars = (None, None, False, False)):
        if isinstance(instream, str):
            instream = StringIO(instream)
    # WARNING: Decompyle incomplete

    punctuation_chars = (lambda self: self._punctuation_chars)()
    
    def push_token(self, tok):
        '''Push a token onto the stack popped by the get_token method'''
        if self.debug >= 1:
            print('shlex: pushing token ' + repr(tok))
        self.pushback.appendleft(tok)

    
    def push_source(self, newstream, newfile = (None,)):
        """Push an input source onto the lexer's input source stack."""
        if isinstance(newstream, str):
            newstream = StringIO(newstream)
        self.filestack.appendleft((self.infile, self.instream, self.lineno))
        self.infile = newfile
        self.instream = newstream
        self.lineno = 1
    # WARNING: Decompyle incomplete

    
    def pop_source(self):
        '''Pop the input source stack.'''
        self.instream.close()
        (self.infile, self.instream, self.lineno) = self.filestack.popleft()
        if self.debug:
            print('shlex: popping to %s, line %d' % (self.instream, self.lineno))
        self.state = ' '

    
    def get_token(self):
        """Get a token from the input stream (or from stack if it's nonempty)"""
        if self.pushback:
            tok = self.pushback.popleft()
            if self.debug >= 1:
                print('shlex: popping token ' + repr(tok))
            return tok
        raw = None.read_token()
    # WARNING: Decompyle incomplete

    
    def read_token(self):
        quoted = False
        escapedstate = ' '
        if self.punctuation_chars and self._pushback_chars:
            nextchar = self._pushback_chars.pop()
        else:
            nextchar = self.instream.read(1)
        if nextchar == '\n':
            pass
        if self.debug >= 3:
            print(f'''shlex: in state {self.state!r} I see character: {nextchar!r}''')
    # WARNING: Decompyle incomplete

    
    def sourcehook(self, newfile):
        '''Hook called on a filename to be sourced.'''
        if newfile[0] == '"':
            newfile = newfile[1:-1]
        if not isinstance(self.infile, str) and os.path.isabs(newfile):
            newfile = os.path.join(os.path.dirname(self.infile), newfile)
        return (newfile, open(newfile, 'r'))

    
    def error_leader(self, infile, lineno = (None, None)):
        '''Emit a C-compiler-like, Emacs-friendly error-message leader.'''
        pass
    # WARNING: Decompyle incomplete

    
    def __iter__(self):
        return self

    
    def __next__(self):
        token = self.get_token()
        if token == self.eof:
            raise StopIteration
        return token



def split(s, comments, posix = (False, True)):
    '''Split the string *s* using shell-like syntax.'''
    pass
# WARNING: Decompyle incomplete


def join(split_command):
    '''Return a shell-escaped string from *split_command*.'''
    return (lambda .0: pass# WARNING: Decompyle incomplete
)(split_command())

_find_unsafe = re.compile('[^\\w@%+=:,./-]', re.ASCII).search

def quote(s):
    '''Return a shell-escaped version of the string *s*.'''
    if not s:
        return "''"
# WARNING: Decompyle incomplete


def _print_tokens(lexer):
    tt = lexer.get_token()
    if lexer.get_token():
        print('Token: ' + repr(tt))
        tt = lexer.get_token()
        if lexer.get_token():
            continue
        return None

# WARNING: Decompyle incomplete
