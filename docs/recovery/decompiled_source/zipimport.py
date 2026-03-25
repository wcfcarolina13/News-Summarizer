# Source Generated with Decompyle++
# File: zipimport.pyc (Python 3.12)

"""zipimport provides support for importing Python modules from Zip archives.

This module exports three objects:
- zipimporter: a class; its constructor takes a path to a Zip archive.
- ZipImportError: exception raised by zipimporter objects. It's a
  subclass of ImportError, so it can be caught as ImportError, too.
- _zip_directory_cache: a dict, mapping archive paths to zip directory
  info dicts, as used in zipimporter._files.

It is usually not needed to use the zipimport module explicitly; it is
used by the builtin import mechanism for sys.path items that are paths
to Zip archives.
"""
import _frozen_importlib_external as _bootstrap_external
from _frozen_importlib_external import _unpack_uint16, _unpack_uint32
import _frozen_importlib as _bootstrap
import _imp
import _io
import marshal
import sys
import time
import _warnings
__all__ = [
    'ZipImportError',
    'zipimporter']
path_sep = _bootstrap_external.path_sep
alt_path_sep = _bootstrap_external.path_separators[1:]

class ZipImportError(ImportError):
    pass

_zip_directory_cache = { }
_module_type = type(sys)
END_CENTRAL_DIR_SIZE = 22
STRING_END_ARCHIVE = b'PK\x05\x06'
MAX_COMMENT_LEN = 65535

class zipimporter(_bootstrap_external._LoaderBasics):
    """zipimporter(archivepath) -> zipimporter object

    Create a new zipimporter instance. 'archivepath' must be a path to
    a zipfile, or to a specific path inside a zipfile. For example, it can be
    '/tmp/myimport.zip', or '/tmp/myimport.zip/mydirectory', if mydirectory is a
    valid directory inside the archive.

    'ZipImportError is raised if 'archivepath' doesn't point to a valid Zip
    archive.

    The 'archive' attribute of zipimporter objects contains the name of the
    zipfile targeted.
    """
    
    def __init__(self, path):
        if not isinstance(path, str):
            raise TypeError(f'''expected str, not {type(path)!r}''')
        if not path:
            raise ZipImportError('archive path is empty', path = path)
        if alt_path_sep:
            path = path.replace(alt_path_sep, path_sep)
        prefix = []
        st = _bootstrap_external._path_stat(path)
        if st.st_mode & 61440 != 32768:
            raise ZipImportError('not a Zip file', path = path)
        files = _zip_directory_cache[path]
        self._files = files
        self.archive = path
    # WARNING: Decompyle incomplete

    
    def find_spec(self, fullname, target = (None,)):
        '''Create a ModuleSpec for the specified module.

        Returns None if the module cannot be found.
        '''
        module_info = _get_module_info(self, fullname)
    # WARNING: Decompyle incomplete

    
    def get_code(self, fullname):
        """get_code(fullname) -> code object.

        Return the code object for the specified module. Raise ZipImportError
        if the module couldn't be imported.
        """
        (code, ispackage, modpath) = _get_module_code(self, fullname)
        return code

    
    def get_data(self, pathname):
        """get_data(pathname) -> string with file data.

        Return the data associated with 'pathname'. Raise OSError if
        the file wasn't found.
        """
        if alt_path_sep:
            pathname = pathname.replace(alt_path_sep, path_sep)
        key = pathname
        if pathname.startswith(self.archive + path_sep):
            key = pathname[len(self.archive + path_sep):]
        toc_entry = self._files[key]
        return _get_data(self.archive, toc_entry)
    # WARNING: Decompyle incomplete

    
    def get_filename(self, fullname):
        """get_filename(fullname) -> filename string.

        Return the filename for the specified module or raise ZipImportError
        if it couldn't be imported.
        """
        (code, ispackage, modpath) = _get_module_code(self, fullname)
        return modpath

    
    def get_source(self, fullname):
        """get_source(fullname) -> source string.

        Return the source code for the specified module. Raise ZipImportError
        if the module couldn't be found, return None if the archive does
        contain the module, but has no source for it.
        """
        mi = _get_module_info(self, fullname)
    # WARNING: Decompyle incomplete

    
    def is_package(self, fullname):
        """is_package(fullname) -> bool.

        Return True if the module specified by fullname is a package.
        Raise ZipImportError if the module couldn't be found.
        """
        mi = _get_module_info(self, fullname)
    # WARNING: Decompyle incomplete

    
    def load_module(self, fullname):
        """load_module(fullname) -> module.

        Load the module specified by 'fullname'. 'fullname' must be the
        fully qualified (dotted) module name. It returns the imported
        module, or raises ZipImportError if it could not be imported.

        Deprecated since Python 3.10. Use exec_module() instead.
        """
        msg = 'zipimport.zipimporter.load_module() is deprecated and slated for removal in Python 3.12; use exec_module() instead'
        _warnings.warn(msg, DeprecationWarning)
        (code, ispackage, modpath) = _get_module_code(self, fullname)
        mod = sys.modules.get(fullname)
    # WARNING: Decompyle incomplete

    
    def get_resource_reader(self, fullname):
        """Return the ResourceReader for a package in a zip file.

        If 'fullname' is a package within the zip file, return the
        'ResourceReader' object for the package.  Otherwise return None.
        """
        if not self.is_package(fullname):
            return None
        ZipReader = ZipReader
        import importlib.readers
        return ZipReader(self, fullname)
    # WARNING: Decompyle incomplete

    
    def invalidate_caches(self):
        '''Reload the file data of the archive path.'''
        self._files = _read_directory(self.archive)
        _zip_directory_cache[self.archive] = self._files
        return None
    # WARNING: Decompyle incomplete

    
    def __repr__(self):
        return f'''<zipimporter object "{self.archive}{path_sep}{self.prefix}">'''


_zip_searchorder = ((path_sep + '__init__.pyc', True, True), (path_sep + '__init__.py', False, True), ('.pyc', True, False), ('.py', False, False))

def _get_module_path(self, fullname):
    return self.prefix + fullname.rpartition('.')[2]


def _is_dir(self, path):
    dirpath = path + path_sep
    return dirpath in self._files


def _get_module_info(self, fullname):
    path = _get_module_path(self, fullname)
    for suffix, isbytecode, ispackage in _zip_searchorder:
        fullpath = path + suffix
        if not fullpath in self._files:
            continue
        
        return _zip_searchorder, ispackage


def _read_directory(archive):
    fp = _io.open_code(archive)
# WARNING: Decompyle incomplete

cp437_table = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7fÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ '
_importing_zlib = False

def _get_decompress_func():
    global _importing_zlib, _importing_zlib
    if _importing_zlib:
        _bootstrap._verbose_message('zipimport: zlib UNAVAILABLE')
        raise ZipImportError("can't decompress data; zlib not available")
    _importing_zlib = True
    decompress = decompress
    import zlib
    _importing_zlib = False
    _bootstrap._verbose_message('zipimport: zlib available')
    return decompress
# WARNING: Decompyle incomplete


def _get_data(archive, toc_entry):
    (datapath, compress, data_size, file_size, file_offset, time, date, crc) = toc_entry
    if data_size < 0:
        raise ZipImportError('negative data size')
# WARNING: Decompyle incomplete


def _eq_mtime(t1, t2):
    return abs(t1 - t2) <= 1


def _unmarshal_code(self, pathname, fullpath, fullname, data):
    exc_details = {
        'name': fullname,
        'path': fullpath }
    flags = _bootstrap_external._classify_pyc(data, fullname, exc_details)
    hash_based = flags & 1 != 0
# WARNING: Decompyle incomplete

_code_type = type(_unmarshal_code.__code__)

def _normalize_line_endings(source):
    source = source.replace(b'\r\n', b'\n')
    source = source.replace(b'\r', b'\n')
    return source


def _compile_source(pathname, source):
    source = _normalize_line_endings(source)
    return compile(source, pathname, 'exec', dont_inherit = True)


def _parse_dostime(d, t):
    return time.mktime(((d >> 9) + 1980, d >> 5 & 15, d & 31, t >> 11, t >> 5 & 63, (t & 31) * 2, -1, -1, -1))


def _get_mtime_and_size_of_source(self, path):
    pass
# WARNING: Decompyle incomplete


def _get_pyc_source(self, path):
    pass
# WARNING: Decompyle incomplete


def _get_module_code(self, fullname):
    path = _get_module_path(self, fullname)
    import_error = None
# WARNING: Decompyle incomplete

