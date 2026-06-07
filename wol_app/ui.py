"""Flet-based graphical user interface for the Wake-on-LAN application.

The ``WolApp`` class encapsulates all UI controls, layout, event
handlers, and state management, keeping the presentation layer
separate from the WOL protocol and storage logic.
"""

import sys
from functools import partial

import flet as ft

from wol_app.protocol import auto_format_mac, send_wol, validate_ip, validate_mac
from wol_app.storage import VERSION, load_devices, load_settings, save_devices, save_settings


class WolApp:
    """Main application class that owns the Flet page and all controls.

    Initialises the page (theme, app bar, drawer), builds the form for
    entering / editing devices, renders the saved device list, and
    wires up all event handlers.
    """

    def __init__(self, page: ft.Page):
        """Construct the full UI on the given Flet page.

        Args:
            page: The root Flet page provided at startup.
        """
        self.page = page
        self._sending = False
        self._pending_delete_index: int | None = None
        self._editing_index: int | None = None
        self._is_dark = True
        self._setup_page()
        self._build_controls()
        self.refresh_device_list()
        self._build_layout()

    # --- page setup -------------------------------------------------------

    def _setup_page(self):
        """Configure page title, scroll behaviour, theme, and app bar."""
        self.page.title = f"Wake on LAN v{VERSION}" if sys.platform == "win32" else "Wake on LAN"
        self.page.padding = 0
        self.page.scroll = ft.ScrollMode.AUTO
        settings = load_settings()
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
        """Create all input fields, the device list, empty-state placeholder,
        loading indicator, dialogs, and the navigation drawer."""
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
            on_change=self._validate_ip_field,
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
        self.device_cards = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
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
            padding=ft.Padding.symmetric(vertical=24, horizontal=20),
        )
        self.loading = ft.ProgressRing(width=24, height=24, visible=False)
        self.sending_label = ft.Text("Sending...", size=14, color=ft.Colors.GREY_500, visible=False)

        self.wake_button = ft.Button(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.POWER_SETTINGS_NEW, size=24),
                    ft.Text("Wake Up", size=18),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                padding=ft.Padding.symmetric(horizontal=30, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            expand=True,
            on_click=self.on_wake_click,
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
                            ft.Container(
                                content=ft.Image(
                                    src="assets/icon.png",
                                    width=64,
                                    height=64,
                                ),
                                padding=ft.Padding(left=0, top=0, right=0, bottom=8),
                            ),
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
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding.symmetric(vertical=24, horizontal=20),
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Text(
                        "Privacy Policy", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_600
                    ),
                    padding=ft.Padding.symmetric(vertical=12, horizontal=20),
                ),
                *self._drawer_links("Privacy Policy", [
                    ("Privacy Policy (RU)", "https://github.com/IntelOut/Wol_apk/blob/main/PRIVACY_POLICY_RU.md"),
                    ("Privacy Policy (EN)", "https://github.com/IntelOut/Wol_apk/blob/main/PRIVACY_POLICY.md"),
                ]),
                ft.Container(
                    content=ft.Text(
                        "User Agreement", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_600
                    ),
                    padding=ft.Padding.symmetric(vertical=12, horizontal=20),
                ),
                *self._drawer_links("User Agreement", [
                    ("User Agreement (RU)", "https://github.com/IntelOut/Wol_apk/blob/main/USER_AGREEMENT_RU.md"),
                    ("User Agreement (EN)", "https://github.com/IntelOut/Wol_apk/blob/main/USER_AGREEMENT.md"),
                ]),
            ],
        )
        self.page.drawer = self.drawer

    def _on_theme_toggle(self, e):
        """Toggle between dark and light colour themes.

        Persists the choice to settings and updates the AppBar icon.
        """
        self._is_dark = not self._is_dark
        theme_key = "dark" if self._is_dark else "light"
        self.page.theme_mode = ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT
        appbar = self.page.appbar
        if appbar and appbar.actions:
            appbar.actions[0].icon = ft.Icons.DARK_MODE if self._is_dark else ft.Icons.LIGHT_MODE
        save_settings({"theme_mode": theme_key})
        self.page.update()

    def _auto_format_mac(self):
        """Insert colons into a raw 12-hex-character MAC string."""
        raw = self.mac_input.value.strip() if self.mac_input.value else ""
        formatted = auto_format_mac(raw)
        if formatted != raw:
            self.mac_input.value = formatted

    def _validate_mac_field(self, e):
        """Perform real-time MAC validation and show ``error_text`` on the field."""
        self._auto_format_mac()
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        if mac and not validate_mac(mac):
            self.mac_input.error_text = "Invalid MAC format"
        else:
            self.mac_input.error_text = None
        self.page.update()

    def _validate_ip_field(self, e):
        """Replace commas with dots and validate IP format in real time."""
        raw = self.ip_input.value or ""
        if "," in raw:
            self.ip_input.value = raw.replace(",", ".")
        ip = self.ip_input.value.strip() if self.ip_input.value else ""
        if ip and ip != "255.255.255.255" and not validate_ip(ip):
            self.ip_input.error_text = "Invalid IP"
        else:
            self.ip_input.error_text = None
        self.page.update()

    async def open_drawer(self):
        """Open the navigation drawer (privacy / user agreement links)."""
        await self.page.show_drawer()

    def _drawer_links(self, _section: str, items: list[tuple[str, str]]) -> list[ft.ListTile]:
        """Build a list of ``ListTile`` controls that open external URLs.

        Each tile displays a document title and opens the corresponding
        URL when tapped.

        Args:
            _section: Section label (unused, kept for consistency).
            items: Pairs of ``(display_title, url)``.

        Returns:
            A list of ``ft.ListTile`` controls.
        """
        return [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED),
                title=ft.Text(title),
                on_click=partial(self._navigate_to_url, url),
            )
            for title, url in items
        ]

    def _navigate_to_url(self, url: str, e) -> None:
        """Open an external URL via the system browser.

        Args:
            url: The URL to open.
            e: The Flet click event (ignored).
        """
        self.page.run_task(ft.UrlLauncher().launch_url, url)

    # --- helpers ----------------------------------------------------------

    def show_snack(self, message: str, error: bool = False):
        """Display a brief SnackBar notification.

        Args:
            message: The text to show.
            error:   If True the background is red, otherwise green.
        """
        snack = ft.SnackBar(
            content=ft.Text(message, size=16),
            bgcolor=ft.Colors.RED_ACCENT_700 if error else ft.Colors.GREEN_ACCENT_700,
            open=True,
        )
        self.page.overlay.append(snack)
        self.page.update()

    def _run_send(self, mac: str, ip: str = "", port: str = ""):
        """Spawn the async WOL send coroutine from a card click event."""
        self.page.run_task(self._send_from_list, mac, ip, port)

    def _prompt_delete(self, index: int):
        """Show the delete confirmation dialog for the given device index."""
        self._pending_delete_index = index
        self.page.show_dialog(self.confirm_delete_dialog)

    def _on_edit(self, idx: int, e) -> None:
        """Callback wrapper that populates the form with device *idx*.

        Args:
            idx: Index of the device to edit.
            e: The Flet click event (ignored).
        """
        self._start_edit(idx)

    def _on_delete(self, idx: int, e) -> None:
        """Callback wrapper that shows the delete confirmation dialog.

        Args:
            idx: Index of the device to delete.
            e: The Flet click event (ignored).
        """
        self._prompt_delete(idx)

    def _on_device_click(self, mac: str, ip: str, port: str, e) -> None:
        """Callback wrapper that fills the form and sends a WOL packet.

        Args:
            mac:  Target MAC address.
            ip:   Target IP or broadcast address.
            port: Destination UDP port.
            e: The Flet click event (ignored).
        """
        self._run_send(mac, ip, port)

    def _on_dismiss_wrapper(self, idx: int, e) -> None:
        """Callback wrapper that handles a swipe-to-dismiss gesture.

        Args:
            idx: Index of the dismissed device.
            e: The Flet dismiss event (ignored).
        """
        self._on_dismiss_delete(idx)

    def refresh_device_list(self):
        """Reload the device list from storage and rebuild the UI cards."""
        self.device_cards.controls.clear()
        devices = load_devices()
        for i, dev in enumerate(devices):
            name = dev.get("name", "Unknown")
            mac = dev.get("mac", "")
            dev_ip = dev.get("ip", "")
            dev_port = dev.get("port", "")
            subtitle = ft.Row(
                controls=[ft.Text(mac, size=12, color=ft.Colors.GREY_600)],
                wrap=True,
                spacing=0,
            )
            if dev_ip:
                subtitle.controls.append(ft.Text(" | ", size=12, color=ft.Colors.GREY_500))
                subtitle.controls.append(ft.Text(dev_ip, size=12, color=ft.Colors.GREY_600))
            if dev_port:
                subtitle.controls.append(ft.Text(" | ", size=12, color=ft.Colors.GREY_500))
                subtitle.controls.append(ft.Text(str(dev_port), size=12, color=ft.Colors.GREY_600))

            card = ft.Card(
                content=ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.DEVICES, size=20),
                            ft.Column(
                                controls=[
                                    ft.Text(name, size=14, weight=ft.FontWeight.W_600),
                                    subtitle,
                                ],
                                spacing=0,
                                expand=True,
                            ),
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        tooltip="Edit",
                                        icon_size=18,
                                        on_click=partial(self._on_edit, i),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        tooltip="Delete",
                                        icon_size=18,
                                        on_click=partial(self._on_delete, i),
                                    ),
                                ],
                                spacing=0,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding.symmetric(vertical=4, horizontal=6),
                    on_click=partial(self._on_device_click, mac, dev_ip, dev_port),
                ),
                elevation=1,
                margin=ft.Margin.symmetric(vertical=1),
            )

            dismissible = ft.Dismissible(
                content=card,
                background=ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.DELETE_FOREVER, size=28, color=ft.Colors.WHITE),
                            ft.Text("Delete", size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=8,
                    ),
                    padding=ft.Padding.symmetric(horizontal=24),
                    bgcolor=ft.Colors.RED_ACCENT_700,
                    alignment=ft.Alignment(1.0, 0.0),
                ),
                dismiss_direction=ft.DismissDirection.END_TO_START,
                on_dismiss=partial(self._on_dismiss_wrapper, i),
            )
            self.device_cards.controls.append(dismissible)
        self.empty_state.visible = len(devices) == 0
        self.page.update()

    def _start_edit(self, index: int):
        """Fill the input form with an existing device's data for editing.

        Args:
            index: The index of the device in the saved list.
        """
        devices = load_devices()
        dev = devices[index]
        self.mac_input.value = dev.get("mac", "")
        self.name_input.value = dev.get("name", "")
        self.ip_input.value = dev.get("ip", "255.255.255.255")
        self.port_input.value = str(dev.get("port", 9))
        self._editing_index = index
        self.page.update()

    def _on_dismiss_delete(self, index: int):
        """Handle a swipe-to-dismiss gesture by showing the confirmation dialog.

        Args:
            index: The index of the device that was swiped.
        """
        self._pending_delete_index = index
        self.page.show_dialog(self.confirm_delete_dialog)

    def _confirm_delete(self, e):
        """Execute deletion after the user confirms the dialog."""
        self.confirm_delete_dialog.open = False
        if self._pending_delete_index is not None:
            self._delete_device(self._pending_delete_index)
            self._pending_delete_index = None
        self.page.update()

    def _cancel_delete(self, e):
        """Cancel deletion and restore any dismissed device card."""
        self.confirm_delete_dialog.open = False
        self._pending_delete_index = None
        self.refresh_device_list()
        self.page.update()

    def _delete_device(self, index: int):
        """Remove a device from storage by list index and refresh the UI.

        Args:
            index: The index of the device to remove.
        """
        devices = load_devices()
        if 0 <= index < len(devices):
            removed = devices.pop(index)
            save_devices(devices)
            self.refresh_device_list()
            self.show_snack(f'Deleted "{removed.get("name", "")}"')

    # --- input validation -------------------------------------------------

    def validate_inputs(self) -> tuple:
        """Validate the form fields and return cleaned values.

        Returns:
            A (mac, ip, port) tuple where ``mac`` and ``ip`` are strings
            and ``port`` is an int.

        Raises:
            ValueError: If the MAC is empty, invalid, or port is not numeric.
        """
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        if not mac:
            raise ValueError("MAC address is required")
        if not validate_mac(mac):
            raise ValueError("Invalid MAC format. Use XX:XX:XX:XX:XX:XX")
        ip = self.ip_input.value.strip() if self.ip_input.value else "255.255.255.255"
        if ip and not validate_ip(ip):
            raise ValueError("Invalid IP address format")
        try:
            port = int(self.port_input.value.strip()) if self.port_input.value else 9
        except ValueError as e:
            raise ValueError("Port must be a number") from e
        return mac, ip, port

    # --- WOL actions ------------------------------------------------------

    async def send_wol_action(self):
        """Validate inputs, send the magic packet, and display the result.

        The Wake Up button and loading indicator are toggled during the
        asynchronous send to prevent duplicate submissions.
        """
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
        self.sending_label.visible = True
        self.page.update()

        success, msg = await send_wol(mac, ip, port)

        self.loading.visible = False
        self.sending_label.visible = False
        self.wake_button.disabled = False
        self._sending = False
        self.show_snack(msg, error=not success)
        self.page.update()

    async def on_wake_click(self, e):
        """Event handler for the Wake Up button."""
        await self.send_wol_action()

    async def _send_from_list(self, mac: str, dev_ip: str = "", dev_port: str = ""):
        """Populate the form from a saved device and send WOL immediately.

        Args:
            mac:      The device MAC address.
            dev_ip:   Optional per-device IP override.
            dev_port: Optional per-device port override.
        """
        self.mac_input.value = mac
        if dev_ip:
            self.ip_input.value = dev_ip
        if dev_port:
            self.port_input.value = str(dev_port)
        self.page.update()
        await self.send_wol_action()

    def _clear_form(self):
        """Reset all input fields and cancel any in-progress edit."""
        self.mac_input.value = ""
        self.mac_input.error_text = None
        self.ip_input.value = "255.255.255.255"
        self.port_input.value = "9"
        self.name_input.value = ""
        self._editing_index = None

    def on_save_click(self, e):
        """Save or update the current device, then refresh the list.

        Validates the MAC and name.  If an edit is in progress the
        existing entry is updated; otherwise a new entry is appended.
        """
        self._auto_format_mac()
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        name = self.name_input.value.strip() if self.name_input.value else ""
        if not validate_mac(mac):
            self.show_snack("Enter a valid MAC before saving", error=True)
            return
        if not name:
            self.show_snack("Enter a device name", error=True)
            return
        ip = self.ip_input.value.strip() if self.ip_input.value else "255.255.255.255"
        try:
            port = int(self.port_input.value.strip()) if self.port_input.value else 9
        except ValueError:
            self.show_snack("Port must be a number", error=True)
            return

        device = {"name": name, "mac": mac.upper(), "ip": ip, "port": port}
        devices = load_devices()
        if self._editing_index is not None:
            devices[self._editing_index] = device
            self._editing_index = None
        else:
            devices.append(device)
        save_devices(devices)
        self._clear_form()
        self.refresh_device_list()
        self.show_snack(f'Saved "{name}"')

    def on_clear_click(self, e):
        """Reset all input fields to their defaults."""
        self._clear_form()
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
                                        ft.Text("Device", size=20, weight=ft.FontWeight.W_600),
                                        ft.Row(
                                            controls=[self.mac_input, self.mac_helper],
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        ft.Text("Save device", size=20, weight=ft.FontWeight.W_600),
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
                                        ft.Row(
                                            controls=[
                                                self.ip_input,
                                                self.port_input,
                                            ],
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        ft.Divider(height=12),
                                        ft.Container(
                                            content=self.wake_button,
                                            padding=ft.Padding.symmetric(horizontal=8),
                                        ),
                                        ft.Container(
                                            content=ft.Row(
                                                controls=[
                                                    self.loading,
                                                    self.sending_label,
                                                ],
                                                alignment=ft.MainAxisAlignment.CENTER,
                                                spacing=8,
                                            ),
                                            padding=ft.Padding.symmetric(vertical=2),
                                        ),
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
                                    spacing=6,
                                ),
                                padding=ft.Padding.all(16),
                            ),
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text("Saved devices", size=20, weight=ft.FontWeight.W_600),
                                        self.device_cards,
                                        self.empty_state,
                                    ],
                                    spacing=4,
                                ),
                                padding=ft.Padding(left=16, top=0, right=16, bottom=16),
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
