# -*- coding: utf-8 -*-

"""
    AONX Server - Pequeño servidor de Argentum Online.
    Copyright (C) 2011 Alejandro Santos <alejolp@alejolp.com.ar>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""
Aca va todo lo que no encaja en otros modulos.
"""

from ConfigParser import SafeConfigParser

def debug_print(*args):
    print "[debug] ",
    for a in args:
        print a,
    print

def between(x, a, b):
    return x >= a and x <= b

def espiral(pos, lim=100):
    """Genera un patron de busqueda en forma de espiral."""
    x, y = pos

    yield (x, y)

    d = 1
    s = 1

    while lim > 0:
        for a in xrange(d):
            x = x + s
            lim = lim - 1
            yield (x, y)
            if lim == 0: return

        for a in xrange(d):
            y = y + s
            lim = lim - 1
            yield (x, y)
            if lim == 0: return

        s = s * -1
        d = d + 1

class MyConfigParser(SafeConfigParser):
    def read(self, *args, **kwargs):
        ret = SafeConfigParser.read(self, *args, **kwargs)

        secs = list(self.sections())
        for s in secs:
            items = self.items(s)
            self.remove_section(s)

            s = s.lower()
            self.add_section(s)
            for i in items:
                self.set(s, i[0].lower(), i[1])

        return ret

    def get(self, section, option, *args, **kwargs):
        return SafeConfigParser.get(self, section.lower(), option.lower(), *args, **kwargs)

    def has_section(self, section):
        return SafeConfigParser.has_section(self, section.lower())

    def getint(self, section, option):
        val = self.get(section, option)
        if "'" in val:
            val = val.split("'", 1)[0]
        return int(val)

class positiverolist(object):
    __slots__ = ('data',)
    def __init__(self, data):
        self.data = data

    def __getitem__(self, i):
        if i < 0:
            raise IndexError('negative')
        return self.data[i]

    def __setitem__(self, i, v):
        raise TypeError('read only list')

