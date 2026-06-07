import sys

import flet as ft

from wol_app.config import PRIVACY_POLICY_URLS, USER_AGREEMENT_URLS, VERSION
from wol_app.models import Device
from wol_app.protocol import auto_format_mac, normalize_mac, send_wol, validate_ip, validate_mac
from wol_app.storage import load_devices, load_settings, save_devices, save_settings
from wol_app.ui.dialogs import build_delete_dialog
from wol_app.ui.widgets import (
    build_device_card,
    build_drawer,
    build_empty_state,
    build_ip_input,
    build_loading,
    build_mac_helper,
    build_mac_input,
    build_name_input,
    build_port_input,
    build_sending_label,
    build_wake_button,
)


class WolApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self._sending = False
        self._snackbar: ft.SnackBar | None = None
        self._pending_delete_index: int | None = None
        self._editing_index: int | None = None
        self._is_dark = True
        self._setup_page()
        self._build_controls()
        self.refresh_device_list()
        self._build_layout()

    def _setup_page(self):
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

    def _build_controls(self):
        self.mac_input = build_mac_input(self._validate_mac_field)
        self.mac_helper = build_mac_helper()
        self.ip_input = build_ip_input(self._validate_ip_field)
        self.port_input = build_port_input()
        self.name_input = build_name_input()
        self.device_cards = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        self.empty_state = build_empty_state()
        self.loading = build_loading()
        self.sending_label = build_sending_label()
        self.wake_button = build_wake_button(self.on_wake_click)

        self.confirm_delete_dialog = build_delete_dialog(
            on_confirm=self._confirm_delete,
            on_cancel=self._cancel_delete,
        )

        self.drawer = build_drawer(
            version=VERSION,
            privacy_urls=PRIVACY_POLICY_URLS,
            agreement_urls=USER_AGREEMENT_URLS,
            on_open_url=self._navigate_to_url,
        )
        self.page.drawer = self.drawer

    def _on_theme_toggle(self, e) -> None:
        self._is_dark = not self._is_dark
        theme_key = "dark" if self._is_dark else "light"
        self.page.theme_mode = ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT
        appbar = self.page.appbar
        if appbar and appbar.actions:  # type: ignore[union-attr]
            appbar.actions[0].icon = ft.Icons.DARK_MODE if self._is_dark else ft.Icons.LIGHT_MODE  # type: ignore[union-attr]
        save_settings({"theme_mode": theme_key})
        self.page.update()

    def _auto_format_mac(self) -> None:
        raw = self.mac_input.value.strip() if self.mac_input.value else ""
        formatted = auto_format_mac(raw)
        if formatted != raw:
            self.mac_input.value = formatted

    def _validate_mac_field(self, e) -> None:
        self._auto_format_mac()
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        if mac and not validate_mac(mac):
            self.mac_input.error_text = "Invalid MAC format"
        else:
            self.mac_input.error_text = None
        self.page.update()

    def _validate_ip_field(self, e) -> None:
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
        await self.page.show_drawer()

    def _navigate_to_url(self, url: str, e) -> None:
        self.page.run_task(ft.UrlLauncher().launch_url, url)

    def show_snack(self, message: str, error: bool = False) -> None:
        if self._snackbar is None:
            self._snackbar = ft.SnackBar(
                content=ft.Text(message, size=16),
                bgcolor=ft.Colors.GREEN_ACCENT_700,
                open=True,
            )
            self.page.overlay.append(self._snackbar)
        self._snackbar.content = ft.Text(message, size=16)
        self._snackbar.bgcolor = ft.Colors.RED_ACCENT_700 if error else ft.Colors.GREEN_ACCENT_700
        self._snackbar.open = True
        self.page.update()

    def _run_send(self, mac: str, ip: str = "", port: str = ""):
        self.page.run_task(self._send_from_list, mac, ip, port)

    def _prompt_delete(self, index: int):
        self._pending_delete_index = index
        self.page.show_dialog(self.confirm_delete_dialog)

    def _on_edit(self, idx: int, e) -> None:
        self._start_edit(idx)

    def _on_delete(self, idx: int, e) -> None:
        self._prompt_delete(idx)

    def _on_device_click(self, mac: str, ip: str, port: str, e) -> None:
        self._run_send(mac, ip, port)

    def _on_dismiss_wrapper(self, idx: int, e) -> None:
        self._on_dismiss_delete(idx)

    def refresh_device_list(self):
        self.device_cards.controls.clear()
        devices = load_devices()
        for i, dev in enumerate(devices):
            card = build_device_card(
                dev=dev,
                index=i,
                on_edit=self._on_edit,
                on_delete=self._on_delete,
                on_click=self._on_device_click,
                on_dismiss=self._on_dismiss_wrapper,
            )
            self.device_cards.controls.append(card)
        self.empty_state.visible = len(devices) == 0
        self.page.update()

    def _start_edit(self, index: int):
        devices = load_devices()
        dev = devices[index]
        self.mac_input.value = dev.mac
        self.name_input.value = dev.name
        self.ip_input.value = dev.ip
        self.port_input.value = str(dev.port)
        self._editing_index = index
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
        devices = load_devices()
        if 0 <= index < len(devices):
            removed = devices.pop(index)
            save_devices(devices)
            self.refresh_device_list()
            self.show_snack(f'Deleted "{removed.name}"')

    def validate_inputs(self) -> tuple[str, str, int]:
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

    async def send_wol_action(self):
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
        await self.send_wol_action()

    async def _send_from_list(self, mac: str, dev_ip: str = "", dev_port: str = ""):
        self.mac_input.value = mac
        if dev_ip:
            self.ip_input.value = dev_ip
        if dev_port:
            self.port_input.value = str(dev_port)
        self.page.update()
        await self.send_wol_action()

    def _clear_form(self):
        self.mac_input.value = ""
        self.mac_input.error_text = None
        self.ip_input.value = "255.255.255.255"
        self.port_input.value = "9"
        self.name_input.value = ""
        self._editing_index = None

    def on_save_click(self, e):
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

        device = Device(name=name, mac=normalize_mac(mac), ip=ip, port=port)
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
        self._clear_form()
        self.page.update()

    def _build_layout(self):
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
