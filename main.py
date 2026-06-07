"""Wake-on-LAN mobile application built with Flet.

Sends Wake-on-LAN magic packets to devices on the local network.
Supports saving device lists, dark/light theme, and error handling.

Copyright IntelOut (c) 2026. All rights reserved.
https://github.com/IntelOut
"""

import asyncio
import json
import os
import re
import socket
import sys

import flet as ft
from flet.controls.margin import Margin
from flet.controls.padding import Padding
from flet.security import decrypt, encrypt

DATA_FILE = "devices.json"
SETTINGS_FILE = "settings.json"
CRYPT_KEY = "FsxFtSDzEHDRJd5H7IXuQZOa6fyK585I"
VERSION = "0.4.0"


def _validate_mac(mac: str) -> bool:
    """Validate a MAC address in XX:XX:XX:XX:XX:XX format."""
    pattern = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
    return bool(re.match(pattern, mac.strip()))


def _mac_to_bytes(mac: str) -> bytes:
    """Convert a MAC address string to 6 bytes."""
    return bytes.fromhex(mac.strip().replace(":", ""))


def _build_magic_packet(mac: bytes) -> bytes:
    """Build a WOL magic packet: 6 bytes of 0xFF + 16 repeats of the MAC."""
    return b"\xff" * 6 + mac * 16


async def _send_wol(mac_address: str, ip: str, port: int) -> str:
    """Send a Wake-on-LAN magic packet and return a status message.

    Args:
        mac_address: MAC address in XX:XX:XX:XX:XX:XX format.
        ip: Target IP or broadcast address.
        port: Destination UDP port.

    Returns:
        A human-readable status message.
    """
    mac_bytes = _mac_to_bytes(mac_address)
    packet = _build_magic_packet(mac_bytes)

    loop = asyncio.get_event_loop()

    def _send():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(5)
            sock.sendto(packet, (ip.strip(), port))

    try:
        await loop.run_in_executor(None, _send)
        return f"Magic packet sent to {mac_address}"
    except OSError as e:
        return f"Network error: {e}"
    except Exception as e:
        return f"Error: {e}"


def _load_devices() -> list:
    """Load saved devices from the encrypted local file."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            encrypted = f.read()
        decrypted = decrypt(encrypted, CRYPT_KEY)
        return json.loads(decrypted)
    except Exception:
        return []


def _save_devices(devices: list) -> None:
    """Save the device list to an encrypted local file."""
    plain = json.dumps(devices, ensure_ascii=False)
    encrypted = encrypt(plain, CRYPT_KEY)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(encrypted)


def _load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f)


class WolApp:
    """Encapsulates all WOL application state and event handlers.

    Separating the logic from Flet controls makes the code testable
    without requiring a running Flet page.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self._sending = False
        self._pending_delete_index = None
        self._setup_page()
        self._build_controls()
        self.refresh_device_list()
        self._build_layout()

    # --- page setup -------------------------------------------------------

    def _setup_page(self):
        """Configure page title, scroll, theme, and app bar."""
        self.page.title = f"Wake on LAN v{VERSION}" if sys.platform == "win32" else "Wake on LAN"
        self.page.padding = 0
        self.page.scroll = ft.ScrollMode.AUTO
        settings = _load_settings()
        theme_key = settings.get("theme_mode", "dark")
        self._is_dark = theme_key != "light"
        self.page.theme_mode = ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT
        self.page.appbar = ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.MENU,
                on_click=lambda _: self.page.run_task(self.open_drawer),
            ),
            title=ft.Text("Wake on LAN", size=20, weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.DARK_MODE if self._is_dark else ft.Icons.LIGHT_MODE,
                    tooltip="Toggle theme",
                    on_click=self._on_theme_toggle,
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    tooltip="Network settings",
                    on_click=lambda _: self.open_settings(),
                ),
            ],
        )
        self.page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(primary=ft.Colors.INDIGO),
        )
        self.page.dark_theme = ft.Theme(
            color_scheme=ft.ColorScheme(primary=ft.Colors.INDIGO_ACCENT_200),
        )

    # --- controls ---------------------------------------------------------

    def _build_controls(self):
        """Create all input fields, device list, empty state, and loading indicator."""
        self.mac_input = ft.TextField(
            label="MAC-address",
            hint_text="XX:XX:XX:XX:XX:XX",
            prefix_icon=ft.Icons.WIFI,
            border_radius=12,
            text_size=16,
            expand=True,
            on_change=self._validate_mac_field,
        )
        self.mac_helper = ft.Icon(
            ft.Icons.HELP_OUTLINE,
            size=24,
            color=ft.Colors.GREY_500,
            tooltip=ft.Tooltip(
                message="Format: XX:XX:XX:XX:XX:XX\ne.g. AA:BB:CC:DD:EE:FF",
                padding=10,
                vertical_offset=0,
            ),
        )
        self.ip_input = ft.TextField(
            label="IP or Broadcast",
            hint_text="255.255.255.255",
            prefix_icon=ft.Icons.LAN,
            border_radius=12,
            text_size=16,
            value="255.255.255.255",
            expand=True,
        )
        self.port_input = ft.TextField(
            label="Port",
            hint_text="9",
            prefix_icon=ft.Icons.SETTINGS_ETHERNET,
            border_radius=12,
            text_size=16,
            value="9",
            width=120,
        )
        self.name_input = ft.TextField(
            label="Device name",
            hint_text="e.g. Home PC",
            prefix_icon=ft.Icons.LABEL_OUTLINE,
            border_radius=12,
            text_size=16,
            expand=True,
        )
        self.device_cards = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
        self.empty_state = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.DEVICES_OTHER_OUTLINED,
                        size=64,
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Text(
                        "No saved devices yet",
                        size=16,
                        color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Add a device above and tap Save",
                        size=14,
                        color=ft.Colors.GREY_400,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=Padding.symmetric(vertical=40, horizontal=20),
        )
        self.loading = ft.ProgressRing(width=24, height=24, visible=False)

        self.wake_button = ft.Button(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.POWER_SETTINGS_NEW,
                        size=24,
                    ),
                    ft.Text("Wake Up", size=18),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                padding=Padding.symmetric(
                    horizontal=30, vertical=14
                ),
                shape=ft.RoundedRectangleBorder(
                    radius=12
                ),
            ),
            expand=True,
            on_click=self.on_wake_click,
        )

        self.settings_dialog = ft.AlertDialog(
            title=ft.Text("Network settings", size=16, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                controls=[
                    self.ip_input,
                    self.port_input,
                ],
                spacing=8,
                width=300,
                height=140,
                tight=True,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda _: self.close_settings()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.confirm_delete_dialog = ft.AlertDialog(
            title=ft.Text("Delete device", size=16, weight=ft.FontWeight.BOLD),
            content=ft.Text("Are you sure you want to delete this device?"),
            actions=[
                ft.TextButton("Cancel", on_click=self._cancel_delete),
                ft.TextButton("Delete", on_click=self._confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.drawer = ft.NavigationDrawer(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Wake on LAN", size=22, weight=ft.FontWeight.BOLD),
                            ft.Row(
                                controls=[
                                    ft.Text(f"v{VERSION}", size=14, color=ft.Colors.GREY_500),
                                    ft.Container(expand=True),
                                    ft.Text("(c) IntelOut", size=14, color=ft.Colors.GREY_500),
                                ],
                                alignment=ft.MainAxisAlignment.START,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=Padding.symmetric(vertical=24, horizontal=20),
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Text(
                        "Privacy Policy",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.GREY_600,
                    ),
                    padding=Padding.symmetric(vertical=12, horizontal=20),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED),
                    title=ft.Text("Privacy Policy (RU)"),
                    on_click=lambda _: self.page.run_task(
                        ft.UrlLauncher().launch_url,
                        "https://github.com/IntelOut/Wol_apk/blob/main/PRIVACY_POLICY_RU.md"
                    ),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED),
                    title=ft.Text("Privacy Policy (EN)"),
                    on_click=lambda _: self.page.run_task(
                        ft.UrlLauncher().launch_url,
                        "https://github.com/IntelOut/Wol_apk/blob/main/PRIVACY_POLICY.md"
                    ),
                ),
                ft.Container(
                    content=ft.Text(
                        "User Agreement",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.GREY_600,
                    ),
                    padding=Padding.symmetric(vertical=12, horizontal=20),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED),
                    title=ft.Text("User Agreement (RU)"),
                    on_click=lambda _: self.page.run_task(
                        ft.UrlLauncher().launch_url,
                        "https://github.com/IntelOut/Wol_apk/blob/main/USER_AGREEMENT_RU.md"
                    ),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED),
                    title=ft.Text("User Agreement (EN)"),
                    on_click=lambda _: self.page.run_task(
                        ft.UrlLauncher().launch_url,
                        "https://github.com/IntelOut/Wol_apk/blob/main/USER_AGREEMENT.md"
                    ),
                ),
            ],
        )
        self.page.drawer = self.drawer

    def _on_theme_toggle(self, e):
        self._is_dark = not self._is_dark
        theme_key = "dark" if self._is_dark else "light"
        self.page.theme_mode = ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT
        appbar = self.page.appbar
        if appbar and appbar.actions:
            appbar.actions[0].icon = ft.Icons.DARK_MODE if self._is_dark else ft.Icons.LIGHT_MODE
        _save_settings({"theme_mode": theme_key})
        self.page.update()

    def _validate_mac_field(self, e):
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        if mac and not _validate_mac(mac):
            self.mac_input.error_text = "Invalid MAC format"
        else:
            self.mac_input.error_text = None
        self.page.update()

    def open_settings(self):
        self.page.show_dialog(self.settings_dialog)

    def close_settings(self):
        self.settings_dialog.open = False
        self.page.update()

    async def open_drawer(self):
        await self.page.show_drawer()

    # --- helpers ----------------------------------------------------------

    def show_snack(self, message: str, error: bool = False):
        """Show a SnackBar with the given message."""
        snack = ft.SnackBar(
            content=ft.Text(message, size=16),
            bgcolor=ft.Colors.RED_ACCENT_700 if error else ft.Colors.GREEN_ACCENT_700,
            open=True,
        )
        self.page.overlay.append(snack)
        self.page.update()

    def refresh_device_list(self):
        """Rebuild the device card list from storage."""
        self.device_cards.controls.clear()
        devices = _load_devices()
        for i, dev in enumerate(devices):
            name = dev.get("name", "Unknown")
            mac = dev.get("mac", "")

            async def _on_send(_, _mac=mac):
                await self._send_from_list(_mac)

            def _on_delete(_, _idx=i):
                self._pending_delete_index = _idx
                self.page.show_dialog(self.confirm_delete_dialog)

            card = ft.Card(
                content=ft.Container(
                    content=ft.ListTile(
                        leading=ft.Icon(ft.Icons.DEVICES, size=28),
                        title=ft.Text(name, size=16, weight=ft.FontWeight.W_600),
                        subtitle=ft.Text(mac, size=14, color=ft.Colors.GREY_600),
                        trailing=ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            tooltip="Delete",
                            icon_size=28,
                            on_click=_on_delete,
                        ),
                        on_click=_on_send,
                    ),
                    padding=Padding.symmetric(vertical=4, horizontal=4),
                ),
                elevation=1.5,
                margin=Margin.symmetric(vertical=2),
            )

            dismissible = ft.Dismissible(
                content=card,
                background=ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.DELETE_FOREVER, size=28, color=ft.Colors.WHITE
                            ),
                            ft.Text(
                                "Delete",
                                size=16,
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=8,
                    ),
                    padding=Padding.symmetric(horizontal=24),
                    bgcolor=ft.Colors.RED_ACCENT_700,
                    alignment=ft.Alignment(1.0, 0.0),
                ),
                dismiss_direction=ft.DismissDirection.END_TO_START,
                on_dismiss=lambda _, _idx=i: self._on_dismiss_delete(_idx),
            )
            self.device_cards.controls.append(dismissible)
        self.empty_state.visible = len(devices) == 0
        self.page.update()

    def _on_dismiss_delete(self, index: int):
        self._pending_delete_index = index
        self.page.show_dialog(self.confirm_delete_dialog)

    def _confirm_delete(self, e):
        self.confirm_delete_dialog.open = False
        if self._pending_delete_index is not None:
            self._delete_device(self._pending_delete_index)
            self._pending_delete_index = None
        self.page.update()

    def _cancel_delete(self, e):
        self.confirm_delete_dialog.open = False
        self._pending_delete_index = None
        self.refresh_device_list()
        self.page.update()

    def _delete_device(self, index: int):
        """Remove a device from storage by list index and refresh the UI."""
        devices = _load_devices()
        if 0 <= index < len(devices):
            removed = devices.pop(index)
            _save_devices(devices)
            self.refresh_device_list()
            self.show_snack(f'Deleted "{removed.get("name", "")}"')

    # --- input validation -------------------------------------------------

    def validate_inputs(self) -> tuple:
        """Validate form inputs and return a clean (mac, ip, port) tuple.

        Returns:
            A tuple of (mac_address, ip_address, port_number).

        Raises:
            ValueError: If the MAC is empty, invalid, or port is not a number.
        """
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        if not mac:
            raise ValueError("MAC address is required")
        if not _validate_mac(mac):
            raise ValueError("Invalid MAC format. Use XX:XX:XX:XX:XX:XX")
        ip = self.ip_input.value.strip() if self.ip_input.value else "255.255.255.255"
        try:
            port = int(self.port_input.value.strip()) if self.port_input.value else 9
        except ValueError as e:
            raise ValueError("Port must be a number") from e
        return mac, ip, port

    # --- WOL actions ------------------------------------------------------

    async def send_wol_action(self):
        """Validate inputs, show loading, send WOL, then hide loading and show result."""
        if self._sending:
            return
        try:
            mac, ip, port = self.validate_inputs()
        except ValueError as e:
            self.show_snack(str(e), error=True)
            return

        self._sending = True
        self.wake_button.disabled = True
        self.loading.visible = True
        self.page.update()

        msg = await _send_wol(mac, ip, port)

        self.loading.visible = False
        self.wake_button.disabled = False
        self._sending = False
        if "Error" in msg or "error" in msg:
            self.show_snack(msg, error=True)
        else:
            self.show_snack(msg)
        self.page.update()

    async def on_wake_click(self, e):
        """Event handler for the Wake Up button."""
        await self.send_wol_action()

    async def _send_from_list(self, mac: str):
        """Populate the MAC field from a saved device and immediately send WOL."""
        self.mac_input.value = mac
        self.page.update()
        await self.send_wol_action()

    def on_save_click(self, e):
        """Event handler for the Save button."""
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        name = self.name_input.value.strip() if self.name_input.value else ""
        if not _validate_mac(mac):
            self.show_snack("Enter a valid MAC before saving", error=True)
            return
        if not name:
            self.show_snack("Enter a device name", error=True)
            return
        devices = _load_devices()
        devices.append({"name": name, "mac": mac.upper()})
        _save_devices(devices)
        self.refresh_device_list()
        self.show_snack(f'Saved "{name}"')

    def on_clear_click(self, e):
        """Event handler for the Clear button."""
        self.mac_input.value = ""
        self.mac_input.error_text = None
        self.ip_input.value = "255.255.255.255"
        self.port_input.value = "9"
        self.name_input.value = ""
        self.page.update()

    # --- layout -----------------------------------------------------------

    def _build_layout(self):
        """Assemble the full page layout inside a SafeArea with scrolling."""
        self.page.add(
            ft.SafeArea(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Device",
                                            size=20,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                        ft.Row(
                                            controls=[self.mac_input, self.mac_helper],
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        ft.Text(
                                            "Save device",
                                            size=20,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                        ft.Row(
                                            controls=[
                                                self.name_input,
                                                ft.IconButton(
                                                    icon=ft.Icons.SAVE,
                                                    tooltip="Save",
                                                    icon_size=28,
                                                    on_click=self.on_save_click,
                                                ),
                                            ],
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        ft.Divider(height=20),
                                        ft.Container(
                                            content=self.wake_button,
                                            padding=Padding.symmetric(
                                                horizontal=8
                                            ),
                                        ),
                                        self.loading,
                                        ft.Row(
                                            controls=[
                                                ft.OutlinedButton(
                                                    "Clear fields",
                                                    icon=ft.Icons.CLEAR_ALL,
                                                    on_click=self.on_clear_click,
                                                ),
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                        ),
                                    ],
                                    spacing=12,
                                ),
                                padding=Padding.all(20),
                            ),
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Saved devices",
                                            size=20,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                        self.device_cards,
                                        self.empty_state,
                                    ],
                                    spacing=10,
                                ),
                                padding=Padding(left=20, top=0, right=20, bottom=20),
                            ),
                        ],
                        spacing=0,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                ),
                expand=True,
            ),
        )


def main(page: ft.Page):
    """Application entry point."""
    if sys.platform == "win32":
        icon_path = os.path.abspath("icon.ico")
    else:
        icon_path = os.path.abspath("icon.png")
    page.window.icon = icon_path
    page.window.width = 360
    page.window.height = 760
    WolApp(page)


if __name__ == "__main__":
    ft.run(main=main, name=f"Wake on LAN v{VERSION}")
