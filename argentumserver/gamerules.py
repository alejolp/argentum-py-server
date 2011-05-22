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

__all__ = ['isValidPlayerName']

import re

# ---


# ---

VALID_PLAYER_NAME = re.compile(r'^[ a-zA-Z]+$')

def isValidPlayerName(name, create):
    """
    Un nombre válido:

    - Tiene entre 3 y 32 caracteres.
    - No tiene dos espacios consecutivos.
    - No tiene espacios al inicio ni final.
    - Solo esta compuesto por letras y espacios.
    - No lleva acentos ni simbolos especiales.
    - No es un nombre prohibido (solo para la creacion de pjs).

    Nombres inválidos:

    - "Un"
    - "Juan  Pedro"
    - " Juan"
    - "Juan!"
    - "Raúl"
    - "Argentum"

    Nombres válidos:

    - "Juan Pedro Marcos De Los Palotes"
    - "Raul"
    """

    if len(name) > 32 or len(name) < 3:
        return False

    if '  ' in name or name.strip() != name:
        return False

    if VALID_PLAYER_NAME.match(name) is None:
        return False

    if create and name.lower() in forbiddenNames:
        return False

    return True


