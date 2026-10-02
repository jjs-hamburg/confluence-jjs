# -*- coding: utf-8 -*-
from __future__ import absolute_import

import sys

import xbmc
import xbmcgui
import xbmcaddon

from nocover_manager import apply as apply_no_cover, save_free_image

MAIN_FONT_SETTING = "CCMainMenuFontFamily"
MAIN_SIZE_SETTING = "CCMainMenuFontSize"
MAIN_NORMAL_COLOR_SETTING = "CCMainMenuColorNormal"
MAIN_ACTIVE_COLOR_SETTING = "CCMainMenuColorActive"
MAIN_Y_OFFSET_SETTING = "CCMainMenuYOffset"

SUB_FONT_SETTING = "CCSubMenuFontFamily"
SUB_SIZE_SETTING = "CCSubMenuFontSize"
SUB_NORMAL_COLOR_SETTING = "CCSubMenuColorNormal"
SUB_ACTIVE_COLOR_SETTING = "CCSubMenuColorActive"

HOME_COVER_SIZE_SETTING = "CCHomeMusicCoverSize"
HOME_COVER_STYLE_SETTING = "CCHomeMusicCoverStyle"
HOME_SHADOW_WIDTH_SETTING = "CCHomeMusicShadowWidth"
HOME_SHADOW_OFFSET_SETTING = "CCHomeMusicShadowOffset"
HOME_FLOOR_STYLE_SETTING = "CCHomeFloorStyle"
HOME_ARTWORK_MODE_SETTING = "CCMusicArtworkMode"
HOME_NO_COVER_SETTING = "CCHomeNoCoverStyle"
EXIT_BUTTON_SETTING = "CCExitButtonAction"
SKIN_DEFAULT_BACKGROUND = "special://skin/backgrounds/DefaultWallpaper.jpg"

SONG_SELECTOR_FONT_SETTING = "CCSongSelectorFontFamily"
SONG_SELECTOR_SIZE_SETTING = "CCSongSelectorFontSize"
SONG_SELECTOR_NORMAL_COLOR_SETTING = "CCSongSelectorColorNormal"
SONG_SELECTOR_CURRENT_COLOR_SETTING = "CCSongSelectorColorCurrent"
SONG_SELECTOR_ACTIVE_COLOR_SETTING = "CCSongSelectorColorActive"
SONG_SELECTOR_HIGHLIGHT_COLOR_SETTING = "CCSongSelectorHighlightColor"
SONG_SELECTOR_ENABLED_SETTING = "CCSongSelectorEnabled"
SONG_SELECTOR_TRACK_SETTING = "CCSongSelectorShowTrackNumbers"
SONG_SELECTOR_AUTO_OPEN_SETTING = "CCSongSelectorAutoOpen"
SONG_SELECTOR_LYRICS_CENTERED_SETTING = "CCSongSelectorLyricsCentered"
SONG_SELECTOR_LYRICS_SYNC_DELAY_SETTING = "CCSongSelectorLyricsSyncDelay"
SONG_SELECTOR_BACKGROUND_SETTING = "CCSongSelectorBackground"
SONG_SELECTOR_TIME_BACKGROUND_SETTING = "CCSongSelectorTimeBackground"
SONG_SELECTOR_SELECTION_TIMEOUT_SETTING = "CCSongSelectorSelectionTimeout"
SONG_SELECTOR_FOCUS_TIMEOUT_SETTING = "CCSongSelectorFocusTimeout"
SONG_SELECTOR_HIGHLIGHT_TIMEOUT_SETTING = "CCSongSelectorHighlightTimeout"
SONG_SELECTOR_RETURN_V127_MIGRATION_SETTING = "CCSongSelectorReturnV127Migrated"
SONG_TIME_CURRENT_SETTING = "CCSongTimeCurrent"
SONG_TIME_REMAINING_SETTING = "CCSongTimeRemaining"
ALBUM_TIME_CURRENT_SETTING = "CCAlbumTimeCurrent"
ALBUM_TIME_REMAINING_SETTING = "CCAlbumTimeRemaining"
PLAYER_TIMES_DIMMED_SETTING = "CCPlayerTimesDimmed"
ALBUM_LINE_OVERFLOW_SETTING = "CCNowPlayingAlbumOverflow"
SONG_LINE_OVERFLOW_SETTING = "CCNowPlayingSongOverflow"
AUDIO_BADGE_SIZE_SETTING = "CCAudioBadgeSize"
AUDIO_BADGE_COLOR_SETTING = "CCAudioBadgeColor"
AUDIO_BADGE_OPACITY_SETTING = "CCAudioBadgeOpacity"
AUDIO_BADGE_RADIUS_SETTING = "CCAudioBadgeRadius"
AUDIO_BADGE_3D_SETTING = "CCAudioBadge3D"
AUDIO_BADGE_TEXTURE_SETTING = "CCAudioBadgeTextureV117"
AUDIO_BADGE_OVERLAY_SETTING = "CCAudioBadgeOverlayV117"
AUDIO_BADGE_CONTENT_SETTING = "CCAudioBadgeContentMode"

DEFAULT_MAIN_FONT = "roboto"
DEFAULT_MAIN_SIZE = "60"
DEFAULT_MAIN_NORMAL_COLOR = "FF505050"
DEFAULT_MAIN_ACTIVE_COLOR = "FF0084FF"
DEFAULT_MAIN_Y_OFFSET = "0"

DEFAULT_SUB_FONT = "default"
DEFAULT_SUB_SIZE = "26"
DEFAULT_SUB_NORMAL_COLOR = "FF999999"
DEFAULT_SUB_ACTIVE_COLOR = "FFFFFFFF"

DEFAULT_HOME_COVER_SIZE = "195"
DEFAULT_HOME_COVER_STYLE = "frame"
DEFAULT_HOME_SHADOW_WIDTH = "14"
DEFAULT_HOME_SHADOW_OFFSET = "4"
DEFAULT_HOME_FLOOR_STYLE = "original"
DEFAULT_HOME_ARTWORK_MODE = "front"
DEFAULT_HOME_NO_COVER = "custom"
DEFAULT_EXIT_BUTTON = "quit"

DEFAULT_SONG_SELECTOR_FONT = "submenu"
DEFAULT_SONG_SELECTOR_SIZE = "26"
DEFAULT_SONG_SELECTOR_NORMAL_COLOR = "FF999999"
DEFAULT_SONG_SELECTOR_CURRENT_COLOR = "FFFFFFFF"
DEFAULT_SONG_SELECTOR_ACTIVE_COLOR = "FFFFFFFF"
DEFAULT_SONG_SELECTOR_HIGHLIGHT_COLOR = "default"
DEFAULT_SONG_SELECTOR_ENABLED = "true"
DEFAULT_SONG_SELECTOR_TRACK = "false"
DEFAULT_SONG_SELECTOR_AUTO_OPEN = "false"
DEFAULT_SONG_SELECTOR_LYRICS_CENTERED = "true"
DEFAULT_SONG_SELECTOR_LYRICS_SYNC_DELAY = "0.25"
DEFAULT_SONG_SELECTOR_BACKGROUND = "submenu"
DEFAULT_SONG_SELECTOR_TIME_BACKGROUND = "transparent"
DEFAULT_SONG_SELECTOR_SELECTION_TIMEOUT = "5"
DEFAULT_SONG_SELECTOR_FOCUS_TIMEOUT = "30"
DEFAULT_SONG_SELECTOR_HIGHLIGHT_TIMEOUT = "10"
DEFAULT_SONG_TIME_CURRENT = "true"
DEFAULT_SONG_TIME_REMAINING = "true"
DEFAULT_ALBUM_TIME_CURRENT = "true"
DEFAULT_ALBUM_TIME_REMAINING = "true"
DEFAULT_PLAYER_TIMES_DIMMED = "false"
DEFAULT_ALBUM_LINE_OVERFLOW = "wrap"
DEFAULT_SONG_LINE_OVERFLOW = "wrap"
DEFAULT_AUDIO_BADGE_SIZE = "90"
DEFAULT_AUDIO_BADGE_COLOR = "submenu"
DEFAULT_AUDIO_BADGE_OPACITY = "55"
DEFAULT_AUDIO_BADGE_RADIUS = "30"
DEFAULT_AUDIO_BADGE_3D = "true"
DEFAULT_AUDIO_BADGE_CONTENT = "logo"

MAIN_FONTS = [("roboto", "Roboto Bold"), ("montserrat", "Montserrat Black")]
MAIN_SIZES = ["42", "48", "54", "60", "66", "72"]

MAIN_Y_OFFSETS = [str(v) for v in range(-250, 301, 25)]

SUB_FONTS = [
    ("default", "Skin default"),
    ("roboto", "Roboto Regular"),
    ("robotobold", "Roboto Bold"),
    ("montserrat", "Montserrat Black"),
]
SUB_SIZES = [str(v) for v in range(20, 31)]

SONG_SELECTOR_FONTS = [("submenu", "Same as submenu"), ("roboto", "Roboto Regular"), ("robotobold", "Roboto Bold"), ("montserrat", "Montserrat Black")]
SONG_SELECTOR_SIZES = SUB_SIZES
SONG_SELECTOR_BACKGROUNDS = [("submenu", "Same as submenu"), ("transparent", "Transparent (gray)"), ("off", "Off")]
SONG_SELECTOR_TIME_BACKGROUNDS = [("submenu", "Same as submenu"), ("transparent", "Transparent (gray)"), ("off", "Off")]
SONG_SELECTOR_SELECTION_TIMEOUTS = [("0", "Off"), ("5", "5 s"), ("10", "10 s"), ("15", "15 s"), ("30", "30 s"), ("60", "60 s")]
SONG_SELECTOR_FOCUS_TIMEOUTS = [("0", "Off"), ("10", "10 s"), ("20", "20 s"), ("30", "30 s"), ("60", "60 s")]
SONG_SELECTOR_HIGHLIGHT_TIMEOUTS = [("0", "Off"), ("5", "5 s"), ("10", "10 s"), ("15", "15 s"), ("30", "30 s"), ("60", "60 s")]
SONG_SELECTOR_LYRICS_SYNC_DELAYS = [("{:.2f}".format(v / 100.0), "{:.2f} s".format(v / 100.0)) for v in range(0, 101, 5)]
AUDIO_BADGE_SIZES = [(v, v + " %") for v in ("80", "90", "100", "110", "120", "130", "140", "150", "160", "170", "180")]
AUDIO_BADGE_CONTENTS = [("logo", "Logo"), ("text", "Text")]
AUDIO_BADGE_COLORS = [("black", "Black"), ("anthracite", "Anthracite"), ("blue", "Confluence blue"), ("submenu", "Same as submenu")]
AUDIO_BADGE_OPACITIES = [(v, v + " %") for v in ("25", "40", "55", "70", "85")]
ALBUM_LINE_OVERFLOWS = [("truncate", "Truncate"), ("scroll", "Scroll"), ("wrap", "Wrap")]

HOME_COVER_SIZES = [
    ("195", "Original (195 px)"),
    ("210", "210 px"),
    ("225", "225 px"),
    ("240", "240 px"),
    ("270", "270 px"),
    ("300", "300 px"),
    ("330", "330 px"),
    ("360", "360 px"),
    ("390", "390 px (2x)"),
    ("420", "420 px"),
    ("450", "450 px"),
    ("480", "480 px"),
    ("510", "510 px"),
    ("540", "540 px"),
    ("585", "585 px (3x)"),
]
HOME_COVER_STYLES = [
    ("frame", "Frame"),
    ("hardshadow", "Hard shadow"),
    ("softshadow", "Soft shadow"),
]
HOME_SHADOW_WIDTHS = [("6", "6 px"), ("10", "10 px"), ("14", "14 px"), ("18", "18 px"), ("22", "22 px"), ("26", "26 px"), ("30", "30 px"), ("34", "34 px"), ("38", "38 px")]
HOME_SHADOW_OFFSETS = [("0", "0 px"), ("2", "2 px"), ("4", "4 px"), ("6", "6 px"), ("8", "8 px"), ("10", "10 px"), ("12", "12 px"), ("14", "14 px"), ("16", "16 px"), ("18", "18 px"), ("20", "20 px"), ("22", "22 px"), ("24", "24 px")]
HOME_FLOOR_STYLES = [
    ("original", "Original"),
    ("dark", "Dark"),
    ("transparent", "Transparent"),
    ("off", "Off"),
]
HOME_NO_COVER_STYLES = [
    ("kodi", "Kodi Default"),
    ("custom", "Confluence-jjs default"),
    ("free", "Choose image"),
]
EXIT_BUTTON_ACTIONS = [("quit", "Quit"), ("power", "Power menu")]

# Name, ARGB. "Default" is supplied separately because normal/active and
# main/submenu deliberately have different Confluence defaults.
COLOR_PRESETS = [
    ("White", "FFFFFFFF"),
    ("Light gray", "FFC0C0C0"),
    ("Gray", "FF808080"),
    ("Black", "FF000000"),
    ("Blue", "FF0066CC"),
    ("Light blue", "FF33B5E5"),
    ("Red", "FFE53935"),
    ("Green", "FF43A047"),
    ("Yellow", "FFFDD835"),
    ("Orange", "FFF57C00"),
    ("Purple", "FF8E24AA"),
]


def _get(name, default=""):
    value = xbmc.getInfoLabel("Skin.String({})".format(name))
    return value or default


def _quote(value):
    return '"{}"'.format(str(value).replace('\\', '\\\\').replace('"', '\\"'))


def _set(name, value):
    xbmc.executebuiltin("Skin.SetString({},{})".format(_quote(name), _quote(value)))


def ensure_defaults():
    if not _get("DefaultHomeFocus"):
        _set("DefaultHomeFocus", "5")
    if not _get("DefaultHomeFocusItem"):
        try:
            label = xbmcaddon.Addon("skin.confluence.custom").getLocalizedString(31956)
        except Exception:
            label = ""
        _set("DefaultHomeFocusItem", label or "Music")

    defaults = (
        (MAIN_FONT_SETTING, DEFAULT_MAIN_FONT),
        (MAIN_SIZE_SETTING, DEFAULT_MAIN_SIZE),
        (MAIN_NORMAL_COLOR_SETTING, DEFAULT_MAIN_NORMAL_COLOR),
        (MAIN_ACTIVE_COLOR_SETTING, DEFAULT_MAIN_ACTIVE_COLOR),
        (MAIN_Y_OFFSET_SETTING, DEFAULT_MAIN_Y_OFFSET),
        (SUB_FONT_SETTING, DEFAULT_SUB_FONT),
        (SUB_SIZE_SETTING, DEFAULT_SUB_SIZE),
        (SUB_NORMAL_COLOR_SETTING, DEFAULT_SUB_NORMAL_COLOR),
        (SUB_ACTIVE_COLOR_SETTING, DEFAULT_SUB_ACTIVE_COLOR),
        (HOME_COVER_SIZE_SETTING, DEFAULT_HOME_COVER_SIZE),
        (HOME_COVER_STYLE_SETTING, DEFAULT_HOME_COVER_STYLE),
        (HOME_SHADOW_WIDTH_SETTING, DEFAULT_HOME_SHADOW_WIDTH),
        (HOME_SHADOW_OFFSET_SETTING, DEFAULT_HOME_SHADOW_OFFSET),
        (HOME_FLOOR_STYLE_SETTING, DEFAULT_HOME_FLOOR_STYLE),
        (HOME_ARTWORK_MODE_SETTING, DEFAULT_HOME_ARTWORK_MODE),
        (HOME_NO_COVER_SETTING, DEFAULT_HOME_NO_COVER),
        (EXIT_BUTTON_SETTING, DEFAULT_EXIT_BUTTON),
        (SONG_SELECTOR_FONT_SETTING, DEFAULT_SONG_SELECTOR_FONT),
        (SONG_SELECTOR_SIZE_SETTING, DEFAULT_SONG_SELECTOR_SIZE),
        (SONG_SELECTOR_NORMAL_COLOR_SETTING, DEFAULT_SONG_SELECTOR_NORMAL_COLOR),
        (SONG_SELECTOR_CURRENT_COLOR_SETTING, DEFAULT_SONG_SELECTOR_CURRENT_COLOR),
        (SONG_SELECTOR_ACTIVE_COLOR_SETTING, DEFAULT_SONG_SELECTOR_ACTIVE_COLOR),
        (SONG_SELECTOR_HIGHLIGHT_COLOR_SETTING, DEFAULT_SONG_SELECTOR_HIGHLIGHT_COLOR),
        (SONG_SELECTOR_ENABLED_SETTING, DEFAULT_SONG_SELECTOR_ENABLED),
        (SONG_SELECTOR_TRACK_SETTING, DEFAULT_SONG_SELECTOR_TRACK),
        (SONG_SELECTOR_AUTO_OPEN_SETTING, DEFAULT_SONG_SELECTOR_AUTO_OPEN),
        (SONG_SELECTOR_LYRICS_CENTERED_SETTING, DEFAULT_SONG_SELECTOR_LYRICS_CENTERED),
        (SONG_SELECTOR_LYRICS_SYNC_DELAY_SETTING, DEFAULT_SONG_SELECTOR_LYRICS_SYNC_DELAY),
        (SONG_SELECTOR_BACKGROUND_SETTING, DEFAULT_SONG_SELECTOR_BACKGROUND),
        (SONG_SELECTOR_TIME_BACKGROUND_SETTING, DEFAULT_SONG_SELECTOR_TIME_BACKGROUND),
        (SONG_SELECTOR_SELECTION_TIMEOUT_SETTING, DEFAULT_SONG_SELECTOR_SELECTION_TIMEOUT),
        (SONG_SELECTOR_FOCUS_TIMEOUT_SETTING, DEFAULT_SONG_SELECTOR_FOCUS_TIMEOUT),
        (ALBUM_LINE_OVERFLOW_SETTING, DEFAULT_ALBUM_LINE_OVERFLOW),
        (SONG_LINE_OVERFLOW_SETTING, DEFAULT_SONG_LINE_OVERFLOW),
        (AUDIO_BADGE_SIZE_SETTING, DEFAULT_AUDIO_BADGE_SIZE),
        (AUDIO_BADGE_COLOR_SETTING, DEFAULT_AUDIO_BADGE_COLOR),
        (AUDIO_BADGE_OPACITY_SETTING, DEFAULT_AUDIO_BADGE_OPACITY),
        (AUDIO_BADGE_RADIUS_SETTING, DEFAULT_AUDIO_BADGE_RADIUS),
        (AUDIO_BADGE_3D_SETTING, DEFAULT_AUDIO_BADGE_3D),
        (AUDIO_BADGE_CONTENT_SETTING, DEFAULT_AUDIO_BADGE_CONTENT),
    )
    for name, value in defaults:
        if not _get(name):
            _set(name, value)
    # Legacy: the old single shadow mode is the soft shadow mode.
    if _get(HOME_COVER_STYLE_SETTING).lower() == "shadow":
        _set(HOME_COVER_STYLE_SETTING, "softshadow")

    # 5.0.32 used a near-white value as submenu focus default.
    # Confluence itself uses pure white; migrate only that legacy default.
    if _get(SUB_ACTIVE_COLOR_SETTING).upper() == "FFF1F1F1":
        _set(SUB_ACTIVE_COLOR_SETTING, DEFAULT_SUB_ACTIVE_COLOR)
    # 5.0.32/5.0.33 offered oversized submenu fonts. Clamp them to the new maximum.
    if _get(SUB_SIZE_SETTING) in ("34", "38"):
        _set(SUB_SIZE_SETTING, "30")
    # 5.0.47 stored selector font settings but did not expose/use them. Preserve its look.
    if _get(SONG_SELECTOR_FONT_SETTING).lower() == "default":
        _set(SONG_SELECTOR_FONT_SETTING, "submenu")
    # 5.0.127 changes the old dormant/default 10-second selector value into the
    # active return-to-playing timeout requested for the always-visible cursor.
    # Migrate that legacy default once; later user choices are left untouched.
    if _get(SONG_SELECTOR_RETURN_V127_MIGRATION_SETTING) != "1":
        if _get(SONG_SELECTOR_SELECTION_TIMEOUT_SETTING, "10") == "10":
            _set(SONG_SELECTOR_SELECTION_TIMEOUT_SETTING, "5")
        _set(SONG_SELECTOR_RETURN_V127_MIGRATION_SETTING, "1")
    _update_audio_badge_texture()


def _choose(title, setting, values_and_labels, default):
    current = _get(setting, default)
    values = [item[0] for item in values_and_labels]
    labels = [item[1] for item in values_and_labels]
    try:
        preselect = values.index(current)
    except ValueError:
        try:
            preselect = values.index(default)
        except ValueError:
            preselect = 0
    choice = xbmcgui.Dialog().select(title, labels, preselect=preselect)
    if choice >= 0:
        _set(setting, values[choice])


def choose_main_font():
    _choose("Main menu font", MAIN_FONT_SETTING, MAIN_FONTS, DEFAULT_MAIN_FONT)


def choose_main_size():
    _choose(
        "Main menu font size",
        MAIN_SIZE_SETTING,
        [(v, "{} px".format(v)) for v in MAIN_SIZES],
        DEFAULT_MAIN_SIZE,
    )


def choose_main_y_offset():
    values = []
    for v in MAIN_Y_OFFSETS:
        n = int(v)
        if n == 0:
            label = "Default"
        elif n < 0:
            label = "{} px higher".format(abs(n))
        else:
            label = "{} px lower".format(n)
        values.append((v, label))
    _choose("Vertical menu position", MAIN_Y_OFFSET_SETTING, values, DEFAULT_MAIN_Y_OFFSET)


def choose_sub_font():
    _choose("Submenu font", SUB_FONT_SETTING, SUB_FONTS, DEFAULT_SUB_FONT)


def choose_sub_size():
    _choose(
        "Submenu font size",
        SUB_SIZE_SETTING,
        [(v, "{} px".format(v)) for v in SUB_SIZES],
        DEFAULT_SUB_SIZE,
    )


def choose_color(title, setting, default_value):
    choices = [(default_value, "Default")] + [(value, label) for label, value in COLOR_PRESETS if value.upper() != default_value.upper()]
    current = _get(setting, default_value).upper()
    values = [item[0].upper() for item in choices]
    labels = [item[1] for item in choices]
    try:
        preselect = values.index(current)
    except ValueError:
        preselect = 0
    choice = xbmcgui.Dialog().select(title, labels, preselect=preselect)
    if choice >= 0:
        _set(setting, choices[choice][0])



def choose_exit_button():
    _choose(
        "Exit button",
        EXIT_BUTTON_SETTING,
        EXIT_BUTTON_ACTIONS,
        DEFAULT_EXIT_BUTTON,
    )


def choose_home_cover_size():
    _choose(
        "Home screen cover size",
        HOME_COVER_SIZE_SETTING,
        HOME_COVER_SIZES,
        DEFAULT_HOME_COVER_SIZE,
    )


def choose_home_cover_style():
    _choose(
        "Home screen cover appearance",
        HOME_COVER_STYLE_SETTING,
        HOME_COVER_STYLES,
        DEFAULT_HOME_COVER_STYLE,
    )


def choose_home_shadow_width():
    _choose(
        "Home screen shadow width",
        HOME_SHADOW_WIDTH_SETTING,
        HOME_SHADOW_WIDTHS,
        DEFAULT_HOME_SHADOW_WIDTH,
    )


def choose_home_shadow_offset():
    _choose(
        "Home screen shadow offset",
        HOME_SHADOW_OFFSET_SETTING,
        HOME_SHADOW_OFFSETS,
        DEFAULT_HOME_SHADOW_OFFSET,
    )


def choose_home_floor_style():
    _choose(
        "Home screen bottom bar",
        HOME_FLOOR_STYLE_SETTING,
        HOME_FLOOR_STYLES,
        DEFAULT_HOME_FLOOR_STYLE,
    )


def restore_skin_default_background():
    # The regular Confluence image picker intentionally stays untouched. This
    # action only provides a deterministic way back to the wallpaper shipped
    # with Confluence-jjs, for both normal and master profiles.
    _set("CustomBackgroundPath", SKIN_DEFAULT_BACKGROUND)
    _set("MasterCustomBackgroundPath", SKIN_DEFAULT_BACKGROUND)
    xbmc.executebuiltin("Skin.SetBool(UseCustomBackground,true)")
    xbmcgui.Dialog().notification(
        "Confluence-jjs", "Skin default background restored", xbmcgui.NOTIFICATION_INFO, 2500
    )


def choose_home_no_cover():
    current = _get(HOME_NO_COVER_SETTING, DEFAULT_HOME_NO_COVER).lower()
    if current == "jewelcase":
        current = "custom"
    elif current == "standard":
        current = "kodi"
    values = [item[0] for item in HOME_NO_COVER_STYLES]
    labels = [item[1] for item in HOME_NO_COVER_STYLES]
    try:
        preselect = values.index(current)
    except ValueError:
        preselect = 1
    index = xbmcgui.Dialog().select("No-cover image", labels, preselect=preselect)
    if index < 0:
        return
    mode = values[index]
    if mode == "free":
        image = xbmcgui.Dialog().browseSingle(
            2, "Choose no-cover image", "files", ".png|.jpg|.jpeg|.webp|.bmp"
        )
        if not image:
            return
        if not save_free_image(image):
            xbmcgui.Dialog().notification(
                "Confluence-jjs", "Image could not be saved", xbmcgui.NOTIFICATION_ERROR, 3500
            )
            return
    applied_mode, ok = apply_no_cover(mode, reload_skin=True)
    if not ok:
        xbmcgui.Dialog().notification(
            "Confluence-jjs", "No-cover image could not be activated", xbmcgui.NOTIFICATION_ERROR, 3500
        )
        return


def choose_song_selector_font():
    _choose("Song popup font", SONG_SELECTOR_FONT_SETTING, SONG_SELECTOR_FONTS, DEFAULT_SONG_SELECTOR_FONT)


def choose_song_selector_size():
    _choose(
        "Song popup font size",
        SONG_SELECTOR_SIZE_SETTING,
        [(v, "{} px".format(v)) for v in SONG_SELECTOR_SIZES],
        DEFAULT_SONG_SELECTOR_SIZE,
    )


def choose_song_selector_highlight_color():
    choices = [(DEFAULT_SONG_SELECTOR_HIGHLIGHT_COLOR, "Default")] + [(value, label) for label, value in COLOR_PRESETS]
    current = _get(SONG_SELECTOR_HIGHLIGHT_COLOR_SETTING, DEFAULT_SONG_SELECTOR_HIGHLIGHT_COLOR)
    values = [item[0].upper() for item in choices]
    labels = [item[1] for item in choices]
    try:
        preselect = values.index(current.upper())
    except ValueError:
        preselect = 0
    choice = xbmcgui.Dialog().select("Song popup highlight", labels, preselect=preselect)
    if choice >= 0:
        _set(SONG_SELECTOR_HIGHLIGHT_COLOR_SETTING, choices[choice][0])


def toggle_song_selector():
    current = _get(SONG_SELECTOR_ENABLED_SETTING, DEFAULT_SONG_SELECTOR_ENABLED).lower()
    _set(SONG_SELECTOR_ENABLED_SETTING, "false" if current != "false" else "true")


def toggle_song_selector_track_numbers():
    current = _get(SONG_SELECTOR_TRACK_SETTING, DEFAULT_SONG_SELECTOR_TRACK).lower()
    _set(SONG_SELECTOR_TRACK_SETTING, "false" if current == "true" else "true")


def toggle_song_selector_auto_open():
    _toggle_bool_setting(SONG_SELECTOR_AUTO_OPEN_SETTING, DEFAULT_SONG_SELECTOR_AUTO_OPEN)


def toggle_song_selector_lyrics_centered():
    _toggle_bool_setting(SONG_SELECTOR_LYRICS_CENTERED_SETTING, DEFAULT_SONG_SELECTOR_LYRICS_CENTERED)


def choose_song_selector_lyrics_sync_delay():
    _choose(
        "Lyrics sync delay",
        SONG_SELECTOR_LYRICS_SYNC_DELAY_SETTING,
        SONG_SELECTOR_LYRICS_SYNC_DELAYS,
        DEFAULT_SONG_SELECTOR_LYRICS_SYNC_DELAY,
    )


def choose_song_selector_background():
    _choose("Song popup background", SONG_SELECTOR_BACKGROUND_SETTING, SONG_SELECTOR_BACKGROUNDS, DEFAULT_SONG_SELECTOR_BACKGROUND)


def choose_song_selector_time_background():
    _choose("Time badge background", SONG_SELECTOR_TIME_BACKGROUND_SETTING, SONG_SELECTOR_TIME_BACKGROUNDS, DEFAULT_SONG_SELECTOR_TIME_BACKGROUND)


def choose_song_selector_selection_timeout():
    _choose("Return selection to current song", SONG_SELECTOR_SELECTION_TIMEOUT_SETTING, SONG_SELECTOR_SELECTION_TIMEOUTS, DEFAULT_SONG_SELECTOR_SELECTION_TIMEOUT)


def choose_song_selector_focus_timeout():
    _choose("Return focus to menu bar", SONG_SELECTOR_FOCUS_TIMEOUT_SETTING, SONG_SELECTOR_FOCUS_TIMEOUTS, DEFAULT_SONG_SELECTOR_FOCUS_TIMEOUT)

def choose_song_selector_highlight_timeout():
    _choose("Return selection to current song", SONG_SELECTOR_SELECTION_TIMEOUT_SETTING, SONG_SELECTOR_SELECTION_TIMEOUTS, DEFAULT_SONG_SELECTOR_SELECTION_TIMEOUT)


def _toggle_bool_setting(name, default="true"):
    current = _get(name, default).lower()
    _set(name, "false" if current != "false" else "true")


def _update_audio_badge_texture():
    # 5.0.117: the tile is rendered from exact-size assets. This avoids Kodi's
    # nine-slice border overlap at small badge heights (the filled rectangle
    # that could extend across/through the rounded corners in 5.0.116).
    size = _get(AUDIO_BADGE_SIZE_SETTING, DEFAULT_AUDIO_BADGE_SIZE)
    opacity = _get(AUDIO_BADGE_OPACITY_SETTING, DEFAULT_AUDIO_BADGE_OPACITY)
    radius = DEFAULT_AUDIO_BADGE_RADIUS
    if _get(AUDIO_BADGE_RADIUS_SETTING, DEFAULT_AUDIO_BADGE_RADIUS) != radius:
        _set(AUDIO_BADGE_RADIUS_SETTING, radius)
    if size not in tuple(v for v, _ in AUDIO_BADGE_SIZES):
        size = DEFAULT_AUDIO_BADGE_SIZE
    if opacity not in tuple(v for v, _ in AUDIO_BADGE_OPACITIES):
        opacity = DEFAULT_AUDIO_BADGE_OPACITY
    _set(AUDIO_BADGE_TEXTURE_SETTING, "CCAudioBadgeBase_s{}_o{}_r{}.png".format(size, opacity, radius))
    _set(AUDIO_BADGE_OVERLAY_SETTING, "CCAudioBadge3D_s{}_r{}.png".format(size, radius))


def _choose_audio_badge(title, setting, choices, default):
    current = _get(setting, default)
    values = [item[0] for item in choices]
    labels = [item[1] for item in choices]
    try:
        preselect = values.index(current)
    except ValueError:
        preselect = values.index(default) if default in values else 0
    choice = xbmcgui.Dialog().select(title, labels, preselect=preselect)
    if choice >= 0:
        _set(setting, values[choice])
        _update_audio_badge_texture()


def choose_album_line_overflow():
    _choose("Long album titles", ALBUM_LINE_OVERFLOW_SETTING, ALBUM_LINE_OVERFLOWS, DEFAULT_ALBUM_LINE_OVERFLOW)


def choose_song_line_overflow():
    _choose("Long song titles", SONG_LINE_OVERFLOW_SETTING, ALBUM_LINE_OVERFLOWS, DEFAULT_SONG_LINE_OVERFLOW)


def choose_audio_badge_content():
    _choose("Codec-Darstellung", AUDIO_BADGE_CONTENT_SETTING, AUDIO_BADGE_CONTENTS, DEFAULT_AUDIO_BADGE_CONTENT)


def choose_audio_badge_size():
    _choose_audio_badge("Audio badge size", AUDIO_BADGE_SIZE_SETTING, AUDIO_BADGE_SIZES, DEFAULT_AUDIO_BADGE_SIZE)


def choose_audio_badge_color():
    _choose_audio_badge("Badge background", AUDIO_BADGE_COLOR_SETTING, AUDIO_BADGE_COLORS, DEFAULT_AUDIO_BADGE_COLOR)


def choose_audio_badge_opacity():
    _choose_audio_badge("Badge opacity", AUDIO_BADGE_OPACITY_SETTING, AUDIO_BADGE_OPACITIES, DEFAULT_AUDIO_BADGE_OPACITY)


def toggle_audio_badge_3d():
    _toggle_bool_setting(AUDIO_BADGE_3D_SETTING, DEFAULT_AUDIO_BADGE_3D)
    _update_audio_badge_texture()


def reset_playback_info():
    xbmc.executebuiltin("Skin.SetBool(CCNowPlayingAlbumYear)")
    xbmc.executebuiltin("Skin.SetBool(CCNowPlayingAudioLogo)")
    _set(SONG_TIME_CURRENT_SETTING, DEFAULT_SONG_TIME_CURRENT)
    _set(SONG_TIME_REMAINING_SETTING, DEFAULT_SONG_TIME_REMAINING)
    _set(ALBUM_TIME_CURRENT_SETTING, DEFAULT_ALBUM_TIME_CURRENT)
    _set(ALBUM_TIME_REMAINING_SETTING, DEFAULT_ALBUM_TIME_REMAINING)
    _set(PLAYER_TIMES_DIMMED_SETTING, DEFAULT_PLAYER_TIMES_DIMMED)
    xbmc.executebuiltin("Skin.Reset(CCPlayerTimesBadges)")
    xbmc.executebuiltin("Skin.Reset(CCPlayerTimeBadgesEqual)")
    _set(ALBUM_LINE_OVERFLOW_SETTING, DEFAULT_ALBUM_LINE_OVERFLOW)
    _set(SONG_LINE_OVERFLOW_SETTING, DEFAULT_SONG_LINE_OVERFLOW)
    _set(AUDIO_BADGE_SIZE_SETTING, DEFAULT_AUDIO_BADGE_SIZE)
    _set(AUDIO_BADGE_COLOR_SETTING, DEFAULT_AUDIO_BADGE_COLOR)
    _set(AUDIO_BADGE_OPACITY_SETTING, DEFAULT_AUDIO_BADGE_OPACITY)
    _set(AUDIO_BADGE_RADIUS_SETTING, DEFAULT_AUDIO_BADGE_RADIUS)
    _set(AUDIO_BADGE_3D_SETTING, DEFAULT_AUDIO_BADGE_3D)
    _set(AUDIO_BADGE_CONTENT_SETTING, DEFAULT_AUDIO_BADGE_CONTENT)
    _update_audio_badge_texture()
    xbmcgui.Dialog().notification("Confluence-jjs", "Playback information reset", xbmcgui.NOTIFICATION_INFO, 2500)


def reset_song_selector():
    _set(SONG_SELECTOR_ENABLED_SETTING, DEFAULT_SONG_SELECTOR_ENABLED)
    _set(SONG_SELECTOR_FONT_SETTING, DEFAULT_SONG_SELECTOR_FONT)
    _set(SONG_SELECTOR_SIZE_SETTING, DEFAULT_SONG_SELECTOR_SIZE)
    _set(SONG_SELECTOR_TRACK_SETTING, DEFAULT_SONG_SELECTOR_TRACK)
    _set(SONG_SELECTOR_AUTO_OPEN_SETTING, DEFAULT_SONG_SELECTOR_AUTO_OPEN)
    _set(SONG_SELECTOR_LYRICS_CENTERED_SETTING, DEFAULT_SONG_SELECTOR_LYRICS_CENTERED)
    _set(SONG_SELECTOR_LYRICS_SYNC_DELAY_SETTING, DEFAULT_SONG_SELECTOR_LYRICS_SYNC_DELAY)
    _set(SONG_SELECTOR_BACKGROUND_SETTING, DEFAULT_SONG_SELECTOR_BACKGROUND)
    _set(SONG_SELECTOR_TIME_BACKGROUND_SETTING, DEFAULT_SONG_SELECTOR_TIME_BACKGROUND)
    _set(SONG_SELECTOR_SELECTION_TIMEOUT_SETTING, DEFAULT_SONG_SELECTOR_SELECTION_TIMEOUT)
    _set(SONG_SELECTOR_FOCUS_TIMEOUT_SETTING, DEFAULT_SONG_SELECTOR_FOCUS_TIMEOUT)
    _set(SONG_SELECTOR_HIGHLIGHT_TIMEOUT_SETTING, DEFAULT_SONG_SELECTOR_HIGHLIGHT_TIMEOUT)
    xbmcgui.Dialog().notification(
        "Confluence-jjs", "Song popup reset", xbmcgui.NOTIFICATION_INFO, 2500
    )




def reset_home():
    _set(HOME_COVER_SIZE_SETTING, DEFAULT_HOME_COVER_SIZE)
    _set(HOME_COVER_STYLE_SETTING, DEFAULT_HOME_COVER_STYLE)
    _set(HOME_SHADOW_WIDTH_SETTING, DEFAULT_HOME_SHADOW_WIDTH)
    _set(HOME_SHADOW_OFFSET_SETTING, DEFAULT_HOME_SHADOW_OFFSET)
    _set(HOME_FLOOR_STYLE_SETTING, DEFAULT_HOME_FLOOR_STYLE)
    _set(HOME_ARTWORK_MODE_SETTING, DEFAULT_HOME_ARTWORK_MODE)
    _set(HOME_NO_COVER_SETTING, DEFAULT_HOME_NO_COVER)
    xbmc.executebuiltin("Skin.Reset(CCHomePlaybackFanart)")
    xbmc.executebuiltin("Skin.Reset(CCHomeMusicDisplayAboveMenu)")
    apply_no_cover(DEFAULT_HOME_NO_COVER, reload_skin=False)
    xbmc.executebuiltin("ReloadSkin()")
    xbmcgui.Dialog().notification(
        "Confluence-jjs", "Home screen appearance reset", xbmcgui.NOTIFICATION_INFO, 2500
    )

def reset_main():
    _set(MAIN_FONT_SETTING, DEFAULT_MAIN_FONT)
    _set(MAIN_SIZE_SETTING, DEFAULT_MAIN_SIZE)
    _set(MAIN_NORMAL_COLOR_SETTING, DEFAULT_MAIN_NORMAL_COLOR)
    _set(MAIN_ACTIVE_COLOR_SETTING, DEFAULT_MAIN_ACTIVE_COLOR)
    _set(MAIN_Y_OFFSET_SETTING, DEFAULT_MAIN_Y_OFFSET)
    xbmcgui.Dialog().notification(
        "Confluence-jjs", "Main menu appearance reset", xbmcgui.NOTIFICATION_INFO, 2500
    )


def reset_sub():
    _set(SUB_FONT_SETTING, DEFAULT_SUB_FONT)
    _set(SUB_SIZE_SETTING, DEFAULT_SUB_SIZE)
    _set(SUB_NORMAL_COLOR_SETTING, DEFAULT_SUB_NORMAL_COLOR)
    _set(SUB_ACTIVE_COLOR_SETTING, DEFAULT_SUB_ACTIVE_COLOR)
    xbmcgui.Dialog().notification(
        "Confluence-jjs", "Submenu appearance reset", xbmcgui.NOTIFICATION_INFO, 2500
    )


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    ensure_defaults()
    if mode == "font":
        choose_main_font()
    elif mode == "size":
        choose_main_size()
    elif mode == "normalcolor":
        choose_color("Main menu normal color", MAIN_NORMAL_COLOR_SETTING, DEFAULT_MAIN_NORMAL_COLOR)
    elif mode == "activecolor":
        choose_color("Main menu active color", MAIN_ACTIVE_COLOR_SETTING, DEFAULT_MAIN_ACTIVE_COLOR)
    elif mode == "yoffset":
        choose_main_y_offset()
    elif mode == "reset":
        reset_main()
    elif mode == "subfont":
        choose_sub_font()
    elif mode == "subsize":
        choose_sub_size()
    elif mode == "subnormalcolor":
        choose_color("Submenu normal color", SUB_NORMAL_COLOR_SETTING, DEFAULT_SUB_NORMAL_COLOR)
    elif mode == "subactivecolor":
        choose_color("Submenu active color", SUB_ACTIVE_COLOR_SETTING, DEFAULT_SUB_ACTIVE_COLOR)
    elif mode == "subreset":
        reset_sub()
    elif mode == "songfont":
        choose_song_selector_font()
    elif mode == "songsize":
        choose_song_selector_size()
    elif mode == "songnormalcolor":
        choose_color("Song selector normal color", SONG_SELECTOR_NORMAL_COLOR_SETTING, DEFAULT_SONG_SELECTOR_NORMAL_COLOR)
    elif mode == "songcurrentcolor":
        choose_color("Current song color", SONG_SELECTOR_CURRENT_COLOR_SETTING, DEFAULT_SONG_SELECTOR_CURRENT_COLOR)
    elif mode == "songactivecolor":
        choose_color("Song selector focus color", SONG_SELECTOR_ACTIVE_COLOR_SETTING, DEFAULT_SONG_SELECTOR_ACTIVE_COLOR)
    elif mode == "songhighlightcolor":
        choose_song_selector_highlight_color()
    elif mode == "songenabled":
        toggle_song_selector()
    elif mode == "songtracknumbers":
        toggle_song_selector_track_numbers()
    elif mode == "songautoopen":
        toggle_song_selector_auto_open()
    elif mode == "songlyricscentered":
        toggle_song_selector_lyrics_centered()
    elif mode == "songlyricssyncdelay":
        choose_song_selector_lyrics_sync_delay()
    elif mode == "songbackground":
        choose_song_selector_background()
    elif mode == "songtimebackground":
        choose_song_selector_time_background()
    elif mode == "songselectiontimeout":
        choose_song_selector_selection_timeout()
    elif mode == "songfocustimeout":
        choose_song_selector_focus_timeout()
    elif mode == "songhighlighttimeout":
        choose_song_selector_highlight_timeout()
    elif mode == "songtimecurrent":
        _toggle_bool_setting(SONG_TIME_CURRENT_SETTING, DEFAULT_SONG_TIME_CURRENT)
    elif mode == "songtimeremaining":
        _toggle_bool_setting(SONG_TIME_REMAINING_SETTING, DEFAULT_SONG_TIME_REMAINING)
    elif mode == "albumtimecurrent":
        _toggle_bool_setting(ALBUM_TIME_CURRENT_SETTING, DEFAULT_ALBUM_TIME_CURRENT)
    elif mode == "albumtimeremaining":
        _toggle_bool_setting(ALBUM_TIME_REMAINING_SETTING, DEFAULT_ALBUM_TIME_REMAINING)
    elif mode == "timesdimmed":
        _toggle_bool_setting(PLAYER_TIMES_DIMMED_SETTING, DEFAULT_PLAYER_TIMES_DIMMED)
    elif mode == "albumoverflow":
        choose_album_line_overflow()
    elif mode == "songoverflow":
        choose_song_line_overflow()
    elif mode == "audiobadgecontent":
        choose_audio_badge_content()
    elif mode == "audiobadgesize":
        choose_audio_badge_size()
    elif mode == "audiobadgecolor":
        choose_audio_badge_color()
    elif mode == "audiobadgeopacity":
        choose_audio_badge_opacity()
    elif mode == "audiobadge3d":
        toggle_audio_badge_3d()
    elif mode == "audiobadgerefresh":
        _update_audio_badge_texture()
    elif mode == "playbackreset":
        reset_playback_info()
    elif mode == "songreset":
        reset_song_selector()
    elif mode == "exitbutton":
        choose_exit_button()
    elif mode == "homecover":
        choose_home_cover_size()
    elif mode == "homecoverstyle":
        choose_home_cover_style()
    elif mode == "homenocover":
        choose_home_no_cover()
    elif mode == "homebackgrounddefault":
        restore_skin_default_background()
    elif mode == "homeshadowwidth":
        choose_home_shadow_width()
    elif mode == "homeshadowoffset":
        choose_home_shadow_offset()
    elif mode == "homefloor":
        choose_home_floor_style()
    elif mode == "homereset":
        reset_home()


if __name__ == "__main__":
    main()
