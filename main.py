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
import flet as ft
from flet.controls.margin import Margin
from flet.controls.padding import Padding
from flet.security import encrypt, decrypt


DATA_FILE = "devices.json"
CRYPT_KEY = "wol-app-secret-key-32bytes"
VERSION = "0.3.0"


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
        with open(DATA_FILE, "r", encoding="utf-8") as f:
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


class WolApp:
    """Encapsulates all WOL application state and event handlers.

    Separating the logic from Flet controls makes the code testable
    without requiring a running Flet page.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self._setup_page()
        self._build_controls()
        self.refresh_device_list()
        self._build_layout()

    # --- page setup -------------------------------------------------------

    def _setup_page(self):
        """Configure page title, scroll, theme, and app bar."""
        self.page.title = "Wake on LAN"
        self.page.padding = 0
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.appbar = ft.AppBar(
            title=ft.Text("Wake on LAN", size=20, weight=ft.FontWeight.BOLD),
            center_title=True,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
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
                spacing=8,
            ),
            padding=Padding.symmetric(vertical=40, horizontal=20),
        )
        self.loading = ft.ProgressRing(width=24, height=24, visible=False)

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
                self._delete_device(_idx)

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
                on_dismiss=lambda _, _idx=i: self._delete_device(_idx),
            )
            self.device_cards.controls.append(dismissible)
        self.empty_state.visible = len(devices) == 0
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
        except ValueError:
            raise ValueError("Port must be a number")
        return mac, ip, port

    # --- WOL actions ------------------------------------------------------

    async def send_wol_action(self):
        """Validate inputs, show loading, send WOL, then hide loading and show result."""
        try:
            mac, ip, port = self.validate_inputs()
        except ValueError as e:
            self.show_snack(str(e), error=True)
            return

        self.loading.visible = True
        self.page.update()

        msg = await _send_wol(mac, ip, port)

        self.loading.visible = False
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
                                            "Network",
                                            size=20,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                        self.ip_input,
                                        ft.Row(
                                            controls=[
                                                self.port_input,
                                                ft.Container(expand=True),
                                            ]
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
                                        ft.Button(
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
                                            width=280,
                                            on_click=self.on_wake_click,
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
                            ft.Container(
                                content=ft.Text(
                                    f"v{VERSION}",
                                    size=12,
                                    color=ft.Colors.GREY_500,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                padding=Padding.symmetric(vertical=10, horizontal=20),
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
    WolApp(page)


if __name__ == "__main__":
    ft.run(target=main)
