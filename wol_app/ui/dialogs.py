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
