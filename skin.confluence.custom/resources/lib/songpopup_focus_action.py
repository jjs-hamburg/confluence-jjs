# -*- coding: utf-8 -*-
"""Short-lived UI action that repositions the Song Popup list on the playing row."""
from __future__ import absolute_import

from songselector_action import _native_list_index, focus_current
from songselector_state import current


def main():
    # A user-selected row is already the focused playlist row. Re-running the
    # scroll/focus choreography would temporarily suppress the highlight and
    # produce a visible blink for no functional benefit. Natural track changes
    # still reach focus_current() because their selected row differs.
    selected = _native_list_index()
    playing = current()
    if selected is not None and selected == playing:
        return
    focus_current()


if __name__ == "__main__":
    main()
