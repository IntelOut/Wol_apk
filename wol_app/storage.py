import base64
import functools
import json
import logging
import os

from flet.security import decrypt, encrypt

from wol_app.models import Device

DATA_FILE = "devices.json"
SETTINGS_FILE = "settings.json"
KEY_FILE = ".crypt_key"
DATA_DIR = "."

_logger = logging.getLogger(__name__)


def set_data_dir(path: str) -> None:
    global DATA_DIR
    DATA_DIR = path
    os.makedirs(path, exist_ok=True)
    invalidate_key_cache()


def migrate_from_cwd(target_dir: str) -> None:
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
    return os.path.join(DATA_DIR, KEY_FILE)


def _data_path() -> str:
    return os.path.join(DATA_DIR, DATA_FILE)


def _settings_path() -> str:
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
    _get_encryption_key.cache_clear()


def _encrypt_data(plaintext: str) -> str:
    return encrypt(plaintext, _get_encryption_key())


def _decrypt_data(ciphertext: str) -> str:
    return decrypt(ciphertext, _get_encryption_key())


def load_devices() -> list[Device]:
    dp = _data_path()
    if not os.path.exists(dp):
        return []
    try:
        with open(dp, encoding="utf-8") as f:
            encrypted = f.read()
        decrypted = _decrypt_data(encrypted)
        data = json.loads(decrypted)
        return [Device.from_dict(d) for d in data]
    except Exception:
        return []


def save_devices(devices: list) -> None:
    data = [d.to_dict() if isinstance(d, Device) else d for d in devices]
    plain = json.dumps(data, ensure_ascii=False)
    encrypted = _encrypt_data(plain)
    with open(_data_path(), "w", encoding="utf-8") as f:
        f.write(encrypted)


def load_settings() -> dict:
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
    plain = json.dumps(settings, ensure_ascii=False)
    encrypted = _encrypt_data(plain)
    with open(_settings_path(), "w", encoding="utf-8") as f:
        f.write(encrypted)
