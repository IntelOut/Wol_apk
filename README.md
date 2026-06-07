# Wake-on-LAN Flet приложение

Полностью рабочий код в файле `main.py`.

---

## Функции

- Отправка WOL magic packet по UDP broadcast
- Сохранение устройств в зашифрованный список (AES-256)
- Удаление устройств: **свайпом влево** (Dismissible) или по иконке корзины
- Автоматическая подстановка MAC и отправка при клике на устройство
- Валидация MAC-адреса, обработка ошибок сети
- Тёмная/светлая тема (системная)
- ProgressRing при отправке, Empty State для пустого списка

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
  --icon icon.png \
  --build-version 0.3.0 \
  --build-number 1 \
  --org com.yourorg.wol \
  --product wol-app
```
APK появится в `build/apk/`.

### 3. Через Chaquopy
Помести `main.py` в `app/src/main/python/` и вызови из Java/Kotlin.

---

## Google Play

- **Privacy Policy**: см. [PRIVACY_POLICY.md](PRIVACY_POLICY.md)
- **Data Safety**: Укажите, что приложение передаёт MAC-адреса через UDP (локальная сеть) и хранит данные локально с шифрованием
- **Permissions**: `INTERNET`, `ACCESS_NETWORK_STATE` (добавляются автоматически)
- **Content Rating**: Для всех (Everyone)

---

**Зависимости:** `pip install flet==0.85.2`
