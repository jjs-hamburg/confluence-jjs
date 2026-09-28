# -*- coding: utf-8 -*-
"""One-time migration of original Confluence skin settings into this custom skin."""

import os
import xml.etree.ElementTree as ET

import xbmc
import xbmcvfs

SOURCE_SKIN = "skin.confluence"
TARGET_SKIN = "skin.confluence.custom"
MARKER_NAME = ".confluence-settings-imported-v1"


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[Confluence-jjs] {}".format(message), level)


def q(value):
    # Kodi built-ins use double quotes for literal parameters. Skin paths and
    # labels virtually never contain quotes; strip an unexpected quote rather
    # than producing a malformed built-in command.
    return '"{}"'.format(str(value).replace('"', "'"))


def ensure_dir(path):
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)


def marker_path():
    base = xbmcvfs.translatePath("special://profile/addon_data/{}/".format(TARGET_SKIN))
    ensure_dir(base)
    return os.path.join(base, MARKER_NAME)


def source_settings_paths():
    # Normally profile==masterprofile. Keep both for installations with profiles.
    return [
        xbmcvfs.translatePath("special://profile/addon_data/{}/settings.xml".format(SOURCE_SKIN)),
        xbmcvfs.translatePath("special://masterprofile/addon_data/{}/settings.xml".format(SOURCE_SKIN)),
    ]


def find_source():
    seen = set()
    for path in source_settings_paths():
        if path in seen:
            continue
        seen.add(path)
        if xbmcvfs.exists(path):
            return path
    return None


def apply_setting(setting):
    setting_id = setting.get("id") or setting.get("name")
    setting_type = (setting.get("type") or "").lower()
    value = setting.text or ""
    if not setting_id:
        return False

    if setting_type == "bool":
        if value.strip().lower() == "true":
            xbmc.executebuiltin("Skin.SetBool({})".format(q(setting_id)))
        else:
            xbmc.executebuiltin("Skin.Reset({})".format(q(setting_id)))
        return True

    if setting_type == "string":
        if value:
            xbmc.executebuiltin("Skin.SetString({},{})".format(q(setting_id), q(value)))
        else:
            xbmc.executebuiltin("Skin.Reset({})".format(q(setting_id)))
        return True

    return False


def run():
    # Never import while another skin is active. Home.xml invokes us only from
    # Confluence-jjs, but this protects manual/scripted calls as well.
    if xbmc.getSkinDir() != TARGET_SKIN:
        return

    marker = marker_path()
    if xbmcvfs.exists(marker):
        return

    source = find_source()
    if not source:
        log("Original Confluence settings.xml not found; import skipped", xbmc.LOGWARNING)
        return

    try:
        tree = ET.parse(source)
        root = tree.getroot()
    except Exception as exc:
        log("Could not read original Confluence settings: {}".format(exc), xbmc.LOGERROR)
        return

    if root.tag != "settings":
        log("Unexpected Confluence settings format: root={}".format(root.tag), xbmc.LOGERROR)
        return

    applied = 0
    for setting in root.findall("setting"):
        try:
            if apply_setting(setting):
                applied += 1
        except Exception as exc:
            log("Could not import setting {}: {}".format(setting.get("id"), exc), xbmc.LOGWARNING)

    # Persist a marker independently of skin settings so ReloadSkin cannot loop.
    try:
        f = xbmcvfs.File(marker, "w")
        f.write("Imported {} settings from {}\n".format(applied, source))
        f.close()
    except Exception as exc:
        log("Could not write migration marker: {}".format(exc), xbmc.LOGWARNING)

    log("Imported {} settings from original Confluence".format(applied))
    if applied:
        xbmc.executebuiltin("Notification(Confluence-jjs,Settings imported from Confluence,3000)")


if __name__ == "__main__":
    run()
