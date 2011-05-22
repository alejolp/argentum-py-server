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

import os, sys, datetime, time, gc, re, collections
from ConfigParser import SafeConfigParser

from aoprotocol import clientPackets, serverPackets, clientPacketsFlip
from bytequeue import ByteQueue, ByteQueueError, ByteQueueInsufficientData
from aocommands import *
from util import debug_print
from constants import *

import mapfile, datfile, aoprotocol, corevars

try:
    import twisted
except ImportError:
    print "Es necesario instalar python-twisted"
    sys.exit(1)

if sys.platform == 'linux2': # yeah!
    # En Linux usamos el reactor epoll() que es lo más.
    from twisted.internet import epollreactor
    epollreactor.install()
elif sys.platform == 'win32': # rulz!
    # En Windows usamos el reactor IOCP que es lo más.
    from twisted.internet import iocpreactor
    iocpreactor.install()

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, task

# Singletons

cmdDecoder = None       # Handler para recibir paquetes de los clientes
ServerConfig = None

# ---

class AoProtocol(Protocol):
    """Interfaz con Twisted para el socket del cliente."""

    def __init__(self):
        # Buffers de datos
        self._ao_inbuff = ByteQueue()
        self.outbuf = ByteQueue()

        self._peer = None

        # En medio de una desconexion.
        self._ao_closing = False
        self.lastHandledPacket = int(time.time())

        # la instancia de Player se crea cuando el login es exitoso.
        self.player = None

        # Wrapper para serializar comandos en outbuf.
        self.cmdout = ServerCommandsEncoder(self)

    def dataReceived(self, data):
        if not self._ao_closing:
            self._ao_inbuff.addData(data)
            self._handleData()

    def connectionMade(self):
        debug_print("connectionMade")

        if not gameServer.connectionsLimitReached():
            gameServer.connectionMade(self)
        else:
            self.loseConnection()

    def connectionLost(self, reason):
        debug_print("connectionLost")

        # Todo el codigo de limpieza de la conexion debe ir en loseConnection.

        if not self._ao_closing:
            self.loseConnection()

    def getPeer(self):
        # host, port, type
        if self._peer is None:
            self._peer = self.transport.getPeer()
        return self._peer

    def _handleData(self):
        try:
            cmdDecoder.handleData(self)
        except CriticalDecoderException, e:
            debug_print("CriticalDecoderException")
            self.loseConnection()

    def sendData(self, data):
        self.transport.write(data)

    def flushOutBuf(self):
        self.sendData(self.outbuf.readRaw())

    def loseConnection(self):
        if not self._ao_closing:
            debug_print("loseConnection")
            self._ao_closing = True
            self.cmdout = None
            gameServer.connectionLost(self)

            self.transport.loseConnection()
            if self.player is not None:
                self.player.cmdout = None
                self.player.quit()

class AoProtocolFactory(Factory):
    protocol = AoProtocol

class GameServer(object):
    def __init__(self):
        self._players = set()
        self._playersByName = {}
        self._playersByChar = [None]

        self._connections = set()
        self._ipsCounter = {}

        self._nextCharIdx = collections.deque()
        self._playersLoginCounter = 0

    def playersLimitReached(self):
        playersLimit = ServerConfig.getint('Core', 'PlayersCountLimit')
        if len(self._players) >= playersLimit:
            debug_print("Limite de jugadores alcanzado: %d" % playersLimit)
            return True
        return False

    def connectionsLimitReached(self):
        connLimit = ServerConfig.getint('Core', 'ConnectionsCountLimit')
        if len(self._connections) >= connLimit:
            debug_print("Limite de conexiones alcanzado: %d" % connLimit)
            return True
        return False

    def playerJoin(self, p):
        self._players.add(p)
        self._playersByName[p.playerName.lower()] = p

        charIdx = self.nextCharIdx()
        self._playersByChar[charIdx]
        p.charIdx = charIdx
        p.userIdx = 0

        self._playersLoginCounter += 1

    def playerLeave(self, p):
        self._players.remove(p)
        del self._playersByName[p.playerName.lower()]

        self.freeCharIdx(p.charIdx)
        p.charIdx = None

    def playerRename(self, p):
        """Warning: O(n)"""
        for k, v in self._playersByName.items():
            if v == p:
                oldName = k
                break
        del self._playersByName[oldName]
        self._playersByName[p.playerName.lower()] = p

    def connectionMade(self, c):
        self._connections.add(c)

        ip = c.getPeer().host
        self._ipsCounter[ip] = self._ipsCounter.get(ip, 0) + 1

        if self._ipsCounter[ip] > ServerConfig.getint('Core', 'ConnectionsCountLimitPerIP'):
            c.loseConnection()

    def connectionLost(self, c):
        if c in self._connections:
            self._connections.remove(c)

            ip = c.getPeer().host
            self._ipsCounter[ips] = self._ipsCounter[ips] - 1
            assert self._ipsCounter[ips] >= 0

            if self._ipsCounter[ips] == 0:
                del self._ipsCounter[ips]

    def playerByName(self, playerName):
        return self._playersByName[playerName.lower()]

    def playersCount(self):
        assert len(self._players) == len(self._playersByName)
        assert len(self._players) == len(self._playersByChar)

        return len(self._players)

    def nextCharIdx(self):
        if len(self._nextCharIdx):
            return self._nextCharIdx.popleft()
        else:
            self._playersByChar.append(None)
            return len(self._playersByChar) - 1

    def freeCharIdx(self, n):
        self._nextCharIdx.append(n)
        self._playersByChar[n] = None

    def playersList(self):
        return list(self._players)

    def connectionsList(self):
        return list(self._connections)

class GameMap(object):
    """Un mapa"""

    def __init__(self, mapNum):
        self.players = set()
        self.mapNum = mapNum
        self.mapFile = mapfile.loadMapFile(mapNum, \
            ServerConfig.get('Core', 'MapsFilesPath'))

    def playerJoin(self, p):
        self.player.add(p)

    def playerLeave(self, p):
        self.players.remove(p)

class GameMapList(object):
    def __init__(self, mapCount):
        self.maps = [None] * (mapCount + 1)
    
    def __getitem__(self, n):
        if self.maps[n] is None:
            self.maps[n] = GameMap(n)
        return self.maps[n]

# Timer

def onTimer1():
    """Este timer se ejecuta cada un segundo."""
    pass

def onTimer10():
    """Este timer se ejecuta cada 10 segundos."""

    t = int(time.time())

    # Timeouts de paquetes

    for c in gameServer.connectionsList():
        if c.player is None:
            maxTime = TIMEOUT_NOT_LOGGED
        else:
            maxTime = TIMEOUT_YES_LOGGED

        if t - c.lastHandledPacket > maxTime:
            c.loseConnection()

def onTimer60():
    """Este timer se ejecuta cada 60 segundos."""
    pass

# Main

def loadMaps():
    mapCount = ServerConfig.getint('Core', 'MapCount')
    mapLoadingMode = ServerConfig.get('Core', 'MapLoadingMode').lower()

    corevars.mapData = GameMapList(mapCount)

    if mapLoadingMode == "full":
        print "Cargando mapas... "

        for x in xrange(1, 290+1):
            sys.stdout.write(str(x) + " ")
            sys.stdout.flush()
            mapData[x]

        print

        # Piedad, oh, piedad.
        gc.collect()
    elif mapLoadingMode == "lazy":
        print "Carga de mapas en modo Lazy; se cargaran bajo demanda."
    else:
        raise Exception("Opcion no reconocida: MapLoadingMode=" \
            + mapLoadingMode)

def loadFiles():
    datFilesPath = ServerConfig.get('Core', 'DatFilesPath')
    
    # Objs.
    corevars.objData = datfile.loadObjDat(os.path.join(datFilesPath, 'obj.dat'))
    corevars.npcData = datfile.loadNPCsDat(os.path.join(datFilesPath, 'NPCs.dat'))
    corevars.hechData = datfile.loadHechizosDat(os.path.join(datFilesPath, \
        'Hechizos.dat'))

    # Nombres prohibidos.
    corevars.forbiddenNames = set([x.strip().lower() for x in \
        open(os.path.join(datFilesPath, 'NombresInvalidos.txt'))])

def loadServerConfig():
    global ServerConfig

    corevars.ServerConfig = ServerConfig = SafeConfigParser()
    ServerConfig.read([sys.argv[1]])

def initServer():
    global cmdDecoder, gameServer

    loadServerConfig()

    cmdDecoder = ClientCommandsDecoder()
    gameServer = corevars.gameServer = GameServer()

def runServer():
    listenPort = ServerConfig.getint('Core', 'ListenPort')
    reactor.listenTCP(listenPort, AoProtocolFactory())

    task.LoopingCall(onTimer1).start(1)
    task.LoopingCall(onTimer10).start(10)
    task.LoopingCall(onTimer60).start(60)

    print "Escuchando en el puerto %d, reactor: %s" % ( \
        listenPort, reactor.__class__.__name__)
    print "Para cerrar el servidor presionar Control-C."

    reactor.run()

def main():
    print
    print "Iniciando AONX Server ..."
    print

    # Acentos y caracteres especiales omitidos en todos los print para
    # mayor compatibilidad con terminales.

    if sys.version_info[:2] < (2, 6):
        print "Se requiere Python 2.6+, version actual: "+str(sys.version_info)
        sys.exit(1)

    if len(sys.argv) < 2:
        print "Se debe indicar el archivo de configuracion a usar como primer parametro de la aplicacion. Ejemplo: runserver.py serversettings.txt"
        sys.exit(1)

    startTime = datetime.datetime.now()

    #

    initServer()
    loadFiles()
    loadMaps()

    #

    print
    print "Iniciado. Tiempo de inicio del servidor: " + str(datetime.datetime.now() - startTime)
    print

    runServer()

