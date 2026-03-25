# Source Generated with Decompyle++
# File: runpy.pyc (Python 3.12)

'''runpy.py - locating and running Python code using the module namespace

Provides support for locating and running Python scripts using the Python
module namespace instead of the native filesystem.

This allows Python code to play nicely with non-filesystem based PEP 302
importers when locating support scripts as well as when importing modules.
'''
import sys
import importlib.machinery as importlib
import importlib.util as importlib
import io
import os
__all__ = [
    'run_module',
    'run_path']
ModuleType = type(sys)

class _TempModule(object):
    '''Temporarily replace a module in sys.modules with an empty namespace'''
    
    def __init__(self, mod_name):
        self.mod_name = mod_name
        self.module = ModuleType(mod_name)
        self._saved_module = []

    
    def __enter__(self):
        mod_name = self.mod_name
        self._saved_module.append(sys.modules[mod_name])
        sys.modules[mod_name] = self.module
        return self
    # WARNING: Decompyle incomplete

    
    def __exit__(self, *args):
        if self._saved_module:
            sys.modules[self.mod_name] = self._saved_module[0]
            self._saved_module = []
            return None
        del sys.modules[self.mod_name]
        self._saved_module = []



class _ModifiedArgv0(object):
    
    def __init__(self, value):
        self.value = value
        self._saved_value = object()
        self._sentinel = object()

    
    def __enter__(self):
        if self._saved_value is not self._sentinel:
            raise RuntimeError('Already preserving saved value')
        self._saved_value = sys.argv[0]
        sys.argv[0] = self.value

    
    def __exit__(self, *args):
        self.value = self._sentinel
        sys.argv[0] = self._saved_value



def _run_code(code, run_globals, init_globals, mod_name, mod_spec, pkg_name, script_name = (None, None, None, None, None)):
    '''Helper to run code in nominated namespace'''
    pass
# WARNING: Decompyle incomplete


def _run_module_code(code, init_globals, mod_name, mod_spec, pkg_name, script_name = (None, None, None, None, None)):
    '''Helper to run code in new namespace with sys modified'''
    pass
# WARNING: Decompyle incomplete


def _get_module_details(mod_name, error = (ImportError,)):
    if mod_name.startswith('.'):
        raise error('Relative module names not supported')
    (pkg_name, _, _) = mod_name.rpartition('.')
# WARNING: Decompyle incomplete


class _Error(Exception):
    '''Error that _run_module_as_main() should report without a traceback'''
    pass


def _run_module_as_main(mod_name, alter_argv = (True,)):
    '''Runs the designated module in the __main__ namespace

       Note that the executed module will have full access to the
       __main__ namespace. If this is not desirable, the run_module()
       function should be used to run the module code in a fresh namespace.

       At the very least, these variables in __main__ will be overwritten:
           __name__
           __file__
           __cached__
           __loader__
           __package__
    '''
    if alter_argv or mod_name != '__main__':
        (mod_name, mod_spec, code) = _get_module_details(mod_name, _Error)
    else:
        (mod_name, mod_spec, code) = _get_main_module_details(_Error)
    main_globals = sys.modules['__main__'].__dict__
# WARNING: Decompyle incomplete


def run_module(mod_name, init_globals, run_name, alter_sys = (None, None, False)):
    """Execute a module's code without importing it.

       mod_name -- an absolute module name or package name.

       Optional arguments:
       init_globals -- dictionary used to pre-populate the module’s
       globals dictionary before the code is executed.

       run_name -- if not None, this will be used for setting __name__;
       otherwise, __name__ will be set to mod_name + '__main__' if the
       named module is a package and to just mod_name otherwise.

       alter_sys -- if True, sys.argv[0] is updated with the value of
       __file__ and sys.modules[__name__] is updated with a temporary
       module object for the module being executed. Both are
       restored to their original values before the function returns.

       Returns the resulting module globals dictionary.
    """
    (mod_name, mod_spec, code) = _get_module_details(mod_name)
# WARNING: Decompyle incomplete


def _get_main_module_details(error = (ImportError,)):
    main_name = '__main__'
    saved_main = sys.modules[main_name]
    del sys.modules[main_name]
    sys.modules[main_name] = saved_main
    return _get_module_details(main_name)
# WARNING: Decompyle incomplete


def _get_code_from_file(run_name, fname):
    read_code = read_code
    import pkgutil
    decoded_path = os.path.abspath(os.fsdecode(fname))
# WARNING: Decompyle incomplete


def run_path(path_name, init_globals, run_name = (None, None)):
    """Execute code located at the specified filesystem location.

       path_name -- filesystem location of a Python script, zipfile,
       or directory containing a top level __main__.py script.

       Optional arguments:
       init_globals -- dictionary used to pre-populate the module’s
       globals dictionary before the code is executed.

       run_name -- if not None, this will be used to set __name__;
       otherwise, '<run_path>' will be used for __name__.

       Returns the resulting module globals dictionary.
    """
    pass
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('No module specified for execution', file = sys.stderr)
        return None
    del sys.argv[0]
    _run_module_as_main(sys.argv[0])
    return None
