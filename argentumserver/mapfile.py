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
Funciones y clases para cargar un mapa desde los map/inf/dat a memoria.

La idea es mantener este módulo lo más limpio posible. Acá solamente se cargan
los datos desde los archivos, para inicializar los NPCs y otras yerbas hacerlo
desde el que llama.
"""

import os
from ConfigParser import NoOptionError

from bytequeue import ByteQueue
from util import MyConfigParser
from constants import MAP_SIZE_X, MAP_SIZE_Y

       
class MapFileTile(object):
    __slots__ = ('blocked', 'layers', 'trigger', 'exit', 'npc', 'obj')
    def __init__(self):
        self.blocked = False
        self.layers = [None] * 4
        self.trigger = 0
        self.exit = None
        self.npc = None
        self.obj = None

    def __repr__(self):
        return "MapFileTile<" + ', '.join(["%s=%s" % (x, str(getattr(self, x))) for x in MapFileTile.__slots__]) + ">"

    __str__ = __repr__
    
    def __unicode__(self):
        return unicode(str(self))

class MapFile(object):
    __slots__ = ('mapNum', 'tiles', 'opts', 'mapDesc', 'mapVers', 'mapCrc', 'mapMagicWord')
    def __init__(self, mapNum):
        self.mapNum = mapNum
        self.tiles = []
        self.opts = {}

    def __getitem__(self, p):
        x, y = p

        assert x >= 1 and x <= MAP_SIZE_X
        assert y >= 1 and y <= MAP_SIZE_Y

        return self.tiles[(x - 1) + (y - 1) * MAP_SIZE_X]

    def __str__(self):
        return "MapFile<n=%d>" % self.n

def loadMapFile(mapNum, fileNameBasePath):
    """Carga un mapa"""


    fileNameMap = os.path.join(fileNameBasePath, 'Mapa%d.map' % mapNum)
    fileNameInf = os.path.join(fileNameBasePath, 'Mapa%d.inf' % mapNum)
    fileNameDat = os.path.join(fileNameBasePath, 'Mapa%d.dat' % mapNum)

    # .map
    with open(fileNameMap, 'rb') as f:
        mapData = ByteQueue(f.read())

    # .inf
    with open(fileNameInf, 'rb') as f:
        infData = ByteQueue(f.read())

    # .dat
    datData = MyConfigParser()
    datData.read([fileNameDat])

    # Map object.
    mf = MapFile(mapNum)

    # Map header
    mf.mapVers = mapData.readInt16()
    mf.mapDesc = mapData.readStringFixed(255)
    mf.mapCrc = mapData.readInt32()
    mf.mapMagicWord = mapData.readInt32()

    # Dat data
    datSection = "Mapa%d" % mapNum

    mapOptions = ['Name', 'MusicNum', 'StartPos', 'MagiaSinEfecto', 
        'InviSinEfecto', 'ResuSinEfecto', 'OcultarSinEfecto', 
        'InvocarSinEfecto', 'NoEncriptarMP', 'RoboNpcsPermitido', 'Pk', 
        'Terreno', 'Zona', 'Restringir', 'BACKUP']

    # Carga las opciones del mapa que están dentro del .dat.
    # Si una opcion no está la guarda como None.

    for opt in mapOptions:
        try:
            mf.opts[opt] = datData.get(datSection, opt)
        except NoOptionError, e:
            mf.opts[opt] = None

    # Casos especiales: startpos es una 3-tupla.

    try:
        if mf.opts['StartPos'] is not None:
            mf.opts['StartPos'] = tuple([int(x) \
                for x in mf.opts['StartPos'].split("-")])
    except ValueError, e:
        pass

    # ???
    mapData.readDouble()

    # Inf header
    # FIXME: ???
    infData.readDouble()
    infData.readInt16()

    for y in xrange(1, MAP_SIZE_Y+1):
        for x in xrange(1, MAP_SIZE_X+1):
            tile = MapFileTile()

            tileFlags = mapData.readInt8()

            tile.blocked = bool(tileFlags & 1)

            # Graphics.
            tile.layers[0] = mapData.readInt16()
            if tileFlags & 2:
                tile.layers[1] = mapData.readInt16()
            if tileFlags & 4:
                tile.layers[2] = mapData.readInt16()
            if tileFlags & 8:
                tile.layers[3] = mapData.readInt16()

            # Trigger.
            if tileFlags & 16:
                tile.trigger = mapData.readInt16()

            tileFlags = infData.readInt8()

            # Exit.
            if tileFlags & 1:
                # Map, X, Y.
                tile.exit = (infData.readInt16(), infData.readInt16(), \
                    infData.readInt16())

            # NPC.
            if tileFlags & 2:
                tile.npc = infData.readInt16()

            # Obj.
            if tileFlags & 4:
                tile.obj = (infData.readInt16(), infData.readInt16())

            mf.tiles.append(tile)

    return mf

