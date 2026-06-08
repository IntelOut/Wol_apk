"""Integration tests combining WOL protocol, storage, and UI workflows."""

from unittest.mock import MagicMock, patch

import pytest

from wol_app.models import Device
from wol_app.protocol import build_magic_packet, mac_to_bytes, send_wol, validate_mac
from wol_app.storage import load_devices, save_devices


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
            success, msg = await send_wol(mac_str, "255.255.255.255", 9)
            assert success is True
            assert "sent" in msg.lower()

    @pytest.mark.asyncio
    async def test_save_then_load_and_send(self, patched_storage):
        mac = "AA:BB:CC:DD:EE:FF"
        save_devices([Device(name="Integration PC", mac=mac)])
        loaded = load_devices()
        assert loaded[0].mac == mac

        mac_bytes = mac_to_bytes(loaded[0].mac)
        packet = build_magic_packet(mac_bytes)
        assert len(packet) == 102

        with patch("wol_app.protocol.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__.return_value = mock_sock
            success, msg = await send_wol(mac, "255.255.255.255", 9)
            assert success is True
            assert "sent" in msg.lower()

    @pytest.mark.asyncio
    async def test_full_flow_hyphen_mac(self):
        mac = "AA-BB-CC-DD-EE-FF"
        assert validate_mac(mac) is True
        mac_bytes = mac_to_bytes(mac)
        assert mac_bytes == b"\xaa\xbb\xcc\xdd\xee\xff"
        packet = build_magic_packet(mac_bytes)
        assert len(packet) == 102

        with patch("wol_app.protocol.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value.__enter__.return_value = mock_sock
            success, msg = await send_wol(mac, "255.255.255.255", 9)
            assert success is True
            assert "sent" in msg.lower()

    def test_device_normalization_roundtrip(self, patched_storage):
        save_devices([
            Device(name="A", mac="AA-BB-CC-DD-EE-FF"),
            Device(name="B", mac="aa:bb:cc:dd:ee:ff"),
        ])
        loaded = load_devices()
        assert loaded[0].mac == "AA-BB-CC-DD-EE-FF"
        assert loaded[1].mac == "aa:bb:cc:dd:ee:ff"
