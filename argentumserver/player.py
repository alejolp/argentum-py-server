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

import sys

from constants import *
import corevars as cv
import gamerules, util

def moveTo(pos, d):
    newpos = list(pos)
    if d == DIR_N:
        newpos[1] -= 1
        if newpos[1] < 1:
            return None
    elif d == DIR_E:
        newpos[0] += 1
        if newpos[0] > MAP_SIZE_X:
            return None
    elif d == DIR_S:
        newpos[1] += 1
        if newpos[1] > MAP_SIZE_Y:
            return None
    elif d == DIR_W:
        newpos[0] -= 1
        if newpos[0] < 1:
            return None
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

class PlayerInventory(object):
    def __init__(self, player):
        self.player = player
        self.items = [[None, 0, False] for x in xrange(NUMINVSLOTS)]

    def __getitem__(self, n):
        assert n >= 1
        return self.items[n - 1]

    def __len__(self):
        return len(self.items)

    def addItem(self, objidx, amount):
        """Agrega un nuevo objeto. Devuelve la lista de slots y cuanta
        cantidad de objetos no se pudieron agregar al inv."""

        assert amount > 0 and amount <= MAXINVITEMS
        assert cv.objData[objidx] is not None

        r = []
        
        # Busca algun slot que ya tenga el item.
        for i, x in enumerate(self.items):
            if x[0] == objidx and x[1] < MAXINVITEMS:
                r.append(i+1)

                x[1] += amount
                if x[1] > MAXINVITEMS:
                    amount = x[1] - MAXINVITEMS
                    x[1] = MAXINVITEMS
                else:
                    amount = 0
                    break

        if amount > 0:
            # Busca algun slot libre
            for i, x in enumerate(self.items):
                if x[0] is None:
                    r.append(i+1)

                    x[0] = objidx
                    x[1] = amount
                    x[2] = False
                    amount = 0
                    break

        return r, amount

    def isEmpty(self, slot):
        ss = self[slot]

        assert (ss[0] is None) == (ss[1] == 0)
        return ss[0] is None

    def dropItem(self, slot, amount):
        assert slot >= 1 and util.between(amount, 1, MAXINVITEMS)
        assert not self.isEmpty(slot)

        invs = self[slot]

        if invs[1] < amount:
            return 0

        objidx = invs[0]

        if invs[1] == amount:
            invs[0] = None
            invs[1] = 0
            invs[2] = False
        else:
            invs[1] -= amount

    def sortItems(self):
        self.items.sort(key=(lambda x: sys.maxint if x[0] is None else x[0]))

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
        self.inventario = PlayerInventory(self)

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
            for x in xrange(1, len(self.inventario) + 1):
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

    def m(self, msg, t=FONTTYPES['INFO']):
        self.cmdout.sendConsoleMsg(msg, t)

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

    def onWork(self, skill):
        pass

    def onCustomCmd(self, cmd):
        if cmd == "sortinv":
            self.inventario.sortItems()
            self.sendInventory()

    def onTalk(self, msg, yell):
        act = "dice" if not yell else "grita"

        if msg.startswith("do "):
            self.onCustomCmd(msg[3:])
            return

        for p in cv.gameServer.playersList():
            p.cmdout.sendConsoleMsg(self.playerName + " %s (%d, %d): " % (act, self.pos[0], self.pos[1]) + msg, FONTTYPES['TALK'])

    def doPickUp(self):

        tile = self.map.mapFile[self.pos]
        if tile.objidx is None:
            self.m("No hay nada para levantar.")
            return

        objidx, amount = tile.objidx, tile.objcant
        r, amount_left = self.inventario.addItem(objidx, amount)
        if amount_left > 0:
            self.m("No se pudieron levantar todos los items.")
        else:
            tile.objidx = None
        tile.objcant = amount_left

        for x in r:
            self.sendInventory(x)

    def onDrop(self, slot, amount):
        """Manejador del comando de tirar items al piso."""

        ub = util.between

        if not ub(slot, 1, NUMINVSLOTS) or not ub(amount, 1, MAXINVITEMS):
            self.m("Nah")
            return

        if self.inventario.isEmpty(slot):
            return

        objidx = self.inventario.dropItem(slot, amount)
        if objidx == 0:
            self.m("No tienes esa cantidad.")
            return

        try:
            self.map.dropObjAt(objidx, amount, self.pos)
        except gamerules.NoFreeSpaceOnMap, e:
            self.inventario.addItem(objidx, amount)

        self.sendInventory()

    def onEquipItem(self, slot):
        self.cmdout.sendConsoleMsg("Sin implementar.", FONTTYPES['SERVER'])

    def doAttack(self):
        self.cmdout.sendConsoleMsg("Sin implementar.", FONTTYPES['SERVER'])

