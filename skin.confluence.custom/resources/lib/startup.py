# -*- coding: utf-8 -*-
import xbmc
import factory_defaults
import import_confluence_settings
import library_nodes
from menu_common import ensure_initialised, log
from mainmenu_style import ensure_defaults
from skin_mode import ensure_mode


if __name__ == "__main__":
    try:
        apply_factory_defaults = factory_defaults.begin()
        if apply_factory_defaults:
            try:
                library_nodes.install_missing_defaults()
            except Exception as exc:
                log("Library-node defaults failed: {}".format(exc), xbmc.LOGERROR)
        # A skin update always installs the Custom XML files from the package.
        # If Standard Confluence was active before the update, restore that
        # XML set first and reload before any Custom initialisation runs.
        if ensure_mode():
            raise SystemExit
        import_confluence_settings.run()
        if apply_factory_defaults and factory_defaults.apply():
            xbmc.sleep(150)
            xbmc.executebuiltin("ReloadSkin()")
            raise SystemExit
        ensure_initialised(False)
        ensure_defaults()
    except SystemExit:
        raise
    except Exception as exc:
        log("Startup failed: {}".format(exc), xbmc.LOGERROR)
