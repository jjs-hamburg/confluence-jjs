# -*- coding: utf-8 -*-
import sys

import xbmc
import xbmcgui


HOME_WINDOW_ID = 10000
COVER_SIZE_SETTING = "CCHomeMusicCoverSize"
COVER_DYNAMIC_SETTING = "CCHomeMusicCoverDynamic"
Y_OFFSET_SETTING = "CCMainMenuYOffset"

COVER_DEFAULT = 195
Y_DEFAULT = 0
Y_MIN = -250
Y_MAX = 300
STEP = 25

ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

ID_MAIN_FRAME = 9301
ID_MAIN_SHADOW_COVER = 9302
ID_SELECTOR_SINGLE_FRAME = 9303
ID_SELECTOR_SINGLE_SHADOW_COVER = 9304
ID_SELECTOR_PAIR_FRAME_FRONT = 9305
ID_SELECTOR_PAIR_FRAME_BACK = 9306
ID_SELECTOR_PAIR_SHADOW_FRONT = 9307
ID_SELECTOR_PAIR_SHADOW_BACK = 9308
ID_MAIN_INFO = 9309
ID_MAIN_SHADOWS = 9310
ID_SELECTOR_SINGLE_SHADOWS = 9311
ID_SELECTOR_PAIR_SHADOWS = 9312


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
    return xbmc.getCondVisibility(
        "Skin.HasSetting({})".format(COVER_DYNAMIC_SETTING)
    )


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


def _set_zoom(control, percent, center_x, center_y):
    if control is None:
        return
    attr = (
        "effect=zoom start=100 end={:.4f} center={},{} "
        "time=0 condition=true"
    ).format(float(percent), int(center_x), int(center_y))
    control.setAnimations([("conditional", attr)])


def _apply_dynamic_cover_once(size):
    window = xbmcgui.Window(HOME_WINDOW_ID)
    if _control(window, ID_MAIN_FRAME) is None:
        raise RuntimeError("Home controls not ready")

    size = max(1, int(size))

    # Normal Home cover. The framed control keeps the original 443 px high
    # area until the cover itself becomes taller, preserving the existing
    # bottom alignment and playback layout.
    frame_height = max(443, size)
    frame_top = 68 if size <= 443 else 511 - size
    _set_geometry(
        _control(window, ID_MAIN_FRAME), 30, frame_top, size, frame_height
    )
    _set_geometry(
        _control(window, ID_MAIN_SHADOW_COVER), 30, 495 - size, size, size
    )

    # Centered selector, single cover.
    selector_x = (1920 - size) // 2
    selector_y = (600 - size) // 2
    _set_geometry(
        _control(window, ID_SELECTOR_SINGLE_FRAME),
        selector_x,
        selector_y,
        size,
        size,
    )
    _set_geometry(
        _control(window, ID_SELECTOR_SINGLE_SHADOW_COVER),
        selector_x,
        selector_y,
        size,
        size,
    )

    # Centered selector, front/back pair. Keep the existing 40 px gap.
    front_x = 940 - size
    back_x = 980
    _set_geometry(
        _control(window, ID_SELECTOR_PAIR_FRAME_FRONT),
        front_x,
        selector_y,
        size,
        size,
    )
    _set_geometry(
        _control(window, ID_SELECTOR_PAIR_FRAME_BACK),
        back_x,
        selector_y,
        size,
        size,
    )
    _set_geometry(
        _control(window, ID_SELECTOR_PAIR_SHADOW_FRONT),
        front_x,
        selector_y,
        size,
        size,
    )
    _set_geometry(
        _control(window, ID_SELECTOR_PAIR_SHADOW_BACK),
        back_x,
        selector_y,
        size,
        size,
    )

    # Keep the normal playback text to the right of the resized cover.
    info = _control(window, ID_MAIN_INFO)
    if info is not None:
        info.setPosition(size + 60, 0)
        info.setWidth(max(1, 1230 - size))

    # Reuse the established 195 px shadow implementations and scale their
    # wrapper groups with the cover. This keeps all existing shadow width and
    # offset choices available for arbitrary cover sizes.
    zoom = (float(size) / float(COVER_DEFAULT)) * 100.0
    _set_zoom(_control(window, ID_MAIN_SHADOWS), zoom, 30, 495)
    _set_zoom(_control(window, ID_SELECTOR_SINGLE_SHADOWS), zoom, 960, 300)
    _set_zoom(_control(window, ID_SELECTOR_PAIR_SHADOWS), zoom, 960, 300)


def apply_dynamic_cover(size=None):
    if not _is_dynamic():
        return False
    if size is None:
        size = _skin_int(COVER_SIZE_SETTING, COVER_DEFAULT)

    # Home onload scripts can start a fraction before the skin controls are
    # addressable. Retry briefly rather than silently leaving the old geometry.
    for _ in range(12):
        try:
            _apply_dynamic_cover_once(size)
            return True
        except Exception:
            xbmc.sleep(50)
    return False


def _format_offset(value):
    value = int(value)
    if value == 0:
        return "default"
    return "{:+d}".format(value)


class AdjustDialog(xbmcgui.WindowDialog):
    def __init__(self, mode, value, on_change, on_cancel):
        super(AdjustDialog, self).__init__()
        self.mode = mode
        self.value = int(value)
        self.on_change = on_change
        self.on_cancel = on_cancel
        self.confirmed = False

        # Transparent WindowDialog: Home remains visible. The compact panel on
        # the right acts as the requested live value badge.
        self.panel = xbmcgui.ControlImage(
            1510, 435, 330, 145, "special://skin/media/black-back2.png"
        )
        self.title = xbmcgui.ControlLabel(
            1530,
            448,
            290,
            34,
            "Vertical menu position" if mode == "yoffset" else "Cover size",
            font="font13",
            textColor="FFBFBFBF",
            alignment=6,
        )
        self.value_label = xbmcgui.ControlLabel(
            1530,
            483,
            290,
            52,
            "",
            font="font30_title",
            textColor="FFFFFFFF",
            alignment=6,
        )
        self.hint = xbmcgui.ControlLabel(
            1530,
            540,
            290,
            26,
            "UP / DOWN     OK",
            font="font12",
            textColor="FFBFBFBF",
            alignment=6,
        )
        self.addControls([self.panel, self.title, self.value_label, self.hint])
        self._refresh()

    def _refresh(self):
        if self.mode == "yoffset":
            label = _format_offset(self.value)
        else:
            label = "{} px".format(self.value)
        self.value_label.setLabel(label)

    def onAction(self, action):
        action_id = action.getId()
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
                # No upper limit; 25 px is only the natural lower bound.
                new_value = max(STEP, self.value - STEP)
            self._change(new_value)
        elif action_id == ACTION_SELECT_ITEM:
            self.confirmed = True
            self.close()
        elif action_id in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.on_cancel()
            self.close()

    def _change(self, new_value):
        if new_value == self.value:
            return
        self.value = int(new_value)
        self.on_change(self.value)
        self._refresh()


def _activate_home():
    xbmc.executebuiltin("ActivateWindow(Home)")
    for _ in range(40):
        if xbmcgui.getCurrentWindowId() == HOME_WINDOW_ID:
            return True
        xbmc.sleep(25)
    return xbmcgui.getCurrentWindowId() == HOME_WINDOW_ID


def run(mode):
    mode = (mode or "").strip().lower()

    if mode == "apply":
        apply_dynamic_cover()
        return

    if mode not in ("yoffset", "cover"):
        return

    previous_window = xbmcgui.getCurrentWindowId()

    if mode == "yoffset":
        original = _skin_int(Y_OFFSET_SETTING, Y_DEFAULT)
        current = original

        def on_change(value):
            _set_string(Y_OFFSET_SETTING, value)

        def on_cancel():
            _set_string(Y_OFFSET_SETTING, original)
    else:
        original = _skin_int(COVER_SIZE_SETTING, COVER_DEFAULT)
        dynamic_before = _is_dynamic()
        current = max(1, original)

        def on_change(value):
            _set_string(COVER_SIZE_SETTING, value)
            apply_dynamic_cover(value)

        def on_cancel():
            if dynamic_before:
                _set_string(COVER_SIZE_SETTING, original)
                apply_dynamic_cover(original)
            else:
                # Restore the base control geometry before returning to the
                # original static-size implementation.
                try:
                    _apply_dynamic_cover_once(COVER_DEFAULT)
                except Exception:
                    pass
                _set_string(COVER_SIZE_SETTING, original)
                _set_dynamic(False)

    if not _activate_home():
        return

    if mode == "cover":
        _set_dynamic(True)
        _set_string(COVER_SIZE_SETTING, current)
        apply_dynamic_cover(current)

    dialog = AdjustDialog(mode, current, on_change, on_cancel)
    dialog.doModal()
    confirmed = dialog.confirmed
    del dialog

    if confirmed and mode == "cover":
        _set_dynamic(True)
        apply_dynamic_cover(_skin_int(COVER_SIZE_SETTING, current))

    # Return to the setup window after OK or Back.
    if previous_window and previous_window != HOME_WINDOW_ID:
        xbmc.executebuiltin("ActivateWindow({})".format(previous_window))


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "")
