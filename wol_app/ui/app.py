import logging
import os
import sys
import time

import flet as ft
import sentry_sdk

from wol_app.config import PRIVACY_POLICY_URLS, USER_AGREEMENT_URLS, VERSION
from wol_app.logging_setup import get_log_path
from wol_app.models import Device
from wol_app.protocol import (
    auto_format_mac,
    normalize_mac,
    send_wol,
    validate_ip,
    validate_mac,
    validate_private_ip,
)
from wol_app.storage import Storage, load_devices, load_settings, save_devices, save_settings
from wol_app.strings import get_strings
from wol_app.ui.dialogs import build_delete_dialog, build_log_viewer_dialog
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

_logger = logging.getLogger(__name__)


class WolApp:
    def __init__(self, page: ft.Page, storage: Storage | None = None):
        self.page = page
        self._storage = storage
        self._sending = False
        self._snackbar: ft.SnackBar | None = None
        self._pending_delete_index: int | None = None
        self._editing_index: int | None = None
        self._is_dark = True
        self._lang = "en"
        self.log_dialog = None
        settings = self._load_settings()
        self._lang = settings.get("lang", "en")
        self._s = get_strings(self._lang)
        self._setup_page()
        self._build_controls()
        self.refresh_device_list()
        self._build_layout()
        sentry_sdk.add_breadcrumb(category="ui", message="App initialized", level="info")

    def _load_devices(self) -> list[Device]:
        if self._storage:
            return self._storage.load_devices()
        return load_devices()

    def _save_devices(self, devices: list) -> None:
        if self._storage:
            self._storage.save_devices(devices)
        else:
            save_devices(devices)

    def _load_settings(self) -> dict:
        if self._storage:
            return self._storage.load_settings()
        return load_settings()

    def _save_settings(self, settings: dict) -> None:
        if self._storage:
            self._storage.save_settings(settings)
        else:
            save_settings(settings)

    def _setup_page(self):
        self.page.title = f"WakeOnLAN v{VERSION}" if sys.platform == "win32" else "WakeOnLAN"
        self.page.padding = 0
        self.page.scroll = ft.ScrollMode.AUTO
        settings = self._load_settings()
        theme_key = settings.get("theme_mode", "dark")
        self._is_dark = theme_key != "light"
        self.page.theme_mode = ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT

        self._theme_button = ft.IconButton(
            icon=ft.Icons.DARK_MODE if self._is_dark else ft.Icons.LIGHT_MODE,
            tooltip="Toggle theme",
            on_click=self._on_theme_toggle,
        )
        self._lang_button = ft.IconButton(
            icon=ft.Icons.TRANSLATE,
            tooltip="RU/EN",
            on_click=self._on_lang_toggle,
        )
        self.page.appbar = ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.MENU,
                on_click=lambda _: self.page.run_task(self.open_drawer),
            ),
            title=ft.Text("WakeOnLAN", size=20, weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            actions=[self._lang_button, self._theme_button],
        )
        self.page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(primary=ft.Colors.INDIGO),
        )
        self.page.dark_theme = ft.Theme(
            color_scheme=ft.ColorScheme(primary=ft.Colors.INDIGO_ACCENT_200),
        )

    def _rebuild_ui(self):
        self._s = get_strings(self._lang)
        self.page.clean()
        self._snackbar = None
        self._build_controls()
        self.refresh_device_list()
        self._build_layout()
        self.page.update()
        sentry_sdk.add_breadcrumb(category="ui", message=f"UI rebuilt ({self._lang})", level="info")

    def _build_controls(self):
        s = self._s
        self.mac_input = build_mac_input(self._validate_mac_field, s)
        self.mac_helper = build_mac_helper(s)
        self.ip_input = build_ip_input(self._validate_ip_field, s)
        self.port_input = build_port_input(s)
        self.name_input = build_name_input(s)
        self.device_cards = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self.empty_state = build_empty_state(s, expand=True)
        self.loading = build_loading()
        self.sending_label = build_sending_label(s)
        self.wake_button = build_wake_button(s, self.on_wake_click)

        self.confirm_delete_dialog = build_delete_dialog(
            on_confirm=self._confirm_delete,
            on_cancel=self._cancel_delete,
        )
        self.log_dialog = None

        privacy_urls = PRIVACY_POLICY_URLS.get(self._lang, [])
        agreement_urls = USER_AGREEMENT_URLS.get(self._lang, [])
        self.drawer = build_drawer(
            version=VERSION,
            privacy_urls=privacy_urls,
            agreement_urls=agreement_urls,
            on_open_url=self._navigate_to_url,
            on_open_log=self._on_open_log,
            s=s,
        )
        self.page.drawer = self.drawer

    def _on_lang_toggle(self, e):
        self._lang = "ru" if self._lang == "en" else "en"
        self._save_settings({**self._load_settings(), "lang": self._lang})
        self._rebuild_ui()

    def _on_open_log(self, e):
        self._refresh_log_viewer()
        self.page.show_dialog(self.log_dialog)

    def _refresh_log_viewer(self):
        log_path = get_log_path()
        lines = []
        if os.path.exists(log_path):
            try:
                with open(log_path, encoding="utf-8") as f:
                    lines = f.read().splitlines()[-200:]
            except Exception:
                lines = ["(error reading log file)"]
        self.log_dialog = build_log_viewer_dialog(lines, self._close_log, on_clear=self._on_clear_log)

    def _on_clear_log(self, e):
        from wol_app.logging_setup import clear_log
        clear_log()
        self._refresh_log_viewer()
        self.page.update()

    def _close_log(self, e):
        if self.log_dialog:
            self.log_dialog.open = False
            self.page.update()

    def _on_theme_toggle(self, e) -> None:
        self._is_dark = not self._is_dark
        theme_key = "dark" if self._is_dark else "light"
        self.page.theme_mode = ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT
        self._theme_button.icon = ft.Icons.DARK_MODE if self._is_dark else ft.Icons.LIGHT_MODE
        self._save_settings({**self._load_settings(), "theme_mode": theme_key})
        self.page.update()
        sentry_sdk.add_breadcrumb(category="ui", message=f"Theme toggled to {theme_key}", level="info")

    def _auto_format_mac(self) -> None:
        raw = self.mac_input.value.strip() if self.mac_input.value else ""
        formatted = auto_format_mac(raw)
        if formatted != raw:
            self.mac_input.value = formatted

    def _validate_mac_field(self, e) -> None:
        self._auto_format_mac()
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        if mac and not validate_mac(mac):
            self.mac_input.error_text = self._s["invalid_mac"]
        else:
            self.mac_input.error_text = None
        self.page.update()

    def _validate_ip_field(self, e) -> None:
        raw = self.ip_input.value or ""
        if "," in raw:
            self.ip_input.value = raw.replace(",", ".")
        ip = self.ip_input.value.strip() if self.ip_input.value else ""
        if ip and ip != "255.255.255.255":
            if not validate_ip(ip):
                self.ip_input.error_text = self._s["invalid_ip"]
            elif not validate_private_ip(ip):
                self.ip_input.error_text = self._s["ip_not_private"]
            else:
                self.ip_input.error_text = None
        else:
            self.ip_input.error_text = None
        self.page.update()

    async def open_drawer(self):
        await self.page.show_drawer()

    def _navigate_to_url(self, url: str, e) -> None:
        self.page.run_task(ft.UrlLauncher().launch_url, url)

    def show_snack(self, message: str, error: bool = False) -> None:
        if self._snackbar is not None:
            self._snackbar.open = False
            self.page.overlay.remove(self._snackbar)
        self._snackbar = ft.SnackBar(
            content=ft.Text(message, size=16),
            bgcolor=ft.Colors.RED_ACCENT_700 if error else ft.Colors.GREEN_ACCENT_700,
            open=True,
        )
        self.page.overlay.append(self._snackbar)
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
        sentry_sdk.add_breadcrumb(category="wol", message=f"Device click: {mac}", level="info")
        self._run_send(mac, ip, port)

    def _on_dismiss_wrapper(self, idx: int, e) -> None:
        self._on_dismiss_delete(idx)

    def refresh_device_list(self):
        self.device_cards.controls.clear()
        devices = self._load_devices()
        for i, dev in enumerate(devices):
            card = build_device_card(
                dev=dev,
                index=i,
                on_edit=self._on_edit,
                on_delete=self._on_delete,
                on_click=self._on_device_click,
                on_dismiss=self._on_dismiss_wrapper,
                s=self._s,
            )
            self.device_cards.controls.append(card)
        self.empty_state.visible = len(devices) == 0
        self.page.update()

    def _start_edit(self, index: int):
        devices = self._load_devices()
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
        devices = self._load_devices()
        if 0 <= index < len(devices):
            removed = devices.pop(index)
            self._save_devices(devices)
            self.refresh_device_list()
            self.show_snack(f'{self._s["deleted"]} "{removed.name}"')
            sentry_sdk.add_breadcrumb(category="ui", message=f"Deleted device: {removed.name}", level="info")

    def validate_inputs(self) -> tuple[str, str, int]:
        s = self._s
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        if not mac:
            raise ValueError(s["mac_required"])
        if not validate_mac(mac):
            raise ValueError(s["invalid_mac_format"])
        ip = self.ip_input.value.strip() if self.ip_input.value else "255.255.255.255"
        if ip and ip != "255.255.255.255":
            if not validate_ip(ip):
                raise ValueError(s["invalid_ip_format"])
            if not validate_private_ip(ip):
                raise ValueError(s["ip_not_private"])
        try:
            port = int(self.port_input.value.strip()) if self.port_input.value else 9
        except ValueError as e:
            raise ValueError(s["port_must_be_number"]) from e
        if port <= 0 or port > 65535:
            raise ValueError(s["port_range"])
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
        sentry_sdk.add_breadcrumb(category="wol", message=f"Sending WOL: {mac}", level="info")

        success, msg = await send_wol(mac, ip, port)

        self.loading.visible = False
        self.sending_label.visible = False
        self.wake_button.disabled = False
        self._sending = False
        self.show_snack(msg, error=not success)
        if success:
            self._update_last_woken(mac, ip, str(port))
        self.page.update()

    async def on_wake_click(self, e):
        await self.send_wol_action()

    async def _send_from_list(self, mac: str, dev_ip: str = "", dev_port: str = ""):
        self.mac_input.value = mac
        if dev_ip:
            self.ip_input.value = dev_ip
        if dev_port:
            self.port_input.value = str(dev_port)
        self._sending = True
        self.wake_button.disabled = True
        self.loading.visible = True
        self.sending_label.visible = True
        self.page.update()
        success, _ = await send_wol(mac, dev_ip or "255.255.255.255", int(dev_port) if dev_port else 9)
        self.loading.visible = False
        self.sending_label.visible = False
        self.wake_button.disabled = False
        self._sending = False
        if success:
            self._update_last_woken(mac, dev_ip, dev_port)
        self.page.update()

    def _update_last_woken(self, mac: str, ip: str, port: str):
        devices = self._load_devices()
        now = time.time()
        updated = False
        for d in devices:
            if d.mac == mac and d.ip == (ip or "255.255.255.255"):
                d.last_woken = now
                updated = True
                break
        if updated:
            self._save_devices(devices)

    def _clear_form(self):
        self.mac_input.value = ""
        self.mac_input.error_text = None
        self.ip_input.value = "255.255.255.255"
        self.port_input.value = "9"
        self.name_input.value = ""
        self._editing_index = None

    def on_save_click(self, e):
        s = self._s
        self._auto_format_mac()
        mac = self.mac_input.value.strip() if self.mac_input.value else ""
        name = self.name_input.value.strip() if self.name_input.value else ""
        if not validate_mac(mac):
            self.show_snack(s["mac_valid_required"], error=True)
            return
        if not name:
            self.show_snack(s["name_required"], error=True)
            return
        ip = self.ip_input.value.strip() if self.ip_input.value else "255.255.255.255"
        if ip and ip != "255.255.255.255":
            if not validate_ip(ip):
                self.show_snack(s["invalid_ip_format"], error=True)
                return
            if not validate_private_ip(ip):
                self.show_snack(s["ip_not_private"], error=True)
                return
        try:
            port = int(self.port_input.value.strip()) if self.port_input.value else 9
        except ValueError:
            self.show_snack(s["port_must_be_number"], error=True)
            return
        if port <= 0 or port > 65535:
            self.show_snack(s["port_range"], error=True)
            return

        device = Device(name=name, mac=normalize_mac(mac), ip=ip, port=port)
        devices = self._load_devices()
        if self._editing_index is not None:
            devices[self._editing_index] = device
            self._editing_index = None
        else:
            devices.append(device)
        self._save_devices(devices)
        self._clear_form()
        self.refresh_device_list()
        self.show_snack(f'{s["saved"]} "{name}"')
        sentry_sdk.add_breadcrumb(category="ui", message=f"Saved device: {name}", level="info")

    def on_clear_click(self, e):
        self._clear_form()
        self.page.update()

    def _build_layout(self):
        s = self._s
        self.page.add(
            ft.SafeArea(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(s["device"], size=20, weight=ft.FontWeight.W_600),
                                        ft.Row(
                                            controls=[self.mac_input, self.mac_helper],
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        ft.Text(s["save_device"], size=20, weight=ft.FontWeight.W_600),
                                        ft.Row(
                                            controls=[
                                                self.name_input,
                                                ft.IconButton(
                                                    icon=ft.Icons.SAVE,
                                                    tooltip=s["save"],
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
                                                    s["clear_fields"],
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
                                expand=True,
                                content=ft.Column(
                                    expand=True,
                                    controls=[
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
