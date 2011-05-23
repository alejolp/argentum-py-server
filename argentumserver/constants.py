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

# El cliente espera los mensajes en latin-1.
TEXT_ENCODING = "latin-1"

AONX_RELEASE_NUM = '1'
WELCOME_MSG = (u"Servidor AONX r%s - visite www.aonx.com.ar" % AONX_RELEASE_NUM).encode(TEXT_ENCODING)

CREACION_PJS = u"La creación de personajes se hace desde el juego. Inicie sesión con el usuario y contraseña deseada.".encode(TEXT_ENCODING)

TIMEOUT_NOT_LOGGED = 15
TIMEOUT_YES_LOGGED = 5 * 60

DIR_N, DIR_E, DIR_S, DIR_W = range(1, 5)

MAP_SIZE_X = 100
MAP_SIZE_Y = 100

NICKCOLOR_CRIMINAL  = 1
NICKCOLOR_CIUDADANO = 2
NICKCOLOR_ATACABLE  = 4

FONTTYPES = dict(zip(['TALK', 'FIGHT', 'WARNING', 'INFO', 'INFOBOLD', \
    'EJECUCION', 'PARTY', 'VENENO', 'GUILD', 'SERVER', 'GUILDMSG', 'CONSEJO', \
    'CONSEJOCAOS', 'CONSEJOVesA', 'CONSEJOCAOSVesA', 'CENTINELA', 'GMMSG', \
    'GM', 'CITIZEN', 'CONSE', 'DIOS'], range(1, 21 + 1)))

PLAYERTYPE_USER = 1

CLASES = dict(zip(['Mage', 'Cleric', 'Warrior', 'Assasin', 'Thief',\
    'Bard', 'Druid', 'Bandit', 'Paladin', 'Hunter', 'Worker', 'Pirat'], \
    range(1, 12 + 1)))

RAZAS = dict(zip(['Humano', 'Elfo', 'Drow', 'Gnomo', 'Enano'], \
    range(1, 5 + 1)))

