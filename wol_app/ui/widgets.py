from functools import partial

import flet as ft


def build_device_card(
    dev, index: int,
    on_edit, on_delete, on_click, on_dismiss,
) -> ft.Dismissible:
    subtitle = ft.Row(
        controls=[ft.Text(dev.mac, size=12, color=ft.Colors.GREY_600)],
        wrap=True,
        spacing=0,
    )
    if dev.ip:
        subtitle.controls.append(ft.Text(" | ", size=12, color=ft.Colors.GREY_500))
        subtitle.controls.append(ft.Text(dev.ip, size=12, color=ft.Colors.GREY_600))
    if dev.port:
        subtitle.controls.append(ft.Text(" | ", size=12, color=ft.Colors.GREY_500))
        subtitle.controls.append(ft.Text(str(dev.port), size=12, color=ft.Colors.GREY_600))

    card = ft.Card(
        content=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.DEVICES, size=20),
                    ft.Column(
                        controls=[
                            ft.Text(dev.name, size=14, weight=ft.FontWeight.W_600),
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
                                on_click=partial(on_edit, index),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Delete",
                                icon_size=18,
                                on_click=partial(on_delete, index),
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
            on_click=partial(on_click, dev.mac, dev.ip, dev.port),
        ),
        elevation=1,
        margin=ft.Margin.symmetric(vertical=1),
    )

    return ft.Dismissible(
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
        on_dismiss=partial(on_dismiss, index),
    )


def build_empty_state() -> ft.Container:
    return ft.Container(
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


def build_loading() -> ft.ProgressRing:
    return ft.ProgressRing(width=24, height=24, visible=False)


def build_sending_label() -> ft.Text:
    return ft.Text("Sending...", size=14, color=ft.Colors.GREY_500, visible=False)


def build_wake_button(on_click) -> ft.Button:
    return ft.Button(
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
        on_click=on_click,
    )


def build_drawer(version: str, privacy_urls, agreement_urls, on_open_url) -> ft.NavigationDrawer:
    controls: list[ft.Control] = []
    if privacy_urls:
        controls.append(
            ft.Container(
                content=ft.Text(
                    "Privacy Policy", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_600
                ),
                padding=ft.Padding.symmetric(vertical=12, horizontal=20),
            )
        )
        for title, url in privacy_urls:
            controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED),
                    title=ft.Text(title),
                    on_click=partial(on_open_url, url),
                )
            )
    if agreement_urls:
        controls.append(ft.Divider(height=1))
        controls.append(
            ft.Container(
                content=ft.Text(
                    "User Agreement", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_600
                ),
                padding=ft.Padding.symmetric(vertical=12, horizontal=20),
            )
        )
        for title, url in agreement_urls:
            controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED),
                    title=ft.Text(title),
                    on_click=partial(on_open_url, url),
                )
            )

    return ft.NavigationDrawer(
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
                                ft.Text(f"v{version}", size=14, color=ft.Colors.GREY_500),
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
            *controls,
        ],
    )


def build_mac_input(on_change) -> ft.TextField:
    return ft.TextField(
        label="MAC-address",
        hint_text="XX:XX:XX:XX:XX:XX",
        prefix_icon=ft.Icons.WIFI,
        border_radius=12,
        text_size=16,
        expand=True,
        on_change=on_change,
    )


def build_mac_helper() -> ft.Icon:
    return ft.Icon(
        ft.Icons.HELP_OUTLINE,
        size=24,
        color=ft.Colors.GREY_500,
        tooltip=ft.Tooltip(
            message="Format: XX:XX:XX:XX:XX:XX\ne.g. AA:BB:CC:DD:EE:FF",
            padding=10,
            vertical_offset=0,
        ),
    )


def build_ip_input(on_change) -> ft.TextField:
    return ft.TextField(
        label="IP or Broadcast",
        hint_text="255.255.255.255",
        prefix_icon=ft.Icons.LAN,
        border_radius=12,
        text_size=16,
        value="255.255.255.255",
        expand=True,
        on_change=on_change,
    )


def build_port_input() -> ft.TextField:
    return ft.TextField(
        label="Port",
        hint_text="9",
        prefix_icon=ft.Icons.SETTINGS_ETHERNET,
        border_radius=12,
        text_size=16,
        value="9",
        width=120,
    )


def build_name_input() -> ft.TextField:
    return ft.TextField(
        label="Device name",
        hint_text="e.g. Home PC",
        prefix_icon=ft.Icons.LABEL_OUTLINE,
        border_radius=12,
        text_size=16,
        expand=True,
    )
