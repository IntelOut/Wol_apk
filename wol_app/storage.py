"""Encrypted local storage for device data and application settings.

On first run a random 256-bit key is generated and saved to ``.crypt_key``.
Both ``devices.json`` (device list) and ``settings.json`` (theme, …) are
encrypted with this key via PBKDF2 + Fernet (AES-128-CBC).
"""

import base64
import functools
import json
import logging
import os

from flet.security import decrypt, encrypt

VERSION = "0.5.1"
DATA_FILE = "devices.json"
SETTINGS_FILE = "settings.json"
KEY_FILE = ".crypt_key"

_logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _get_encryption_key() -> str:
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, encoding="utf-8") as f:
            return f.read().strip()
    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        _logger.warning("could not set permissions on %s", KEY_FILE)
    return key


def invalidate_key_cache():
    """Clear the cached encryption key (used by tests after changing KEY_FILE)."""
    _get_encryption_key.cache_clear()


def _encrypt_data(plaintext: str) -> str:
    return encrypt(plaintext, _get_encryption_key())


def _decrypt_data(ciphertext: str) -> str:
    return decrypt(ciphertext, _get_encryption_key())


def load_devices() -> list:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            encrypted = f.read()
        decrypted = _decrypt_data(encrypted)
        return json.loads(decrypted)
    except Exception:
        return []


def save_devices(devices: list) -> None:
    plain = json.dumps(devices, ensure_ascii=False)
    encrypted = _encrypt_data(plain)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(encrypted)


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            encrypted = f.read()
        decrypted = _decrypt_data(encrypted)
        return json.loads(decrypted)
    except Exception:
        return {}


def save_settings(settings: dict) -> None:
    plain = json.dumps(settings, ensure_ascii=False)
    encrypted = _encrypt_data(plain)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.write(encrypted)
