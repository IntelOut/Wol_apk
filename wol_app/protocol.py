import asyncio
import ipaddress
import re
import socket


def validate_mac(mac: str) -> bool:
    stripped = mac.strip()
    pattern = r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$"
    return bool(re.match(pattern, stripped))


def mac_to_bytes(mac: str) -> bytes:
    return bytes.fromhex(mac.strip().replace(":", "").replace("-", ""))


def auto_format_mac(raw: str) -> str:
    cleaned = raw.strip().replace("-", "").replace(":", "").strip()
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
        try:
            parts = ip.strip().split(".")
            if len(parts) != 4:
                return False
            cleaned = ".".join(str(int(p)) for p in parts)
            ipaddress.IPv4Address(cleaned)
            return True
        except ValueError:
            return False


def build_magic_packet(mac: bytes) -> bytes:
    return b"\xff" * 6 + mac * 16


async def send_wol(mac_address: str, ip: str, port: int) -> tuple[bool, str]:
    mac_bytes = mac_to_bytes(mac_address)
    packet = build_magic_packet(mac_bytes)

    loop = asyncio.get_running_loop()

    def _send():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(5)
            sock.sendto(packet, (ip.strip(), port))

    try:
        await loop.run_in_executor(None, _send)
        return (True, f"Magic packet sent to {mac_address}")
    except OSError as e:
        return (False, f"Network error: {e}")
    except Exception as e:
        return (False, f"Error: {e}")
