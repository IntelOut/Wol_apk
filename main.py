"""Entry point for the Wake-on-LAN Flet application.

Initialises the application window and launches the WolApp UI.
"""

import logging
import os
import sys

import flet as ft

from wol_app.config import VERSION
from wol_app.logging_setup import setup_logging, setup_sentry
from wol_app.storage import migrate_from_cwd, set_data_dir
from wol_app.ui import WolApp

_logger = logging.getLogger(__name__)


def main(page: ft.Page):
    """Configure and launch the Wake-on-LAN application.

    Sets up the platform-appropriate data directory (``~/.wol_app_data``
    on desktop, app-private on Android), migrates existing files from the
    old CWD location if present, then builds the full UI.

    Args:
        page: The root Flet page provided by the framework.
    """
    is_desktop = page.platform in (ft.PagePlatform.WINDOWS, ft.PagePlatform.LINUX, ft.PagePlatform.MACOS)

    if is_desktop:
        data_dir = os.path.join(os.path.expanduser("~"), ".wol_app_data")
    else:
        data_dir = os.path.join(os.path.expanduser("~"), ".wol_app_data")

    os.environ.setdefault("WOL_DATA_DIR", data_dir)

    setup_logging(data_dir)
    _logger.info("Starting WakeOnLAN v%s on %s", VERSION, page.platform)

    sentry_dsn = os.environ.get("WOL_SENTRY_DSN", "")
    sentry_consent = os.environ.get("WOL_SENTRY_CONSENT", "0") == "1"
    if sentry_dsn:
        setup_sentry(sentry_dsn, consent_given=sentry_consent)

    migrate_from_cwd(data_dir)
    set_data_dir(data_dir)
    if is_desktop:
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
    ft.run(main=main, name=f"WakeOnLAN v{VERSION}")
