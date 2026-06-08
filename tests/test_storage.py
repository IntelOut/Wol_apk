"""Tests for Device dataclass and encrypted key-value storage."""

import json
import os

import pytest

from wol_app.models import Device
from wol_app.storage import load_devices, load_settings, save_devices, save_settings

# ---------------------------------------------------------------------------
# Device dataclass
# ---------------------------------------------------------------------------


class TestDeviceDataclass:
    def test_default_values(self):
        d = Device(name="Test", mac="AA:BB:CC:DD:EE:FF")
        assert d.name == "Test"
        assert d.mac == "AA:BB:CC:DD:EE:FF"
        assert d.ip == "255.255.255.255"
        assert d.port == 9
        assert d.group == ""
        assert d.last_woken is None

    def test_custom_values(self):
        d = Device(name="PC", mac="11:22:33:44:55:66", ip="10.0.0.1", port=7)
        assert d.name == "PC"
        assert d.mac == "11:22:33:44:55:66"
        assert d.ip == "10.0.0.1"
        assert d.port == 7

    def test_to_dict(self):
        d = Device(name="PC", mac="AA:BB:CC:DD:EE:FF", ip="10.0.0.1", port=7)
        expected = {"name": "PC", "mac": "AA:BB:CC:DD:EE:FF", "ip": "10.0.0.1", "port": 7, "group": "", "last_woken": None}
        assert d.to_dict() == expected

    def test_to_dict_defaults(self):
        d = Device(name="PC", mac="AA:BB:CC:DD:EE:FF")
        expected = {"name": "PC", "mac": "AA:BB:CC:DD:EE:FF", "ip": "255.255.255.255", "port": 9, "group": "", "last_woken": None}
        assert d.to_dict() == expected

    def test_from_dict(self):
        data = {"name": "PC", "mac": "AA:BB:CC:DD:EE:FF", "ip": "10.0.0.1", "port": 7}
        d = Device.from_dict(data)
        assert d.name == "PC"
        assert d.mac == "AA:BB:CC:DD:EE:FF"
        assert d.ip == "10.0.0.1"
        assert d.port == 7
        assert d.last_woken is None

    def test_from_dict_with_last_woken(self):
        data = {"name": "PC", "mac": "AA:BB:CC:DD:EE:FF", "last_woken": 1234567890.0}
        d = Device.from_dict(data)
        assert d.last_woken == 1234567890.0

    def test_from_dict_partial(self):
        data = {"name": "PC", "mac": "AA:BB:CC:DD:EE:FF"}
        d = Device.from_dict(data)
        assert d.name == "PC"
        assert d.mac == "AA:BB:CC:DD:EE:FF"
        assert d.ip == "255.255.255.255"
        assert d.port == 9

    def test_from_dict_empty(self):
        d = Device.from_dict({})
        assert d.name == ""
        assert d.mac == ""

    def test_roundtrip(self):
        original = Device(name="PC", mac="AA:BB:CC:DD:EE:FF", ip="10.0.0.1", port=7)
        restored = Device.from_dict(original.to_dict())
        assert original == restored

    def test_equality_ignores_last_woken(self):
        d1 = Device(name="PC", mac="AA:BB:CC:DD:EE:FF", last_woken=100.0)
        d2 = Device(name="PC", mac="AA:BB:CC:DD:EE:FF", last_woken=200.0)
        assert d1 == d2

    def test_inequality(self):
        d1 = Device(name="PC", mac="AA:BB:CC:DD:EE:FF")
        d2 = Device(name="Laptop", mac="11:22:33:44:55:66")
        assert d1 != d2


# ---------------------------------------------------------------------------
# Device storage (save/load with auto-generated key)
# ---------------------------------------------------------------------------


class TestDeviceStorage:
    def test_save_and_load_roundtrip(self, patched_storage):
        devices = [
            Device(name="Home PC", mac="AA:BB:CC:DD:EE:FF"),
            Device(name="Laptop", mac="11:22:33:44:55:66"),
        ]
        save_devices(devices)
        assert load_devices() == devices

    def test_load_empty_when_no_file(self, patched_storage):
        assert load_devices() == []

    def test_save_empty_list(self, patched_storage):
        save_devices([])
        assert load_devices() == []

    def test_load_corrupted_file_returns_empty(self, patched_storage):
        import wol_app.storage as s
        st = s.get_storage()
        with open(st._data_path(), "w", encoding="utf-8") as f:
            f.write("not encrypted data")
        assert load_devices() == []

    def test_multiple_saves_overwrite(self, patched_storage):
        save_devices([Device(name="A", mac="AA:AA:AA:AA:AA:AA")])
        save_devices([Device(name="B", mac="BB:BB:BB:BB:BB:BB")])
        assert load_devices() == [Device(name="B", mac="BB:BB:BB:BB:BB:BB")]

    def test_save_unicode_names(self, patched_storage):
        devices = [Device(name="Компьютер", mac="AA:BB:CC:DD:EE:FF")]
        save_devices(devices)
        assert load_devices() == devices

    def test_save_large_number_of_devices(self, patched_storage):
        devices = [
            Device(name=f"Device {i}", mac=f"AA:BB:CC:DD:EE:{i:02X}")
            for i in range(50)
        ]
        save_devices(devices)
        assert load_devices() == devices

    def test_encrypted_output_not_plaintext(self, patched_storage):
        import wol_app.storage as s
        st = s.get_storage()
        save_devices([Device(name="secret", mac="AA:BB:CC:DD:EE:FF")])
        with open(st._data_path(), encoding="utf-8") as f:
            raw = f.read()
        assert "AA:BB:CC:DD:EE:FF" not in raw
        with pytest.raises((json.JSONDecodeError, ValueError)):
            json.loads(raw)

    def test_crypt_key_generated_on_first_save(self, patched_storage):
        import wol_app.storage as s
        st = s.get_storage()
        save_devices([Device(name="X", mac="AA:AA:AA:AA:AA:AA")])
        assert os.path.exists(st._key_path())
        with open(st._key_path(), encoding="utf-8") as f:
            key = f.read().strip()
        assert len(key) > 0

    def test_crypt_key_reused(self, patched_storage):
        import wol_app.storage as s
        st = s.get_storage()
        save_devices([Device(name="A", mac="AA:AA:AA:AA:AA:AA")])
        with open(st._key_path(), encoding="utf-8") as f:
            first_key = f.read()
        save_devices([Device(name="B", mac="BB:BB:BB:BB:BB:BB")])
        with open(st._key_path(), encoding="utf-8") as f:
            second_key = f.read()
        assert first_key == second_key

    def test_wrong_key_cant_read(self, patched_storage):
        import wol_app.storage as s
        st = s.get_storage()
        save_devices([Device(name="secret", mac="AA:BB:CC:DD:EE:FF")])
        with open(st._key_path(), "w", encoding="utf-8") as f:
            f.write("aW52YWxpZC1rZXktZm9yLXRlc3RpbmctcHVycG9zZXM=")
        st = s.get_storage()
        st._key = None
        assert load_devices() == []

    def test_settings_encrypted(self, patched_storage):
        import wol_app.storage as s
        st = s.get_storage()
        save_settings({"theme_mode": "dark"})
        with open(st._settings_path(), encoding="utf-8") as f:
            raw = f.read()
        assert "theme_mode" not in raw

    def test_settings_roundtrip(self, patched_storage):
        save_settings({"theme_mode": "dark", "language": "ru"})
        loaded = load_settings()
        assert loaded.get("theme_mode") == "dark"
        assert loaded.get("language") == "ru"

    def test_settings_empty_when_no_file(self, patched_storage):
        import wol_app.storage as s
        st = s.get_storage()
        if os.path.exists(st._settings_path()):
            os.remove(st._settings_path())
        assert load_settings() == {}

    def test_backward_compat_dict_save(self, patched_storage):
        save_devices([{"name": "Dict Device", "mac": "AA:BB:CC:DD:EE:FF"}])
        loaded = load_devices()
        assert len(loaded) == 1
        assert loaded[0].name == "Dict Device"
        assert loaded[0].mac == "AA:BB:CC:DD:EE:FF"
