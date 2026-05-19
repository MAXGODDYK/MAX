# Табачная смесь для кальяна

В этом репозитории лежит сам проект приложения, без готовой SQLite-базы. Данные хранятся в Google Таблице, а файл `project/Подбор ингредиентов/ingredients.db` создаётся локально на каждом устройстве как кэш.

## Быстрый запуск

1. Установи Python 3.11 или новее.
2. Клонируй репозиторий.
3. В папке `project/` создай локальный `google_sheets_config.json` из `google_sheets_config.example.json`.
4. Положи JSON-ключ service account в `project/secrets/google_service_account.json`.
5. Запусти:

```powershell
.\project\run_app.bat
```

Если синхронизация настроена, приложение создаст локальный `ingredients.db` и подтянет данные из Google Таблицы при запуске.

## Что не хранится в GitHub

- `project/Подбор ингредиентов/ingredients.db`
- `project/google_sheets_config.json`
- `project/secrets/`
- локальные архивы, backup-файлы и кэши Python

## Состав проекта

- `project/Подбор ингредиентов/app.py` — GUI-приложение.
- `project/Подбор ингредиентов/schema.sql` — схема локального кэша.
- `project/Подбор ингредиентов/sample_data.sql` — демонстрационные данные для локального режима.
- `project/setup_google_sheets.py` — первичная выгрузка локальной базы в Google Таблицу.
- `project/tests/` — unit-тесты синхронизации, рецептов, фасовок и калькулятора.
- `project/Точные рецепты/` — DOCX/PDF техкарты и скрипт их пересборки.

## Google Sheets

Google Таблица считается главной удалённой копией данных. На новом устройстве не нужно переносить `ingredients.db`: достаточно настроить локальные credentials, и приложение само заполнит кэш из Google Sheets.
