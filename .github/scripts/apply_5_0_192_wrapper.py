# -*- coding: utf-8 -*-
from pathlib import Path
import runpy

live = Path("skin.confluence.custom/resources/lib/live_home_adjust.py")
text = live.read_text(encoding="utf-8")
needle = "import xbmcvfs\n\nHOME_WINDOW_ID = 10000\n"
shim = "import xbmcvfs\n\nfrom worker_lock import WorkerLock\n\nHOME_WINDOW_ID = 10000\n"
if needle not in text:
    raise SystemExit("live_home_adjust import precondition not found")
live.write_text(text.replace(needle, shim, 1), encoding="utf-8")

runpy.run_path(".github/scripts/apply_5_0_192.py", run_name="__main__")

# The temporary WorkerLock import existed only to match the old exact patch
# anchor. It was not part of live_home_adjust and must not remain in 5.0.192.
text = live.read_text(encoding="utf-8")
text = text.replace("from worker_lock import WorkerLock\n", "", 1)
live.write_text(text, encoding="utf-8")
print("5.0.192 live-home import anchor handled cleanly")
