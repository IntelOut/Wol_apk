"""Tests for WolApp UI class with mocked Flet Page."""

import sys
from unittest.mock import patch

import pytest

from wol_app.config import VERSION
from wol_app.models import Device
from wol_app.storage import load_devices, save_devices
from wol_app.ui import WolApp


class TestWolAppInit:
    def test_page_title_and_padding(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        WolApp(page)
        if sys.platform == "win32":
            assert page.title == f"WakeOnLAN v{VERSION}"
        else:
            assert page.title == "WakeOnLAN"
        assert page.padding == 0

    def test_page_scroll_not_set(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        WolApp(page)
        assert page.scroll is None

    def test_page_theme_mode_system(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        WolApp(page)
        assert page.theme_mode is not None

    def test_page_appbar_set(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        WolApp(page)
        assert page.appbar is not None


class TestWolAppInputs:
    def test_mac_input_accepts_value(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        mac, ip, port = app.validate_inputs()
        assert mac == "AA:BB:CC:DD:EE:FF"
        assert ip == "255.255.255.255"
        assert port == 9

    def test_validate_inputs_custom_ip_port(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "11:22:33:44:55:66"
        app.ip_input.value = "10.0.0.255"
        app.port_input.value = "7"
        mac, ip, port = app.validate_inputs()
        assert mac == "11:22:33:44:55:66"
        assert ip == "10.0.0.255"
        assert port == 7

    def test_validate_inputs_raises_no_mac(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = ""
        with pytest.raises(ValueError, match="MAC address is required"):
            app.validate_inputs()

    def test_validate_inputs_raises_invalid_mac(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "invalid"
        with pytest.raises(ValueError, match="Invalid MAC format"):
            app.validate_inputs()

    def test_validate_inputs_raises_bad_port(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.port_input.value = "not-a-number"
        with pytest.raises(ValueError, match="Port must be a number"):
            app.validate_inputs()

    def test_validate_inputs_raises_bad_port_range(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.port_input.value = "0"
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            app.validate_inputs()

    def test_validate_inputs_raises_port_too_high(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.port_input.value = "70000"
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            app.validate_inputs()

    def test_validate_inputs_strips_whitespace(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "  AA:BB:CC:DD:EE:FF  "
        app.ip_input.value = "  10.0.0.1  "
        mac, ip, _ = app.validate_inputs()
        assert mac == "AA:BB:CC:DD:EE:FF"
        assert ip.strip() == ip

    def test_validate_inputs_private_ip_required(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.ip_input.value = "8.8.8.8"
        with pytest.raises(ValueError, match="Only local network IPs"):
            app.validate_inputs()

    def test_validate_inputs_private_ip_allowed(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.ip_input.value = "192.168.1.100"
        _, ip, _ = app.validate_inputs()
        assert ip == "192.168.1.100"

    def test_validate_inputs_broadcast_allowed(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.ip_input.value = "255.255.255.255"
        _, ip, _ = app.validate_inputs()
        assert ip == "255.255.255.255"


class TestWolAppClear:
    def test_clear_resets_all_fields(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.ip_input.value = "10.0.0.1"
        app.port_input.value = "7"
        app.name_input.value = "My PC"
        app.on_clear_click(None)
        assert app.mac_input.value == ""
        assert app.ip_input.value == "255.255.255.255"
        assert app.port_input.value == "9"
        assert app.name_input.value == ""


class TestWolAppSave:
    def test_save_valid_device(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.name_input.value = "My PC"
        app.ip_input.value = "192.168.1.255"
        app.port_input.value = "9"
        app.on_save_click(None)
        devices = load_devices()
        assert len(devices) == 1
        assert devices[0].name == "My PC"
        assert devices[0].mac == "AA:BB:CC:DD:EE:FF"
        assert devices[0].ip == "192.168.1.255"
        assert devices[0].port == 9

    def test_save_converts_mac_to_upper(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "aa:bb:cc:dd:ee:ff"
        app.name_input.value = "Lower"
        app.on_save_click(None)
        devices = load_devices()
        assert devices[0].mac == "AA:BB:CC:DD:EE:FF"

    def test_save_rejects_invalid_mac(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "invalid"
        app.name_input.value = "Bad"
        app.on_save_click(None)
        assert load_devices() == []

    def test_save_rejects_empty_name(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.name_input.value = ""
        app.on_save_click(None)
        assert load_devices() == []

    def test_save_with_hyphen_mac_normalizes(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "aa-bb-cc-dd-ee-ff"
        app.name_input.value = "Hyphen PC"
        app.on_save_click(None)
        devices = load_devices()
        assert devices[0].mac == "AA:BB:CC:DD:EE:FF"


class TestWolAppEdit:
    def test_edit_device_updates_instead_of_appending(self, patched_storage):
        from tests.conftest import _make_mock_page
        save_devices([Device(name="Old", mac="AA:AA:AA:AA:AA:AA", ip="", port=9)])
        page = _make_mock_page()
        app = WolApp(page)
        app._start_edit(0)
        app.name_input.value = "Updated"
        app.mac_input.value = "BB:BB:BB:BB:BB:BB"
        app.on_save_click(None)
        devices = load_devices()
        assert len(devices) == 1
        assert devices[0].name == "Updated"
        assert devices[0].mac == "BB:BB:BB:BB:BB:BB"


class TestWolAppDelete:
    def test_delete_existing_device(self, patched_storage):
        from tests.conftest import _make_mock_page
        save_devices([Device(name="A", mac="AA:AA:AA:AA:AA:AA")])
        page = _make_mock_page()
        app = WolApp(page)
        app._delete_device(0)
        assert load_devices() == []

    def test_delete_out_of_range_does_nothing(self, patched_storage):
        from tests.conftest import _make_mock_page
        save_devices([Device(name="A", mac="AA:AA:AA:AA:AA:AA")])
        page = _make_mock_page()
        app = WolApp(page)
        app._delete_device(5)
        assert len(load_devices()) == 1

    def test_delete_negative_index_does_nothing(self, patched_storage):
        from tests.conftest import _make_mock_page
        save_devices([Device(name="A", mac="AA:AA:AA:AA:AA:AA")])
        page = _make_mock_page()
        app = WolApp(page)
        app._delete_device(-1)
        assert len(load_devices()) == 1


class TestWolAppSendFromList:
    @pytest.mark.asyncio
    async def test_send_from_list_sets_mac_and_sends(self, patched_storage):
        from tests.conftest import _make_mock_page
        save_devices([Device(name="Test", mac="AA:BB:CC:DD:EE:FF")])
        page = _make_mock_page()
        app = WolApp(page)
        with patch("wol_app.ui.app.send_wol", return_value=(True, "Magic packet sent to AA:BB:CC:DD:EE:FF")):
            await app._send_from_list("AA:BB:CC:DD:EE:FF")
            assert app.mac_input.value == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_send_from_list_sets_ip_port(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        with patch("wol_app.ui.app.send_wol", return_value=(True, "Magic packet sent to AA:BB:CC:DD:EE:FF")):
            await app._send_from_list("AA:BB:CC:DD:EE:FF", "10.0.0.255", "7")
            assert app.ip_input.value == "10.0.0.255"
            assert app.port_input.value == "7"


class TestWolAppRefreshDeviceList:
    def test_refresh_with_devices(self, patched_storage):
        from tests.conftest import _make_mock_page
        save_devices([Device(name="PC", mac="AA:BB:CC:DD:EE:FF")])
        page = _make_mock_page()
        app = WolApp(page)
        assert len(app.device_cards.controls) == 1

    def test_refresh_with_no_devices(self, patched_storage):
        from tests.conftest import _make_mock_page
        save_devices([])
        page = _make_mock_page()
        app = WolApp(page)
        assert len(app.device_cards.controls) == 0


class TestWolAppSnackBar:
    def test_shows_success_snack(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.show_snack("OK")
        assert len(page.overlay) > 0

    def test_shows_error_snack(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.show_snack("FAIL", error=True)
        assert len(page.overlay) > 0

    def test_snackbar_creates_new_instance(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        app.show_snack("First")
        app.show_snack("Second")
        assert len(page.overlay) == 1


class TestWolAppTheme:
    def test_on_theme_toggle(self, patched_storage):
        from tests.conftest import _make_mock_page
        page = _make_mock_page()
        app = WolApp(page)
        initial_dark = app._is_dark
        app._on_theme_toggle(None)
        assert app._is_dark == (not initial_dark)
