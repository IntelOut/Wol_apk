"""Wake-on-LAN protocol implementation.

Provides functions for MAC address validation, magic packet construction,
and asynchronous UDP broadcast delivery of Wake-on-LAN packets.
"""

import asyncio
import re
import socket


def validate_mac(mac: str) -> bool:
    """Check whether a string is a valid MAC address in XX:XX:XX:XX:XX:XX format.

    Args:
        mac: The MAC address string to validate. Leading/trailing whitespace
             is tolerated but separators must be colons.

    Returns:
        True if the format is correct, False otherwise.
    """
    pattern = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
    return bool(re.match(pattern, mac.strip()))


def mac_to_bytes(mac: str) -> bytes:
    """Convert a colon-separated MAC address string to 6 raw bytes.

    Args:
        mac: MAC address in XX:XX:XX:XX:XX:XX format (colons and whitespace
             are stripped automatically).

    Returns:
        6 bytes representing the MAC address.
    """
    return bytes.fromhex(mac.strip().replace(":", ""))


def validate_ip(ip: str) -> bool:
    """Check whether a string is a valid IPv4 address.

    Args:
        ip: The IP address string to validate.

    Returns:
        True if the format is correct, False otherwise.
    """
    pattern = r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"
    m = re.match(pattern, ip.strip())
    if not m:
        return False
    return all(0 <= int(g) <= 255 for g in m.groups())


def build_magic_packet(mac: bytes) -> bytes:
    """Build a Wake-on-LAN magic packet.

    The packet consists of 6 bytes of 0xFF followed by the target MAC
    address repeated 16 times (102 bytes total).

    Args:
        mac: Exactly 6 bytes of the target MAC address.

    Returns:
        A 102-byte magic packet ready for UDP transmission.
    """
    return b"\xff" * 6 + mac * 16


async def send_wol(mac_address: str, ip: str, port: int) -> str:
    """Send a Wake-on-LAN magic packet via UDP broadcast.

    The packet is constructed from the given MAC and delivered to the
    specified IP and port.  The actual socket I/O runs in a thread-pool
    executor so the caller is not blocked.

    Args:
        mac_address: Target MAC in XX:XX:XX:XX:XX:XX format.
        ip:          Destination IP or broadcast address (e.g. 255.255.255.255).
        port:        Destination UDP port (typically 7 or 9).

    Returns:
        A human-readable status message indicating success or describing
        the error.
    """
    mac_bytes = mac_to_bytes(mac_address)
    packet = build_magic_packet(mac_bytes)

    loop = asyncio.get_event_loop()

    def _send():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(5)
            sock.sendto(packet, (ip.strip(), port))

    try:
        await loop.run_in_executor(None, _send)
        return f"Magic packet sent to {mac_address}"
    except OSError as e:
        return f"Network error: {e}"
    except Exception as e:
        return f"Error: {e}"
