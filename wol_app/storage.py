import base64
import json
import logging
import os

from flet.security import decrypt, encrypt

from wol_app.models import Device

DATA_FILE = "devices.json"
SETTINGS_FILE = "settings.json"
KEY_FILE = ".crypt_key"

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

_DEFAULT_STORAGE: "Storage | None" = None


def get_storage() -> "Storage":
    global _DEFAULT_STORAGE
    if _DEFAULT_STORAGE is None:
        _DEFAULT_STORAGE = Storage(".")
    return _DEFAULT_STORAGE


def set_data_dir(path: str) -> None:
    global _DEFAULT_STORAGE
    _DEFAULT_STORAGE = Storage(path)


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


class Storage:
    def __init__(self, data_dir: str):
        self._data_dir = data_dir
        self._key: str | None = None
        self._fallback_dir = None
        try:
            os.makedirs(data_dir, exist_ok=True)
        except OSError:
            import tempfile
            self._fallback_dir = tempfile.mkdtemp(prefix="wol_")
            self._data_dir = self._fallback_dir
            _logger.warning("Using fallback data dir: %s", self._fallback_dir)

    @property
    def data_dir(self) -> str:
        return self._data_dir

    def _key_path(self) -> str:
        return os.path.join(self._data_dir, KEY_FILE)

    def _data_path(self) -> str:
        return os.path.join(self._data_dir, DATA_FILE)

    def _settings_path(self) -> str:
        return os.path.join(self._data_dir, SETTINGS_FILE)

    def _get_encryption_key(self) -> str:
        if self._key is not None:
            return self._key
        kp = self._key_path()
        if os.path.exists(kp):
            with open(kp, encoding="utf-8") as f:
                self._key = f.read().strip()
                return self._key
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        with open(kp, "w", encoding="utf-8") as f:
            f.write(key)
        if os.name != "nt":
            try:
                os.chmod(kp, 0o600)
            except Exception:
                _logger.warning("could not set permissions on %s", kp)
        self._key = key
        return key

    def _encrypt(self, plaintext: str) -> str:
        return encrypt(plaintext, self._get_encryption_key())

    def _decrypt(self, ciphertext: str) -> str:
        return decrypt(ciphertext, self._get_encryption_key())

    def load_devices(self) -> list[Device]:
        dp = self._data_path()
        if not os.path.exists(dp):
            return []
        try:
            with open(dp, encoding="utf-8") as f:
                encrypted = f.read()
            decrypted = self._decrypt(encrypted)
            data = json.loads(decrypted)
            return [Device.from_dict(d) for d in data]
        except Exception:
            return []

    def save_devices(self, devices: list) -> None:
        data = [d.to_dict() if isinstance(d, Device) else d for d in devices]
        plain = json.dumps(data, ensure_ascii=False)
        encrypted = self._encrypt(plain)
        with open(self._data_path(), "w", encoding="utf-8") as f:
            f.write(encrypted)

    def load_settings(self) -> dict:
        sp = self._settings_path()
        if not os.path.exists(sp):
            return {}
        try:
            with open(sp, encoding="utf-8") as f:
                encrypted = f.read()
            decrypted = self._decrypt(encrypted)
            return json.loads(decrypted)
        except Exception:
            return {}

    def save_settings(self, settings: dict) -> None:
        plain = json.dumps(settings, ensure_ascii=False)
        encrypted = self._encrypt(plain)
        with open(self._settings_path(), "w", encoding="utf-8") as f:
            f.write(encrypted)


def load_devices() -> list[Device]:
    return get_storage().load_devices()


def save_devices(devices: list) -> None:
    get_storage().save_devices(devices)


def load_settings() -> dict:
    return get_storage().load_settings()


def save_settings(settings: dict) -> None:
    get_storage().save_settings(settings)
