from dataclasses import asdict, dataclass

from wol_app.config import DEFAULT_IP, DEFAULT_PORT


@dataclass
class Device:
    name: str
    mac: str
    ip: str = DEFAULT_IP
    port: int = DEFAULT_PORT

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Device":
        return cls(
            name=data.get("name", ""),
            mac=data.get("mac", ""),
            ip=data.get("ip", DEFAULT_IP),
            port=data.get("port", DEFAULT_PORT),
        )
