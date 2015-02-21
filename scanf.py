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
_calldict['s'] = lambda val: val  # allows bytes and strs to both work
_calldict['c'] = _calldict['s']
_calldict['r'] = eval

class SF_Pattern(object):
    def __new__(cls, fmt):
        self = super(SF_Pattern, cls).__new__(cls)
        self._type = None
        return self

    def __init__(self, fmt):
        raise RuntimeError('SF_Pattern objects cannot be instantiated directly')

    def scan(self, string):
        pass

    @property
    def type(self):
        """The return type from scan method.

        This will be either a tuple or a dictionary type object.
        """
        return self._type


def compile(fmt):
    """Return a new scanf pattern object.

    Compiling a pattern is more efficient than using the module scan function.
    """
    return SF_Pattern.__new__(fmt)


# lifted from fnmatch in the standard lib
def _compile_pattern(pat):
    """Compile a scanf format specifer into a regex pattern object."""
    if isinstance(pat, bytes):
        pat_str = str(pat, 'ISO-8859-1')
        res_str = translate(pat_str)
        res = bytes(res_str, 'ISO-8859-1')
    else:
        res = translate(pat)
    return re.compile(res).match


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
    print(sfd)

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
        spec = '(?<' + sfd['key'] + '>' + spec + ')'
    else:
        spec = '(' + spec + ')'

    # all other specs should consume leading whitespace
    if sfd['spec'] != 'c':
        spec = r'\s*' + spec

    return spec


def translate(scanf_spec):
    """Translate a scanf format into a regular expression."""
    strlst = []

    split = _splitter.split(scanf_spec)
    for i, s in enumerate(split):
        if i % 2:
            strlst.append(_process_spec(s))
        else:
            strlst.append(_process_ws(s))

    print(scanf_spec)
    print(strlst)
    print(''.join(strlst))

    return ''.join(strlst)


def scan(fmt, string):
    """Scan the provided string.

    Return either a tuple or a dictionary of parsed values, or None if the
    string did not conform to the format. For a format string with no formats,
    an empty tuple will be returned.
    """
    re_fmt = compile(fmt)
    return re_fmt.scan(string)


def _test():
    translate('.punct*$uation @ %d middle %s almost end %c')
    translate('%(singlechar)7c middle %(s)s almost end %(d)4d')
    translate('    words @ %d middle %s almost end %c')
    translate('    some escapes %% and some other stuff %d')
    translate('try %e some %f floats %g')

if __name__ == '__main__':
    _test()
