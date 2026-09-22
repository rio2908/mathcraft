# MathCraft

Детская математическая игра на `pygame-ce` в стилистике Minecraft. Работает
локально, в браузере через Pygbag и как Android APK.

## Документация проекта

- [`AGENTS.md`](AGENTS.md) — обязательная точка входа для AI-агентов;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — архитектура, состояния и сохранения;
- [`docs/GAME_DESIGN.md`](docs/GAME_DESIGN.md) — правила игры, баланс и предметы;
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — запуск, тестирование и сборки.

## Локальный запуск web-версии в Windows PowerShell

Требуется Python 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m py_compile main.py game_content.py game_tasks.py game_storage.py
.\.venv\Scripts\python.exe -m pyflakes main.py game_content.py game_tasks.py game_storage.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pygbag --ume_block 0 .
```

После запуска откройте адрес, который напечатает Pygbag, обычно
`http://localhost:8000`.

Переменная `PYTHONUTF8` обязательна для Pygbag 0.9.3 в русской локали Windows:
без неё инструмент пытается прочитать UTF-8 исходник как CP1251.

## Web-версия на Android

Откройте опубликованную GitHub Pages-версию в актуальном Google Chrome и
поверните телефон в альбомную ориентацию. Игра сохраняет внутреннее разрешение
1000×600 и автоматически вписывается в экран без искажения пропорций.

Первый запуск может занять дольше последующих: браузер загружает и кеширует
Python/WASM-окружение. Для первого запуска нужен доступ к интернету. Не
используйте режим инкогнито, если хотите сохранить прогресс между запусками.

## Нативный Android APK

Workflow `Build Android Debug APK` запускается вручную в GitHub Actions и
публикует APK как artifact `MathCraft-Android-debug`. Технические параметры и
важное ограничение подписи debug-сборок описаны в
[`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md#8-android-apk).

## Сборка web-версии

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pygbag --build --ume_block 0 .
```

Результат появится в `build/web`. При push в `main` эта же сборка автоматически
публикуется в GitHub Pages.
