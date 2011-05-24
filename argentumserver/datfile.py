#!/usr/bin/env python
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
Conjunto de funciones para leer archivos .DAT en formato estándar INI, usando
la librería ConfigParser de Python.

Los DAT originales de Argentum (morgoao) rompen con ConfigParser ya
que ésta es mucho más estricta al validar y parsear los archivos.

Entonces, dentro del directorio "tools" que acompaña al presente código 
existe un pequeño programa llamado "datfixer.py" para corregir los DATs y que 
ConfigParser los pueda entender.
"""

import ConfigParser

from util import MyConfigParser, positiverolist

class ObjItem(object):
    __slots__ = ('Name', 'GrhIndex', 'ObjType', 'Agarrable', 'Valor', \
        'Crucial')
    __tipos__ = (str, int, int, bool, int, bool,)
    def __init__(self):
        pass

class NPCDat(object):
    __slots__ = ('Name', 'NpcType', 'Desc', 'Head', 'Body', 'Heading', )
    __tipos__ = (str, int, str, int, int, int)
    def __init__(self):
        pass

class HechizoDat(object):
    __slots__ = ('Nombre', 'Desc', 'PalabrasMagicas')
    __tipos__ = (str, str, str)
    def __init__(self):
        pass

def loadObjDat(fileName):
    parser = MyConfigParser()
    parser.read([fileName])
    
    maxObj = parser.getint('INIT', 'NumOBJs')
    return loadDatFile(parser, maxObj, ObjItem, ObjItem.__slots__, \
        ObjItem.__tipos__, 'OBJ%d')

def loadNPCsDat(fileName):
    parser = MyConfigParser()
    parser.read([fileName])
    
    maxNPCs = parser.getint('INIT', 'NumNPCs')
    return loadDatFile(parser, maxNPCs, NPCDat, NPCDat.__slots__, \
        NPCDat.__tipos__, 'NPC%d')
   
def loadHechizosDat(fileName):
    parser = MyConfigParser()
    parser.read([fileName])
    
    maxHech = parser.getint('INIT', 'NumeroHechizos')
    return loadDatFile(parser, maxHech, HechizoDat, HechizoDat.__slots__, \
        HechizoDat.__tipos__, 'HECHIZO%d')

def loadDatFile(parser, maxIdx, datItemClass, attrsList, tiposList, headerStr):
    """
    Lee un .DAT en formato estándar.
    """

    datItemList = [None] * (maxIdx + 1)

    for objIdx in xrange(1, maxIdx+1):
        if not parser.has_section(headerStr % objIdx):
            continue

        datItemList[objIdx] = o = datItemClass()

        # FIXME: Esto del casting de tipos esta medio medio... revisarlo.

        for attr, t in zip(attrsList, tiposList):
            try:
                v = t(parser.get(headerStr % objIdx, attr))
            except ConfigParser.NoOptionError, e:
                v = None

            setattr(o, attr, v)

    return positiverolist(datItemList)

