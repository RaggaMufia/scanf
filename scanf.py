"""A scanf implementation for Python under a liberal license.

Although regular expressions are available in Python and are very powerful,
they can be overly verbose and complicated for certain types of simple use
cases.
"""
from __future__ import unicode_literals, print_function, absolute_import

import re
import sys
import logging
import functools

try:
    import unittest2 as unittest
except:
    import unittest

logging.basicConfig()
_log = logging.getLogger(__name__ if __name__ != '__main__' else 'scanf')
_log.setLevel(logging.DEBUG)


# account for differences in in Python 2 and 3
if sys.version_info[0] < 3:
    from future_builtins import ascii, filter, hex, map, oct, zip
    bytes = str
    str = unicode
    range = xrange
else:
    pass

# spec with groups
_gspec = r'(?P<escape>%%)|(?:%(?:\((?P<key>\w+)\))?(?P<skip>\*)?(?P<width>[0-9]+)?(?:h{1,2}|l{1,2}|j|z|t|L)?(?P<spec>[duioxXeEfFgGcrs]))'
_gbspec = re.compile(_gspec.encode('latin1'))
_gspec = re.compile(_gspec)



def _return_input(obj):
    return obj

# Map specifiers to their regex. Leave num repetitions to be filled in later.
_fmts = dict()
# integral numbers
_fmts['d'] = r'[-+]?[0-9]+'
_fmts['u'] = r'[0-9]{n}'
_fmts['o'] = r'[-+]?[0-7]+'
_fmts['x'] = r'[-+]?(?:0[xX])?[0-9A-Fa-f]+'
_fmts['i'] = r'[-+]?(?:(?:0[xX][0-9A-Fa-f]+)|(?:0[0-7]+)|(?:[0-9]+))'

# TODO: fix float parsing
# real numbers
_fmts['f'] = r'(?:[-+]?(?:(?:\.[0-9]+)|(?:[0-9]+\.[0-9]+)|(?:[0-9]+\.?))'
_fmts['f'] += r'(?:[eE][-+]?[0-9]+)?)'  # optional exponent
_fmts['f'] += r'|(?:[-+]?[nN][aA][nN])'  # Not a Number (NaN)
_fmts['f'] += r'|(?:[-+]?[iI][nN][fF](?:[iI][nN][iI][tT][yY])?)'  # infinity
_fmts['e'] = _fmts['f']
_fmts['g'] = _fmts['f']

# strings and chars
_fmts['s'] = r'\S{n}'
_fmts['c'] = r'.{n}'
_fmts['r'] = _fmts['c']

for _key in frozenset(_fmts):
    _fmts[_key.encode('latin1')] = _fmts[_key]


# map specifiers to callables to cast to python types
_casts = dict()
_casts['i'] = functools.partial(int, base=0)
_casts['d'] = functools.partial(int, base=10)
_casts['u'] = _casts['d']
_casts['o'] = functools.partial(int, base=8)
_casts['x'] = functools.partial(int, base=16)
_casts['f'] = float
_casts['e'] = _casts['f']
_casts['g'] = _casts['f']
_casts['s'] = _return_input  # allows bytes and strs to both work
_casts['c'] = _casts['s']
_casts['r'] = eval  # evaluate as python statements

for _key in frozenset(_casts):
    _casts[_key.encode('latin1')] = _casts[_key]

class SF_Pattern(object):
    def __new__(cls, format):
        """Compile pattern and determine return type."""
        self = super(SF_Pattern, cls).__new__(cls)

        if isinstance(format, bytes):
            uni_str = format.decode('ISO-8859-1')  # decode to unicode
            trans_str = translate(uni_str)  # translate only works with unicode
            re_fmt = trans_str.encode('ISO-8859-1')  # encode back to bytes
            self._spec = _gbspec
        else:
            re_fmt = translate(format)
            self._spec = _gspec

        self._format = format
        self._re = cre = re.compile(re_fmt)

        if cre.groupindex and len(cre.groupindex) != cre.groups:
            raise RuntimeError('cannot mix mapped and unmapped specifiers')
        elif not cre.groupindex:
            self._retfunc = self._return_tuple
            self._type = tuple
        else:
            self._retfunc = self._return_dict
            self._type = dict

        self._casts = self._get_types()

        return self

    def __init__(self, format):
        """Dummy function."""
        raise RuntimeError('Cannot instantiate SF_Pattern objects directly')

    def _return_tuple(self, match):
        t = []
        for c, v in zip(self._casts, match.groups()):
            t.append(_casts[c](v))
        return tuple(t)

    def _return_dict(self, match):
        d = match.groupdict()
        for k, v in d.items():
            cast = self._casts[k]
            d[k] = _casts[cast](v)
        return d

    def _get_types(self):
        retval = None
        if isinstance(self.format, bytes):
            key = 'key'
            spec= 'spec'
        else:
            key = 'key'
            spec= 'spec'

        if self.type == dict:
            retval = {}
            for match in self._spec.finditer(self.format):
                d = match.groupdict()
                k = d[key]
                _log.debug(k)
                retval[k] = d[spec].lower()
        elif self.type == tuple:
            retval = []
            for match in self._spec.finditer(self.format):
                d = match.groupdict()
                retval.append(d[spec].lower())
            retval = tuple(retval)
        _log.debug(retval)
        return retval

    def scanf(self, string):
        """Scan input string according to format.

        Return either a tuple of values, or a dictionary, depending on how
        specifiers were formatted.
        """
        match = self._re.match(string)
        return self._retfunc(match) if match is not None else None

    @property
    def format(self):
        """The initial input scanf format string."""
        return self._format

    @property
    def re_format(self):
        """The regex pattern built from the input scanf format string."""
        return self._re.pattern

    @property
    def type(self):
        """The return type from scanf method.

        This will be either a tuple or a dictionary type object.
        """
        return self._type


class _SizedDict(dict):
    def __init__(self, max=128):
        self.__max = int(max)

    def __setitem__(self, key, val):
        # In Python 2, byte strings and unicode strings silently cast to,
        # eachother if their values are equal. In Python 3, this always fails.
        # To make sure Python 2 works like Python 3, we put the value and its
        # type in a tuple. Since tuples and class types are hashable, this
        # works as we want it to.
        if (type(key), key) not in self and len(self) + 1 > self.__max:
            self.popitem()

        return super(_SizedDict, self).__setitem__((type(key), key), val)

    def __getitem__(self, key):
        return super(_SizedDict, self).__getitem__((type(key), key))

_cache = _SizedDict()


def purge():
    """Clear the cache."""
    _cache.clear()


def compile(format):
    """Return a new scanf pattern object.

    Compiling a pattern is more efficient than using the module scanf function.
    However, previous formats are cached, so the cost is not too great in most
    circumstances.
    """
    try:
        return _cache[format]
    except KeyError:
        _cache[format] = retval = SF_Pattern.__new__(SF_Pattern, format)
        return retval


def _process_ws(s):
    # deal with common edge cases
    if not s:  # empty string
        return ''
    elif not s.strip():  # string of only white space
        return r'\s+'

    # split on whitespace, including leading and trailing
    split = []
    if len(s.lstrip()) < len(s):
        split.append('')

    split += s.split()

    if len(s.rstrip()) < len(s):
        split.append('')
    # _log.debug(split)

    # escape characters that might cause problems with regex
    for i in range(len(split)):
        split[i] = re.escape(split[i])

    # _log.debug(split)

    # replace whitespace to consume all whitespace
    join = r'\s+'.join(split)
    # _log.debug(join)

    return join


_width = {'c': ('{', '}'),
          'r': ('{1', '}?')}  # non-greedy

_no_width = {'c': '',
             'r': '*?'}  # non-greedy


def _process_spec(match):
    """Convert scanf specifier string into regex string."""
    # sfd = _gspec.match(s).groupdict()
    sfd = match.groupdict()

    if sfd['escape']:
        return r'\%'

    spec = _fmts[sfd['spec'].lower()]

    if sfd['width']:
        ends = _width.get(sfd['spec'], ('{', '}'))
        spec = spec.format(n=ends[0] + sfd['width'] + ends[1])
    else:
        reps = _no_width.get(sfd['spec'], '+')
        spec = spec.format(n=reps)

    if sfd['skip']:
        spec = '(?:' + spec + ')'  # non-capturing re group
    elif sfd['key']:
        spec = '(?P<' + sfd['key'] + '>' + spec + ')'  # keyword group
    else:
        spec = '(' + spec + ')'  # regular group

    # all other specs should consume leading whitespace
    if sfd['spec'] != 'c':
        spec = r'\s*' + spec

    return spec


def translate(format):
    strlist = []
    end_index = 0
    for match in _gspec.finditer(format):
        strlist.append(_process_ws(format[end_index:match.start()]))
        strlist.append(_process_spec(match))
        end_index = match.end()

    # deal with trailing characters
    if end_index != len(format):
        strlist.append(_process_ws(format[end_index:]))

    return ''.join(strlist)


def scanf(format, string):
    """Scan the provided string.

    Return either a tuple or a dictionary of parsed values, or None if the
    string did not conform to the format. For a format string with no formats,
    an empty tuple will be returned.
    """
    re_fmt = compile(format)
    result = re_fmt.scanf(string)
    _log.debug('%r <- %r = %r', format, string, result)
    return result


class _TestScanf(unittest.TestCase):
    def setUp(self):
        import math
        self.math = math

    def test_int_parsing(self):
        d = scanf('%(c)7c middle %(s)s end %(i)i', 'asdfghj middle str end 123')
        self.assertEqual(d['i'], 123)

        t = scanf('.*$ @ %d middle %s end %c', '.*$ @ 9 middle mo end ?')
        self.assertEqual(t[0], 9)

    def test_float_parsing(self):
        t = scanf(b'floats: %f %f %f %f', b'floats: 1.0 .1e20 -Inf Inf')
        self.assertEqual(t, (1.0, .1e20, float('-Inf'), float('Inf')))

        t = scanf(b'floats: %f %f %f %f', b'floats: -1.0 -.1e20 -NaN -Inf')
        self.assertTrue(self.math.isnan(t[2]))
        self.assertTrue(self.math.isinf(t[3]))
        self.assertLess(t[3], 0)

        t = scanf(b'floats: %f', b'floats: 1.')
        self.assertEqual(t[0], 1.)

        d = scanf(b'exp float %(float)f', b'exp float 12345.2345e2')
        self.assertEqual(d[b'float'], 12345.2345e2)

    def test_ws_ignore(self):
        # test weird spacing
        retval = scanf('%s middle %s end',
                       ' smog        middle \tbleck         end')
        self.assertIsNotNone(retval)

    def test_uni_and_bytes(self):
        retval = scanf('%s: unicode format', 'happy: unicode format')
        self.assertIsNotNone(retval)

        retval = scanf(b'%s: bytes format', b'happy: bytes format')
        self.assertIsNotNone(retval)


def _test():
    # translate('%(c)7c middle %(s)s end %(i)i')
    # return
    pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
    # _test()
