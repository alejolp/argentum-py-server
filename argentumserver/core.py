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

import os, sys, struct, socket
from aoprotocol import clientPackets, serverPackets, clientPacketsFlip
from bytequeue import ByteQueue, ByteQueueError, ByteQueueInsufficientData

try:
    import twisted
except ImportError:
    print "Es necesario instalar python-twisted"
    sys.exit(1)

if sys.platform == 'linux2': # yeah!
    from twisted.internet import epollreactor
    epollreactor.install()
elif sys.platform == 'win32': # rulz!
    from twisted.internet import iocpreactor
    iocpreactor.install()

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

# ---

WELCOME_MSG = "Bienvenido al servidor AONX - visite www.aonx.com.ar"

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

        prot.player = Player(prot, playerName)

    def handleCmdTalk(self, prot, buf):
        pass

    def handleCmdWalk(self, prot, buf):
        pass

    def handleCmdOnline(self, prot, buff):
        pass

class ServerCommandsEncoder(object):
    """Conjunto de funciones para generar comandos hacia el cliente"""

    __slots__ = ('buf', 'prot', )

    def __init__(self, prot):
        self.buf = prot.outbuf
        self.prot = prot

    def sendConsoleMsg(self, msg, font=0):
        self.buf.writeInt8(serverPackets['ConsoleMsg'])
        self.buf.writeString(msg)
        self.buf.writeInt8(font)

    def sendLogged(self, userClass):
        self.buf.writeInt8(serverPackets['Logged'])
        self.buf.writeInt8(userClass)

    def sendChangeMap(self, n, vers):
        self.buf.writeInt8(serverPackets['ChangeMap'])
        self.buf.writeInt16(n)
        self.buf.writeInt16(vers)

    def sendUserIndexInServer(self, n):
        self.buf.writeInt8(serverPackets['UserIndexInServer'])
        self.buf.writeInt16(n)

    def sendUserCharIndexInServer(self, n):
        self.buf.writeInt8(serverPackets['UserCharIndexInServer'])
        self.buf.writeInt16(n)

class AoProtocol(Protocol):
    """Interfaz con Twisted para el socket del cliente."""

    def __init__(self):
        # Buffer de datos
        self._ao_inbuff = ByteQueue()
        self.outbuf = ByteQueue()

        # En medio de una desconexion.
        self._ao_closing = False

        # la instancia de Player se crea cuando el login es exitoso.
        self.player = None

    def dataReceived(self, data):
        self._ao_inbuff.addData(data)
        self._handleData()

    def connectionMade(self):
        pass

    def connectionLost(self, reason):
        debug_print("connectionLost")

        if not self._ao_closing:
            self.loseConnection()

    def _handleData(self):
        try:
            cmdDecoder.handleData(self)
        except CriticalDecoderException, e:
            self.loseConnection()

    def sendData(self, data):
        self.transport.write(data)

    def flushOutBuf(self):
        self.sendData(self.outbuf.readRaw())

    def loseConnection(self):
        if not self._ao_closing:
            debug_print("loseConnection")
            self._ao_closing = True

            self.transport.loseConnection()
            if self.player is not None:
                self.player.quit()

class AoProtocolFactory(Factory):
    protocol = AoProtocol

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

        self.prot.flushOutBuf()

    def quit(self):
        if not self.closing:
            self.closing = True

            self.prot.loseConnection()

class GameMap(object):
    """Un mapa"""

    def __init__(self):
        self.players = {}

    def playerJoin(self, p):
        pass

    def playerLeave(self, p):
        pass

# Globales

cmdDecoder = None
mapData = None

# Main

def initServer():
    global cmdDecoder, mapData

    cmdDecoder = ClientCommandsDecoder()
    mapData = []

    mapData.append(GameMap())

def runServer():
    reactor.listenTCP(7666, AoProtocolFactory())
    print "Escuchando en el puerto 7666, reactor: " + \
        reactor.__class__.__name__

    reactor.run()

def main():
    initServer()
    runServer()


if __name__ == '__main__':
    main()

