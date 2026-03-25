# Source Generated with Decompyle++
# File: csv.pyc (Python 3.12)

'''
csv.py - read/write/investigate CSV files
'''
import re
import types
from _csv import Error, __version__, writer, reader, register_dialect, unregister_dialect, get_dialect, list_dialects, field_size_limit, QUOTE_MINIMAL, QUOTE_ALL, QUOTE_NONNUMERIC, QUOTE_NONE, QUOTE_STRINGS, QUOTE_NOTNULL, __doc__
from _csv import Dialect as _Dialect
from io import StringIO
__all__ = [
    'QUOTE_MINIMAL',
    'QUOTE_ALL',
    'QUOTE_NONNUMERIC',
    'QUOTE_NONE',
    'QUOTE_STRINGS',
    'QUOTE_NOTNULL',
    'Error',
    'Dialect',
    '__doc__',
    'excel',
    'excel_tab',
    'field_size_limit',
    'reader',
    'writer',
    'register_dialect',
    'get_dialect',
    'list_dialects',
    'Sniffer',
    'unregister_dialect',
    '__version__',
    'DictReader',
    'DictWriter',
    'unix_dialect']

class Dialect:
    '''Describe a CSV dialect.

    This must be subclassed (see csv.excel).  Valid attributes are:
    delimiter, quotechar, escapechar, doublequote, skipinitialspace,
    lineterminator, quoting.

    '''
    _name = ''
    _valid = False
    delimiter = None
    quotechar = None
    escapechar = None
    doublequote = None
    skipinitialspace = None
    lineterminator = None
    quoting = None
    
    def __init__(self):
        if self.__class__ != Dialect:
            self._valid = True
        self._validate()

    
    def _validate(self):
        _Dialect(self)
        return None
    # WARNING: Decompyle incomplete



class excel(Dialect):
    '''Describe the usual properties of Excel-generated CSV files.'''
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = QUOTE_MINIMAL

register_dialect('excel', excel)

class excel_tab(excel):
    '''Describe the usual properties of Excel-generated TAB-delimited files.'''
    delimiter = '\t'

register_dialect('excel-tab', excel_tab)

class unix_dialect(Dialect):
    '''Describe the usual properties of Unix-generated CSV files.'''
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\n'
    quoting = QUOTE_ALL

register_dialect('unix', unix_dialect)

class DictReader:
    
    def __init__(self, f, fieldnames, restkey, restval, dialect = (None, None, None, 'excel'), *args, **kwds):
        pass
    # WARNING: Decompyle incomplete

    
    def __iter__(self):
        return self

    fieldnames = (lambda self: pass# WARNING: Decompyle incomplete
)()
    fieldnames = (lambda self, value: self._fieldnames = value)()
    
    def __next__(self):
        if self.line_num == 0:
            self.fieldnames
        row = next(self.reader)
        self.line_num = self.reader.line_num
        if row == []:
            row = next(self.reader)
            if row == []:
                continue
        d = dict(zip(self.fieldnames, row))
        lf = len(self.fieldnames)
        lr = len(row)
        if lf < lr:
            d[self.restkey] = row[lf:]
            return d
        if None > lr:
            for key in self.fieldnames[lr:]:
                d[key] = self.restval
        return d

    __class_getitem__ = classmethod(types.GenericAlias)


class DictWriter:
    
    def __init__(self, f, fieldnames, restval, extrasaction, dialect = ('', 'raise', 'excel'), *args, **kwds):
        pass
    # WARNING: Decompyle incomplete

    
    def writeheader(self):
        header = dict(zip(self.fieldnames, self.fieldnames))
        return self.writerow(header)

    
    def _dict_to_list(self, rowdict):
        pass
    # WARNING: Decompyle incomplete

    
    def writerow(self, rowdict):
        return self.writer.writerow(self._dict_to_list(rowdict))

    
    def writerows(self, rowdicts):
        return self.writer.writerows(map(self._dict_to_list, rowdicts))

    __class_getitem__ = classmethod(types.GenericAlias)


class Sniffer:
    '''
    "Sniffs" the format of a CSV file (i.e. delimiter, quotechar)
    Returns a Dialect object.
    '''
    
    def __init__(self):
        self.preferred = [
            ',',
            '\t',
            ';',
            ' ',
            ':']

    
    def sniff(self, sample, delimiters = (None,)):
        '''
        Returns a dialect (or None) corresponding to the sample
        '''
        (quotechar, doublequote, delimiter, skipinitialspace) = self._guess_quote_and_delimiter(sample, delimiters)
        if not delimiter:
            (delimiter, skipinitialspace) = self._guess_delimiter(sample, delimiters)
        if not delimiter:
            raise Error('Could not determine delimiter')
        
        class dialect(Dialect):
            _name = 'sniffed'
            lineterminator = '\r\n'
            quoting = QUOTE_MINIMAL

        dialect.doublequote = doublequote
        dialect.delimiter = delimiter
        if not quotechar:
            quotechar
        dialect.quotechar = '"'
        dialect.skipinitialspace = skipinitialspace
        return dialect

    
    def _guess_quote_and_delimiter(self, data, delimiters):
        """
        Looks for text enclosed between two identical quotes
        (the probable quotechar) which are preceded and followed
        by the same character (the probable delimiter).
        For example:
                         ,'some text',
        The quote with the most wins, same with the delimiter.
        If there is no quotechar the delimiter can't be determined
        this way.
        """
        matches = []
        for restr in ('(?P<delim>[^\\w\\n"\\\'])(?P<space> ?)(?P<quote>["\\\']).*?(?P=quote)(?P=delim)', '(?:^|\\n)(?P<quote>["\\\']).*?(?P=quote)(?P<delim>[^\\w\\n"\\\'])(?P<space> ?)', '(?P<delim>[^\\w\\n"\\\'])(?P<space> ?)(?P<quote>["\\\']).*?(?P=quote)(?:$|\\n)', '(?:^|\\n)(?P<quote>["\\\']).*?(?P=quote)(?:$|\\n)'):
            regexp = re.compile(restr, re.DOTALL | re.MULTILINE)
            matches = regexp.findall(data)
            if not matches:
                continue
            ('(?P<delim>[^\\w\\n"\\\'])(?P<space> ?)(?P<quote>["\\\']).*?(?P=quote)(?P=delim)', '(?:^|\\n)(?P<quote>["\\\']).*?(?P=quote)(?P<delim>[^\\w\\n"\\\'])(?P<space> ?)', '(?P<delim>[^\\w\\n"\\\'])(?P<space> ?)(?P<quote>["\\\']).*?(?P=quote)(?:$|\\n)', '(?:^|\\n)(?P<quote>["\\\']).*?(?P=quote)(?:$|\\n)')
        if not matches:
            return ('', False, None, 0)
        quotes = { }
        delims = { }
        spaces = 0
    # WARNING: Decompyle incomplete

    
    def _guess_delimiter(self, data, delimiters):
        """
        The delimiter /should/ occur the same number of times on
        each row. However, due to malformed data, it may not. We don't want
        an all or nothing approach, so we allow for small variations in this
        number.
          1) build a table of the frequency of each character on every line.
          2) build a table of frequencies of this frequency (meta-frequency?),
             e.g.  'x occurred 5 times in 10 rows, 6 times in 1000 rows,
             7 times in 2 rows'
          3) use the mode of the meta-frequency to determine the /expected/
             frequency for that character
          4) find out how often the character actually meets that goal
          5) the character that best meets its goal is the delimiter
        For performance reasons, the data is evaluated in chunks, so it can
        try and evaluate the smallest portion of the data possible, evaluating
        additional chunks as necessary.
        """
        data = list(filter(None, data.split('\n')))
    # WARNING: Decompyle incomplete

    
    def has_header(self, sample):
        rdr = reader(StringIO(sample), self.sniff(sample))
        header = next(rdr)
        columns = len(header)
        columnTypes = { }
        for i in range(columns):
            columnTypes[i] = None
        checked = 0
    # WARNING: Decompyle incomplete


