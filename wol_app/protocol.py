import asyncio
import ipaddress
import logging
import re
import socket
import uuid

WOL_TIMEOUT = 10

_logger = logging.getLogger(__name__)


def validate_mac(mac: str) -> bool:
    stripped = mac.strip()
    pattern = r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$"
    return bool(re.match(pattern, stripped))


def mac_to_bytes(mac: str) -> bytes:
    return bytes.fromhex(mac.strip().replace(":", "").replace("-", ""))


def auto_format_mac(raw: str) -> str:
    cleaned = raw.strip().replace("-", "").replace(":", "")
    if not cleaned:
        return raw
    if len(cleaned) == 12 and re.match(r"^[0-9A-Fa-f]{12}$", cleaned):
        return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))
    return raw


def normalize_mac(mac: str) -> str:
    return ":".join(
        p.upper() for p in mac.strip().replace("-", ":").split(":") if p
    )


def validate_ip(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip.strip())
        return True
    except ValueError:
        return False


_PRIVATE_NETWORKS = [
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
]
_BROADCAST_ADDR = ipaddress.IPv4Address("255.255.255.255")


def validate_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.IPv4Address(ip.strip())
    except ValueError:
        return False
    if addr == _BROADCAST_ADDR:
        return True
    return any(addr in net for net in _PRIVATE_NETWORKS)


def build_magic_packet(mac: bytes) -> bytes:
    return b"\xff" * 6 + mac * 16


def get_interfaces() -> list[tuple[int, str]]:
    try:
        return socket.if_nameindex()
    except (OSError, AttributeError):
        return []


async def send_wol(mac_address: str, ip: str, port: int) -> tuple[bool, str]:
    correlation_id = uuid.uuid4().hex[:8]
    mac_bytes = mac_to_bytes(mac_address)
    packet = build_magic_packet(mac_bytes)
    _logger.info("[%s] Sending WOL to %s via %s:%d", correlation_id, mac_address, ip.strip(), port)

    loop = asyncio.get_running_loop()

    def _send():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(WOL_TIMEOUT)
            sock.sendto(packet, (ip.strip(), port))

    try:
        await asyncio.wait_for(loop.run_in_executor(None, _send), timeout=WOL_TIMEOUT + 2)
        _logger.info("[%s] Success", correlation_id)
        return (True, f"Magic packet sent to {mac_address}")
    except TimeoutError:
        _logger.warning("[%s] Timeout after %ds", correlation_id, WOL_TIMEOUT)
        return (False, f"Timeout after {WOL_TIMEOUT}s — device did not respond")
    except OSError as e:
        _logger.warning("[%s] Network error: %s", correlation_id, e)
        return (False, f"Network error: {e}")
    except Exception as e:
        _logger.warning("[%s] Error: %s", correlation_id, e)
        return (False, f"Error: {e}")
