# -*- coding: utf-8 -*-
"""Foreground/event action for Home music artwork geometry.

The persistent Now Playing worker may request this action when artwork or the
relevant skin settings change, but it never touches Kodi GUI controls itself.
Keeping getControl()/setPosition()/setWidth()/setHeight() in this short-lived
action avoids background-thread GUI mutation while preserving the existing
geometry implementation in cover_display_action.py.
"""
from __future__ import absolute_import

from cover_display_action import sync_info_cover_geometry


def main():
    sync_info_cover_geometry()


if __name__ == "__main__":
    main()
