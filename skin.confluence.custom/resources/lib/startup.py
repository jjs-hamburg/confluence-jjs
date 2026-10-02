# -*- coding: utf-8 -*-
import xbmc
import factory_defaults
import import_confluence_settings
import library_nodes
from menu_common import ensure_initialised, log
from mainmenu_style import ensure_defaults
from skin_mode import ensure_mode
import xbmcgui
from worker_lock import worker_is_running


def _start_background_services():
    home = xbmcgui.Window(10000)
    if (home.getProperty("ConfluenceCustom.SongSelector.ServiceRunning") != "1"
            and not worker_is_running("songselector")):
        xbmc.executebuiltin("RunScript(special://skin/resources/lib/songselector_service.py)", wait=False)
    if (home.getProperty("ConfluenceCustom.Lyrics.ServiceRunning") != "1"
            and not worker_is_running("lyrics")):
        xbmc.executebuiltin("RunScript(special://skin/resources/lib/culrc_runner.py)", wait=False)


def _wait_for_skin_switch_confirmation():
    """Keep first-run work out of Kodi's timed Keep Skin confirmation window."""
    if not factory_defaults.needs_first_run_settle():
        return xbmc.getSkinDir() == factory_defaults.SKIN_ID

    monitor = xbmc.Monitor()
    dialog_seen = False
    log("Fresh-install startup waiting for Kodi skin confirmation")

    # Home.xml is loaded before Kodi opens the timed yes/no confirmation. Give
    # that core dialog enough time to appear while doing no initialization work.
    for _ in range(50):
        if xbmc.getSkinDir() != factory_defaults.SKIN_ID:
            return False
        if xbmc.getCondVisibility("Window.IsActive(yesnodialog)"):
            dialog_seen = True
            break
        if monitor.waitForAbort(0.1):
            return False

    if dialog_seen:
        while xbmc.getCondVisibility("Window.IsActive(yesnodialog)"):
            if monitor.waitForAbort(0.1):
                return False

    # A negative/timeout answer queues the switch back immediately after the
    # dialog closes. Let Kodi finish that switch before deciding whether to run.
    if monitor.waitForAbort(0.5):
        return False
    return xbmc.getSkinDir() == factory_defaults.SKIN_ID


if __name__ == "__main__":
    try:
        # Decide whether this is a genuine fresh install before Kodi has had
        # time to persist any skin settings. begin() only creates the small
        # pending/state marker; all real initialization still happens later.
        apply_factory_defaults = factory_defaults.begin()
        if not _wait_for_skin_switch_confirmation():
            raise SystemExit
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
            factory_defaults.apply()
        ensure_initialised(False)
        ensure_defaults()
        _start_background_services()
    except SystemExit:
        raise
    except Exception as exc:
        log("Startup failed: {}".format(exc), xbmc.LOGERROR)
