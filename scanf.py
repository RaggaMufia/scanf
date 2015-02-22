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
_fmts = dict()
# integral numbers
_fmts['d'] = r'[-+]?[0-9]+'
_fmts['u'] = r'[0-9]{n}'
_fmts['o'] = r'[-+]?[0-7]+'
_fmts['x'] = r'[-+]?(?:0[xX])?[0-9A-Fa-f]+'
_fmts['i'] = r'[-+]?(?:(?:0[xX][0-9A-Fa-f]+)|(?:0[0-7]+)|(?:[0-9]+))'

# real numbers
_fmts['f'] = r'(?:[-+]?(?:(?:[0-9]+\.?)|(?:\.[0-9]+)|(?:[0-9]+\.[0-9]+)))'
_fmts['f'] += r'(?:[eE][-+]?[0-9]+)?'  # optional exponent
_fmts['f'] += r'|(?:[-+]?[nN][aA][nN])'  # Not a Number (NaN)
_fmts['f'] += r'|(?:[-+]?[iI][nN][fF](?:[iI][nN][iI][tT][yY])?)'  # infinity
_fmts['e'] = _fmts['f']
_fmts['g'] = _fmts['f']

# strings and chars
_fmts['s'] = r'\S{n}'
_fmts['r'] = _fmts['s']
_fmts['c'] = r'.{n}'


# map specifiers to callables to cast to python types
_calldict = dict()
_calldict['i'] = functools.partial(int, base=0)
_calldict['d'] = functools.partial(int, base=10)
_calldict['u'] = _calldict['d']
_calldict['o'] = functools.partial(int, base=8)
_calldict['x'] = functools.partial(int, base=16)
_calldict['f'] = float
_calldict['e'] = _calldict['f']
_calldict['g'] = _calldict['f']
_calldict['s'] = _return_input  # allows bytes and strs to both work
_calldict['c'] = _calldict['s']
_calldict['r'] = eval  # evaluate as python statements


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
    if not s:
        return ''
    elif not s.strip():
        return r'\s+'

    split = []
    if len(s.lstrip()) < len(s):
        split.append('')

    split += s.split()

    if len(s.rstrip()) < len(s):
        split.append('')
    # print(split)

    # escape characters that might cause problems with regex
    for j in range(len(split)):
        split[j] = re.escape(split[j])

    # print(split)

    # replace whitespace to consume all whitespace
    join = r'\s+'.join(split)
    # print(join)

    return join


def _process_spec(match):
    # sfd = _gspec.match(s).groupdict()
    sfd = match.groupdict()

    if sfd['escape']:
        return r'\%'

    spec = _fmts[sfd['spec'].lower()]

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


def old_translate(scanf_spec):
    """Translate a scanf format into a regular expression."""
    strlst = []

    split = _splitter.split(scanf_spec)
    for i, s in enumerate(split):
        if i % 2:
            strlst.append(_process_spec(s))
        else:
            strlst.append(_process_ws(s))

    return ''.join(strlst)


# TODO: also return a tuple or dictionary of types to cast to
def translate(format):
    strlist = []
    end_index = 0
    for match in _gspec.finditer(format):
        strlist.append(_process_ws(format[end_index:match.start()]))
        strlist.append(_process_spec(match))
        # print('%r' % match.group(0))
        end_index = match.end()
        # print('match end: %r' % (match.end()))
        # print('format end: %r' % (len(format)))

    if end_index != len(format):
        print('trailing characters: %r' % format[end_index:])
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
    print('%r <- %r = %r' % (format, string, result), file=sys.stderr)
    return result


def _test():
    # translate('%(c)7c middle %(s)s end %(i)i')
    # return

    scanf('.*$ @ %d middle %s end %c', '.*$ @ 9 middle mo end ?')
    scanf('%(c)7c middle %(s)s end %(i)i', 'asdfghj middle str end 1234')

    # test weird spacing
    scanf('%s middle %s end', ' smog        middle \tbleck         end')

    scanf('%s: unicode format', 'happy: unicode format')
    scanf(b'%s: bytes format', b'happy: bytes format')
    scanf(b'floats: %f %f %f %f', b'floats: 1.0 .1e20 NaN Inf')
    scanf(b'floats: %f %f %f %f', b'floats: -1.0 -.1e20 -NaN -Inf')
    scanf(b'exp float %(float)f', b'exp float 12345.2345e2')

if __name__ == '__main__':
    _test()
