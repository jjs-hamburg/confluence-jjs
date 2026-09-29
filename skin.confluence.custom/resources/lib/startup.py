# -*- coding: utf-8 -*-
import xbmc
import factory_defaults
import import_confluence_settings
import library_nodes
from menu_common import ensure_initialised, log
from mainmenu_style import ensure_defaults
from skin_mode import ensure_mode
import xbmcgui


def _start_background_services():
    home = xbmcgui.Window(10000)
    if home.getProperty("ConfluenceCustom.SongSelector.ServiceRunning") != "1":
        xbmc.executebuiltin("RunScript(special://skin/resources/lib/songselector_service.py)", wait=False)
    if home.getProperty("ConfluenceCustom.Lyrics.ServiceRunning") != "1":
        xbmc.executebuiltin("RunScript(special://skin/resources/lib/culrc_runner.py)", wait=False)



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
        if apply_factory_defaults:
            # Do not reload here. On a genuine fresh skin switch Kodi is still
            # showing its own "keep these settings" confirmation dialog.
            # ReloadSkin() at this point steals that dialog's focus and lets the
            # confirmation time out, which makes Kodi fall back to the old skin.
            # Skin settings written below are live, so initialization can safely
            # continue without a reload.
            factory_defaults.apply()
        ensure_initialised(False)
        ensure_defaults()
        _start_background_services()
    except SystemExit:
        raise
    except Exception as exc:
        log("Startup failed: {}".format(exc), xbmc.LOGERROR)
