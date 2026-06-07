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

VERSION = "0.5.2"
DATA_FILE = "devices.json"
SETTINGS_FILE = "settings.json"
KEY_FILE = ".crypt_key"
DATA_DIR = "."

_logger = logging.getLogger(__name__)


def set_data_dir(path: str) -> None:
    """Set the application data directory and ensure it exists.

    All subsequent file I/O (devices, settings, encryption key) will
    be rooted at *path*.  The cached encryption key is invalidated
    so it is re-read from the new location on next access.

    Args:
        path: Absolute path to the data directory.
    """
    global DATA_DIR
    DATA_DIR = path
    os.makedirs(path, exist_ok=True)
    invalidate_key_cache()


def migrate_from_cwd(target_dir: str) -> None:
    """Copy existing data files from the working directory to *target_dir*.

    Migration runs only once — after a successful copy the sentinel file
    ``.migrated`` is written to prevent re-migration on subsequent starts.
    If any individual file copy fails the sentinel is **not** written so
    the migration is retried on the next launch.

    Args:
        target_dir: The destination directory for migrated files.
    """
    _migration_sentinel = ".migrated"
    sentinel = os.path.join(target_dir, _migration_sentinel)
    if os.path.exists(sentinel):
        return
    os.makedirs(target_dir, exist_ok=True)
    import shutil
    failed = False
    for name in (DATA_FILE, SETTINGS_FILE, KEY_FILE):
        src = os.path.join(".", name)
        dst = os.path.join(target_dir, name)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
                _logger.info("migrated %s to %s", name, target_dir)
            except Exception:
                _logger.warning("could not migrate %s", name)
                failed = True
    if not failed:
        try:
            with open(sentinel, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass


def _key_path() -> str:
    """Full path to the encryption key file."""
    return os.path.join(DATA_DIR, KEY_FILE)


def _data_path() -> str:
    """Full path to the devices data file."""
    return os.path.join(DATA_DIR, DATA_FILE)


def _settings_path() -> str:
    """Full path to the settings file."""
    return os.path.join(DATA_DIR, SETTINGS_FILE)


@functools.lru_cache(maxsize=1)
def _get_encryption_key() -> str:
    kp = _key_path()
    if os.path.exists(kp):
        with open(kp, encoding="utf-8") as f:
            return f.read().strip()
    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    with open(kp, "w", encoding="utf-8") as f:
        f.write(key)
    try:
        os.chmod(kp, 0o600)
    except Exception:
        _logger.warning("could not set permissions on %s", kp)
    return key


def invalidate_key_cache():
    """Clear the cached encryption key (used by tests after changing KEY_FILE)."""
    _get_encryption_key.cache_clear()


def _encrypt_data(plaintext: str) -> str:
    return encrypt(plaintext, _get_encryption_key())


def _decrypt_data(ciphertext: str) -> str:
    return decrypt(ciphertext, _get_encryption_key())


def load_devices() -> list:
    """Load the saved device list from encrypted storage.

    Returns:
        A list of device dicts (keys ``name``, ``mac``, ``ip``, ``port``).
        Returns an empty list if the file does not exist or cannot be
        decrypted.
    """
    dp = _data_path()
    if not os.path.exists(dp):
        return []
    try:
        with open(dp, encoding="utf-8") as f:
            encrypted = f.read()
        decrypted = _decrypt_data(encrypted)
        return json.loads(decrypted)
    except Exception:
        return []


def save_devices(devices: list) -> None:
    """Persist the device list to encrypted storage.

    Args:
        devices: A list of device dicts.
    """
    plain = json.dumps(devices, ensure_ascii=False)
    encrypted = _encrypt_data(plain)
    with open(_data_path(), "w", encoding="utf-8") as f:
        f.write(encrypted)


def load_settings() -> dict:
    """Load application settings (theme, language, …) from encrypted storage.

    Returns:
        A dict of settings. Returns an empty dict if the file does not
        exist or cannot be decrypted.
    """
    sp = _settings_path()
    if not os.path.exists(sp):
        return {}
    try:
        with open(sp, encoding="utf-8") as f:
            encrypted = f.read()
        decrypted = _decrypt_data(encrypted)
        return json.loads(decrypted)
    except Exception:
        return {}


def save_settings(settings: dict) -> None:
    """Persist application settings to encrypted storage.

    Args:
        settings: A dict of settings (e.g. ``{"theme_mode": "dark"}``).
    """
    plain = json.dumps(settings, ensure_ascii=False)
    encrypted = _encrypt_data(plain)
    with open(_settings_path(), "w", encoding="utf-8") as f:
        f.write(encrypted)
