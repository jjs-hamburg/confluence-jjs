# -*- coding: utf-8 -*-
from menu_common import ensure_initialised, log

if __name__ == "__main__":
    try:
        ensure_initialised(False)
    except Exception as exc:
        import xbmc
        log("Initialisation failed: {}".format(exc), xbmc.LOGERROR)
