# -*- coding: utf-8 -*-
"""Run the bundled CU LRC popup-only engine as an internal skin worker."""

import xbmc
import xbmcgui

from culrc.gui import MAIN
from worker_lock import WorkerLock


HOME_ID = 10000
SERVICE_RUNNING_PROP = "ConfluenceCustom.Lyrics.ServiceRunning"


def run():
    MAIN()


if __name__ == "__main__":
    home = xbmcgui.Window(HOME_ID)
    worker_lock = WorkerLock("lyrics")
    if worker_lock.acquire():
        home.setProperty(SERVICE_RUNNING_PROP, "1")
        try:
            run()
        except Exception as exc:
            xbmc.log("[ConfluenceCustom] Embedded lyrics runtime failed: {!r}".format(exc), xbmc.LOGERROR)
        finally:
            home.clearProperty(SERVICE_RUNNING_PROP)
            worker_lock.release()
    else:
        xbmc.log("[ConfluenceCustom] Embedded lyrics worker already running; duplicate start suppressed",
                 xbmc.LOGINFO)
