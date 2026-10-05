# -*- coding: utf-8 -*-
import sys

import xbmc
import xbmcgui
import xbmcvfs

HOME_WINDOW_ID = 10000
COVER_SIZE_SETTING = "CCHomeMusicCoverSize"
COVER_DYNAMIC_SETTING = "CCHomeMusicCoverDynamic"
Y_OFFSET_SETTING = "CCMainMenuYOffset"
SHADOW_WIDTH_SETTING = "CCHomeMusicShadowWidth"
SHADOW_OFFSET_SETTING = "CCHomeMusicShadowOffset"
COVER_DEFAULT = 195
Y_DEFAULT = 0
Y_MIN = -250
Y_MAX = 300
STEP = 25
SHADOW_WIDTH_DEFAULT = 14
SHADOW_OFFSET_DEFAULT = 4
SHADOW_STEP = 1
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
DIALOG_XML = "CustomLiveHomeAdjust.xml"
BADGE_TITLE_PROP = "ConfluenceCustom.LiveAdjust.Title"
BADGE_HELP_PROP = "ConfluenceCustom.LiveAdjust.Help"
ADJUST_ACTIVE_PROP = "ConfluenceCustom.LiveAdjust.Active"
ID_MAIN_FRAME = 9301
ID_MAIN_SHADOW_COVER = 9302
ID_SELECTOR_SINGLE_FRAME = 9303
ID_SELECTOR_SINGLE_SHADOW_COVER = 9304
ID_SELECTOR_PAIR_FRAME_FRONT = 9305
ID_SELECTOR_PAIR_FRAME_BACK = 9306
ID_SELECTOR_PAIR_SHADOW_FRONT = 9307
ID_SELECTOR_PAIR_SHADOW_BACK = 9308
ID_MAIN_INFO = 9309
DYNAMIC_SHADOW_CONTROLS = (
    (9400, 9410, "main"),
    (9420, 9430, "single"),
)
DYNAMIC_PAIR_SHADOW_CONTROLS = (
    ((9440, 9441, 9442), (9450, 9451, 9452), "pair_front"),
    ((9460, 9461, 9462), (9470, 9471, 9472), "pair_back"),
)


def _skin_string(name, default=""):
    value = xbmc.getInfoLabel("Skin.String({})".format(name))
    return value if value else default


def _skin_int(name, default):
    try:
        return int(_skin_string(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


def _set_string(name, value):
    xbmc.executebuiltin("Skin.SetString({},{})".format(name, int(value)))


def _is_dynamic():
    return xbmc.getCondVisibility("Skin.HasSetting({})".format(COVER_DYNAMIC_SETTING))


def _set_dynamic(enabled):
    if enabled:
        xbmc.executebuiltin("Skin.SetBool({})".format(COVER_DYNAMIC_SETTING))
    else:
        xbmc.executebuiltin("Skin.Reset({})".format(COVER_DYNAMIC_SETTING))


def _control(window, control_id):
    try:
        return window.getControl(control_id)
    except Exception:
        return None


def _set_geometry(control, x, y, width, height):
    if control is None:
        return
    control.setPosition(int(x), int(y))
    control.setWidth(max(1, int(width)))
    control.setHeight(max(1, int(height)))


def _shadow_cover_rect(kind, size):
    selector_y = (600 - size) // 2
    if kind == "main":
        return 30, 495 - size
    if kind == "single":
        return (1920 - size) // 2, selector_y
    if kind == "pair_front":
        return 940 - size, selector_y
    return 980, selector_y


def _set_shadow_piece(control, rect):
    if control is None:
        return
    if rect is None:
        _set_geometry(control, -10000, -10000, 1, 1)
        return
    _set_geometry(control, *rect)


def _pair_shadow_rects(cover_x, cover_y, size, width, offset):
    # Build the visible part of the shifted/enlarged shadow explicitly.
    # This is the rectangle S minus the cover rectangle C. Because offset
    # is never negative, the result is at most: right strip, bottom strip,
    # and bottom-right corner. No control is ever drawn above or left.
    size = int(size)
    width = max(0, int(width))
    offset = max(0, int(offset))
    shadow_x = int(cover_x) + offset
    shadow_y = int(cover_y) + offset
    shadow_right = shadow_x + size + width
    shadow_bottom = shadow_y + size + width
    cover_right = int(cover_x) + size
    cover_bottom = int(cover_y) + size

    right_x = max(cover_right, shadow_x)
    right_y = shadow_y
    right_w = shadow_right - right_x
    right_h = min(cover_bottom, shadow_bottom) - right_y

    bottom_x = shadow_x
    bottom_y = max(cover_bottom, shadow_y)
    bottom_w = min(cover_right, shadow_right) - bottom_x
    bottom_h = shadow_bottom - bottom_y

    corner_x = max(cover_right, shadow_x)
    corner_y = max(cover_bottom, shadow_y)
    corner_w = shadow_right - corner_x
    corner_h = shadow_bottom - corner_y

    def rect(x, y, w, h):
        return (x, y, w, h) if w > 0 and h > 0 else None

    return (
        rect(right_x, right_y, right_w, right_h),
        rect(bottom_x, bottom_y, bottom_w, bottom_h),
        rect(corner_x, corner_y, corner_w, corner_h),
    )


def _apply_dynamic_shadow_once(size):
    window = xbmcgui.Window(HOME_WINDOW_ID)
    width = max(0, _skin_int(SHADOW_WIDTH_SETTING, SHADOW_WIDTH_DEFAULT))
    offset = max(0, _skin_int(SHADOW_OFFSET_SETTING, SHADOW_OFFSET_DEFAULT))

    # Keep the already verified 5.0.178 whole-rectangle path for main/single.
    extent = max(1, int(size) + width)
    for hard_id, soft_id, kind in DYNAMIC_SHADOW_CONTROLS:
        cover_x, cover_y = _shadow_cover_rect(kind, size)
        x = cover_x + offset
        y = cover_y + offset
        _set_geometry(_control(window, hard_id), x, y, extent, extent)
        _set_geometry(_control(window, soft_id), x, y, extent, extent)

    # 5.0.179: pair artwork uses explicit visible pieces. This avoids relying
    # on the cover image to mask the shadow inside its nominal square control.
    for hard_ids, soft_ids, kind in DYNAMIC_PAIR_SHADOW_CONTROLS:
        cover_x, cover_y = _shadow_cover_rect(kind, size)
        rects = _pair_shadow_rects(cover_x, cover_y, size, width, offset)
        for control_id, rect in zip(hard_ids, rects):
            _set_shadow_piece(_control(window, control_id), rect)
        for control_id, rect in zip(soft_ids, rects):
            _set_shadow_piece(_control(window, control_id), rect)


def _apply_dynamic_cover_once(size):
    window = xbmcgui.Window(HOME_WINDOW_ID)
    if _control(window, ID_MAIN_FRAME) is None:
        raise RuntimeError("Home controls not ready")
    size = max(1, int(size))
    frame_height = max(443, size)
    frame_top = 68 if size <= 443 else 511 - size
    _set_geometry(_control(window, ID_MAIN_FRAME), 30, frame_top, size, frame_height)
    _set_geometry(_control(window, ID_MAIN_SHADOW_COVER), 30, 495 - size, size, size)
    selector_x = (1920 - size) // 2
    selector_y = (600 - size) // 2
    _set_geometry(_control(window, ID_SELECTOR_SINGLE_FRAME), selector_x, selector_y, size, size)
    _set_geometry(_control(window, ID_SELECTOR_SINGLE_SHADOW_COVER), selector_x, selector_y, size, size)
    front_x = 940 - size
    back_x = 980
    _set_geometry(_control(window, ID_SELECTOR_PAIR_FRAME_FRONT), front_x, selector_y, size, size)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_FRAME_BACK), back_x, selector_y, size, size)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_SHADOW_FRONT), front_x, selector_y, size, size)
    _set_geometry(_control(window, ID_SELECTOR_PAIR_SHADOW_BACK), back_x, selector_y, size, size)
    info = _control(window, ID_MAIN_INFO)
    if info is not None:
        info.setPosition(size + 60, 0)
        info.setWidth(max(1, 1230 - size))
    # Shadow width/offset are absolute pixels: never zoom them with the cover.
    _apply_dynamic_shadow_once(size)


def apply_dynamic_cover(size=None):
    if not _is_dynamic():
        return False
    if size is None:
        size = _skin_int(COVER_SIZE_SETTING, COVER_DEFAULT)
    for _ in range(12):
        try:
            _apply_dynamic_cover_once(size)
            return True
        except Exception:
            xbmc.sleep(50)
    return False


def _format_offset(value):
    value = int(value)
    return "default" if value == 0 else "{:+d}".format(value)


def _badge_lines(mode, value):
    if mode == "yoffset":
        return "Vertical Menu Position    {}".format(_format_offset(value)), "Up/Down: Change   ·   OK: Save"
    if mode == "cover":
        return "Music Cover Size    {} px".format(int(value)), "Up/Down: Change   ·   OK: Save"
    width, offset = value
    return "Shadow    Width {} px / Offset {} px".format(width, offset), "L/R: Width   ·   U/D: Offset   ·   OK: Save"


def _set_badge(mode, value):
    title, help_text = _badge_lines(mode, value)
    home = xbmcgui.Window(HOME_WINDOW_ID)
    home.setProperty(BADGE_TITLE_PROP, title)
    home.setProperty(BADGE_HELP_PROP, help_text)


def _clear_badge():
    home = xbmcgui.Window(HOME_WINDOW_ID)
    home.clearProperty(BADGE_TITLE_PROP)
    home.clearProperty(BADGE_HELP_PROP)


def _set_adjust_active(enabled):
    home = xbmcgui.Window(HOME_WINDOW_ID)
    if enabled:
        home.setProperty(ADJUST_ACTIVE_PROP, "true")
    else:
        home.clearProperty(ADJUST_ACTIVE_PROP)



class AdjustDialog(xbmcgui.WindowXMLDialog):
    def configure(self, mode, value, on_change, on_cancel):
        self.mode = mode
        self.value = value if mode == "shadow" else int(value)
        self.on_change_callback = on_change
        self.on_cancel_callback = on_cancel
        self.confirmed = False
        _set_badge(self.mode, self.value)

    def onAction(self, action):
        action_id = action.getId()
        if self.mode == "shadow":
            width, offset = self.value
            if action_id == ACTION_MOVE_LEFT:
                self._change((max(0, width - SHADOW_STEP), offset))
            elif action_id == ACTION_MOVE_RIGHT:
                self._change((width + SHADOW_STEP, offset))
            elif action_id == ACTION_MOVE_UP:
                self._change((width, max(0, offset - SHADOW_STEP)))
            elif action_id == ACTION_MOVE_DOWN:
                self._change((width, offset + SHADOW_STEP))
            elif action_id == ACTION_SELECT_ITEM:
                self.confirmed = True
                self.close()
            elif action_id in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
                self.on_cancel_callback()
                self.close()
            return
        if action_id == ACTION_MOVE_UP:
            if self.mode == "yoffset":
                new_value = max(Y_MIN, self.value - STEP)
            else:
                new_value = self.value + STEP
            self._change(new_value)
        elif action_id == ACTION_MOVE_DOWN:
            if self.mode == "yoffset":
                new_value = min(Y_MAX, self.value + STEP)
            else:
                new_value = max(STEP, self.value - STEP)
            self._change(new_value)
        elif action_id == ACTION_SELECT_ITEM:
            self.confirmed = True
            self.close()
        elif action_id in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.on_cancel_callback()
            self.close()

    def _change(self, new_value):
        if new_value == self.value:
            return
        self.value = new_value
        self.on_change_callback(self.value)
        _set_badge(self.mode, self.value)


def _activate_home():
    xbmc.executebuiltin("ActivateWindow(Home)")
    for _ in range(40):
        if xbmcgui.getCurrentWindowId() == HOME_WINDOW_ID:
            return True
        xbmc.sleep(25)
    return xbmcgui.getCurrentWindowId() == HOME_WINDOW_ID


def _open_adjust_dialog(mode, current, on_change, on_cancel):
    skin_path = xbmcvfs.translatePath("special://skin/")
    dialog = AdjustDialog(DIALOG_XML, skin_path)
    dialog.configure(mode, current, on_change, on_cancel)
    try:
        dialog.doModal()
        return bool(dialog.confirmed)
    finally:
        _clear_badge()
        del dialog


def run(mode):
    mode = (mode or "").strip().lower()
    if mode == "apply":
        apply_dynamic_cover()
        return
    if mode not in ("yoffset", "cover", "shadow"):
        return
    previous_window = xbmcgui.getCurrentWindowId()
    dynamic_before = _is_dynamic()
    if mode == "yoffset":
        original = _skin_int(Y_OFFSET_SETTING, Y_DEFAULT)
        current = original
        def on_change(value):
            _set_string(Y_OFFSET_SETTING, value)
        def on_cancel():
            _set_string(Y_OFFSET_SETTING, original)
    elif mode == "cover":
        original = _skin_int(COVER_SIZE_SETTING, COVER_DEFAULT)
        current = max(1, original)
        def on_change(value):
            _set_string(COVER_SIZE_SETTING, value)
            apply_dynamic_cover(value)
        def on_cancel():
            _set_string(COVER_SIZE_SETTING, original)
            if dynamic_before:
                apply_dynamic_cover(original)
            else:
                _set_dynamic(False)
    else:
        original = (_skin_int(SHADOW_WIDTH_SETTING, SHADOW_WIDTH_DEFAULT), _skin_int(SHADOW_OFFSET_SETTING, SHADOW_OFFSET_DEFAULT))
        current = original
        def on_change(value):
            width, offset = value
            _set_string(SHADOW_WIDTH_SETTING, width)
            _set_string(SHADOW_OFFSET_SETTING, offset)
            apply_dynamic_cover(_skin_int(COVER_SIZE_SETTING, COVER_DEFAULT))
        def on_cancel():
            _set_string(SHADOW_WIDTH_SETTING, original[0])
            _set_string(SHADOW_OFFSET_SETTING, original[1])
            if dynamic_before:
                apply_dynamic_cover(_skin_int(COVER_SIZE_SETTING, COVER_DEFAULT))
            else:
                _set_dynamic(False)
    _set_adjust_active(True)
    try:
        if not _activate_home():
            return
        if mode in ("cover", "shadow"):
            _set_dynamic(True)
            if mode == "cover":
                _set_string(COVER_SIZE_SETTING, current)
            apply_dynamic_cover(_skin_int(COVER_SIZE_SETTING, COVER_DEFAULT))
        confirmed = _open_adjust_dialog(mode, current, on_change, on_cancel)
        if confirmed and mode in ("cover", "shadow"):
            _set_dynamic(True)
            apply_dynamic_cover(_skin_int(COVER_SIZE_SETTING, COVER_DEFAULT))
    finally:
        _set_adjust_active(False)
    if previous_window and previous_window != HOME_WINDOW_ID:
        xbmc.executebuiltin("ActivateWindow({})".format(previous_window))


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "")
