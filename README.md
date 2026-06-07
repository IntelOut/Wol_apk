# Wake-on-LAN Flet приложение

Мобильное приложение для отправки Wake-on-LAN magic-пакетов через UDP broadcast.
Поддерживает сохранение устройств с шифрованием, тёмную/светлую тему, редактирование и per-device IP/порт.

[![Test](https://github.com/IntelOut/Wol_apk/actions/workflows/test.yml/badge.svg)](https://github.com/IntelOut/Wol_apk/actions/workflows/test.yml)

---

## Функции

- Отправка WOL magic packet по UDP broadcast
- Сохранение устройств в зашифрованный список (AES-256 через PBKDF2 + Fernet)
- Редактирование и удаление устройств (свайп / кнопка)
- Per-device IP и порт, автоматическая подстановка при клике
- Валидация MAC-адреса в реальном времени, автоформатирование
- Тёмная/светлая тема (переключатель в AppBar)
- ProgressRing + "Sending..." при отправке, Empty State для пустого списка
- Навигационный drawer с Privacy Policy и User Agreement
- Адаптивно под Android (APK) и Windows

---

## Структура проекта

```
├── main.py                  # Точка входа
├── wol_app/
│   ├── __init__.py           # Пакет
│   ├── config.py             # Константы, версия, ссылки на политики
│   ├── models.py             # Device dataclass
│   ├── protocol.py           # WOL-функции (MAC, magic packet, отправка)
│   ├── storage.py            # Шифрование, загрузка/сохранение данных, миграция
│   └── ui/
│       ├── __init__.py       # Re-export WolApp
│       ├── app.py            # WolApp — основной класс UI
│       ├── widgets.py        # Переиспользуемые виджеты
│       └── dialogs.py        # Диалоги
├── assets/
│   ├── icon.png              # Иконка приложения (Android)
│   ├── icon.ico              # Иконка приложения (Windows)
│   ├── icon256.png           # Иконка 256×256
│   └── feature_graphic.png   # Графика для Google Play (1024×500)
├── tests/
│   └── test_main.py          # 131 тест (pytest + pytest-asyncio)
├── .github/workflows/test.yml
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── AGENTS.md
└── README.md
```

---

---

## Автоматические сборки и релизы

При пуше тега в формате `v<version>-<platform>.<build_number>` GitHub Actions собирает приложение и создаёт GitHub Release с артефактами.

| Платформа | Пример тега | Триггер |
|-----------|-------------|---------|
| Android   | `v1.2.3-android.1` | Любой тег, содержащий `v*android*` |
| Windows   | `v1.2.3-windows.1` | Любой тег, содержащий `v*windows*` |

### Как сделать релиз

```bash
# Android
git tag v1.0.0-android.1
git push origin v1.0.0-android.1

# Windows
git tag v1.0.0-windows.1
git push origin v1.0.0-windows.1
```

После пуша тега:
1. Workflow запускает сборку соответствующей платформы.
2. По завершении создаётся GitHub Release с тем же именем, что и тег.
3. В релиз прикрепляются собранные артефакты (`*.apk` для Android, `*.exe` и сопутствующие файлы для Windows).

**Важно:** `build-version` извлекается из тега автоматически — часть до первого дефиса (с отсечением `v` для Windows). Например, тег `v1.2.3-android.1` → версия `v1.2.3` (Android) / `1.2.3` (Windows).

---

## Запуск на Android

### 1. Через Pydroid 3
```bash
pip install flet cryptography
```
Открой `main.py` и нажми **Run**.

### 2. Сборка APK (рекомендуется)
```bash
pip install flet cryptography
flet build apk \
  --build-version 0.6.0 \
  --build-number 1 \
  --org com.intelout.wol
```
APK появится в `build/apk/`.

### 3. Через Chaquopy
Помести `main.py` в `app/src/main/python/` и вызови из Java/Kotlin.

---

## Запуск на Windows

```bash
pip install -r requirements.txt
python main.py
```

Данные сохраняются в `~/.wol_app_data/` (`%USERPROFILE%\.wol_app_data\`).

---

## Тестирование

```bash
pip install -r requirements-dev.txt
PYTHONPATH=. pytest tests/ --cov=wol_app -v
```

---

## Google Play

- **App title**: `Wake on LAN` (≤30 символов)
- **Short description (≤80 символов)**: `Wake devices on your local network with one tap`
- **Privacy Policy**: см. [PRIVACY_POLICY.md](PRIVACY_POLICY.md) / [PRIVACY_POLICY_RU.md](PRIVACY_POLICY_RU.md)
- **User Agreement**: см. [USER_AGREEMENT.md](USER_AGREEMENT.md) / [USER_AGREEMENT_RU.md](USER_AGREEMENT_RU.md)
- **Data Safety**: Укажите, что приложение передаёт MAC-адреса через UDP (локальная сеть) и хранит данные локально с шифрованием
- **Permissions**: `INTERNET`, `ACCESS_NETWORK_STATE` (добавляются автоматически)
- **Content Rating**: Для всех (Everyone)
- **Feature graphic**: `assets/feature_graphic.png` (1024×500)
- **Screenshots**: загрузите 2–8 скриншотов 9:16 (портрет) в Google Play Console

---

**Зависимости:** `pip install -r requirements.txt` (flet, cryptography)
