"""E2E tests — smoke-level checks that UI components render without crash."""

from unittest.mock import MagicMock

from wol_app.strings import get_strings
from wol_app.ui.dialogs import build_delete_dialog, build_log_viewer_dialog
from wol_app.ui.widgets import (
    build_device_card,
    build_empty_state,
    build_loading,
    build_mac_helper,
    build_mac_input,
    build_name_input,
    build_port_input,
    build_sending_label,
    build_wake_button,
)


class TestE2EWidgets:
    def test_mac_input_created(self):
        field = build_mac_input(lambda e: None, get_strings("en"))
        assert field.label == "MAC-address"

    def test_empty_state_created(self):
        state = build_empty_state(get_strings("en"))
        assert state.visible is None or state.visible is True

    def test_loading_widget_created(self):
        spinner = build_loading()
        assert not spinner.visible

    def test_sending_label_created(self):
        label = build_sending_label(get_strings("en"))
        assert "Sending" in label.value

    def test_wake_button_created(self):
        btn = build_wake_button(get_strings("en"), lambda e: None)
        assert btn.on_click is not None

    def test_delete_dialog_created(self):
        dialog = build_delete_dialog(lambda e: None, lambda e: None)
        assert "Delete" in str(dialog.title.value)

    def test_device_card_created(self):
        dev = MagicMock()
        dev.name = "Test"
        dev.mac = "AA:BB:CC:DD:EE:FF"
        dev.ip = "10.0.0.1"
        dev.port = 9
        dev.last_woken = None
        card = build_device_card(
            dev, 0,
            on_edit=lambda i, e: None,
            on_delete=lambda i, e: None,
            on_click=lambda m, i, p, e: None,
            on_dismiss=lambda i, e: None,
            s=get_strings("en"),
        )
        assert card is not None

    def test_name_input_created(self):
        field = build_name_input(get_strings("en"))
        assert field.hint_text == "e.g. Home PC"

    def test_port_input_created(self):
        field = build_port_input(get_strings("en"))
        assert field.value == "9"

    def test_mac_helper_created(self):
        helper = build_mac_helper(get_strings("en"))
        assert helper.tooltip is not None

    def test_log_viewer_dialog_created(self):
        dialog = build_log_viewer_dialog(["line1"], lambda e: None)
        assert dialog is not None
