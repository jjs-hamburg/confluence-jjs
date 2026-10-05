# -*- coding: utf-8 -*-
import xbmc
import xbmcgui


SKIN_ID = "skin.confluence.custom"
HOME_WINDOW_ID = 10000
SHADOW_WIDTH_SETTING = "CCHomeMusicShadowWidth"
SHADOW_OFFSET_SETTING = "CCHomeMusicShadowOffset"
DEFAULT_SHADOW_WIDTH = "14"
DEFAULT_SHADOW_OFFSET = "4"


def _skin_value(name, default):
    value = xbmc.getInfoLabel("Skin.String({})".format(name))
    return value if value else default


def _shadow_state():
    return (
        _skin_value(SHADOW_WIDTH_SETTING, DEFAULT_SHADOW_WIDTH),
        _skin_value(SHADOW_OFFSET_SETTING, DEFAULT_SHADOW_OFFSET),
    )


def main():
    monitor = xbmc.Monitor()
    last_state = _shadow_state()
    rebuild_pending = False

    while not monitor.abortRequested():
        if xbmc.getSkinDir() == SKIN_ID:
            current_state = _shadow_state()
            if current_state != last_state:
                last_state = current_state
                rebuild_pending = True

            # Shadow border textures are selected through conditional includes
            # when Home is built. Rebuild once after the user has left settings;
            # never reload underneath DialogSelect or SkinSettings itself.
            if rebuild_pending and xbmcgui.getCurrentWindowId() == HOME_WINDOW_ID:
                rebuild_pending = False
                xbmc.executebuiltin("ReloadSkin()")
                if monitor.waitForAbort(0.75):
                    break
        else:
            # Do not carry a pending Confluence-jjs refresh into another skin.
            last_state = _shadow_state()
            rebuild_pending = False

        if monitor.waitForAbort(0.20):
            break


if __name__ == "__main__":
    main()
