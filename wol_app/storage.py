"""Encrypted local storage for device data and application settings.

On first run a random 256-bit key is generated and saved to ``.crypt_key``.
Both ``devices.json`` (device list) and ``settings.json`` (theme, …) are
encrypted with this key via PBKDF2 + Fernet (AES-128-CBC).
"""

import base64
import json
import os

from flet.security import decrypt, encrypt

VERSION = "0.5.0"
DATA_FILE = "devices.json"
SETTINGS_FILE = "settings.json"
KEY_FILE = ".crypt_key"


def _get_encryption_key() -> str:
    """Return the stored encryption key or generate a new one.

    The key is a 32-byte random value encoded in URL-safe Base64.
    On Unix-like systems the key file is chmod'ed to 0600.

    Returns:
        A Base64-encoded encryption key string.
    """
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, encoding="utf-8") as f:
            return f.read().strip()
    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    return key


def _encrypt_data(plaintext: str) -> str:
    """Encrypt plaintext with the device-specific key.

    Args:
        plaintext: String data to encrypt.

    Returns:
        URL-safe Base64 ciphertext.
    """
    return encrypt(plaintext, _get_encryption_key())


def _decrypt_data(ciphertext: str) -> str:
    """Decrypt ciphertext that was produced by :func:`_encrypt_data`.

    Args:
        ciphertext: URL-safe Base64 payload from a previous :func:`encrypt` call.

    Returns:
        Decrypted UTF-8 text.
    """
    return decrypt(ciphertext, _get_encryption_key())


def load_devices() -> list:
    """Load the saved device list from the encrypted data file.

    Returns:
        A list of device dicts, or an empty list if the file does not
        exist or cannot be decrypted.
    """
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
    """Persist the device list to the encrypted data file.

    Args:
        devices: A list of device dicts to save.
    """
    plain = json.dumps(devices, ensure_ascii=False)
    encrypted = _encrypt_data(plain)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(encrypted)


def load_settings() -> dict:
    """Load application settings (theme, …) from the encrypted file.

    Returns:
        A settings dict, or an empty dict if the file does not exist or
        cannot be decrypted.
    """
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
    """Persist application settings to the encrypted file.

    Args:
        settings: A dict of settings key-value pairs.
    """
    plain = json.dumps(settings, ensure_ascii=False)
    encrypted = _encrypt_data(plain)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.write(encrypted)
