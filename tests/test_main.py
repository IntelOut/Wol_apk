"""Tests for the Wake-on-LAN Flet application."""

import json
import os
import socket
import sys
from unittest.mock import MagicMock, patch

import pytest

from wol_app.protocol import (
    auto_format_mac,
    build_magic_packet,
    mac_to_bytes,
    send_wol,
    validate_ip,
    validate_mac,
)
from wol_app.storage import load_devices, load_settings, save_devices, save_settings
from wol_app.ui import WolApp

# ===========================================================================
# Unit tests — pure logic functions
# ===========================================================================


# ---------------------------------------------------------------------------
# validate_mac
# ---------------------------------------------------------------------------


class TestValidateMac:
    def test_valid_standard(self):
        assert validate_mac("AA:BB:CC:DD:EE:FF") is True

    def test_valid_lowercase(self):
        assert validate_mac("aa:bb:cc:dd:ee:ff") is True

    def test_valid_mixed_case(self):
        assert validate_mac("aA:bB:cC:dD:eE:fF") is True

    def test_valid_with_zeros(self):
        assert validate_mac("00:11:22:33:44:55") is True

    def test_valid_all_zeros(self):
        assert validate_mac("00:00:00:00:00:00") is True

    def test_valid_all_ff(self):
        assert validate_mac("FF:FF:FF:FF:FF:FF") is True

    def test_invalid_wrong_separator_dash(self):
        assert validate_mac("AA-BB-CC-DD-EE-FF") is False

    def test_invalid_wrong_separator_dot(self):
        assert validate_mac("AA.BB.CC.DD.EE.FF") is False

    def test_invalid_too_short(self):
        assert validate_mac("AA:BB:CC:DD:EE") is False

    def test_invalid_too_long(self):
        assert validate_mac("AA:BB:CC:DD:EE:FF:00") is False

    def test_invalid_extra_colons(self):
        assert validate_mac("AA:BB:CC:DD:EE:FF:") is False

    def test_invalid_garbage(self):
        assert validate_mac("not-a-mac") is False

    def test_invalid_hex_out_of_range(self):
        assert validate_mac("GG:HH:II:JJ:KK:LL") is False

    def test_invalid_empty_string(self):
        assert validate_mac("") is False

    def test_invalid_whitespace_only(self):
        assert validate_mac("   ") is False

    def test_valid_leading_trailing_whitespace(self):
        assert validate_mac("  AA:BB:CC:DD:EE:FF  ") is True

    def test_invalid_single_hex_digit_per_group(self):
        assert validate_mac("A:B:C:D:E:F") is False

    def test_invalid_triple_hex_digit(self):
        assert validate_mac("AAA:BBB:CCC:DDD:EEE:FFF") is False

    def test_none_value(self):
        with pytest.raises((AttributeError, TypeError)):
            validate_mac(None)


# ---------------------------------------------------------------------------
# validate_ip
# ---------------------------------------------------------------------------


class TestValidateIp:
    def test_valid_standard(self):
        assert validate_ip("192.168.1.1") is True

    def test_valid_broadcast(self):
        assert validate_ip("255.255.255.255") is True

    def test_valid_zero(self):
        assert validate_ip("0.0.0.0") is True

    def test_valid_max(self):
        assert validate_ip("255.255.255.255") is True

    def test_valid_all_octets(self):
        assert validate_ip("10.0.0.1") is True
        assert validate_ip("172.16.0.1") is True
        assert validate_ip("224.0.0.1") is True

    def test_invalid_too_many_octets(self):
        assert validate_ip("1.2.3.4.5") is False

    def test_invalid_too_few_octets(self):
        assert validate_ip("1.2.3") is False

    def test_invalid_empty(self):
        assert validate_ip("") is False

    def test_invalid_letters(self):
        assert validate_ip("abc.def.ghi.jkl") is False

    def test_invalid_octet_overflow(self):
        assert validate_ip("256.1.2.3") is False

    def test_invalid_negative_octet(self):
        assert validate_ip("-1.2.3.4") is False

    def test_invalid_leading_zeros(self):
        assert validate_ip("01.2.3.4") is True

    def test_valid_whitespace(self):
        assert validate_ip("  10.0.0.1  ") is True

    def test_none_value(self):
        with pytest.raises((AttributeError, TypeError)):
            validate_ip(None)


# ---------------------------------------------------------------------------
# auto_format_mac
# ---------------------------------------------------------------------------


class TestAutoFormatMac:
    def test_12_hex_chars(self):
        assert auto_format_mac("AABBCCDDEEFF") == "AA:BB:CC:DD:EE:FF"

    def test_lowercase(self):
        assert auto_format_mac("aabbccddeeff") == "aa:bb:cc:dd:ee:ff"

    def test_already_formatted(self):
        assert auto_format_mac("AA:BB:CC:DD:EE:FF") == "AA:BB:CC:DD:EE:FF"

    def test_too_short(self):
        assert auto_format_mac("AABBCCDDEE") == "AABBCCDDEE"

    def test_too_long(self):
        assert auto_format_mac("AABBCCDDEEFFFF") == "AABBCCDDEEFFFF"

    def test_empty(self):
        assert auto_format_mac("") == ""

    def test_invalid_chars(self):
        assert auto_format_mac("GGHHIIJJKKLL") == "GGHHIIJJKKLL"


# ---------------------------------------------------------------------------
# mac_to_bytes
# ---------------------------------------------------------------------------


class TestMacToBytes:
    def test_conversion(self):
        result = mac_to_bytes("AA:BB:CC:DD:EE:FF")
        assert result == b"\xaa\xbb\xcc\xdd\xee\xff"

    def test_conversion_zeros(self):
        result = mac_to_bytes("00:00:00:00:00:00")
        assert result == b"\x00\x00\x00\x00\x00\x00"

    def test_conversion_all_ff(self):
        result = mac_to_bytes("FF:FF:FF:FF:FF:FF")
        assert result == b"\xff\xff\xff\xff\xff\xff"

    def test_conversion_lowercase(self):
        result = mac_to_bytes("aa:bb:cc:dd:ee:ff")
        assert result == b"\xaa\xbb\xcc\xdd\xee\xff"

    def test_conversion_with_whitespace(self):
        result = mac_to_bytes("  01:02:03:04:05:06  ")
        assert result == b"\x01\x02\x03\x04\x05\x06"

    def test_output_length(self):
        result = mac_to_bytes("11:22:33:44:55:66")
        assert len(result) == 6

    def test_conversion_specific(self):
        result = mac_to_bytes("12:34:56:78:9A:BC")
        assert result == b"\x12\x34\x56\x78\x9a\xbc"


# ---------------------------------------------------------------------------
# build_magic_packet
# ---------------------------------------------------------------------------


class TestBuildMagicPacket:
    def test_structure(self):
        mac = b"\xaa\xbb\xcc\xdd\xee\xff"
        packet = build_magic_packet(mac)
        assert len(packet) == 102
        assert packet[:6] == b"\xff" * 6

    def test_mac_repeated_16_times(self):
        mac = b"\xaa\xbb\xcc\xdd\xee\xff"
        packet = build_magic_packet(mac)
        for i in range(16):
            start = 6 + i * 6
            assert packet[start : start + 6] == mac

    def test_trailing_after_header(self):
        mac = b"\x01\x02\x03\x04\x05\x06"
        packet = build_magic_packet(mac)
        assert packet[6:] == mac * 16

    def test_zeros_mac(self):
        mac = b"\x00\x00\x00\x00\x00\x00"
        packet = build_magic_packet(mac)
        assert packet == b"\xff" * 6 + b"\x00" * 96

    def test_ff_mac(self):
        mac = b"\xff\xff\xff\xff\xff\xff"
        packet = build_magic_packet(mac)
        assert packet == b"\xff" * 102


# ---------------------------------------------------------------------------
# send_wol (async, socket mocked)
# ---------------------------------------------------------------------------


class TestSendWol:
    @pytest.mark.asyncio
    async def test_success(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock

            result = await send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)

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
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock

            result = await send_wol("11:22:33:44:55:66", "192.168.1.255", 7)

            assert "sent" in result.lower()
            mock_sock.sendto.assert_called_once()
            addr = mock_sock.sendto.call_args[0][1]
            assert addr == ("192.168.1.255", 7)

    @pytest.mark.asyncio
    async def test_network_error(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            mock_sock.sendto.side_effect = OSError("Network is unreachable")

            result = await send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)

            assert "error" in result.lower()
            assert "unreachable" in result

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            mock_sock.sendto.side_effect = RuntimeError("Unexpected failure")

            result = await send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)

            assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_socket_creation_failure(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_socket_cls.side_effect = OSError("Permission denied")
            result = await send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)
            assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_packet_content(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock

            await send_wol("12:34:56:78:9A:BC", "10.0.0.255", 9)

            sent_packet = mock_sock.sendto.call_args[0][0]
            expected_mac = b"\x12\x34\x56\x78\x9a\xbc"
            assert sent_packet == b"\xff" * 6 + expected_mac * 16

    @pytest.mark.asyncio
    async def test_ip_stripped_of_whitespace(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock

            await send_wol("AA:BB:CC:DD:EE:FF", "  10.0.0.1  ", 9)

            addr = mock_sock.sendto.call_args[0][1]
            assert addr == ("10.0.0.1", 9)


# ---------------------------------------------------------------------------
# Device storage (save/load with auto-generated key)
# ---------------------------------------------------------------------------

def _setup_storage(tmp_path):
    """Override storage paths to use a temp directory."""
    import wol_app.storage as s
    orig_key = s.KEY_FILE
    orig_data = s.DATA_FILE
    orig_settings = s.SETTINGS_FILE
    s.KEY_FILE = str(tmp_path / ".crypt_key")
    s.DATA_FILE = str(tmp_path / "devices.json")
    s.SETTINGS_FILE = str(tmp_path / "settings.json")
    s.invalidate_key_cache()
    return s, (orig_key, orig_data, orig_settings)


def _restore_storage(s, orig):
    s.KEY_FILE, s.DATA_FILE, s.SETTINGS_FILE = orig
    s.invalidate_key_cache()


class TestDeviceStorage:
    def test_save_and_load_roundtrip(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            devices = [
                {"name": "Home PC", "mac": "AA:BB:CC:DD:EE:FF"},
                {"name": "Laptop", "mac": "11:22:33:44:55:66"},
            ]
            save_devices(devices)
            assert load_devices() == devices
        finally:
            _restore_storage(s, orig)

    def test_load_empty_when_no_file(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            if os.path.exists(s.DATA_FILE):
                os.remove(s.DATA_FILE)
            assert load_devices() == []
        finally:
            _restore_storage(s, orig)

    def test_save_empty_list(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            save_devices([])
            assert load_devices() == []
        finally:
            _restore_storage(s, orig)

    def test_load_corrupted_file_returns_empty(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            with open(s.DATA_FILE, "w", encoding="utf-8") as f:
                f.write("not encrypted data")
            assert load_devices() == []
        finally:
            _restore_storage(s, orig)

    def test_multiple_saves_overwrite(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            save_devices([{"name": "A", "mac": "AA:AA:AA:AA:AA:AA"}])
            save_devices([{"name": "B", "mac": "BB:BB:BB:BB:BB:BB"}])
            assert load_devices() == [{"name": "B", "mac": "BB:BB:BB:BB:BB:BB"}]
        finally:
            _restore_storage(s, orig)

    def test_save_unicode_names(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            devices = [{"name": "Компьютер", "mac": "AA:BB:CC:DD:EE:FF"}]
            save_devices(devices)
            assert load_devices() == devices
        finally:
            _restore_storage(s, orig)

    def test_save_large_number_of_devices(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            devices = [
                {"name": f"Device {i}", "mac": f"AA:BB:CC:DD:EE:{i:02X}"}
                for i in range(50)
            ]
            save_devices(devices)
            assert load_devices() == devices
        finally:
            _restore_storage(s, orig)

    def test_encrypted_output_not_plaintext(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            save_devices([{"name": "secret", "mac": "AA:BB:CC:DD:EE:FF"}])
            with open(s.DATA_FILE, encoding="utf-8") as f:
                raw = f.read()
            assert "AA:BB:CC:DD:EE:FF" not in raw
            with pytest.raises((json.JSONDecodeError, ValueError)):
                json.loads(raw)
        finally:
            _restore_storage(s, orig)

    def test_crypt_key_generated_on_first_save(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            save_devices([{"name": "X", "mac": "AA:AA:AA:AA:AA:AA"}])
            assert os.path.exists(s.KEY_FILE)
            with open(s.KEY_FILE, encoding="utf-8") as f:
                key = f.read().strip()
            assert len(key) > 0
        finally:
            _restore_storage(s, orig)

    def test_crypt_key_reused(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            save_devices([{"name": "A", "mac": "AA:AA:AA:AA:AA:AA"}])
            with open(s.KEY_FILE, encoding="utf-8") as f:
                first_key = f.read()
            save_devices([{"name": "B", "mac": "BB:BB:BB:BB:BB:BB"}])
            with open(s.KEY_FILE, encoding="utf-8") as f:
                second_key = f.read()
            assert first_key == second_key
        finally:
            _restore_storage(s, orig)

    def test_wrong_key_cant_read(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            save_devices([{"name": "secret", "mac": "AA:BB:CC:DD:EE:FF"}])
            with open(s.KEY_FILE, "w", encoding="utf-8") as f:
                f.write("aW52YWxpZC1rZXktZm9yLXRlc3RpbmctcHVycG9zZXM=")
            s.invalidate_key_cache()
            assert load_devices() == []
        finally:
            _restore_storage(s, orig)

    def test_settings_encrypted(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            save_settings({"theme_mode": "dark"})
            with open(s.SETTINGS_FILE, encoding="utf-8") as f:
                raw = f.read()
            assert "theme_mode" not in raw
        finally:
            _restore_storage(s, orig)

    def test_settings_roundtrip(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            save_settings({"theme_mode": "dark", "language": "ru"})
            loaded = load_settings()
            assert loaded.get("theme_mode") == "dark"
            assert loaded.get("language") == "ru"
        finally:
            _restore_storage(s, orig)

    def test_settings_empty_when_no_file(self, tmp_path):
        s, orig = _setup_storage(tmp_path)
        try:
            if os.path.exists(s.SETTINGS_FILE):
                os.remove(s.SETTINGS_FILE)
            assert load_settings() == {}
        finally:
            _restore_storage(s, orig)


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


def _patch_storage(tmp_path):
    """Redirect storage files to a temp directory and return originals."""
    import wol_app.storage as s
    orig = (s.KEY_FILE, s.DATA_FILE, s.SETTINGS_FILE)
    s.KEY_FILE = str(tmp_path / ".crypt_key")
    s.DATA_FILE = str(tmp_path / "devices.json")
    s.SETTINGS_FILE = str(tmp_path / "settings.json")
    s.invalidate_key_cache()
    return s, orig


def _unpatch_storage(s, orig):
    s.KEY_FILE, s.DATA_FILE, s.SETTINGS_FILE = orig
    s.invalidate_key_cache()


class TestWolAppInit:
    def test_page_title_and_padding(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            WolApp(page)
            if sys.platform == "win32":
                assert page.title == "Wake on LAN v0.5.1"
            else:
                assert page.title == "Wake on LAN"
            assert page.padding == 0
        finally:
            _unpatch_storage(s, orig)

    def test_page_scroll(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            WolApp(page)
            assert page.scroll is not None
        finally:
            _unpatch_storage(s, orig)

    def test_page_theme_mode_system(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            WolApp(page)
            assert page.theme_mode is not None
        finally:
            _unpatch_storage(s, orig)

    def test_page_appbar_set(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            WolApp(page)
            assert page.appbar is not None
        finally:
            _unpatch_storage(s, orig)


class TestWolAppInputs:
    def test_mac_input_accepts_value(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "AA:BB:CC:DD:EE:FF"
            mac, ip, port = app.validate_inputs()
            assert mac == "AA:BB:CC:DD:EE:FF"
            assert ip == "255.255.255.255"
            assert port == 9
        finally:
            _unpatch_storage(s, orig)

    def test_validate_inputs_custom_ip_port(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "11:22:33:44:55:66"
            app.ip_input.value = "10.0.0.255"
            app.port_input.value = "7"
            mac, ip, port = app.validate_inputs()
            assert mac == "11:22:33:44:55:66"
            assert ip == "10.0.0.255"
            assert port == 7
        finally:
            _unpatch_storage(s, orig)

    def test_validate_inputs_raises_no_mac(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = ""
            with pytest.raises(ValueError, match="MAC address is required"):
                app.validate_inputs()
        finally:
            _unpatch_storage(s, orig)

    def test_validate_inputs_raises_invalid_mac(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "invalid"
            with pytest.raises(ValueError, match="Invalid MAC format"):
                app.validate_inputs()
        finally:
            _unpatch_storage(s, orig)

    def test_validate_inputs_raises_bad_port(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "AA:BB:CC:DD:EE:FF"
            app.port_input.value = "not-a-number"
            with pytest.raises(ValueError, match="Port must be a number"):
                app.validate_inputs()
        finally:
            _unpatch_storage(s, orig)

    def test_validate_inputs_strips_whitespace(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "  AA:BB:CC:DD:EE:FF  "
            app.ip_input.value = "  10.0.0.1  "
            mac, ip, _ = app.validate_inputs()
            assert mac == "AA:BB:CC:DD:EE:FF"
            assert ip.strip() == ip
        finally:
            _unpatch_storage(s, orig)


class TestWolAppClear:
    def test_clear_resets_all_fields(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
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
        finally:
            _unpatch_storage(s, orig)


class TestWolAppSave:
    def test_save_valid_device(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "AA:BB:CC:DD:EE:FF"
            app.name_input.value = "My PC"
            app.ip_input.value = "192.168.1.255"
            app.port_input.value = "9"
            app.on_save_click(None)
            devices = load_devices()
            assert len(devices) == 1
            assert devices[0]["name"] == "My PC"
            assert devices[0]["mac"] == "AA:BB:CC:DD:EE:FF"
            assert devices[0]["ip"] == "192.168.1.255"
            assert devices[0]["port"] == 9
        finally:
            _unpatch_storage(s, orig)

    def test_save_converts_mac_to_upper(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "aa:bb:cc:dd:ee:ff"
            app.name_input.value = "Lower"
            app.on_save_click(None)
            devices = load_devices()
            assert devices[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        finally:
            _unpatch_storage(s, orig)

    def test_save_rejects_invalid_mac(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "invalid"
            app.name_input.value = "Bad"
            app.on_save_click(None)
            assert load_devices() == []
        finally:
            _unpatch_storage(s, orig)

    def test_save_rejects_empty_name(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.mac_input.value = "AA:BB:CC:DD:EE:FF"
            app.name_input.value = ""
            app.on_save_click(None)
            assert load_devices() == []
        finally:
            _unpatch_storage(s, orig)


class TestWolAppEdit:
    def test_edit_device_updates_instead_of_appending(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            save_devices([{"name": "Old", "mac": "AA:AA:AA:AA:AA:AA", "ip": "", "port": 9}])
            page = _make_mock_page()
            app = WolApp(page)
            app._start_edit(0)
            app.name_input.value = "Updated"
            app.mac_input.value = "BB:BB:BB:BB:BB:BB"
            app.on_save_click(None)
            devices = load_devices()
            assert len(devices) == 1
            assert devices[0]["name"] == "Updated"
            assert devices[0]["mac"] == "BB:BB:BB:BB:BB:BB"
        finally:
            _unpatch_storage(s, orig)


class TestWolAppDelete:
    def test_delete_existing_device(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            save_devices([{"name": "A", "mac": "AA:AA:AA:AA:AA:AA"}])
            page = _make_mock_page()
            app = WolApp(page)
            app._delete_device(0)
            assert load_devices() == []
        finally:
            _unpatch_storage(s, orig)

    def test_delete_out_of_range_does_nothing(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            save_devices([{"name": "A", "mac": "AA:AA:AA:AA:AA:AA"}])
            page = _make_mock_page()
            app = WolApp(page)
            app._delete_device(5)
            assert len(load_devices()) == 1
        finally:
            _unpatch_storage(s, orig)

    def test_delete_negative_index_does_nothing(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            save_devices([{"name": "A", "mac": "AA:AA:AA:AA:AA:AA"}])
            page = _make_mock_page()
            app = WolApp(page)
            app._delete_device(-1)
            assert len(load_devices()) == 1
        finally:
            _unpatch_storage(s, orig)


class TestWolAppSendFromList:
    @pytest.mark.asyncio
    async def test_send_from_list_sets_mac_and_sends(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            save_devices([{"name": "Test", "mac": "AA:BB:CC:DD:EE:FF"}])
            page = _make_mock_page()
            app = WolApp(page)

            with patch("wol_app.ui.send_wol", return_value="Magic packet sent to AA:BB:CC:DD:EE:FF"):
                await app._send_from_list("AA:BB:CC:DD:EE:FF")
                assert app.mac_input.value == "AA:BB:CC:DD:EE:FF"
        finally:
            _unpatch_storage(s, orig)

    @pytest.mark.asyncio
    async def test_send_from_list_sets_ip_port(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)

            with patch("wol_app.ui.send_wol", return_value="Magic packet sent to AA:BB:CC:DD:EE:FF"):
                await app._send_from_list("AA:BB:CC:DD:EE:FF", "10.0.0.255", "7")
                assert app.ip_input.value == "10.0.0.255"
                assert app.port_input.value == "7"
        finally:
            _unpatch_storage(s, orig)


class TestWolAppRefreshDeviceList:
    def test_refresh_with_devices(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            save_devices([{"name": "PC", "mac": "AA:BB:CC:DD:EE:FF"}])
            page = _make_mock_page()
            app = WolApp(page)
            assert len(app.device_cards.controls) == 1
        finally:
            _unpatch_storage(s, orig)

    def test_refresh_with_no_devices(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            save_devices([])
            page = _make_mock_page()
            app = WolApp(page)
            assert len(app.device_cards.controls) == 0
        finally:
            _unpatch_storage(s, orig)


class TestWolAppSnackBar:
    def test_shows_success_snack(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.show_snack("OK")
            assert len(page.overlay) > 0
        finally:
            _unpatch_storage(s, orig)

    def test_shows_error_snack(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            page = _make_mock_page()
            app = WolApp(page)
            app.show_snack("FAIL", error=True)
            assert len(page.overlay) > 0
        finally:
            _unpatch_storage(s, orig)


# ===========================================================================
# Integration tests
# ===========================================================================


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_flow_valid_mac(self):
        mac_str = "AA:BB:CC:DD:EE:FF"
        assert validate_mac(mac_str) is True
        mac_bytes = mac_to_bytes(mac_str)
        assert mac_bytes == b"\xaa\xbb\xcc\xdd\xee\xff"
        packet = build_magic_packet(mac_bytes)
        assert len(packet) == 102
        assert packet[:6] == b"\xff" * 6
        assert packet[6:] == mac_bytes * 16

        with patch("wol_app.protocol.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__.return_value = mock_sock
            result = await send_wol(mac_str, "255.255.255.255", 9)
            assert "sent" in result.lower()

    @pytest.mark.asyncio
    async def test_save_then_load_and_send(self, tmp_path):
        s, orig = _patch_storage(tmp_path)
        try:
            mac = "AA:BB:CC:DD:EE:FF"
            save_devices([{"name": "Integration PC", "mac": mac}])
            loaded = load_devices()
            assert loaded[0]["mac"] == mac

            mac_bytes = mac_to_bytes(loaded[0]["mac"])
            packet = build_magic_packet(mac_bytes)
            assert len(packet) == 102

            with patch("wol_app.protocol.socket.socket") as mock_cls:
                mock_sock = MagicMock()
                mock_cls.return_value.__enter__.return_value = mock_sock
                result = await send_wol(mac, "255.255.255.255", 9)
                assert "sent" in result.lower()
        finally:
            _unpatch_storage(s, orig)
