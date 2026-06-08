import flet as ft


def build_delete_dialog(on_confirm, on_cancel) -> ft.AlertDialog:
    return ft.AlertDialog(
        title=ft.Text("Delete device", size=16, weight=ft.FontWeight.BOLD),
        content=ft.Text("Are you sure you want to delete this device?"),
        actions=[
            ft.TextButton("Cancel", on_click=on_cancel),
            ft.TextButton("Delete", on_click=on_confirm),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def build_log_viewer_dialog(lines: list[str], on_close, on_clear=None) -> ft.AlertDialog:
    actions: list[ft.Control] = []
    if on_clear:
        actions.append(ft.TextButton("Clear", on_click=on_clear))
    actions.append(ft.TextButton("Close", on_click=on_close))
    return ft.AlertDialog(
        title=ft.Text("Log viewer", size=16, weight=ft.FontWeight.BOLD),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(line, size=11, font_family="monospace")
                    for line in (lines or ["No log entries"])
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
