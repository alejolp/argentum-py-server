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

from constants import *
import corevars as cv

class Player(object):
    """Un jugador"""

    def __init__(self, prot, playerName):
        self.prot = prot
        self.cmdout = prot.cmdout

        self.playerName = playerName
        self.currentMap = None
        self.chridx = None
        self.userIdx = None
        self.map = None

        self.closing = False

        cv.gameServer.playerJoin(self)

    def start(self):
        
        self.pos = [50, 50]
        self.map = None # Cuando no esta en ningun mapa es None.

        cv.mapData[1].playerJoin(self)

        self.cmdout.sendUserIndexInServer(self.userIdx)
        self.cmdout.sendUserCharIndexInServer(self.chridx)
        self.cmdout.sendLogged(0)
        self.cmdout.sendConsoleMsg(WELCOME_MSG)

    def quit(self):
        if not self.closing:
            self.closing = True
            cv.gameServer.playerLeave(self)
            self.map.playerLeave(self)

            self.prot.loseConnection()

    def sendPosUpdate(self):
        self.cmdout.sendPosUpdate(self.pos.x, self.pos.y)

    def move(self, d):
        p2 = list(self.pos)
        if d == DIR_N:
            p2[1] -= 1
        elif d == DIR_E:
            p2[0] += 1
        elif d == DIR_S:
            p2[1] += 1
        elif d == DIR_W:
            p2[0] -= 1

        if not self.map.validPos(p2):
            self.sendPosUpdate()
        else:
            oldpos = self.pos
            self.pos = p2
            self.map.playerMove(self, oldpos)

