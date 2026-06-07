"""Tests for the Wake-on-LAN Flet application."""

import json
import socket
from unittest.mock import MagicMock, patch

import pytest

from main import (
    WolApp,
    _build_magic_packet,
    _load_devices,
    _mac_to_bytes,
    _save_devices,
    _send_wol,
    _validate_mac,
)

# ===========================================================================
# Unit tests — pure logic functions
# ===========================================================================


# ---------------------------------------------------------------------------
# _validate_mac
# ---------------------------------------------------------------------------


class TestValidateMac:
    def test_valid_standard(self):
        assert _validate_mac("AA:BB:CC:DD:EE:FF") is True

    def test_valid_lowercase(self):
        assert _validate_mac("aa:bb:cc:dd:ee:ff") is True

    def test_valid_mixed_case(self):
        assert _validate_mac("aA:bB:cC:dD:eE:fF") is True

    def test_valid_with_zeros(self):
        assert _validate_mac("00:11:22:33:44:55") is True

    def test_valid_all_zeros(self):
        assert _validate_mac("00:00:00:00:00:00") is True

    def test_valid_all_ff(self):
        assert _validate_mac("FF:FF:FF:FF:FF:FF") is True

    def test_invalid_wrong_separator_dash(self):
        assert _validate_mac("AA-BB-CC-DD-EE-FF") is False

    def test_invalid_wrong_separator_dot(self):
        assert _validate_mac("AA.BB.CC.DD.EE.FF") is False

    def test_invalid_too_short(self):
        assert _validate_mac("AA:BB:CC:DD:EE") is False

    def test_invalid_too_long(self):
        assert _validate_mac("AA:BB:CC:DD:EE:FF:00") is False

    def test_invalid_extra_colons(self):
        assert _validate_mac("AA:BB:CC:DD:EE:FF:") is False

    def test_invalid_garbage(self):
        assert _validate_mac("not-a-mac") is False

    def test_invalid_hex_out_of_range(self):
        assert _validate_mac("GG:HH:II:JJ:KK:LL") is False

    def test_invalid_empty_string(self):
        assert _validate_mac("") is False

    def test_invalid_whitespace_only(self):
        assert _validate_mac("   ") is False

    def test_valid_leading_trailing_whitespace(self):
        assert _validate_mac("  AA:BB:CC:DD:EE:FF  ") is True

    def test_invalid_single_hex_digit_per_group(self):
        assert _validate_mac("A:B:C:D:E:F") is False

    def test_invalid_triple_hex_digit(self):
        assert _validate_mac("AAA:BBB:CCC:DDD:EEE:FFF") is False

    def test_none_value(self):
        with pytest.raises((AttributeError, TypeError)):
            _validate_mac(None)


# ---------------------------------------------------------------------------
# _mac_to_bytes
# ---------------------------------------------------------------------------


class TestMacToBytes:
    def test_conversion(self):
        result = _mac_to_bytes("AA:BB:CC:DD:EE:FF")
        assert result == b"\xaa\xbb\xcc\xdd\xee\xff"

    def test_conversion_zeros(self):
        result = _mac_to_bytes("00:00:00:00:00:00")
        assert result == b"\x00\x00\x00\x00\x00\x00"

    def test_conversion_all_ff(self):
        result = _mac_to_bytes("FF:FF:FF:FF:FF:FF")
        assert result == b"\xff\xff\xff\xff\xff\xff"

    def test_conversion_lowercase(self):
        result = _mac_to_bytes("aa:bb:cc:dd:ee:ff")
        assert result == b"\xaa\xbb\xcc\xdd\xee\xff"

    def test_conversion_with_whitespace(self):
        result = _mac_to_bytes("  01:02:03:04:05:06  ")
        assert result == b"\x01\x02\x03\x04\x05\x06"

    def test_output_length(self):
        result = _mac_to_bytes("11:22:33:44:55:66")
        assert len(result) == 6

    def test_conversion_specific(self):
        result = _mac_to_bytes("12:34:56:78:9A:BC")
        assert result == b"\x12\x34\x56\x78\x9a\xbc"


# ---------------------------------------------------------------------------
# _build_magic_packet
# ---------------------------------------------------------------------------


class TestBuildMagicPacket:
    def test_structure(self):
        mac = b"\xaa\xbb\xcc\xdd\xee\xff"
        packet = _build_magic_packet(mac)
        assert len(packet) == 102
        assert packet[:6] == b"\xff" * 6

    def test_mac_repeated_16_times(self):
        mac = b"\xaa\xbb\xcc\xdd\xee\xff"
        packet = _build_magic_packet(mac)
        for i in range(16):
            start = 6 + i * 6
            assert packet[start : start + 6] == mac

    def test_trailing_after_header(self):
        mac = b"\x01\x02\x03\x04\x05\x06"
        packet = _build_magic_packet(mac)
        assert packet[6:] == mac * 16

    def test_zeros_mac(self):
        mac = b"\x00\x00\x00\x00\x00\x00"
        packet = _build_magic_packet(mac)
        assert packet == b"\xff" * 6 + b"\x00" * 96

    def test_ff_mac(self):
        mac = b"\xff\xff\xff\xff\xff\xff"
        packet = _build_magic_packet(mac)
        assert packet == b"\xff" * 102


# ---------------------------------------------------------------------------
# _send_wol (async, socket mocked)
# ---------------------------------------------------------------------------


class TestSendWol:
    @pytest.mark.asyncio
    async def test_success(self):
        with patch("main.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock

            result = await _send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)

            assert "sent" in result.lower()
            mock_sock.setsockopt.assert_called_once_with(
                socket.SOL_SOCKET, socket.SO_BROADCAST, 1
            )
            mock_sock.settimeout.assert_called_once_with(5)
            mock_sock.sendto.assert_called_once()

            sent_packet = mock_sock.sendto.call_args[0][0]
            assert len(sent_packet) == 102
            assert sent_packet[:6] == b"\xff" * 6

    @pytest.mark.asyncio
    async def test_success_custom_ip_port(self):
        with patch("main.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock

            result = await _send_wol("11:22:33:44:55:66", "192.168.1.255", 7)

            assert "sent" in result.lower()
            mock_sock.sendto.assert_called_once()
            addr = mock_sock.sendto.call_args[0][1]
            assert addr == ("192.168.1.255", 7)

    @pytest.mark.asyncio
    async def test_network_error(self):
        with patch("main.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            mock_sock.sendto.side_effect = OSError("Network is unreachable")

            result = await _send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)

            assert "error" in result.lower()
            assert "unreachable" in result

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        with patch("main.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            mock_sock.sendto.side_effect = RuntimeError("Unexpected failure")

            result = await _send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)

            assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_socket_creation_failure(self):
        with patch("main.socket.socket") as mock_socket_cls:
            mock_socket_cls.side_effect = OSError("Permission denied")
            result = await _send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)
            assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_packet_content(self):
        with patch("main.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock

            await _send_wol("12:34:56:78:9A:BC", "10.0.0.255", 9)

            sent_packet = mock_sock.sendto.call_args[0][0]
            expected_mac = b"\x12\x34\x56\x78\x9a\xbc"
            assert sent_packet == b"\xff" * 6 + expected_mac * 16

    @pytest.mark.asyncio
    async def test_ip_stripped_of_whitespace(self):
        with patch("main.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock

            await _send_wol("AA:BB:CC:DD:EE:FF", "  10.0.0.1  ", 9)

            addr = mock_sock.sendto.call_args[0][1]
            assert addr == ("10.0.0.1", 9)


# ---------------------------------------------------------------------------
# _save_devices / _load_devices
# ---------------------------------------------------------------------------


class TestDeviceStorage:
    def test_save_and_load_roundtrip(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "devices.json")
            devices = [
                {"name": "Home PC", "mac": "AA:BB:CC:DD:EE:FF"},
                {"name": "Laptop", "mac": "11:22:33:44:55:66"},
            ]
            _save_devices(devices)
            assert _load_devices() == devices
        finally:
            m.DATA_FILE = original

    def test_load_empty_when_no_file(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "nonexistent.json")
            assert _load_devices() == []
        finally:
            m.DATA_FILE = original

    def test_save_empty_list(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "empty.json")
            _save_devices([])
            assert _load_devices() == []
        finally:
            m.DATA_FILE = original

    def test_load_corrupted_file_returns_empty(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            fpath = tmp_path / "corrupted.json"
            m.DATA_FILE = str(fpath)
            fpath.write_text("not encrypted data", encoding="utf-8")
            assert _load_devices() == []
        finally:
            m.DATA_FILE = original

    def test_multiple_saves_overwrite(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "multi.json")
            _save_devices([{"name": "A", "mac": "AA:AA:AA:AA:AA:AA"}])
            _save_devices([{"name": "B", "mac": "BB:BB:BB:BB:BB:BB"}])
            assert _load_devices() == [{"name": "B", "mac": "BB:BB:BB:BB:BB:BB"}]
        finally:
            m.DATA_FILE = original

    def test_save_unicode_names(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "unicode.json")
            devices = [{"name": "Компьютер", "mac": "AA:BB:CC:DD:EE:FF"}]
            _save_devices(devices)
            assert _load_devices() == devices
        finally:
            m.DATA_FILE = original

    def test_save_large_number_of_devices(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "large.json")
            devices = [
                {"name": f"Device {i}", "mac": f"AA:BB:CC:DD:EE:{i:02X}"}
                for i in range(50)
            ]
            _save_devices(devices)
            assert _load_devices() == devices
        finally:
            m.DATA_FILE = original

    def test_encrypted_output_not_plaintext(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            fpath = tmp_path / "encrypted.json"
            m.DATA_FILE = str(fpath)
            _save_devices([{"name": "secret", "mac": "AA:BB:CC:DD:EE:FF"}])
            raw = fpath.read_text(encoding="utf-8")
            assert "AA:BB:CC:DD:EE:FF" not in raw
            with pytest.raises((json.JSONDecodeError, ValueError)):
                json.loads(raw)
        finally:
            m.DATA_FILE = original

    def test_encrypt_decrypt_key_mismatch(self, tmp_path):
        import main as m

        original_key = m.CRYPT_KEY
        original_file = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "key_mismatch.json")
            m.CRYPT_KEY = "first-key-1234567890123456"
            _save_devices([{"name": "X", "mac": "AA:BB:CC:DD:EE:FF"}])
            m.CRYPT_KEY = "second-key-9876543210987654"
            result = _load_devices()
            assert result == []
        finally:
            m.CRYPT_KEY = original_key
            m.DATA_FILE = original_file


# ===========================================================================
# WolApp class tests — mocked Flet Page
# ===========================================================================


def _make_mock_page():
    """Create a mock ft.Page that can handle all calls made during WolApp init."""
    page = MagicMock()
    page.overlay = []
    page.padding = None
    page.scroll = None
    page.theme_mode = None
    page.appbar = None
    page.theme = None
    page.dark_theme = None
    return page


class TestWolAppInit:
    """Verify that WolApp correctly configures the Flet page."""

    def test_page_title_and_padding(self):
        page = _make_mock_page()
        WolApp(page)
        assert page.title == "Wake on LAN"
        assert page.padding == 0

    def test_page_scroll(self):
        page = _make_mock_page()
        WolApp(page)
        assert page.scroll is not None

    def test_page_theme_mode_system(self):
        page = _make_mock_page()
        WolApp(page)
        assert page.theme_mode is not None

    def test_page_appbar_set(self):
        page = _make_mock_page()
        WolApp(page)
        assert page.appbar is not None


class TestWolAppInputs:
    """Test input values and validation through WolApp."""

    def test_mac_input_accepts_value(self):
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        mac, ip, port = app.validate_inputs()
        assert mac == "AA:BB:CC:DD:EE:FF"
        assert ip == "255.255.255.255"
        assert port == 9

    def test_validate_inputs_custom_ip_port(self):
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "11:22:33:44:55:66"
        app.ip_input.value = "10.0.0.255"
        app.port_input.value = "7"
        mac, ip, port = app.validate_inputs()
        assert mac == "11:22:33:44:55:66"
        assert ip == "10.0.0.255"
        assert port == 7

    def test_validate_inputs_raises_no_mac(self):
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = ""
        with pytest.raises(ValueError, match="MAC address is required"):
            app.validate_inputs()

    def test_validate_inputs_raises_invalid_mac(self):
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "invalid"
        with pytest.raises(ValueError, match="Invalid MAC format"):
            app.validate_inputs()

    def test_validate_inputs_raises_bad_port(self):
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "AA:BB:CC:DD:EE:FF"
        app.port_input.value = "not-a-number"
        with pytest.raises(ValueError, match="Port must be a number"):
            app.validate_inputs()

    def test_validate_inputs_strips_whitespace(self):
        page = _make_mock_page()
        app = WolApp(page)
        app.mac_input.value = "  AA:BB:CC:DD:EE:FF  "
        app.ip_input.value = "  10.0.0.1  "
        mac, ip, port = app.validate_inputs()
        assert mac == "AA:BB:CC:DD:EE:FF"
        assert ip.strip() == ip  # already stripped inside validate_inputs


class TestWolAppClear:
    """Test the clear-fields functionality."""

    def test_clear_resets_all_fields(self):
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
    """Test the save-device logic via on_save_click."""

    def test_save_valid_device(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "save_test.json")
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "AA:BB:CC:DD:EE:FF"
            app.name_input.value = "My PC"
            app.on_save_click(None)
            devices = _load_devices()
            assert len(devices) == 1
            assert devices[0]["name"] == "My PC"
            assert devices[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        finally:
            m.DATA_FILE = original

    def test_save_converts_mac_to_upper(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "upper_test.json")
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "aa:bb:cc:dd:ee:ff"
            app.name_input.value = "Lower"
            app.on_save_click(None)
            devices = _load_devices()
            assert devices[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        finally:
            m.DATA_FILE = original

    def test_save_rejects_invalid_mac(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "invalid_save.json")
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "invalid"
            app.name_input.value = "Bad"
            app.on_save_click(None)
            assert _load_devices() == []
        finally:
            m.DATA_FILE = original

    def test_save_rejects_empty_name(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "noname.json")
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "AA:BB:CC:DD:EE:FF"
            app.name_input.value = ""
            app.on_save_click(None)
            assert _load_devices() == []
        finally:
            m.DATA_FILE = original


class TestWolAppDelete:
    """Test deleting devices from the saved list."""

    def test_delete_existing_device(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "delete_test.json")
            _save_devices([{"name": "A", "mac": "AA:AA:AA:AA:AA:AA"}])
            page = _make_mock_page()
            app = WolApp(page)
            app._delete_device(0)
            assert _load_devices() == []
        finally:
            m.DATA_FILE = original

    def test_delete_out_of_range_does_nothing(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "delete_oob.json")
            _save_devices([{"name": "A", "mac": "AA:AA:AA:AA:AA:AA"}])
            page = _make_mock_page()
            app = WolApp(page)
            app._delete_device(5)
            assert len(_load_devices()) == 1
        finally:
            m.DATA_FILE = original

    def test_delete_negative_index_does_nothing(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "delete_neg.json")
            _save_devices([{"name": "A", "mac": "AA:AA:AA:AA:AA:AA"}])
            page = _make_mock_page()
            app = WolApp(page)
            app._delete_device(-1)
            assert len(_load_devices()) == 1
        finally:
            m.DATA_FILE = original


class TestWolAppSendFromList:
    """Test sending from the device list."""

    @pytest.mark.asyncio
    async def test_send_from_list_sets_mac_and_sends(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "send_list.json")
            _save_devices([{"name": "Test", "mac": "AA:BB:CC:DD:EE:FF"}])
            page = _make_mock_page()
            app = WolApp(page)

            with patch(
                "main._send_wol", return_value="Magic packet sent to AA:BB:CC:DD:EE:FF"
            ):
                await app._send_from_list("AA:BB:CC:DD:EE:FF")
                assert app.mac_input.value == "AA:BB:CC:DD:EE:FF"
        finally:
            m.DATA_FILE = original


class TestWolAppRefreshDeviceList:
    """Test the device list refresh."""

    def test_refresh_with_devices(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "refresh.json")
            _save_devices([{"name": "PC", "mac": "AA:BB:CC:DD:EE:FF"}])
            page = _make_mock_page()
            app = WolApp(page)
            assert len(app.device_cards.controls) == 1
        finally:
            m.DATA_FILE = original

    def test_refresh_with_no_devices(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "refresh_empty.json")
            _save_devices([])
            page = _make_mock_page()
            app = WolApp(page)
            assert len(app.device_cards.controls) == 0
        finally:
            m.DATA_FILE = original


class TestWolAppSnackBar:
    """Test the snack bar helper."""

    def test_shows_success_snack(self):
        page = _make_mock_page()
        app = WolApp(page)
        app.show_snack("OK")
        assert len(page.overlay) > 0

    def test_shows_error_snack(self):
        page = _make_mock_page()
        app = WolApp(page)
        app.show_snack("FAIL", error=True)
        assert len(page.overlay) > 0


# ===========================================================================
# Integration tests
# ===========================================================================


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_flow_valid_mac(self):
        mac_str = "AA:BB:CC:DD:EE:FF"
        assert _validate_mac(mac_str) is True
        mac_bytes = _mac_to_bytes(mac_str)
        assert mac_bytes == b"\xaa\xbb\xcc\xdd\xee\xff"
        packet = _build_magic_packet(mac_bytes)
        assert len(packet) == 102
        assert packet[:6] == b"\xff" * 6
        assert packet[6:] == mac_bytes * 16

        with patch("main.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__.return_value = mock_sock
            result = await _send_wol(mac_str, "255.255.255.255", 9)
            assert "sent" in result.lower()

    @pytest.mark.asyncio
    async def test_save_then_load_and_send(self, tmp_path):
        import main as m

        original = m.DATA_FILE
        try:
            m.DATA_FILE = str(tmp_path / "integration.json")
            mac = "AA:BB:CC:DD:EE:FF"
            _save_devices([{"name": "Integration PC", "mac": mac}])
            loaded = _load_devices()
            assert loaded[0]["mac"] == mac

            mac_bytes = _mac_to_bytes(loaded[0]["mac"])
            packet = _build_magic_packet(mac_bytes)
            assert len(packet) == 102

            with patch("main.socket.socket") as mock_cls:
                mock_sock = MagicMock()
                mock_cls.return_value.__enter__.return_value = mock_sock
                result = await _send_wol(mac, "255.255.255.255", 9)
                assert "sent" in result.lower()
        finally:
            m.DATA_FILE = original
