# -*- coding: utf-8 -*-
import sys
import xbmc
from menu_common import skin_string, log


def run():
    group = ""
    for raw in sys.argv[1:]:
        if raw.startswith("group="):
            group = raw.split("=", 1)[1]
            break
    if not group:
        return
    action = skin_string("CCMain_{}_Action".format(group))
    if action:
        log("Execute main {} -> {}".format(group, action))
        xbmc.executebuiltin(action)

if __name__ == "__main__":
    run()
