"""Entry point for the Wake-on-LAN Flet application.

Initialises the application window and launches the WolApp UI.
"""

import os
import sys

import flet as ft

from wol_app.config import VERSION
from wol_app.storage import migrate_from_cwd, set_data_dir
from wol_app.ui import WolApp


def main(page: ft.Page):
    """Configure and launch the Wake-on-LAN application.

    Sets up the platform-appropriate data directory (``~/.wol_app_data``
    on desktop, app-private on Android), migrates existing files from the
    old CWD location if present, then builds the full UI.

    Args:
        page: The root Flet page provided by the framework.
    """
    data_dir = os.path.join(os.path.expanduser("~"), ".wol_app_data")
    migrate_from_cwd(data_dir)
    set_data_dir(data_dir)
    if page.platform in (ft.PagePlatform.WINDOWS, ft.PagePlatform.LINUX, ft.PagePlatform.MACOS):
        icon = (
            "icon.ico"
            if sys.platform == "win32" and os.path.exists(os.path.join("assets", "icon.ico"))
            else "icon.png"
        )
        page.window.icon = os.path.abspath(os.path.join("assets", icon))
        page.window.width = 400
        page.window.height = 800
        page.window.max_width = 400
        page.window.max_height = 800
    WolApp(page)


if __name__ == "__main__":
    ft.run(main=main, name=f"Wake on LAN v{VERSION}")
