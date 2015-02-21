"""A scanf implementation for Python under a liberal license.

Although regular expressions are available in python and are very powerful,
they can be overly verbose and complicated for certain types of simple use
cases. This module is designed to work with 2.7 or greater.
"""
from __future__ import unicode_literals, print_function, absolute_import

import re
import sys

# account for differences in in Python 2 and 3
if sys.version_info[0] < 3:
    from future_builtins import ascii, filter, hex, map, oct, zip
    bytes = str
    str = unicode
    range = xrange
else:
    pass

# spec with no groups
_spec = r'(%%|(?:%(?:\(\w+\))?\*?[0-9]*(?:h{1,2}|l{1,2}|j|z|t|L)?[duioxeEfFgGcrs]))'
_spec = re.compile(_spec)

# spec with groups
_gspec = r'(?P<escape>%%)|(?:%(?P<key>\(\w+\))?(?P<skip>\*)?(?P<width>[0-9]+)?(?:h{1,2}|l{1,2}|j|z|t|L)?(?P<spec>[duioxXeEfFgGcrs]))'
_gspec = re.compile(_gspec)


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
    """Returns a new scanf pattern object.

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


def translate(scanf_spec):
    """Translate a scanf format specifier into a regular expression string."""
    split = _spec.split(scanf_spec)
    print(split)

    strlst = []
    for i, s in enumerate(split):
        if i % 2 == 0:
            # split on whitespace
            split = s.split()
            print(split)

            # escape characters that might cause problems with regex
            for j in range(len(split)):
                split[j] = re.escape(split[j])
            print(split)

            # replace whitespace to consume all whitespace
            join = r'\s+'.join(split)
            print(join)
            strlst.append(join)
        else:
            sfd = _gspec.match(s).groupdict()
            print(sfd)

            if sfd['escape']:
                strlst.append(r'\%')
                continue

            if sfd['skip']:
                grpstrt = '(?:'
            elif sfd['key']:
                grpstrt = '(?<' + sfd['key'] + '>'
            else:
                grpstrt = '('

            if sfd['spec'] == 'i':
                spec = r'[-+]?(?:0[xX][\dA-Fa-f]+|0[0-7]*|\d+)'
            elif sfd['spec'] == 'd':
                spec = r'[-+]?\d+'
            elif sfd['spec'] == 'o':
                spec = r'[-+]?[0-7]+'
            elif sfd['spec'].lower() == 'x':
                spec = r'[-+]?(0[xX])?[\dA-Fa-f]+'

            if sfd['width']:
                pass
            strlst.append(s)

    print(strlst)
    return scanf_spec


def scan(fmt, string):
    """Scan the provided string.

    Return either a tuple or a dictionary of parsed values, or None if the
    string did not conform to the format."""
    re_fmt = compile(fmt)
    return re_fmt.scan(string)


def _test():
    translate('.punct*$uation @ %d middle %s almost end %c')
    translate('%d middle %s almost end %c')

if __name__ == '__main__':
    _test()
