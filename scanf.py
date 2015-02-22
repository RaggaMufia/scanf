"""A scanf implementation for Python under a liberal license.

Although regular expressions are available in python and are very powerful,
they can be overly verbose and complicated for certain types of simple use
cases. This module is designed to work with 2.7 or greater.
"""
from __future__ import unicode_literals, print_function, absolute_import

import re
import sys
import functools

# account for differences in in Python 2 and 3
if sys.version_info[0] < 3:
    from future_builtins import ascii, filter, hex, map, oct, zip
    bytes = str
    str = unicode
    range = xrange
else:
    pass

# spec with no groups for splitting
_splitter = r'(%%|(?:%(?:\(\w+\))?\*?[0-9]*(?:h{1,2}|l{1,2}|j|z|t|L)?[duioxeEfFgGcrs]))'
_splitter = re.compile(_splitter)

# spec with groups
_gspec = r'(?P<escape>%%)|(?:%(?:\((?P<key>\w+)\))?(?P<skip>\*)?(?P<width>[0-9]+)?(?:h{1,2}|l{1,2}|j|z|t|L)?(?P<spec>[duioxXeEfFgGcrs]))'
_gspec = re.compile(_gspec)


def _return_input(obj):
    return obj


def _return_tuple(match):
    return match.groups()


def _return_dict(match):
    return match.groupdict()


# Map specifiers to their regex. Leave num repetitions to be filled in later.
_fmtdict = dict()
_fmtdict['i'] = r'[-+]?(?:0[xX][\dA-Fa-f]{n}|0[0-7]*|\d{n})'
_fmtdict['d'] = r'[-+]?\d{n}'
_fmtdict['u'] = r'\d{n}'
_fmtdict['o'] = r'[-+]?[0-7]{n}'
_fmtdict['x'] = r'[-+]?(?:0[xX])?[\dA-Fa-f]{n}'
_fmtdict['e'] = r'(?:[-+]?\d{n}(?:\.\d*)?)|'
_fmtdict['e'] += r'(?:\.\d{n})(?:[eE][-+]?\d{n})|'
_fmtdict['e'] += r'(?:[-+]?[nN][aA][aN])|'  # Not a Number
_fmtdict['e'] += r'(?:[-+]?[iI][nN][fF](?:[iI][nN][iI][tT][yY])?)'  # infinity
_fmtdict['f'] = _fmtdict['e']
_fmtdict['g'] = _fmtdict['e']
_fmtdict['s'] = r'\S{n}'
_fmtdict['r'] = _fmtdict['s']
_fmtdict['c'] = r'.{n}'


# map specifiers to callables to cast to python types
_calldict = dict()
_calldict['i'] = int
_calldict['d'] = functools.partial(int, base=10)
_calldict['u'] = _calldict['d']
_calldict['o'] = functools.partial(int, base=8)
_calldict['x'] = functools.partial(int, base=16)
_calldict['e'] = float
_calldict['f'] = _calldict['e']
_calldict['g'] = _calldict['e']
_calldict['s'] = _return_input  # allows bytes and strs to both work
_calldict['c'] = _calldict['s']
_calldict['r'] = eval


class SF_Pattern(object):
    def __new__(cls, format):
        """Compile pattern and determine return type."""
        self = super(SF_Pattern, cls).__new__(cls)

        if isinstance(format, bytes):
            uni_str = format.decode('ISO-8859-1')  # decode to unicode
            trans_str = translate(uni_str)  # translate only works with unicode
            re_fmt = trans_str.encode('ISO-8859-1')  # encode back to bytes
        else:
            re_fmt = translate(format)
        self._format = format
        self._re_format = re_fmt

        self._re = cre = re.compile(re_fmt)

        if cre.groupindex and len(cre.groupindex) != cre.groups:
            raise RuntimeError('cannot mix mapped and unmapped specifiers')
        elif not cre.groupindex:
            self._retfunc = _return_tuple
            self._type = tuple
        else:
            self._retfunc = _return_dict
            self._type = dict

        return self

    def __init__(self, format):
        """Dummy function."""
        raise RuntimeError('Cannot instantiate SF_Pattern objects directly')

    def scanf(self, string):
        """Scan input string according to format.

        Return either a tuple of values, or a dictionary, depending on how
        specifiers were formatted.
        """
        match = self._re.match(string)
        if match is not None:
            return self._retfunc(match)

    @property
    def format(self):
        """The initial input scanf format string."""
        return self._format

    @property
    def re_format(self):
        """The regex format string built from the input scanf format string."""
        return self._re_format

    @property
    def type(self):
        """The return type from scan method.

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
        if key not in self and len(self) + 1 > self.__max:
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
    # split on whitespace
    split = s.split()

    # escape characters that might cause problems with regex
    for j in range(len(split)):
        split[j] = re.escape(split[j])

    # replace whitespace to consume all whitespace
    join = r'\s+'.join(split)

    return join


def _process_spec(s):
    sfd = _gspec.match(s).groupdict()

    if sfd['escape']:
        return r'\%'

    spec = _fmtdict[sfd['spec'].lower()]

    if sfd['width']:
        if sfd['spec'] == 'c':
            spec = spec.format(n='{' + sfd['width'] + '}')
        else:
            spec = spec.format(n='{1,' + sfd['width'] + '}')
    elif sfd['spec'] == 'c':
        spec = spec.format(n='')
    else:
        spec = spec.format(n='+')

    if sfd['skip']:
        spec = '(?:' + spec + ')'
    elif sfd['key']:
        spec = '(?P<' + sfd['key'] + '>' + spec + ')'
    else:
        spec = '(' + spec + ')'

    # all other specs should consume leading whitespace
    if sfd['spec'] != 'c':
        spec = r'\s*' + spec

    return spec


# TODO: also return a tuple or dictionary of types to cast to
def translate(scanf_spec):
    """Translate a scanf format into a regular expression."""
    strlst = []

    split = _splitter.split(scanf_spec)
    for i, s in enumerate(split):
        if i % 2:
            strlst.append(_process_spec(s))
        else:
            strlst.append(_process_ws(s))

    return ''.join(strlst)


def scanf(format, string):
    """Scan the provided string.

    Return either a tuple or a dictionary of parsed values, or None if the
    string did not conform to the format. For a format string with no formats,
    an empty tuple will be returned.
    """
    re_fmt = compile(format)
    return re_fmt.scanf(string)


def _test():
    print(scanf('.*$ @ %d middle %s end %c', '.*$ @ 9 middle mo end ?'))
    print(scanf('%(c)7c middle %(s)s end %(d)4d', 'asdfghj middle str end 1234'))
    # print(scanf('    words @ %d middle %s almost end %c'))
    # print(scanf('    some escapes %% and some other stuff %d'))
    # print(scanf('try %e some %f floats %g'))

    print(scanf('%s: simple format', 'happy: simple format'))
    print(scanf(b'%s: bytes format', b'happy: bytes format'))
    print(scanf(b'parse a float %(float)f', b'parse a float 12345.2345'))

if __name__ == '__main__':
    _test()
