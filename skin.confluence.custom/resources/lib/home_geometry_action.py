# -*- coding: utf-8 -*-
"""Foreground/event action for Home music artwork geometry.

The persistent Now Playing worker requests this action only when the actual
playing artwork or relevant skin settings change. Returning from another Kodi
window must not rebuild Home artwork geometry by itself.
"""
from __future__ import absolute_import

from cover_display_action import sync_info_cover_geometry
from live_home_adjust import apply_dynamic_cover


def main():
    # Centered and info-side geometry are applied together in one short-lived
    # foreground action. Neither operation is tied to Home onload anymore.
    apply_dynamic_cover()
    sync_info_cover_geometry()


if __name__ == "__main__":
    main()
