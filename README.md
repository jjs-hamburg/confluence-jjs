# Confluence-jjs

Confluence-jjs is a customized **Confluence skin for Kodi 21 (Omega)**, based on the original work by **Jezz_X / Team Kodi**.

The main goal is to preserve the simple and direct Confluence experience while improving music presentation and configurability.

## Overview

Confluence-jjs keeps the familiar Confluence home screen while adding more information about the currently playing music and extended artwork options.

![Confluence-jjs playback overview](docs/screenshots/overview-playback.webp)

The artwork display can be enlarged and optionally show the front and back cover together.

![Confluence-jjs front and back cover](docs/screenshots/overview-artwork.webp)

## Main additions

- improved artwork display, including optional back covers
- configurable fonts, colors and font sizes
- more information about the currently playing music, including timing, format, DOR, lyrics and credits
- configurable home screen, main menu and submenus
- menu options that standard Confluence does not expose, such as **Files** in the Music submenu
- integrated menu editor without Skin Shortcuts
- selectable **Confluence-jjs** and **Standard Confluence** modes
- skin-settings backup/restore and bundled library-node defaults

The Confluence-jjs settings are organized into separate tabs for easier navigation.

## Song popup

The song popup provides additional information and functions without leaving the home screen.

### Track list

![Song popup track list](docs/screenshots/popup-tracklist.webp)

### Synchronized lyrics

![Song popup synchronized lyrics](docs/screenshots/popup-lyrics.webp)

### Credits

![Song popup credits](docs/screenshots/popup-credits.webp)

## Installation

Download the current release ZIP from **Releases** and install it in Kodi via:

**Add-ons → Install from zip file**

The package is named:

`skin.confluence.custom-<version>.zip`

## Add-on ID

The visible skin name is **Confluence-jjs**, but the technical add-on ID intentionally remains:

`skin.confluence.custom`

This preserves normal update behavior and existing skin settings. Changing the ID would make Kodi treat it as a different skin.

## Development

The release workflow validates the skin XML, Python files and ZIP structure before publishing a directly installable release package.

## Credits and license

Based on **Confluence by Jezz_X / Team Kodi**.

License: **GNU General Public License version 2**.
