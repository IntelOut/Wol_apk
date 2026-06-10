VERSION = "0.7.3"
DEFAULT_IP = "255.255.255.255"
DEFAULT_PORT = 9

PRIVACY_POLICY_URLS: dict[str, list[tuple[str, str]]] = {
    "ru": [
        ("Политика конфиденциальности", "https://github.com/IntelOut/Wol_apk/blob/main/PRIVACY_POLICY_RU.md"),
    ],
    "en": [
        ("Privacy Policy", "https://github.com/IntelOut/Wol_apk/blob/main/PRIVACY_POLICY.md"),
    ],
}

USER_AGREEMENT_URLS: dict[str, list[tuple[str, str]]] = {
    "ru": [
        ("Пользовательское соглашение", "https://github.com/IntelOut/Wol_apk/blob/main/USER_AGREEMENT_RU.md"),
    ],
    "en": [
        ("User Agreement", "https://github.com/IntelOut/Wol_apk/blob/main/USER_AGREEMENT.md"),
    ],
}
