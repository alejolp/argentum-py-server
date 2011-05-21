#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
