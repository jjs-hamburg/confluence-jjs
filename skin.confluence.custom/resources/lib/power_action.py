# -*- coding: utf-8 -*-
from __future__ import absolute_import

import xbmc


def run():
    # Android devices such as NVIDIA Shield should leave Kodi via Quit.
    # Native Linux / LibreELEC should show Kodi's normal power menu.
    if xbmc.getCondVisibility("System.Platform.Android"):
        xbmc.executebuiltin("Quit()")
        return
    if xbmc.getCondVisibility("System.Platform.Linux"):
        xbmc.executebuiltin("ActivateWindow(ShutdownMenu)")
        return
    xbmc.executebuiltin("Quit()")


if __name__ == "__main__":
    run()
