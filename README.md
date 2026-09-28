# Confluence-jjs

**Current development version: 5.0.143**

Confluence-jjs is an extended Confluence skin for Kodi Omega, based on the original Confluence skin by **Jezz_X / Team Kodi**. It keeps the direct Confluence workflow while adding extensive music playback, home-screen and remote-control features.

## Compatibility and add-on ID

The visible skin name is **Confluence-jjs**.

The technical Kodi add-on ID intentionally remains:

`skin.confluence.custom`

Keeping the existing ID preserves update compatibility and existing skin settings. Renaming the add-on ID would make Kodi treat Confluence-jjs as a different skin.

## Highlights

- configurable main menu and submenu appearance
- integrated main-menu/submenu editor
- configurable home-screen cover display
- front/back-cover modes and compact cover view
- hard and soft cover shadows
- configurable playback information and time displays
- audio and time badges
- song popup with playlist, credits and lyrics
- long album/song title handling
- Custom and Standard Confluence modes
- skin-settings backup and restore
- bundled library-node defaults
- portable factory defaults for fresh installations

## Settings

The Confluence-jjs settings page is split into compact tabs instead of one long scrolling page:

- **General**
- **Menu editor**
- **Main menu**
- **Submenu**
- **Home**
- **Song popup**
- **Playback**
- **Badges**

The reorganization changes only the presentation of the settings. Existing setting names and stored values remain unchanged.

## Installation

Install the ZIP published under **Releases**:

`skin.confluence.custom-<version>.zip`

In Kodi, use:

**Add-ons → Install from zip file**

The release ZIP contains exactly one add-on root, `skin.confluence.custom/`, and is directly installable.

## Custom and Standard Confluence modes

Confluence-jjs contains two complete sets of the central Confluence XML files:

- **Confluence-jjs**
- **Standard Confluence**

The mode switch preserves the Confluence-jjs settings. After an update, the startup service verifies that the previously selected XML set is active and restores it when necessary.

## Menu editor

The integrated menu editor does not require Skin Shortcuts. It supports, among other things:

- renaming main-menu entries
- changing main-menu targets
- moving managed main-menu entries
- editing submenus
- up to seven submenu entries per group
- Kodi library nodes
- favorites
- add-on entry points
- capturing normal Kodi list items through the context menu

## Music playback

The home screen and song popup are designed for large music libraries and remote-control use.

Available options include:

- configurable album-cover size and appearance
- front/back-cover switching
- compact cover display
- album and song title overflow handling
- current/remaining song and album times
- optional time badges with equal-width mode
- audio codec/channel badge
- configurable song popup
- track-number display
- lyrics with LRC synchronization
- credits/personnel display

## Backups and defaults

Confluence-jjs can back up and restore all skin-specific Boolean and string settings as JSON. General Kodi settings are not changed.

Factory defaults are applied only to genuine fresh installations. Normal skin updates do not overwrite existing user settings.

Bundled music/video library nodes are copied only when missing during a fresh installation. The explicit reset command can restore the bundled node trees on demand.

## Project structure

- `skin.confluence.custom/addon.xml` — add-on metadata and version
- `skin.confluence.custom/1080p/` — active skin XML
- `skin.confluence.custom/resources/skin_modes/custom/` — Confluence-jjs XML set
- `skin.confluence.custom/resources/skin_modes/standard/` — Standard Confluence XML set
- `skin.confluence.custom/resources/lib/` — runtime services and helper scripts
- `skin.confluence.custom/resources/library_nodes/` — bundled library nodes
- `skin.confluence.custom/resources/factory-default-settings.json` — fresh-install defaults
- `skin.confluence.custom/media/` — textures, badges and codec logos
- `skin.confluence.custom/backgrounds/` — bundled backgrounds
- `skin.confluence.custom/fonts/` — bundled fonts and their license files
- `skin.confluence.custom/language/` — inherited Confluence localization resources

## Build and release

The GitHub workflow validates:

- `addon.xml`
- add-on ID and version
- the Kodi skin extension
- required Custom/Standard XML sets
- required runtime files
- Python syntax
- XML syntax
- ZIP root structure and archive integrity

Releases are published as:

`skin.confluence.custom-<version>.zip`

The package filename intentionally follows the technical add-on ID even though the visible skin name is Confluence-jjs.

## Upstream and license

Confluence-jjs is based on **Confluence by Jezz_X / Team Kodi**.

License: **GNU General Public License version 2**

Bundled fonts retain their respective included license files.
