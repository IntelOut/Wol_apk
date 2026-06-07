"""Entry point for the Wake-on-LAN Flet application.

Initialises the application window and launches the WolApp UI.
"""

import os
import sys

import flet as ft

from wol_app.storage import VERSION
from wol_app.ui import WolApp


def main(page: ft.Page):
    """Configure and launch the Wake-on-LAN application.

    Args:
        page: The root Flet page provided by the framework.
    """
    icon = "icon.ico" if sys.platform == "win32" else "icon.png"
    page.window.icon = os.path.abspath(os.path.join("assets", icon))
    page.window.width = 360
    page.window.height = 760
    WolApp(page)


if __name__ == "__main__":
    ft.run(main=main, name=f"Wake on LAN v{VERSION}")
