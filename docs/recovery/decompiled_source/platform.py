# Source Generated with Decompyle++
# File: platform.pyc (Python 3.12)

__doc__ = ' This module tries to retrieve as much platform-identifying data as\n    possible. It makes this information available via function APIs.\n\n    If called from the command line, it prints the platform\n    information concatenated as single string to stdout. The output\n    format is usable as part of a filename.\n\n'
__copyright__ = '\n    Copyright (c) 1999-2000, Marc-Andre Lemburg; mailto:mal@lemburg.com\n    Copyright (c) 2000-2010, eGenix.com Software GmbH; mailto:info@egenix.com\n\n    Permission to use, copy, modify, and distribute this software and its\n    documentation for any purpose and without fee or royalty is hereby granted,\n    provided that the above copyright notice appear in all copies and that\n    both that copyright notice and this permission notice appear in\n    supporting documentation or portions thereof, including modifications,\n    that you make.\n\n    EGENIX.COM SOFTWARE GMBH DISCLAIMS ALL WARRANTIES WITH REGARD TO\n    THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND\n    FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL,\n    INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING\n    FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,\n    NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION\n    WITH THE USE OR PERFORMANCE OF THIS SOFTWARE !\n\n'
__version__ = '1.0.8'
import collections
import os
import re
import sys
import functools
import itertools
_ver_stages = {
    'dev': 10,
    'alpha': 20,
    'a': 20,
    'beta': 30,
    'b': 30,
    'c': 40,
    'RC': 50,
    'rc': 50,
    'pl': 200,
    'p': 200 }

def _comparable_version(version):
    component_re = re.compile('([0-9]+|[._+-])')
    result = []
    for v in component_re.split(version):
        if not v not in '._+-':
            continue
        v = int(v, 10)
        t = 100
        result.extend((t, v))
    return result
# WARNING: Decompyle incomplete


def libc_ver(executable, lib, version, chunksize = (None, '', '', 16384)):
    ''' Tries to determine the libc version that the file executable
        (which defaults to the Python interpreter) is linked against.

        Returns a tuple of strings (lib,version) which default to the
        given parameters in case the lookup fails.

        Note that the function has intimate knowledge of how different
        libc versions add symbols to the executable and thus is probably
        only usable for executables compiled using gcc.

        The file is read and scanned in chunks of chunksize bytes.

    '''
    pass
# WARNING: Decompyle incomplete


def _norm_version(version, build = ('',)):
    ''' Normalize the version and build strings and return a single
        version string using the format major.minor.build (or patchlevel).
    '''
    l = version.split('.')
    if build:
        l.append(build)
    strings = list(map(str, map(int, l)))
    version = '.'.join(strings[:3])
    return version
# WARNING: Decompyle incomplete


def _syscmd_ver(system, release, version, supported_platforms = ('', '', '', ('win32', 'win16', 'dos'))):
    ''' Tries to figure out the OS version used and returns
        a tuple (system, release, version).

        It uses the "ver" shell command for this which is known
        to exists on Windows, DOS. XXX Others too ?

        In case this fails, the given parameters are used as
        defaults.

    '''
    if sys.platform not in supported_platforms:
        return (system, release, version)
    import subprocess
    for cmd in ('ver', 'command /c ver', 'cmd /c ver'):
        info = subprocess.check_output(cmd, stdin = subprocess.DEVNULL, stderr = subprocess.DEVNULL, text = True, encoding = 'locale', shell = True)
        ('ver', 'command /c ver', 'cmd /c ver')
    return (system, release, version)
    ver_output = re.compile('(?:([\\w ]+) ([\\w.]+) .*\\[.* ([\\d.]+)\\])')
    info = info.strip()
    m = ver_output.match(info)
# WARNING: Decompyle incomplete

import _wmi

def _wmi_query(table, *keys):
    pass
# WARNING: Decompyle incomplete

_WIN32_CLIENT_RELEASES = [
    ((10, 1, 0), 'post11'),
    ((10, 0, 22000), '11'),
    ((6, 4, 0), '10'),
    ((6, 3, 0), '8.1'),
    ((6, 2, 0), '8'),
    ((6, 1, 0), '7'),
    ((6, 0, 0), 'Vista'),
    ((5, 2, 3790), 'XP64'),
    ((5, 2, 0), 'XPMedia'),
    ((5, 1, 0), 'XP'),
    ((5, 0, 0), '2000')]
_WIN32_SERVER_RELEASES = [
    ((10, 1, 0), 'post2022Server'),
    ((10, 0, 20348), '2022Server'),
    ((10, 0, 17763), '2019Server'),
    ((6, 4, 0), '2016Server'),
    ((6, 3, 0), '2012ServerR2'),
    ((6, 2, 0), '2012Server'),
    ((6, 1, 0), '2008ServerR2'),
    ((6, 0, 0), '2008Server'),
    ((5, 2, 0), '2003Server'),
    ((5, 0, 0), '2000Server')]

def win32_is_iot():
    return win32_edition() in ('IoTUAP', 'NanoServer', 'WindowsCoreHeadless', 'IoTEdgeOS')


def win32_edition():
    import winreg
    cvkey = 'SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion'
# WARNING: Decompyle incomplete


def _win32_ver(version, csd, ptype):
    (version, product_type, ptype, spmajor, spminor) = _wmi_query('OS', 'Version', 'ProductType', 'BuildType', 'ServicePackMajorVersion', 'ServicePackMinorVersion')
    is_client = int(product_type) == 1
    if spminor and spminor != '0':
        csd = f'''SP{spmajor}.{spminor}'''
    else:
        csd = f'''SP{spmajor}'''
    return (version, csd, ptype, is_client)
# WARNING: Decompyle incomplete


def win32_ver(release, version, csd, ptype = ('', '', '', '')):
    pass
# WARNING: Decompyle incomplete


def _mac_ver_xml():
    fn = '/System/Library/CoreServices/SystemVersion.plist'
    if not os.path.exists(fn):
        return None
    import plistlib
# WARNING: Decompyle incomplete


def mac_ver(release, versioninfo, machine = ('', ('', '', ''), '')):
    """ Get macOS version information and return it as tuple (release,
        versioninfo, machine) with versioninfo being a tuple (version,
        dev_stage, non_release_version).

        Entries which cannot be determined are set to the parameter values
        which default to ''. All tuple entries are strings.
    """
    info = _mac_ver_xml()
# WARNING: Decompyle incomplete


def _java_getprop(name, default):
    System = System
    import java.lang
    value = System.getProperty(name)
# WARNING: Decompyle incomplete


def java_ver(release, vendor, vminfo, osinfo = ('', '', ('', '', ''), ('', '', ''))):
    """ Version interface for Jython.

        Returns a tuple (release, vendor, vminfo, osinfo) with vminfo being
        a tuple (vm_name, vm_release, vm_vendor) and osinfo being a
        tuple (os_name, os_version, os_arch).

        Values which cannot be determined are set to the defaults
        given as parameters (which all default to '').

    """
    import java.lang as java
    vendor = _java_getprop('java.vendor', vendor)
    release = _java_getprop('java.version', release)
    (vm_name, vm_release, vm_vendor) = vminfo
    vm_name = _java_getprop('java.vm.name', vm_name)
    vm_vendor = _java_getprop('java.vm.vendor', vm_vendor)
    vm_release = _java_getprop('java.vm.version', vm_release)
    vminfo = (vm_name, vm_release, vm_vendor)
    (os_name, os_version, os_arch) = osinfo
    os_arch = _java_getprop('java.os.arch', os_arch)
    os_name = _java_getprop('java.os.name', os_name)
    os_version = _java_getprop('java.os.version', os_version)
    osinfo = (os_name, os_version, os_arch)
    return (release, vendor, vminfo, osinfo)
# WARNING: Decompyle incomplete


def system_alias(system, release, version):
    ''' Returns (system, release, version) aliased to common
        marketing names used for some systems.

        It also does some reordering of the information in some cases
        where it would otherwise cause confusion.

    '''
    if system == 'SunOS':
        if release < '5':
            return (system, release, version)
        l = None.split('.')
        if l:
            major = int(l[0])
            major = major - 3
            l[0] = str(major)
            release = '.'.join(l)
        if release < '6':
            system = 'Solaris'
        else:
            system = 'Solaris'
    elif system in ('win32', 'win16'):
        system = 'Windows'
    return (system, release, version)
# WARNING: Decompyle incomplete


def _platform(*args):
    ''' Helper to format the platform string in a filename
        compatible format e.g. "system-version-machine".
    '''
    platform = (lambda .0: pass# WARNING: Decompyle incomplete
)(filter(len, args)())
    platform = platform.replace(' ', '_')
    platform = platform.replace('/', '-')
    platform = platform.replace('\\', '-')
    platform = platform.replace(':', '-')
    platform = platform.replace(';', '-')
    platform = platform.replace('"', '-')
    platform = platform.replace('(', '-')
    platform = platform.replace(')', '-')
    platform = platform.replace('unknown', '')
    cleaned = platform.replace('--', '-')
    if cleaned == platform:
        pass
    else:
        platform = cleaned
    if platform[-1] == '-':
        platform = platform[:-1]
        if platform[-1] == '-':
            continue
    return platform


def _node(default = ('',)):
    ''' Helper to determine the node name of this machine.
    '''
    import socket
    return socket.gethostname()
# WARNING: Decompyle incomplete


def _follow_symlinks(filepath):
    ''' In case filepath is a symlink, follow it until a
        real file is reached.
    '''
    filepath = os.path.abspath(filepath)
    if os.path.islink(filepath):
        filepath = os.path.normpath(os.path.join(os.path.dirname(filepath), os.readlink(filepath)))
        if os.path.islink(filepath):
            continue
    return filepath


def _syscmd_file(target, default = ('',)):
    """ Interface to the system's file command.

        The function uses the -b option of the file command to have it
        omit the filename in its output. Follow the symlinks. It returns
        default in case the command should fail.

    """
    if sys.platform in ('dos', 'win32', 'win16'):
        return default
    import subprocess
    target = _follow_symlinks(target)
    env = dict(os.environ, LC_ALL = 'C')
    output = subprocess.check_output([
        'file',
        '-b',
        target], stderr = subprocess.DEVNULL, env = env)
    if not output:
        return default
    return None.decode('latin-1')
# WARNING: Decompyle incomplete

_default_architecture = {
    'win32': ('', 'WindowsPE'),
    'win16': ('', 'Windows'),
    'dos': ('', 'MSDOS') }

def architecture(executable, bits, linkage = (sys.executable, '', '')):
    ''' Queries the given executable (defaults to the Python interpreter
        binary) for various architecture information.

        Returns a tuple (bits, linkage) which contains information about
        the bit architecture and the linkage format used for the
        executable. Both values are returned as strings.

        Values that cannot be determined are returned as given by the
        parameter presets. If bits is given as \'\', the sizeof(pointer)
        (or sizeof(long) on Python version < 1.5.2) is used as
        indicator for the supported pointer size.

        The function relies on the system\'s "file" command to do the
        actual work. This is available on most if not all Unix
        platforms. On some non-Unix platforms where the "file" command
        does not exist and the executable is set to the Python interpreter
        binary defaults from _default_architecture are used.

    '''
    if not bits:
        import struct
        size = struct.calcsize('P')
        bits = str(size * 8) + 'bit'
    if executable:
        fileout = _syscmd_file(executable, '')
    else:
        fileout = ''
    if fileout and executable == sys.executable:
        if sys.platform in _default_architecture:
            (b, l) = _default_architecture[sys.platform]
            if b:
                bits = b
            if l:
                linkage = l
        return (bits, linkage)
    if None not in fileout and 'shared object' not in fileout:
        return (bits, linkage)
    if None in fileout:
        bits = '32bit'
    elif '64-bit' in fileout:
        bits = '64bit'
    if 'ELF' in fileout:
        linkage = 'ELF'
        return (bits, linkage)
    if None in fileout:
        if 'Windows' in fileout:
            linkage = 'WindowsPE'
            return (bits, linkage)
        linkage = None
        return (bits, linkage)
    if None in fileout:
        linkage = 'COFF'
        return (bits, linkage)
    if None in fileout:
        linkage = 'MSDOS'
        return (bits, linkage)
    return (bits, linkage)


def _get_machine_win32():
    pass
# WARNING: Decompyle incomplete


class _Processor:
    get = (lambda cls: func = getattr(cls, f'''get_{sys.platform}''', cls.from_subprocess)if not func():
func()'')()
    
    def get_win32():
        (manufacturer, caption) = _wmi_query('CPU', 'Manufacturer', 'Caption')
        return f'''{caption}, {manufacturer}'''
    # WARNING: Decompyle incomplete

    
    def get_OpenVMS():
        import vms_lib
        (csid, cpu_number) = vms_lib.getsyi('SYI$_CPU', 0)
        if cpu_number >= 128:
            return 'Alpha'
        return None
    # WARNING: Decompyle incomplete

    
    def from_subprocess():
        '''
        Fall back to `uname -p`
        '''
        import subprocess
        return subprocess.check_output([
            'uname',
            '-p'], stderr = subprocess.DEVNULL, text = True, encoding = 'utf8').strip()
    # WARNING: Decompyle incomplete



def _unknown_as_blank(val):
    if val == 'unknown':
        return ''


def uname_result():
    '''uname_result'''
    pass
# WARNING: Decompyle incomplete

uname_result = <NODE:27>(uname_result, 'uname_result', collections.namedtuple('uname_result_base', 'system node release version machine'))
_uname_cache = None

def uname():
    """ Fairly portable uname interface. Returns a tuple
        of strings (system, node, release, version, machine, processor)
        identifying the underlying platform.

        Note that unlike the os.uname function this also returns
        possible processor information as an additional tuple entry.

        Entries which cannot be determined are set to ''.

    """
    pass
# WARNING: Decompyle incomplete


def system():
    """ Returns the system/OS name, e.g. 'Linux', 'Windows' or 'Java'.

        An empty string is returned if the value cannot be determined.

    """
    return uname().system


def node():
    """ Returns the computer's network name (which may not be fully
        qualified)

        An empty string is returned if the value cannot be determined.

    """
    return uname().node


def release():
    """ Returns the system's release, e.g. '2.2.0' or 'NT'

        An empty string is returned if the value cannot be determined.

    """
    return uname().release


def version():
    """ Returns the system's release version, e.g. '#3 on degas'

        An empty string is returned if the value cannot be determined.

    """
    return uname().version


def machine():
    """ Returns the machine type, e.g. 'i386'

        An empty string is returned if the value cannot be determined.

    """
    return uname().machine


def processor():
    """ Returns the (true) processor name, e.g. 'amdk6'

        An empty string is returned if the value cannot be
        determined. Note that many platforms do not provide this
        information or simply return the same value as for machine(),
        e.g.  NetBSD does this.

    """
    return uname().processor

_sys_version_cache = { }

def _sys_version(sys_version = (None,)):
    """ Returns a parsed version of Python's sys.version as tuple
        (name, version, branch, revision, buildno, builddate, compiler)
        referring to the Python implementation name, version, branch,
        revision, build number, build date/time as string and the compiler
        identification string.

        Note that unlike the Python sys.version, the returned value
        for the Python version will always include the patchlevel (it
        defaults to '.0').

        The function returns empty strings for tuple entries that
        cannot be determined.

        sys_version may be given to parse an alternative version
        string, e.g. if the version was read from a different Python
        interpreter.

    """
    pass
# WARNING: Decompyle incomplete


def python_implementation():
    """ Returns a string identifying the Python implementation.

        Currently, the following implementations are identified:
          'CPython' (C implementation of Python),
          'Jython' (Java implementation of Python),
          'PyPy' (Python implementation of Python).

    """
    return _sys_version()[0]


def python_version():
    """ Returns the Python version as string 'major.minor.patchlevel'

        Note that unlike the Python sys.version, the returned value
        will always include the patchlevel (it defaults to 0).

    """
    return _sys_version()[1]


def python_version_tuple():
    ''' Returns the Python version as tuple (major, minor, patchlevel)
        of strings.

        Note that unlike the Python sys.version, the returned value
        will always include the patchlevel (it defaults to 0).

    '''
    return tuple(_sys_version()[1].split('.'))


def python_branch():
    ''' Returns a string identifying the Python implementation
        branch.

        For CPython this is the SCM branch from which the
        Python binary was built.

        If not available, an empty string is returned.

    '''
    return _sys_version()[2]


def python_revision():
    ''' Returns a string identifying the Python implementation
        revision.

        For CPython this is the SCM revision from which the
        Python binary was built.

        If not available, an empty string is returned.

    '''
    return _sys_version()[3]


def python_build():
    ''' Returns a tuple (buildno, builddate) stating the Python
        build number and date as strings.

    '''
    return _sys_version()[4:6]


def python_compiler():
    ''' Returns a string identifying the compiler used for compiling
        Python.

    '''
    return _sys_version()[6]

_platform_cache = { }

def platform(aliased, terse = (False, False)):
    ''' Returns a single string identifying the underlying platform
        with as much useful information as possible (but no more :).

        The output is intended to be human readable rather than
        machine parseable. It may look different on different
        platforms and this is intended.

        If "aliased" is true, the function will use aliases for
        various platforms that report system names which differ from
        their common names, e.g. SunOS will be reported as
        Solaris. The system_alias() function is used to implement
        this.

        Setting terse to true causes the function to return only the
        absolute minimum information needed to identify the platform.

    '''
    result = _platform_cache.get((aliased, terse), None)
# WARNING: Decompyle incomplete

_os_release_candidates = ('/etc/os-release', '/usr/lib/os-release')
_os_release_cache = None

def _parse_os_release(lines):
    info = {
        'NAME': 'Linux',
        'ID': 'linux',
        'PRETTY_NAME': 'Linux' }
    os_release_line = re.compile('^(?P<name>[a-zA-Z0-9_]+)=(?P<quote>["\']?)(?P<value>.*)(?P=quote)$')
    os_release_unescape = re.compile('\\\\([\\\\\\$\\"\\\'`])')
# WARNING: Decompyle incomplete


def freedesktop_os_release():
    '''Return operation system identification from freedesktop.org os-release
    '''
    pass
# WARNING: Decompyle incomplete

if __name__ == '__main__':
    if not 'terse' in sys.argv:
        'terse' in sys.argv
    terse = '--terse' in sys.argv
    if 'nonaliased' not in sys.argv:
        'nonaliased' not in sys.argv
    aliased = '--nonaliased' not in sys.argv
    print(platform(aliased, terse))
    sys.exit(0)
    return None
return None
# WARNING: Decompyle incomplete
