# -*- coding: utf-8 -*-
from __future__ import absolute_import

import xbmc
import xbmcgui

SETTING = "CCExitButtonAction"


def _mode():
    return (xbmc.getInfoLabel("Skin.String({})".format(SETTING)) or "quit").strip().lower()


def run():
    if _mode() != "power":
        xbmc.executebuiltin("Quit()")
        return

    labels = []
    actions = []
    if xbmc.getCondVisibility("System.CanPowerDown"):
        labels.append("Herunterfahren")
        actions.append("Powerdown()")
    if xbmc.getCondVisibility("System.CanReboot"):
        labels.append("Neustart")
        actions.append("Reboot()")
    if not actions:
        xbmcgui.Dialog().notification(
            "JJS KODI Confluence Custom", "Keine System-Aktion verfügbar", xbmcgui.NOTIFICATION_WARNING, 3000
        )
        return
    choice = xbmcgui.Dialog().select("System", labels)
    if choice >= 0:
        xbmc.executebuiltin(actions[choice])


if __name__ == "__main__":
    run()
