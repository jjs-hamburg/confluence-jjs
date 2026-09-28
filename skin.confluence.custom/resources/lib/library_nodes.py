# -*- coding: utf-8 -*-
"""Install/restore Confluence-jjs's bundled Kodi library nodes.

Fresh skin installs only fill node files that do not yet exist.  Existing
profiles are never overwritten automatically.  The explicit ``reset`` action
is deliberately destructive for the music/video node trees and restores the
bundled snapshot in full.
"""
from __future__ import absolute_import

import sys

import xbmc
import xbmcgui
import xbmcvfs

SOURCE_ROOT = "special://skin/resources/library_nodes"
TARGET_ROOT = "special://profile/library"
KINDS = ("music", "video")


def _log(message, level=xbmc.LOGINFO):
    xbmc.log("[Confluence-jjs] Library nodes: {}".format(message), level)


def _join(base, name):
    return base.rstrip("/\\") + "/" + name.strip("/\\")


def _ensure_dir(path):
    if not xbmcvfs.exists(path):
        if not xbmcvfs.mkdirs(path) and not xbmcvfs.exists(path):
            raise RuntimeError("Folder could not be created: {}".format(path))


def _copy_tree(source, target, overwrite=False):
    """Copy source tree to target and return (copied, skipped)."""
    _ensure_dir(target)
    copied = 0
    skipped = 0
    dirs, files = xbmcvfs.listdir(source)
    for dirname in dirs:
        c, s = _copy_tree(_join(source, dirname), _join(target, dirname), overwrite)
        copied += c
        skipped += s
    for filename in files:
        src = _join(source, filename)
        dst = _join(target, filename)
        if xbmcvfs.exists(dst):
            if not overwrite:
                skipped += 1
                continue
            try:
                xbmcvfs.delete(dst)
            except Exception:
                pass
        if not xbmcvfs.copy(src, dst):
            raise RuntimeError("File could not be copied: {}".format(filename))
        copied += 1
    return copied, skipped


def _remove_tree(path):
    if not xbmcvfs.exists(path):
        return
    dirs, files = xbmcvfs.listdir(path)
    for filename in files:
        target = _join(path, filename)
        if not xbmcvfs.delete(target) and xbmcvfs.exists(target):
            raise RuntimeError("File could not be deleted: {}".format(target))
    for dirname in dirs:
        _remove_tree(_join(path, dirname))
    try:
        ok = xbmcvfs.rmdir(path, force=True)
    except TypeError:
        ok = xbmcvfs.rmdir(path)
    if not ok and xbmcvfs.exists(path):
        raise RuntimeError("Folder could not be deleted: {}".format(path))


def install_missing_defaults():
    """Fresh-install helper: copy bundled node files only where absent."""
    total_copied = 0
    total_skipped = 0
    for kind in KINDS:
        source = _join(SOURCE_ROOT, kind)
        target = _join(TARGET_ROOT, kind)
        if not xbmcvfs.exists(source):
            raise RuntimeError("Bundled {} nodes are missing".format(kind))
        copied, skipped = _copy_tree(source, target, overwrite=False)
        total_copied += copied
        total_skipped += skipped
    _log("fresh install: {} files created, {} existing files kept".format(total_copied, total_skipped))
    return total_copied, total_skipped


def restore_defaults():
    """Explicit reset: replace both profile node trees with the bundled set."""
    for kind in KINDS:
        target = _join(TARGET_ROOT, kind)
        _remove_tree(target)
    total = 0
    for kind in KINDS:
        source = _join(SOURCE_ROOT, kind)
        target = _join(TARGET_ROOT, kind)
        copied, _ = _copy_tree(source, target, overwrite=True)
        total += copied
    _log("explicit reset: {} node files restored".format(total))
    return total


def reset_interactive():
    dialog = xbmcgui.Dialog()
    if not dialog.yesno(
        "Confluence-jjs",
        "Existing music and video library nodes will be completely replaced by the skin defaults.[CR][CR]Continue?",
    ):
        return False
    try:
        total = restore_defaults()
    except Exception as exc:
        _log("reset failed: {}".format(exc), xbmc.LOGERROR)
        dialog.ok("Confluence-jjs", "Library nodes could not be reset:[CR]{}".format(exc))
        return False
    dialog.notification("Confluence-jjs", "{} library node files restored".format(total), xbmcgui.NOTIFICATION_INFO, 3500)
    xbmc.sleep(250)
    xbmc.executebuiltin("ReloadSkin()")
    return True


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if mode == "reset":
        reset_interactive()


if __name__ == "__main__":
    main()
