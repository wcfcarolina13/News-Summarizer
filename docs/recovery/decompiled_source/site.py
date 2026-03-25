# Source Generated with Decompyle++
# File: site.pyc (Python 3.12)

'''Append module search paths for third-party packages to sys.path.

****************************************************************
* This module is automatically imported during initialization. *
****************************************************************

This will append site-specific paths to the module search path.  On
Unix (including Mac OSX), it starts with sys.prefix and
sys.exec_prefix (if different) and appends
lib/python<version>/site-packages.
On other platforms (such as Windows), it tries each of the
prefixes directly, as well as with lib/site-packages appended.  The
resulting directories, if they exist, are appended to sys.path, and
also inspected for path configuration files.

If a file named "pyvenv.cfg" exists one directory above sys.executable,
sys.prefix and sys.exec_prefix are set to that directory and
it is also checked for site-packages (sys.base_prefix and
sys.base_exec_prefix will always be the "real" prefixes of the Python
installation). If "pyvenv.cfg" (a bootstrap configuration file) contains
the key "include-system-site-packages" set to anything other than "false"
(case-insensitive), the system-level prefixes will still also be
searched for site-packages; otherwise they won\'t.

All of the resulting site-specific directories, if they exist, are
appended to sys.path, and also inspected for path configuration
files.

A path configuration file is a file whose name has the form
<package>.pth; its contents are additional directories (one per line)
to be added to sys.path.  Non-existing directories (or
non-directories) are never added to sys.path; no directory is added to
sys.path more than once.  Blank lines and lines beginning with
\'#\' are skipped. Lines starting with \'import\' are executed.

For example, suppose sys.prefix and sys.exec_prefix are set to
/usr/local and there is a directory /usr/local/lib/python2.5/site-packages
with three subdirectories, foo, bar and spam, and two path
configuration files, foo.pth and bar.pth.  Assume foo.pth contains the
following:

  # foo package configuration
  foo
  bar
  bletch

and bar.pth contains:

  # bar package configuration
  bar

Then the following directories are added to sys.path, in this order:

  /usr/local/lib/python2.5/site-packages/bar
  /usr/local/lib/python2.5/site-packages/foo

Note that bletch is omitted because it doesn\'t exist; bar precedes foo
because bar.pth comes alphabetically before foo.pth; and spam is
omitted because it is not mentioned in either path configuration file.

The readline module is also automatically configured to enable
completion for systems that support it.  This can be overridden in
sitecustomize, usercustomize or PYTHONSTARTUP.  Starting Python in
isolated mode (-I) disables automatic readline configuration.

After these operations, an attempt is made to import a module
named sitecustomize, which can perform arbitrary additional
site-specific customizations.  If this import fails with an
ImportError exception, it is silently ignored.
'''
import sys
import os
import builtins
import _sitebuiltins
import io
PREFIXES = [
    sys.prefix,
    sys.exec_prefix]
ENABLE_USER_SITE = None
USER_SITE = None
USER_BASE = None

def _trace(message):
    if sys.flags.verbose:
        print(message, file = sys.stderr)
        return None


def makepath(*paths):
    pass
# WARNING: Decompyle incomplete


def abs_paths():
    '''Set all module __file__ and __cached__ attributes to an absolute path'''
    for m in set(sys.modules.values()):
        loader_module = None
        loader_module = m.__loader__.__module__
        if loader_module not in frozenset({'_frozen_importlib', '_frozen_importlib_external'}):
            continue
        m.__file__ = os.path.abspath(m.__file__)
        m.__cached__ = os.path.abspath(m.__cached__)
    return None
# WARNING: Decompyle incomplete


def removeduppaths():
    ''' Remove duplicate entries from sys.path along with making them
    absolute'''
    L = []
    known_paths = set()
    for dir in sys.path:
        (dir, dircase) = makepath(dir)
        if not dircase not in known_paths:
            continue
        L.append(dir)
        known_paths.add(dircase)
    sys.path[:] = L
    return known_paths


def _init_pathinfo():
    '''Return a set containing all existing file system items from sys.path.'''
    d = set()
    for item in sys.path:
        if os.path.exists(item):
            (_, itemcase) = makepath(item)
            d.add(itemcase)
    continue
    return d
# WARNING: Decompyle incomplete


def addpackage(sitedir, name, known_paths):
    """Process a .pth file within the site-packages directory:
       For each line in the file, either combine it with sitedir to a path
       and add that to known_paths, or execute it if it starts with 'import '.
    """
    pass
# WARNING: Decompyle incomplete


def addsitedir(sitedir, known_paths = (None,)):
    """Add 'sitedir' argument to sys.path if missing and handle .pth files in
    'sitedir'"""
    _trace(f'''Adding directory: {sitedir!r}''')
# WARNING: Decompyle incomplete


def check_enableusersite():
    '''Check if user site directory is safe for inclusion

    The function tests for the command line flag (including environment var),
    process uid/gid equal to effective uid/gid.

    None: Disabled for security reasons
    False: Disabled by user (command line option)
    True: Safe and enabled
    '''
    if sys.flags.no_user_site:
        return False
    if hasattr(os, 'getuid') and hasattr(os, 'geteuid') and os.geteuid() != os.getuid():
        return None
    if hasattr(os, 'getgid') and hasattr(os, 'getegid') and os.getegid() != os.getgid():
        return None
    return True


def _getuserbase():
    env_base = os.environ.get('PYTHONUSERBASE', None)
    if env_base:
        return env_base
    if None.platform in frozenset({'wasi', 'vxworks', 'emscripten'}):
        return None
    
    def joinuser(*args):
        pass
    # WARNING: Decompyle incomplete

    if os.name == 'nt':
        if not os.environ.get('APPDATA'):
            os.environ.get('APPDATA')
        base = '~'
        return joinuser(base, 'Python')
    if None.platform == 'darwin' and sys._framework:
        return joinuser('~', 'Library', sys._framework, '%d.%d' % sys.version_info[:2])
    return joinuser('~', '.local')


def _get_path(userbase):
    version = sys.version_info
    if os.name == 'nt':
        ver_nodot = sys.winver.replace('.', '')
        return f'''{userbase}\\Python{ver_nodot}\\site-packages'''
    if None.platform == 'darwin' and sys._framework:
        return f'''{userbase}/lib/python/site-packages'''
    return f'''{None}/lib/python{version[0]}.{version[1]}/site-packages'''


def getuserbase():
    '''Returns the `user base` directory path.

    The `user base` directory can be used to store data. If the global
    variable ``USER_BASE`` is not initialized yet, this function will also set
    it.
    '''
    pass
# WARNING: Decompyle incomplete


def getusersitepackages():
    '''Returns the user-specific site-packages directory path.

    If the global variable ``USER_SITE`` is not initialized yet, this
    function will also set it.
    '''
    userbase = getuserbase()
# WARNING: Decompyle incomplete


def addusersitepackages(known_paths):
    '''Add a per user site-package to sys.path

    Each user has its own python directory with site-packages in the
    home directory.
    '''
    _trace('Processing user site-packages')
    user_site = getusersitepackages()
    if ENABLE_USER_SITE and os.path.isdir(user_site):
        addsitedir(user_site, known_paths)
    return known_paths


def getsitepackages(prefixes = (None,)):
    '''Returns a list containing all global site-packages directories.

    For each directory present in ``prefixes`` (or the global ``PREFIXES``),
    this function will find its `site-packages` subdirectory depending on the
    system environment, and will return a list of full paths.
    '''
    sitepackages = []
    seen = set()
# WARNING: Decompyle incomplete


def addsitepackages(known_paths, prefixes = (None,)):
    '''Add site-packages to sys.path'''
    _trace('Processing global site-packages')
    for sitedir in getsitepackages(prefixes):
        if not os.path.isdir(sitedir):
            continue
        addsitedir(sitedir, known_paths)
    return known_paths


def setquit():
    """Define new builtins 'quit' and 'exit'.

    These are objects which make the interpreter exit when called.
    The repr of each object contains a hint at how it works.

    """
    if os.sep == '\\':
        eof = 'Ctrl-Z plus Return'
    else:
        eof = 'Ctrl-D (i.e. EOF)'
    builtins.quit = _sitebuiltins.Quitter('quit', eof)
    builtins.exit = _sitebuiltins.Quitter('exit', eof)


def setcopyright():
    """Set 'copyright' and 'credits' in builtins"""
    builtins.copyright = _sitebuiltins._Printer('copyright', sys.copyright)
    builtins.credits = _sitebuiltins._Printer('credits', '    Thanks to CWI, CNRI, BeOpen.com, Zope Corporation and a cast of thousands\n    for supporting Python development.  See www.python.org for more information.')
    dirs = []
    files = []
    here = getattr(sys, '_stdlib_dir', None)
    if here and hasattr(os, '__file__'):
        here = os.path.dirname(os.__file__)
    if here:
        files.extend([
            'LICENSE.txt',
            'LICENSE'])
        dirs.extend([
            os.path.join(here, os.pardir),
            here,
            os.curdir])
    builtins.license = _sitebuiltins._Printer('license', 'See https://www.python.org/psf/license/', files, dirs)


def sethelper():
    builtins.help = _sitebuiltins._Helper()


def enablerlcompleter():
    '''Enable default readline configuration on interactive prompts, by
    registering a sys.__interactivehook__.

    If the readline module can be imported, the hook will set the Tab key
    as completion key and register ~/.python_history as history file.
    This can be overridden in the sitecustomize or usercustomize module,
    or in a PYTHONSTARTUP file.
    '''
    
    def register_readline():
        pass
    # WARNING: Decompyle incomplete

    sys.__interactivehook__ = register_readline


def venv(known_paths):
    env = os.environ
    if sys.platform == 'darwin' and '__PYVENV_LAUNCHER__' in env:
        executable = os.environ['__PYVENV_LAUNCHER__']
        sys._base_executable = os.environ['__PYVENV_LAUNCHER__']
    else:
        executable = sys.executable
    exe_dir = os.path.dirname(os.path.abspath(executable))
    site_prefix = os.path.dirname(exe_dir)
    sys._home = None
    conf_basename = 'pyvenv.cfg'
    candidate_conf = (lambda .0: pass# WARNING: Decompyle incomplete
)((os.path.join(exe_dir, conf_basename), os.path.join(site_prefix, conf_basename))(), None)
# WARNING: Decompyle incomplete


def execsitecustomize():
    '''Run custom site specific code, if available.'''
    import sitecustomize
    return None
# WARNING: Decompyle incomplete


def execusercustomize():
    '''Run custom user specific code, if available.'''
    import usercustomize
    return None
# WARNING: Decompyle incomplete


def main():
    '''Add standard site-specific directories to the module search path.

    This function is called automatically when this module is imported,
    unless the python interpreter was started with the -S flag.
    '''
    orig_path = sys.path[:]
    known_paths = removeduppaths()
    if orig_path != sys.path:
        abs_paths()
    known_paths = venv(known_paths)
# WARNING: Decompyle incomplete

if not sys.flags.no_site:
    main()

def _script():
    help = "    %s [--user-base] [--user-site]\n\n    Without arguments print some useful information\n    With arguments print the value of USER_BASE and/or USER_SITE separated\n    by '%s'.\n\n    Exit codes with --user-base or --user-site:\n      0 - user site directory is enabled\n      1 - user site directory is disabled by user\n      2 - user site directory is disabled by super user\n          or for security reasons\n     >2 - unknown error\n    "
    args = sys.argv[1:]
    if not args:
        user_base = getuserbase()
        user_site = getusersitepackages()
        print('sys.path = [')
        for dir in sys.path:
            print(f'''    {dir!r},''')
        print(']')
        
        def exists(path):
            pass
        # WARNING: Decompyle incomplete

        print(f'''USER_BASE: {user_base!r} ({exists(user_base)})''')
        print(f'''USER_SITE: {user_site!r} ({exists(user_site)})''')
        print(f'''ENABLE_USER_SITE: {ENABLE_USER_SITE!r}''')
        sys.exit(0)
    buffer = []
    if '--user-base' in args:
        buffer.append(USER_BASE)
    if '--user-site' in args:
        buffer.append(USER_SITE)
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    _script()
    return None
