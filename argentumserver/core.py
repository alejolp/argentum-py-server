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

import sys, datetime, gc, re
from ConfigParser import SafeConfigParser

from aoprotocol import clientPackets, serverPackets, clientPacketsFlip
from bytequeue import ByteQueue, ByteQueueError, ByteQueueInsufficientData
import mapfile

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

# ---

WELCOME_MSG = "Bienvenido al servidor AONX - visite www.aonx.com.ar"

# ---

VALID_PLAYER_NAME = r'^[ a-zA-Z]+$'

def isValidPlayerName(name):
    """
    Un nombre válido:

    - Tiene entre 3 y 32 caracteres.
    - No tiene dos espacios consecutivos.
    - No tiene espacios al inicio ni final.
    - Solo esta compuesto por letras y espacios.
    - No lleva acentos ni simbolos especiales.

    Nombres inválidos:

    - "Un"
    - "Juan  Pedro"
    - " Juan"
    - "Juan!"
    - "Raúl"

    Nombres válidos:

    - "Juan Pedro Marcos De Los Palotes"
    - "Raul"
    """

    if len(name) > 32 or len(name) < 3:
        return False

    if '  ' in name or name.strip() != name:
        return False

    if re.match(VALID_PLAYER_NAME, name) is None:
        return False

    return True

# ---

def debug_print(*args):
    print "[debug] ",
    for a in args:
        print a,
    print

class CommandsDecoderException(Exception):
    """Faltan datos para decodificar un comando del cliente"""
    pass

class CriticalDecoderException(Exception):
    """Error critico en los datos del cliente; cerrar la conexion"""
    pass

class ClientCommandsDecoder(object):
    """Conjunto de funciones para decodificar los datos que envia un cliente"""

    def __init__(self):
        self.cmds = {
            clientPackets['LoginExistingChar'] : self.handleCmdLogin,
#            clientPackets['Talk']: self.handleCmdTalk,
#            clientPackets['Walk']: self.handleCmdWalk,
            clientPackets['Online']: self.handleCmdOnline,
            }

    def handleData(self, prot):
        buf = prot._ao_inbuff
        
        """
        Los comandos consumen los bytes del buffer de entrada, si faltan
        datos se dispara un CommandsDecoderException o ByteQueueError.
        """

        try:
            try:
                while len(buf) > 0:
                    cmd = buf.peekInt8()
                    if cmd not in self.cmds:
                        debug_print("cmd not in cmds:", cmd, \
                            "should be:", clientPacketsFlip.get(cmd, '?'))
                        raise CriticalDecoderException()

                    # Marca la posicion actual por si hay que hacer rollback.
                    buf.mark()

                    # Invoca al handler del comando cmd.
                    self.cmds[cmd](prot, buf)

                # La operacion commit() destruye los datos del buffer,
                # por lo que para llamarla tengo que estar seguro
                # que se leyeron todos los datos del comando actual.
                #
                # Llamarla al final de cada comando puede llegar a ser
                # lento si hay varios comandos encolados.

                buf.commit()

            except:
                buf.rollback()
                raise
        except ByteQueueError, e:
            pass
            debug_print("ByteQueueError", e)
        except ByteQueueInsufficientData, e:
            pass
        except CommandsDecoderException, e:
            pass
            # debug_print("CommandsDecoderException")
        except Exception, e:
            debug_print("handleData Exception: ", e)
            raise

    def handleCmdLogin(self, prot, buf):
        if prot.player is not None:
            # Estado incorrecto
            raise CriticalDecoderException()

        cmd = buf.readInt8()

        playerName = buf.readString()
        playerPass = buf.readString()
        playerVers = '%d.%d.%d' % (buf.readInt8(), buf.readInt8(),\
            buf.readInt8())

        error = False

        if not isValidPlayerName(playerName):
            error = True
            debug_print("Nombre invalido:", repr(playerName))
        elif gameServer.playersLimitReached():
            error = True
        else:
            # La instancia de Player se crea recien cuando es válido.
            prot.player = Player(prot, playerName)

        if error:
            prot.loseConnection()

    def handleCmdTalk(self, prot, buf):
        pass

    def handleCmdWalk(self, prot, buf):
        pass

    def handleCmdOnline(self, prot, buff):
        pass

class ServerCommandsEncoder(object):
    """
    Conjunto de funciones para generar comandos hacia el cliente.
    """

    __slots__ = ('buf', 'prot', )

    def __init__(self, prot):
        self.buf = prot.outbuf
        self.prot = prot # K-Pax.

    def sendConsoleMsg(self, msg, font=0):
        self.buf.writeInt8(serverPackets['ConsoleMsg'])
        self.buf.writeString(msg)
        self.buf.writeInt8(font)

        self.prot.flushOutBuf()

    def sendLogged(self, userClass):
        self.buf.writeInt8(serverPackets['Logged'])
        self.buf.writeInt8(userClass)

        self.prot.flushOutBuf()

    def sendChangeMap(self, n, vers):
        self.buf.writeInt8(serverPackets['ChangeMap'])
        self.buf.writeInt16(n)
        self.buf.writeInt16(vers)

        self.prot.flushOutBuf()

    def sendUserIndexInServer(self, n):
        self.buf.writeInt8(serverPackets['UserIndexInServer'])
        self.buf.writeInt16(n)

        self.prot.flushOutBuf()

    def sendUserCharIndexInServer(self, n):
        self.buf.writeInt8(serverPackets['UserCharIndexInServer'])
        self.buf.writeInt16(n)

        self.prot.flushOutBuf()

class AoProtocol(Protocol):
    """Interfaz con Twisted para el socket del cliente."""

    def __init__(self):
        # Buffers de datos
        self._ao_inbuff = ByteQueue()
        self.outbuf = ByteQueue()

        # En medio de una desconexion.
        self._ao_closing = False

        # la instancia de Player se crea cuando el login es exitoso.
        self.player = None

    def dataReceived(self, data):
        if not self._ao_closing:
            self._ao_inbuff.addData(data)
            self._handleData()

    def connectionMade(self):
        if not gameServer.connectionsLimitReached():
            gameServer.connectionMade(self)
        else:
            self.loseConnection()

    def connectionLost(self, reason):
        debug_print("connectionLost")

        # Todo el codigo de limpieza de la conexion debe ir en loseConnection.

        if not self._ao_closing:
            self.loseConnection()

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
            gameServer.connectionLost(self)

            self.transport.loseConnection()
            if self.player is not None:
                self.player.quit()

class AoProtocolFactory(Factory):
    protocol = AoProtocol

class GameServer(object):
    def __init__(self):
        self._players = set()
        self._playersByName = {}
        self._connections = set()

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

    def playerLeave(self, p):
        self._players.remove(p)
        del self._playersByName[p.playerName.lower()]

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

    def connectionLost(self, c):
        if c in self._connections:
            self._connections.remove(c)

    def playerByName(self, playerName):
        return self._playersByName[playerName.lower()]

class Player(object):
    """Un jugador"""

    def __init__(self, prot, playerName):
        self.prot = prot
        self.playerName = playerName
        self.currentMap = None
        self.closing = False
        self.cmdout = ServerCommandsEncoder(self.prot)

        self.cmdout.sendUserIndexInServer(0)
        self.cmdout.sendUserCharIndexInServer(0)
        self.cmdout.sendChangeMap(32, 0)
        self.cmdout.sendLogged(0)
        self.cmdout.sendConsoleMsg(WELCOME_MSG)

        gameServer.playerJoin(self)

    def quit(self):
        if not self.closing:
            self.closing = True
            gameServer.playerLeave(self)

            self.prot.loseConnection()

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

# Globales

ServerConfig = None     # Configuracion del servidor.
cmdDecoder = None       # Handler para recibir paquetes de los clientes
mapData = None          # Lista de mapas
gameServer = None

# Timer

def onTimer():
    """Este timer se ejecuta cada un segundo"""
    pass

# Main

def loadMaps():
    global mapData


    mapCount = ServerConfig.getint('Core', 'MapCount')
    mapLoadingMode = ServerConfig.get('Core', 'MapLoadingMode')

    mapData = GameMapList(mapCount)

    if mapLoadingMode == "Full":
        print "Cargando mapas... "

        for x in xrange(1, 290+1):
            sys.stdout.write(str(x) + " ")
            sys.stdout.flush()
            mapData[x]

        print

        # Piedad, oh, piedad.
        gc.collect()
    elif mapLoadingMode == "Lazy":
        print "Carga de mapas en modo Lazy; se cargaran bajo demanda."
    else:
        raise Exception("Opcion no reconocida: MapLoadingMode=" \
            + mapLoadingMode)

def loadServerConfig():
    global ServerConfig

    ServerConfig = SafeConfigParser()
    ServerConfig.read([sys.argv[1]])

def initServer():
    global cmdDecoder, gameServer

    loadServerConfig()

    cmdDecoder = ClientCommandsDecoder()
    gameServer = GameServer()

def runServer():
    listenPort = ServerConfig.getint('Core', 'ListenPort')
    reactor.listenTCP(listenPort, AoProtocolFactory())

    t = task.LoopingCall(onTimer)
    t.start(1)

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
    loadMaps()

    #

    print
    print "Iniciado. Tiempo de inicio del servidor: " + str(datetime.datetime.now() - startTime)
    print

    runServer()


if __name__ == '__main__':
    main()

