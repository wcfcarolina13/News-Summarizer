# Source Generated with Decompyle++
# File: rlcompleter.pyc (Python 3.12)

__doc__ = 'Word completion for GNU readline.\n\nThe completer completes keywords, built-ins and globals in a selectable\nnamespace (which defaults to __main__); when completing NAME.NAME..., it\nevaluates (!) the expression up to the last dot and completes its attributes.\n\nIt\'s very cool to do "import sys" type "sys.", hit the completion key (twice),\nand see the list of names defined by the sys module!\n\nTip: to use the tab key as the completion key, call\n\n    readline.parse_and_bind("tab: complete")\n\nNotes:\n\n- Exceptions raised by the completer function are *ignored* (and generally cause\n  the completion to fail).  This is a feature -- since readline sets the tty\n  device in raw (or cbreak) mode, printing a traceback wouldn\'t work well\n  without some complicated hoopla to save, reset and restore the tty state.\n\n- The evaluation of the NAME.NAME... form may cause arbitrary application\n  defined code to be executed if an object with a __getattr__ hook is found.\n  Since it is the responsibility of the application (or the user) to enable this\n  feature, I consider this an acceptable risk.  More complicated expressions\n  (e.g. function calls or indexing operations) are *not* evaluated.\n\n- When the original stdin is not a tty device, GNU readline is never\n  used, and this module (and the readline module) are silently inactive.\n\n'
import atexit
import builtins
import inspect
import keyword
import re
import __main__
__all__ = [
    'Completer']

class Completer:
    
    def __init__(self, namespace = (None,)):
        '''Create a new completer for the command line.

        Completer([namespace]) -> completer instance.

        If unspecified, the default namespace where completions are performed
        is __main__ (technically, __main__.__dict__). Namespaces should be
        given as dictionaries.

        Completer instances should be used as the completion mechanism of
        readline via the set_completer() call:

        readline.set_completer(Completer(my_namespace).complete)
        '''
        if not namespace and isinstance(namespace, dict):
            raise TypeError('namespace must be a dictionary')
    # WARNING: Decompyle incomplete

    
    def complete(self, text, state):
        """Return the next possible completion for 'text'.

        This is called successively with state == 0, 1, 2, ... until it
        returns None.  The completion should begin with 'text'.

        """
        if self.use_main_ns:
            self.namespace = __main__.__dict__
        if not text.strip():
            if state == 0:
                if _readline_available:
                    readline.insert_text('\t')
                    readline.redisplay()
                    return ''
                return '\t'
            return None
        if state == 0:
            if '.' in text:
                self.matches = self.attr_matches(text)
            else:
                self.matches = self.global_matches(text)
        return self.matches[state]
    # WARNING: Decompyle incomplete

    
    def _callable_postfix(self, val, word):
        if callable(val):
            word += '('
            if not inspect.signature(val).parameters:
                word += ')'
            return word
        return None
    # WARNING: Decompyle incomplete

    
    def global_matches(self, text):
        '''Compute matches when text is a simple name.

        Return a list of all keywords, built-in functions and names currently
        defined in self.namespace that match.

        '''
        matches = []
        seen = {
            '__builtins__'}
        n = len(text)
        for word in keyword.kwlist + keyword.softkwlist:
            if not word[:n] == text:
                continue
            seen.add(word)
            if word in frozenset({'try', 'finally'}):
                word = word + ':'
            elif word not in frozenset({'_', 'None', 'True', 'else', 'pass', 'False', 'break', 'continue'}):
                word = word + ' '
            matches.append(word)
        for nspace in (self.namespace, builtins.__dict__):
            for word, val in nspace.items():
                if not word[:n] == text:
                    continue
                if not word not in seen:
                    continue
                seen.add(word)
                matches.append(self._callable_postfix(val, word))
        return matches

    
    def attr_matches(self, text):
        '''Compute matches when text contains a dot.

        Assuming the text is of the form NAME.NAME....[NAME], and is
        evaluable in self.namespace, it will be evaluated and its attributes
        (as revealed by dir()) are used as possible completions.  (For class
        instances, class members are also considered.)

        WARNING: this can still invoke arbitrary C code, if an object
        with a __getattr__ hook is evaluated.

        '''
        m = re.match('(\\w+(\\.\\w+)*)\\.(\\w*)', text)
        if not m:
            return []
        (expr, attr) = None.group(1, 3)
        thisobject = eval(expr, self.namespace)
        words = set(dir(thisobject))
        words.discard('__builtins__')
        if hasattr(thisobject, '__class__'):
            words.add('__class__')
            words.update(get_class_members(thisobject.__class__))
        matches = []
        n = len(attr)
        if attr == '':
            noprefix = '_'
        elif attr == '_':
            noprefix = '__'
        else:
            noprefix = None
    # WARNING: Decompyle incomplete



def get_class_members(klass):
    ret = dir(klass)
    if hasattr(klass, '__bases__'):
        for base in klass.__bases__:
            ret = ret + get_class_members(base)
    return ret

import readline
readline.set_completer(Completer().complete)
atexit.register((lambda : readline.set_completer(None)))
_readline_available = True
return None
# WARNING: Decompyle incomplete
