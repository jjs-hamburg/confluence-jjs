# -*- coding: utf-8 -*-
import sys
import xbmc

from menu_common import item_key, skin_string, log


def args_dict():
    out = {}
    for raw in sys.argv[1:]:
        if "=" in raw:
            k, v = raw.split("=", 1)
            out[k.strip().lower()] = v
    return out


def run():
    args = args_dict()
    group = args.get("group", "")
    try:
        slot = int(args.get("slot", "0"))
    except ValueError:
        slot = 0
    if not group or slot <= 0:
        return
    action = skin_string(item_key(group, slot, "Action"))
    if not action:
        return
    log("Execute {}:{} -> {}".format(group, slot, action))
    xbmc.executebuiltin(action)


if __name__ == "__main__":
    run()
