# -*- coding: utf-8 -*-
"""Run the bundled CU LRC engine only for one Song Popup session."""

import threading

import xbmc
import xbmcgui

from culrc.gui import MAIN as CulrcMain
from culrc.gui import _jjs_popup_visible
from worker_lock import WorkerLock


HOME_ID = 10000
SERVICE_RUNNING_PROP = "ConfluenceCustom.Lyrics.ServiceRunning"


class PopupSessionMain(CulrcMain):
    """Stop the embedded CU LRC loop as soon as its popup session ends."""

    def setup_main(self):
        CulrcMain.setup_main(self)
        watcher = threading.Thread(target=self._watch_popup_session, name="ConfluenceJjsLyricsSession")
        watcher.daemon = True
        watcher.start()

    def _watch_popup_session(self):
        monitor = xbmc.Monitor()
        session_seen = False
        while not monitor.abortRequested() and not self.CULRC_QUIT:
            if _jjs_popup_visible():
                session_seen = True
            elif session_seen:
                self.CULRC_QUIT = True
                return
            if monitor.waitForAbort(0.10):
                return


def run():
    # This runner is launched only after window 1116 has actually opened. The
    # compatibility PopupOpen property is already published at that point, so
    # the session watcher can terminate this worker cleanly when the dialog closes.
    if not _jjs_popup_visible():
        return
    PopupSessionMain()


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
