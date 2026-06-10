import flet as ft

from wol_app.strings import get_strings


def build_delete_dialog(on_confirm, on_cancel, s=None) -> ft.AlertDialog:
    if s is None:
        s = get_strings("en")
    return ft.AlertDialog(
        title=ft.Text(s["delete_device"], size=16, weight=ft.FontWeight.BOLD),
        content=ft.Text(s["delete_confirm"]),
        actions=[
            ft.TextButton(s["cancel"], on_click=on_cancel),
            ft.TextButton(s["delete"], on_click=on_confirm),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def build_log_viewer_dialog(lines: list[str], on_close, on_clear=None, s=None) -> ft.AlertDialog:
    if s is None:
        s = get_strings("en")
    actions: list[ft.Control] = []
    if on_clear:
        actions.append(ft.TextButton("Clear", on_click=on_clear))
    actions.append(ft.TextButton(s["cancel"], on_click=on_close))
    return ft.AlertDialog(
        title=ft.Text(s["log_viewer"], size=16, weight=ft.FontWeight.BOLD),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(line, size=11, font_family="monospace")
                    for line in (lines or [s["log_empty"]])
                ],
                spacing=1,
                scroll=ft.ScrollMode.AUTO,
                height=400,
            ),
            width=500,
        ),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )
