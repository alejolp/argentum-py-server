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

import constants

class ByteQueueError(Exception):
    pass

class ByteQueueInsufficientData(Exception):
    pass

class ByteQueue(object):
    """
    Clase para leer datos binarios y convertirlos a tipos de datos nativos.

    Basada e inspirada en la idea de Maraxus, implementada en morgoao.
    """

    __slots__ = ('data', 'pos', 'markpos', )
    def __init__(self, data=""):
        self.data = data
        self.pos = 0
        self.markpos = 0

    def __len__(self):
        return len(self.data) - self.pos

    def addData(self, data):
        self.data += data

    def commit(self):
        """
        Destruye los bytes del buffer interno liberando la memoria 
        desde el inicio del buffer hasta el puntero pos interno.
        
        Atencion: la funcion commit() no debe llamarse desde dentro
        de la misma ByteQueue ya que no es posible saber precisamente
        cuando hay que hacerlo.
        """

        assert self.pos >= 0 and self.markpos >= 0

        if self.pos != 0:
            self.data = self.data[self.pos:]
            self.pos = 0
            self.markpos = 0

    def mark(self):
        """
        Guarda la marca de posicion actual por si hace falta hacer rollback
        """

        self.markpos = self.pos

    def rollback(self):
        """
        Restaura la posicion de pos hacia la ultima guardada con mark.
        """

        self.pos = self.markpos

    def peekFmt(self, fmt):
        """Lee desde pos sin avanzar el puntero pos"""

        tam = struct.calcsize(fmt)

        if tam > len(self):
            raise ByteQueueInsufficientData()

        try:
            # La funcion buffer() es como un slice[a:b] pero 
            # no hace una copia de los datos.
            return struct.unpack(fmt, buffer(self.data, self.pos, tam))
        except struct.error, e:
            raise ByteQueueError(str(e))

    def read(self, fmt):
        """Lee desde pos avanzando el puntero pos"""

        ret = self.peekFmt(fmt)
        self.pos += struct.calcsize(fmt)
        return ret

    def readRaw(self, cant=None):
        """Lee cant bytes avanzando pos"""

        assert self.pos <= len(self.data)

        if cant is None:
            cant = len(self)
        elif len(self) < cant:
            raise ByteQueueInsufficientData()

        ret = self.data[self.pos:self.pos+cant]
        self.pos += cant

        return ret

    def writeFmt(self, fmt, *args):
        self.data += struct.pack(fmt, *args)

    def readInt8(self):
        return self.read('<B')[0]

    def readInt16(self):
        return self.read('<h')[0]

    def readInt32(self):
        return self.read('<l')[0]

    def readFloat(self):
        return self.read('<f')[0]

    def readDouble(self):
        return self.read('<d')[0]

    def readString(self):
        cant = self.readInt16()
        return self.readRaw(cant)

    def readStringFixed(self, cant):
        return self.readRaw(cant)

    def peekInt8(self):
        return self.peekFmt('<B')[0]

    def peekInt16(self):
        return self.peekFmt('<h')[0]

    def peekInt32(self):
        return self.peekFmt('<l')[0]

    def peekFloat(self):
        return self.peekFmt('<f')[0]

    def peekDouble(self):
        return self.peekFmt('<d')[0]

    def peekString(self):
        cant = self.peekInt16()
        if len(self) < (cant + 2):
            raise ByteQueueInsufficientData()
        return self.data[self.pos+2:self.pos+2+cant]

    def writeInt8(self, n):
        self.writeFmt('<B', n)

    def writeInt16(self, n):
        self.writeFmt('<h', n)
    
    def writeInt32(self, n):
        self.writeFmt('<l', n)

    def writeFloat(self, n):
        self.writeFmt('<f', n)

    def writeDouble(self, n):
        self.writeFmt('<d', n)

    def writeString(self, s):
        if type(s) is unicode:
            s = s.encode(constants.TEXT_ENCODING)
        self.writeInt16(len(s))
        self.data += s

    def writeStringFixed(self, s):
        if type(s) is unicode:
            s = s.encode(constants.TEXT_ENCODING)
        self.data += s

