# -*- coding: utf-8 -*-

from ConfigParser import SafeConfigParser

class MyConfigParser(SafeConfigParser):
    def read(self, *args, **kwargs):
        ret = SafeConfigParser.read(self, *args, **kwargs)

        secs = list(self.sections())
        for s in secs:
            items = self.items(s)
            self.remove_section(s)

            s = s.lower()
            self.add_section(s)
            for i in items:
                self.set(s, i[0].lower(), i[1])

        return ret

    def get(self, section, option, *args, **kwargs):
        return SafeConfigParser.get(self, section.lower(), option.lower(), *args, **kwargs)

    def getint(self, section, option):
        val = self.get(section, option)
        if "'" in val:
            val = val.split("'", 1)[0]
        return int(val)
