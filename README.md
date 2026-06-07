# Wake-on-LAN Flet приложение

Мобильное приложение для отправки Wake-on-LAN magic-пакетов через UDP broadcast. Поддерживает сохранение устройств, тёмную/светлую тему, редактирование и per-device IP/порт.

---

## Функции

- Отправка WOL magic packet по UDP broadcast
- Сохранение устройств в зашифрованный список (AES-256 через PBKDF2)
- Редактирование и удаление устройств (свайп / кнопка)
- Автоматическая подстановка MAC, IP и порта при клике на устройство
- Per-device настройки IP и порта
- Валидация MAC-адреса в реальном времени, обработка ошибок сети
- Тёмная/светлая тема (переключатель в AppBar)
- ProgressRing + "Sending..." при отправке, Empty State для пустого списка
- Адаптивно под Android и Windows

---

## Структура проекта

```
├── main.py                  # Точка входа
├── wol_app/
│   ├── __init__.py
│   ├── protocol.py          # WOL-функции (MAC, magic packet, отправка)
│   ├── storage.py           # Шифрование, загрузка/сохранение данных
│   └── ui.py                # Flet UI (WolApp)
├── assets/
│   ├── icon.png             # Иконка приложения (Android)
│   ├── icon.ico             # Иконка приложения (Windows)
│   ├── icon256.png          # Иконка 256×256
│   └── feature_graphic.png  # Графика для Google Play (1024×500)
├── tests/
│   └── test_main.py         # 79 тестов (pytest)
├── requirements.txt
├── requirements-dev.txt
└── .github/workflows/test.yml
```

---

## Запуск на Android

### 1. Через Pydroid 3
```
pip install flet
```
Открой `main.py` и нажми **Run**.

### 2. Сборка APK (рекомендуется)
```bash
pip install flet
flet build apk \
  --icon assets/icon.png \
  --build-version 0.5.1 \
  --build-number 1 \
  --org com.intelout.wol \
  --orientation portrait
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

---

## Тестирование

```bash
pip install -r requirements-dev.txt
pytest tests/ --cov=wol_app -v
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

**Зависимости:** `pip install -r requirements.txt`
