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

import struct

class ByteQueueError(Exception):
    pass

class ByteQueueInsufficientData(Exception):
    pass

class ByteQueue(object):
    __slots__ = ('data', 'pos', 'markpos', )
    def __init__(self):
        self.data = ""
        self.pos = 0
        self.markpos = 0

    def __len__(self):
        return len(self.data) - self.pos

    def addData(self, data):
        self.data += data

    def commit(self):
        assert self.pos >= 0 and self.markpos >= 0

        if self.pos != 0:
            self.data = self.data[self.pos:]
            self.pos = 0
            self.markpos = 0

    def mark(self):
        self.markpos = self.pos

    def rollback(self):
        self.pos = self.markpos

    def read(self, fmt):
        tam = struct.calcsize(fmt)
        if tam > len(self):
            raise ByteQueueInsufficientData()

        try:
            # La funcion buffer() es como un slice[a:b] pero 
            # no hace una copia de los datos.
            ret = struct.unpack(fmt, buffer(self.data, self.pos, tam))
            self.pos += tam
            return ret
        except struct.error, e:
            #raise ByteQueueInsufficientData()
            raise ByteQueueError(str(e))

    def readRaw(self, cant=None):
        assert self.pos <= len(self.data)

        if cant is None:
            cant = len(self)
        elif len(self) < cant:
            raise ByteQueueInsufficientData()

        ret = self.data[self.pos:self.pos+cant]
        self.pos -= cant

        return ret

    def readInt8(self):
        return self.read('<b')[0]

    def readInt16(self):
        return self.read('<h')[0]

    def readInt32(self):
        return self.read('<l')[0]

    def readString(self):
        cant = self.readInt16()
        return self.readRaw(cant)

    def peekFmt(self, fmt):
        tam = struct.calcsize(fmt)

        if tam > len(self):
            raise ByteQueueInsufficientData()

        return struct.unpack(fmt, buffer(self.data, self.pos, tam))

    def peekInt8(self):
        return self.peekFmt('<b')[0]

    def peekInt16(self):
        return self.peekFmt('<h')[0]

    def peekInt32(self):
        return self.peekFmt('<l')[0]

    def writeFmt(self, fmt, *args):
        self.data += struct.pack(fmt, *args)

    def writeInt8(self, n):
        self.writeFmt('<b', n)

    def writeInt16(self, n):
        self.writeFmt('<h', n)
    
    def writeInt32(self, n):
        self.writeFmt('<l', n)

    def writeString(self, s):
        if type(s) is unicode:
            s = s.encode('utf-8')
        self.writeInt16(len(s))
        self.data += s

