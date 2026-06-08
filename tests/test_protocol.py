"""Tests for WOL protocol logic: MAC/IP validation, formatting, magic packet."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from wol_app.protocol import (
    WOL_TIMEOUT,
    auto_format_mac,
    build_magic_packet,
    mac_to_bytes,
    normalize_mac,
    send_wol,
    validate_ip,
    validate_mac,
    validate_private_ip,
)

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

    def test_valid_dash_separator(self):
        assert validate_mac("AA-BB-CC-DD-EE-FF") is True

    def test_valid_dash_lowercase(self):
        assert validate_mac("aa-bb-cc-dd-ee-ff") is True

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

    def test_valid_dash_with_whitespace(self):
        assert validate_mac("  AA-BB-CC-DD-EE-FF  ") is True

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

    def test_invalid_leading_zeros_cve(self):
        assert validate_ip("01.2.3.4") is False

    def test_valid_whitespace(self):
        assert validate_ip("  10.0.0.1  ") is True

    def test_none_value(self):
        with pytest.raises((AttributeError, TypeError)):
            validate_ip(None)

    def test_valid_private_ranges(self):
        assert validate_ip("10.0.0.0") is True
        assert validate_ip("172.16.0.0") is True
        assert validate_ip("192.168.0.0") is True


# ---------------------------------------------------------------------------
# validate_private_ip
# ---------------------------------------------------------------------------

class TestValidatePrivateIp:
    def test_broadcast_allowed(self):
        assert validate_private_ip("255.255.255.255") is True

    def test_10_range(self):
        assert validate_private_ip("10.0.0.0") is True
        assert validate_private_ip("10.255.255.255") is True

    def test_172_range(self):
        assert validate_private_ip("172.16.0.0") is True
        assert validate_private_ip("172.31.255.255") is True
        assert validate_private_ip("172.32.0.0") is False

    def test_192_range(self):
        assert validate_private_ip("192.168.0.0") is True
        assert validate_private_ip("192.168.255.255") is True
        assert validate_private_ip("192.169.0.0") is False

    def test_public_ip_rejected(self):
        assert validate_private_ip("8.8.8.8") is False
        assert validate_private_ip("1.1.1.1") is False
        assert validate_private_ip("203.0.113.1") is False

    def test_invalid_format(self):
        assert validate_private_ip("not-an-ip") is False
        assert validate_private_ip("256.1.2.3") is False

    def test_localhost_rejected(self):
        assert validate_private_ip("127.0.0.1") is False

    def test_link_local_rejected(self):
        assert validate_private_ip("169.254.1.1") is False

    def test_empty_string(self):
        assert validate_private_ip("") is False

    def test_none(self):
        with pytest.raises((AttributeError, TypeError)):
            validate_private_ip(None)


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

    def test_hyphen_format(self):
        assert auto_format_mac("AA-BB-CC-DD-EE-FF") == "AA:BB:CC:DD:EE:FF"

    def test_hyphen_lowercase(self):
        assert auto_format_mac("aa-bb-cc-dd-ee-ff") == "aa:bb:cc:dd:ee:ff"

    def test_hyphen_with_whitespace(self):
        assert auto_format_mac("  AA-BB-CC-DD-EE-FF  ") == "AA:BB:CC:DD:EE:FF"

    def test_partial_hyphen_no_change(self):
        assert auto_format_mac("AA-BB-CC") == "AA-BB-CC"


# ---------------------------------------------------------------------------
# normalize_mac
# ---------------------------------------------------------------------------

class TestNormalizeMac:
    def test_colon_format(self):
        assert normalize_mac("aa:bb:cc:dd:ee:ff") == "AA:BB:CC:DD:EE:FF"

    def test_hyphen_format(self):
        assert normalize_mac("aa-bb-cc-dd-ee-ff") == "AA:BB:CC:DD:EE:FF"

    def test_mixed_case(self):
        assert normalize_mac("Aa:bB:cC:dD:eE:fF") == "AA:BB:CC:DD:EE:FF"

    def test_with_whitespace(self):
        assert normalize_mac("  aa:bb:cc:dd:ee:ff  ") == "AA:BB:CC:DD:EE:FF"


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

    def test_conversion_hyphen(self):
        result = mac_to_bytes("AA-BB-CC-DD-EE-FF")
        assert result == b"\xaa\xbb\xcc\xdd\xee\xff"

    def test_conversion_hyphen_zeros(self):
        result = mac_to_bytes("00-11-22-33-44-55")
        assert result == b"\x00\x11\x22\x33\x44\x55"


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
            assert packet[start: start + 6] == mac

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
            success, msg = await send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)
            assert success is True
            assert "sent" in msg.lower()
            mock_sock.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            mock_sock.settimeout.assert_called_once_with(WOL_TIMEOUT)
            mock_sock.sendto.assert_called_once()
            sent_packet = mock_sock.sendto.call_args[0][0]
            assert len(sent_packet) == 102
            assert sent_packet[:6] == b"\xff" * 6

    @pytest.mark.asyncio
    async def test_success_custom_ip_port(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            success, msg = await send_wol("11:22:33:44:55:66", "192.168.1.255", 7)
            assert success is True
            assert "sent" in msg.lower()
            mock_sock.sendto.assert_called_once()
            addr = mock_sock.sendto.call_args[0][1]
            assert addr == ("192.168.1.255", 7)

    @pytest.mark.asyncio
    async def test_network_error(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            mock_sock.sendto.side_effect = OSError("Network is unreachable")
            success, msg = await send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)
            assert success is False
            assert "unreachable" in msg

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            mock_sock.sendto.side_effect = RuntimeError("Unexpected failure")
            success, _ = await send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)
            assert success is False

    @pytest.mark.asyncio
    async def test_socket_creation_failure(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_socket_cls.side_effect = OSError("Permission denied")
            success, _ = await send_wol("AA:BB:CC:DD:EE:FF", "255.255.255.255", 9)
            assert success is False

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

    @pytest.mark.asyncio
    async def test_success_with_hyphen_mac(self):
        with patch("wol_app.protocol.socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            success, msg = await send_wol("AA-BB-CC-DD-EE-FF", "255.255.255.255", 9)
            assert success is True
            assert "sent" in msg.lower()
            sent_packet = mock_sock.sendto.call_args[0][0]
            assert len(sent_packet) == 102
            assert sent_packet[:6] == b"\xff" * 6
