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
import gamerules

def moveTo(pos, d):
    newpos = list(pos)
    if d == DIR_N:
        newpos[1] -= 1
    elif d == DIR_E:
        newpos[0] += 1
    elif d == DIR_S:
        newpos[1] += 1
    elif d == DIR_W:
        newpos[0] -= 1
    else:
        return None
    return newpos

class PlayerAttributes(object):
    def __init__(self):
        self.chrclass = None
        self.head = 0
        self.body = 0
        self.attributes = [None] * 5
        self.skills = [None] * NUMSKILLS
        self.hechizos = [None] * 10
        self.inventario = [None] * NUMINVSLOTS
        self.hambre = 0
        self.sed = 0
        self.hambreMax = 0
        self.sedMax = 0
        self.hp = 0
        self.hpMax = 0
        self.mana = 0
        self.manaMax = 0
        self.sta = 0
        self.staMax = 0
        self.gld = 0
        self.gldBank = 0
        self.elv = 0
        self.elu = 0
        self.exp = 0

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

        self.privileges = PLAYERTYPE_USER

        self.attrs = PlayerAttributes()
        self.attrs.chrclass = CLASES['Mage']
        self.attrs.head = 1
        self.attrs.body = 1

        self.closing = False

        cv.gameServer.playerJoin(self)

    def __repr__(self):
        return "<Player Name=%s, ChrIdx=%s, Map=%s>" % (self.playerName, str(self.chridx), str(self.map))

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)

    def start(self):
        
        self.pos = [50, 50]
        self.heading = DIR_S
        self.map = None # Cuando no esta en ningun mapa es None.

        cv.mapData[1].playerJoin(self)

        self.sendUpdateHungerAndThirst()
        self.sendUpdateUserStats()
        self.sendInventory()
        self.sendSpells()

        self.cmdout.sendUserIndexInServer(self.userIdx)
        #self.sendUserCharIndexInServer()
        self.cmdout.sendLogged(self.attrs.chrclass)

        self.cmdout.sendConsoleMsg(WELCOME_MSG, FONTTYPES['SERVER'])
        self.cmdout.sendConsoleMsg(cv.ServerConfig.get('Core', 'WelcomeMessage').encode(TEXT_ENCODING), FONTTYPES['SERVER'])

    def quit(self):
        if not self.closing:
            self.closing = True
            self.map.playerLeave(self)
            cv.gameServer.playerLeave(self)

            self.prot.loseConnection()

    def sendUserCharIndexInServer(self):
        self.cmdout.sendUserCharIndexInServer(self.chridx)

    def sendPosUpdate(self):
        self.cmdout.sendPosUpdate(self.pos[0], self.pos[1])

    def sendUpdateHungerAndThirst(self):
        self.cmdout.sendUpdateHungerAndThirst(self.attrs.sedMax, \
            self.attrs.sed, self.attrs.hambreMax, self.attrs.hambre)

    def sendUpdateSta(self):
        self.cmdout.sendUpdateSta(self.attrs.sta)

    def sendUpdateMana(self):
        self.cmdout.sendUpdateMana(self.attrs.mana)

    def sendUpdateUserStats(self):
        self.cmdout.sendUpdateUserStats(self.attrs.hpMax, self.attrs.hp, \
            self.attrs.manaMax, self.attrs.mana, self.attrs.staMax, \
            self.attrs.sta, self.attrs.gld, self.attrs.elv, self.attrs.elu, \
            self.attrs.exp)

    def sendInventory(self, slot=None):
        """slot, objIdx, name, amount, equipped, grhIdx, objType, hitMax, hit, defMax, defMin, price"""
        
        if slot is None:
            for x in xrange(1, len(self.attrs.inventario) + 1):
                self.sendInventory(x)
        else:
            # Ojo: slot empieza en 1.
            # FIXME: Enviar objetos reales.
            self.cmdout.sendChangeInventorySlot(slot, 0, "", 0, 0, 0, 0, 0, 0, 0, 0, 0.0)

    def sendSpells(self, slot=None):
        if slot is None:
            for x in xrange(1, len(self.attrs.hechizos) + 1):
                self.sendSpells(x)
        else:
            # Ojo: slot empieza en 1.
            # FIXME: Enviar spells reales.
            self.cmdout.sendChangeSpellSlot(slot, 0, 'None')

    def move(self, d):
        newpos = moveTo(self.pos, d)
        if newpos is None:
            return

        try: # EAFP
            self.heading = d
            oldpos = self.pos
            self.map.playerMove(self, oldpos, newpos)
        except gamerules.GameLogicError, e: # Invalid pos
            self.sendPosUpdate()

    def onCharacterChange(self):
        self.map.playerChange(self)

    def getCharacterCreateAttrs(self, forChange=False):
        """chridx, body, head, heading, x, y, weapon, shield, helmet, fx, fxloops, name, nickColor, priv"""

        """chridx, body, head, heading, weapon, shield, helmet, fx, fxloops"""

        d = {'chridx': self.chridx,
            'body': self.attrs.head,
            'head': self.attrs.body,
            'heading': self.heading,
            'weapon': 0,
            'shield': 0,
            'helmet': 0,
            'fx': 0, 
            'fxloops': 0}

        if not forChange:
            d2 = {'x': self.pos[0],
                'y': self.pos[1],
                'name': self.playerName,
                'nickColor': NICKCOLOR_CIUDADANO,
                'priv': self.privileges}
            d.update(d2)

        return d

    def onLookAtTile(self, x, y):
        self.cmdout.sendConsoleMsg("Nada.", FONTTYPES['INFO'])

    def onDoubleClick(self, x, y):
        self.cmdout.sendConsoleMsg("Nada.", FONTTYPES['INFO'])

    def onCastSpell(self, spellIdx):
        self.cmdout.sendConsoleMsg("Sin implementar.", FONTTYPES['SERVER'])
        
    def onDrop(self, slot, amount):
        self.cmdout.sendConsoleMsg("Sin implementar.", FONTTYPES['SERVER'])

    def onWork(self, skill):
        pass

    def onTalk(self, msg, yell):
        act = "dice" if not yell else "grita"

        for p in cv.gameServer.playersList():
            p.cmdout.sendConsoleMsg(self.playerName + " %s (%d, %d): " % (act, self.pos[0], self.pos[1]) + msg, \
                FONTTYPES['TALK'])

