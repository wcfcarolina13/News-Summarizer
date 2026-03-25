# Source Generated with Decompyle++
# File: webbrowser.pyc (Python 3.12)

'''Interfaces for launching and remotely controlling web browsers.'''
import os
import shlex
import shutil
import sys
import subprocess
import threading
import warnings
__all__ = [
    'Error',
    'open',
    'open_new',
    'open_new_tab',
    'get',
    'register']

class Error(Exception):
    pass

_lock = threading.RLock()
_browsers = { }
_tryorder = None
_os_preferred_browser = None

def register(name = None, klass = (None,), instance = {
    'preferred': False }, *, preferred):
    '''Register a browser connector.'''
    pass
# WARNING: Decompyle incomplete


def get(using = (None,)):
    '''Return a browser launcher instance appropriate for the environment.'''
    pass
# WARNING: Decompyle incomplete


def open(url, new, autoraise = (0, True)):
    '''Display url using the default browser.

    If possible, open url in a location determined by new.
    - 0: the same browser window (the default).
    - 1: a new browser window.
    - 2: a new browser page ("tab").
    If possible, autoraise raises the window (the default) or not.
    '''
    pass
# WARNING: Decompyle incomplete


def open_new(url):
    '''Open url in a new window of the default browser.

    If not possible, then open url in the only browser window.
    '''
    return open(url, 1)


def open_new_tab(url):
    '''Open url in a new page ("tab") of the default browser.

    If not possible, then the behavior becomes equivalent to open_new().
    '''
    return open(url, 2)


def _synthesize(browser = None, *, preferred):
    """Attempt to synthesize a controller based on existing controllers.

    This is useful to create a controller when a user specifies a path to
    an entry in the BROWSER environment variable -- we can copy a general
    controller to operate using a specific installation of the desired
    browser in this way.

    If we can't create a controller in this way, or if there is no
    executable for the requested browser, return [None, None].

    """
    cmd = browser.split()[0]
    if not shutil.which(cmd):
        return [
            None,
            None]
    name = None.path.basename(cmd)
    command = _browsers[name.lower()]
    controller = command[1]
    if controller and name.lower() == controller.basename:
        import copy
        controller = copy.copy(controller)
        controller.name = browser
        controller.basename = os.path.basename(browser)
        register(browser, None, instance = controller, preferred = preferred)
        return [
            None,
            controller]
    return [
        None,
        None]
# WARNING: Decompyle incomplete


class BaseBrowser(object):
    '''Parent class for all browsers. Do not use directly.'''
    args = [
        '%s']
    
    def __init__(self, name = ('',)):
        self.name = name
        self.basename = name

    
    def open(self, url, new, autoraise = (0, True)):
        raise NotImplementedError

    
    def open_new(self, url):
        return self.open(url, 1)

    
    def open_new_tab(self, url):
        return self.open(url, 2)



class GenericBrowser(BaseBrowser):
    '''Class for all browsers started with a command
       and without remote functionality.'''
    
    def __init__(self, name):
        if isinstance(name, str):
            self.name = name
            self.args = [
                '%s']
        else:
            self.name = name[0]
            self.args = name[1:]
        self.basename = os.path.basename(self.name)

    
    def open(self, url, new, autoraise = (0, True)):
        sys.audit('webbrowser.open', url)
    # WARNING: Decompyle incomplete



class BackgroundBrowser(GenericBrowser):
    '''Class for all browsers which are to be started in the
       background.'''
    
    def open(self, url, new, autoraise = (0, True)):
        pass
    # WARNING: Decompyle incomplete



class UnixBrowser(BaseBrowser):
    '''Parent class for all Unix browsers with remote functionality.'''
    raise_opts = None
    background = False
    redirect_stdout = True
    remote_args = [
        '%action',
        '%s']
    remote_action = None
    remote_action_newwin = None
    remote_action_newtab = None
    
    def _invoke(self, args, remote, autoraise, url = (None,)):
        raise_opt = []
        if remote and self.raise_opts:
            autoraise = int(autoraise)
            opt = self.raise_opts[autoraise]
            if opt:
                raise_opt = [
                    opt]
        cmdline = [
            self.name] + raise_opt + args
        if remote or self.background:
            inout = subprocess.DEVNULL
        else:
            inout = None
        if self.redirect_stdout:
            self.redirect_stdout
        if not inout:
            inout
        p = subprocess.Popen(cmdline, close_fds = True, stdin = inout, stdout = None, stderr = inout, start_new_session = True)
        if remote:
            rc = p.wait(5)
            return not rc
    # WARNING: Decompyle incomplete

    
    def open(self, url, new, autoraise = (0, True)):
        sys.audit('webbrowser.open', url)
        if new == 0:
            action = self.remote_action
        elif new == 1:
            action = self.remote_action_newwin
    # WARNING: Decompyle incomplete



class Mozilla(UnixBrowser):
    '''Launcher class for Mozilla browsers.'''
    remote_args = [
        '%action',
        '%s']
    remote_action = ''
    remote_action_newwin = '-new-window'
    remote_action_newtab = '-new-tab'
    background = True


class Epiphany(UnixBrowser):
    '''Launcher class for Epiphany browser.'''
    raise_opts = [
        '-noraise',
        '']
    remote_args = [
        '%action',
        '%s']
    remote_action = '-n'
    remote_action_newwin = '-w'
    background = True


class Chrome(UnixBrowser):
    '''Launcher class for Google Chrome browser.'''
    remote_args = [
        '%action',
        '%s']
    remote_action = ''
    remote_action_newwin = '--new-window'
    remote_action_newtab = ''
    background = True

Chromium = Chrome

class Opera(UnixBrowser):
    '''Launcher class for Opera browser.'''
    remote_args = [
        '%action',
        '%s']
    remote_action = ''
    remote_action_newwin = '--new-window'
    remote_action_newtab = ''
    background = True


class Elinks(UnixBrowser):
    '''Launcher class for Elinks browsers.'''
    remote_args = [
        '-remote',
        'openURL(%s%action)']
    remote_action = ''
    remote_action_newwin = ',new-window'
    remote_action_newtab = ',new-tab'
    background = False
    redirect_stdout = False


class Konqueror(BaseBrowser):
    '''Controller for the KDE File Manager (kfm, or Konqueror).

    See the output of ``kfmclient --commands``
    for more information on the Konqueror remote-control interface.
    '''
    
    def open(self, url, new, autoraise = (0, True)):
        sys.audit('webbrowser.open', url)
        if new == 2:
            action = 'newTab'
        else:
            action = 'openURL'
        devnull = subprocess.DEVNULL
        p = subprocess.Popen([
            'kfmclient',
            action,
            url], close_fds = True, stdin = devnull, stdout = devnull, stderr = devnull)
        p.wait()
        return True
    # WARNING: Decompyle incomplete



class Edge(UnixBrowser):
    '''Launcher class for Microsoft Edge browser.'''
    remote_args = [
        '%action',
        '%s']
    remote_action = ''
    remote_action_newwin = '--new-window'
    remote_action_newtab = ''
    background = True


def register_X_browsers():
    if shutil.which('xdg-open'):
        register('xdg-open', None, BackgroundBrowser('xdg-open'))
    if shutil.which('gio'):
        register('gio', None, BackgroundBrowser([
            'gio',
            'open',
            '--',
            '%s']))
    if 'GNOME_DESKTOP_SESSION_ID' in os.environ and shutil.which('gvfs-open'):
        register('gvfs-open', None, BackgroundBrowser('gvfs-open'))
    if 'KDE_FULL_SESSION' in os.environ and shutil.which('kfmclient'):
        register('kfmclient', Konqueror, Konqueror('kfmclient'))
    if shutil.which('x-www-browser'):
        register('x-www-browser', None, BackgroundBrowser('x-www-browser'))
    for browser in ('firefox', 'iceweasel', 'seamonkey', 'mozilla-firefox', 'mozilla'):
        if not shutil.which(browser):
            continue
        register(browser, None, Mozilla(browser))
    if shutil.which('kfm'):
        register('kfm', Konqueror, Konqueror('kfm'))
    elif shutil.which('konqueror'):
        register('konqueror', Konqueror, Konqueror('konqueror'))
    if shutil.which('epiphany'):
        register('epiphany', None, Epiphany('epiphany'))
    for browser in ('google-chrome', 'chrome', 'chromium', 'chromium-browser'):
        if not shutil.which(browser):
            continue
        register(browser, None, Chrome(browser))
    if shutil.which('opera'):
        register('opera', None, Opera('opera'))
    if shutil.which('microsoft-edge'):
        register('microsoft-edge', None, Edge('microsoft-edge'))
        return None


def register_standard_browsers():
    global _tryorder, _os_preferred_browser
    _tryorder = []
    if sys.platform == 'darwin':
        register('MacOSX', None, MacOSXOSAScript('default'))
        register('chrome', None, MacOSXOSAScript('chrome'))
        register('firefox', None, MacOSXOSAScript('firefox'))
        register('safari', None, MacOSXOSAScript('safari'))
    if sys.platform == 'serenityos':
        register('Browser', None, BackgroundBrowser('Browser'))
    if sys.platform[:3] == 'win':
        register('windows-default', WindowsDefault)
        edge64 = os.path.join(os.environ.get('PROGRAMFILES(x86)', 'C:\\Program Files (x86)'), 'Microsoft\\Edge\\Application\\msedge.exe')
        edge32 = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Microsoft\\Edge\\Application\\msedge.exe')
        for browser in ('firefox', 'seamonkey', 'mozilla', 'chrome', 'opera', edge64, edge32):
            if not shutil.which(browser):
                continue
            register(browser, None, BackgroundBrowser(browser))
        if shutil.which('MicrosoftEdge.exe'):
            register('microsoft-edge', None, Edge('MicrosoftEdge.exe'))
        elif os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
            cmd = 'xdg-settings get default-web-browser'.split()
            raw_result = subprocess.check_output(cmd, stderr = subprocess.DEVNULL)
            result = raw_result.decode().strip()
            _os_preferred_browser = result
            register_X_browsers()
    if os.environ.get('TERM'):
        if shutil.which('www-browser'):
            register('www-browser', None, GenericBrowser('www-browser'))
        if shutil.which('links'):
            register('links', None, GenericBrowser('links'))
        if shutil.which('elinks'):
            register('elinks', None, Elinks('elinks'))
        if shutil.which('lynx'):
            register('lynx', None, GenericBrowser('lynx'))
        if shutil.which('w3m'):
            register('w3m', None, GenericBrowser('w3m'))
# WARNING: Decompyle incomplete

if sys.platform[:3] == 'win':
    
    class WindowsDefault(BaseBrowser):
        
        def open(self, url, new, autoraise = (0, True)):
            sys.audit('webbrowser.open', url)
            os.startfile(url)
            return True
        # WARNING: Decompyle incomplete


if sys.platform == 'darwin':
    
    class MacOSX(BaseBrowser):
        '''Launcher class for Aqua browsers on Mac OS X

        Optionally specify a browser name on instantiation.  Note that this
        will not work for Aqua browsers if the user has moved the application
        package after installation.

        If no browser is specified, the default browser, as specified in the
        Internet System Preferences panel, will be used.
        '''
        
        def __init__(self, name):
            warnings.warn(f'''{self.__class__.__name__} is deprecated in 3.11 use MacOSXOSAScript instead.''', DeprecationWarning, stacklevel = 2)
            self.name = name

        
        def open(self, url, new, autoraise = (0, True)):
            sys.audit('webbrowser.open', url)
        # WARNING: Decompyle incomplete


    
    class MacOSXOSAScript(BaseBrowser):
        pass
    # WARNING: Decompyle incomplete


def main():
    import getopt
    usage = 'Usage: %s [-n | -t | -h] url\n    -n: open new window\n    -t: open new tab\n    -h, --help: show help' % sys.argv[0]
    (opts, args) = getopt.getopt(sys.argv[1:], 'ntdh', [
        'help'])
    new_win = 0
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    main()
    return None
