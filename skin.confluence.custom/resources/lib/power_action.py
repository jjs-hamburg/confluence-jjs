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
        labels.append("Power off")
        actions.append("Powerdown()")
    if xbmc.getCondVisibility("System.CanReboot"):
        labels.append("Restart")
        actions.append("Reboot()")
    if not actions:
        xbmcgui.Dialog().notification(
            "Confluence-jjs", "No system action is available", xbmcgui.NOTIFICATION_WARNING, 3000
        )
        return
    choice = xbmcgui.Dialog().select("System", labels)
    if choice >= 0:
        xbmc.executebuiltin(actions[choice])


if __name__ == "__main__":
    run()
