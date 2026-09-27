# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import factory_defaults
import import_confluence_settings
import library_nodes
from menu_common import ensure_initialised, log
from mainmenu_style import ensure_defaults
from skin_mode import ensure_mode
import xbmcgui


BACKGROUND_SERVICE_VERSION_PROP = "ConfluenceCustom.BackgroundServiceVersion"
SONG_SERVICE_RUNNING_PROP = "ConfluenceCustom.SongSelector.ServiceRunning"
LYRICS_SERVICE_RUNNING_PROP = "ConfluenceCustom.Lyrics.ServiceRunning"
SONG_SERVICE_PATH = "special://skin/resources/lib/songselector_service.py"
LYRICS_SERVICE_PATH = "special://skin/resources/lib/culrc_runner.py"


def _start_background_services():
    home = xbmcgui.Window(10000)
    version = xbmcaddon.Addon().getAddonInfo("version") or ""

    # RunScript instances survive a skin package update. If their source changed,
    # keeping the old Python process would combine new XML with old service code.
    # Restart exactly once per installed skin version.
    if home.getProperty(BACKGROUND_SERVICE_VERSION_PROP) != version:
        xbmc.executebuiltin("StopScript({})".format(SONG_SERVICE_PATH))
        xbmc.executebuiltin("StopScript({})".format(LYRICS_SERVICE_PATH))
        xbmc.sleep(120)
        home.clearProperty(SONG_SERVICE_RUNNING_PROP)
        home.clearProperty(LYRICS_SERVICE_RUNNING_PROP)
        home.setProperty(BACKGROUND_SERVICE_VERSION_PROP, version)

    if home.getProperty(SONG_SERVICE_RUNNING_PROP) != "1":
        xbmc.executebuiltin("RunScript({})".format(SONG_SERVICE_PATH), wait=False)
    if home.getProperty(LYRICS_SERVICE_RUNNING_PROP) != "1":
        xbmc.executebuiltin("RunScript({})".format(LYRICS_SERVICE_PATH), wait=False)



if __name__ == "__main__":
    try:
        apply_factory_defaults = factory_defaults.begin()
        if apply_factory_defaults:
            try:
                library_nodes.install_missing_defaults()
            except Exception as exc:
                log("Library-node defaults failed: {}".format(exc), xbmc.LOGERROR)
        # A skin update always installs the Custom XML files from the package.
        # If Standard Confluence was active before the update, restore that
        # XML set first and reload before any Custom initialisation runs.
        if ensure_mode():
            raise SystemExit
        import_confluence_settings.run()
        if apply_factory_defaults and factory_defaults.apply():
            xbmc.sleep(150)
            xbmc.executebuiltin("ReloadSkin()")
            raise SystemExit
        ensure_initialised(False)
        ensure_defaults()
        _start_background_services()
    except SystemExit:
        raise
    except Exception as exc:
        log("Startup failed: {}".format(exc), xbmc.LOGERROR)
