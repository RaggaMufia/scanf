"""A scanf implementation for Python under a liberal license.

Although regular expressions are available in python and are very powerful,
they can be overly verbose and complicated for certain types of simple use
cases. This module is designed to work with 2.7 or greater.
"""
from __future__ import unicode_literals, print_function, absolute_import

import re

# account for difference in bytes and strings in py2 and py3
try:
    unicode
except NameError:
    pass
else:
    bytes = str
    str = unicode

# spec with no groups
spec = (r'(%%|(?:%(?:\([a-zA-Z_]\w*\))?[#]?[0]?[-]?[ ]?[+]?'
        r'(?:[0-9]+|[*])?(?:[.][0-9]+|[*])?[diouxXeEfFgGcrs]))')

# spec with groups
gspec = r'(?P<escaped_percent>%%)|(?:%(?P<kw>\([a-zA-Z_]\w*\))?[#]?[0]?[-]?[ ]?[+]?(?:[0-9]+|[*])?(?:[.][0-9]+|[*])?[diouxXeEfFgGcrs])'


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
        """Return the return type from scan method.

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
    return scanf_spec


def scan(format, string):
    """Return either a tuple or a dictionary of parsed values."""
    pass
