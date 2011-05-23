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

import sys, os

def main():
    if len(sys.argv) < 2:
        print "Forma de uso: datfixer.py archivo.dat"
        sys.exit(1)

    fn = sys.argv[1]
    fixDatFile(fn, fn + ".fix")

    # Hace un swap de los archivos. El archivo original queda con ext. ".old".

    os.rename(fn, fn + ".old")
    os.rename(fn + ".fix", fn)

def fixDatFile(fileNameSrc, fileNameDst):
    """
    Dado un archivo .DAT lo corrige para poder usarlo ConfigParser de Python.

    El archivo original no lo modifica, y el archivo corregido lo guarda
    en fileNameDst.
    """

    f_in = open(fileNameSrc, 'rb')
    f_out = open(fileNameDst, 'wb')

    currentSection = None

    for line in f_in:
        if '[' in line and ']' in line:
            currentSection = line

        # Las comillas simples rompen; no son comentarios.
        
        if len(line.strip()) > 0 and line.strip()[0] == "'":
            # 'Hola
            line = line.replace("'", "; ")

        elif '[' in line and ']' in line and "'" in line:
            # [OBJ1] 'Comentario
            line = line.replace("'", "; ")

        # Las líneas sueltas también rompen.

        elif '=' in line and currentSection is None:
            # Algo====Otro
            line = "; " + line

        else:
            tiene = False
            for x in ['#', "'", ";", '[', ']', '=']:
                if x in line:
                    tiene = True
                    break

            if not tiene and len(line.strip()) > 0:
                line = "; " + line

        f_out.write(line)

    f_out.close()
    f_in.close()

if __name__ == '__main__':
    main()
