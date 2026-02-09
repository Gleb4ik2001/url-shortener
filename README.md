# URL Shortener — Test Task

Небольшое API‑приложение для сокращения ссылок и редиректа по короткому коду.  
Реализовано в рамках тестового задания на позицию **Middle Backend Developer (Python)**.

---

## Содержание
- [Стек](#стек)
- [Функциональность](#функциональность)
- [HTTP API](#http-api)
- [Структура проекта](#структура-проекта)
- [Конфигурация](#конфигурация)
- [Хранилище (sqlite3)](#хранилище-sqlite3)
- [Логирование](#логирование)
- [Установка и запуск](#установка-и-запуск)
- [Тестирование](#тестирование)
- [Типовые сценарии (curl)](#типовые-сценарии-curl)
- [Что можно улучшить](#что-можно-улучшить)

---

## Стек
- Python 3.12+
- FastAPI
- sqlite3 (стандартная библиотека, без ORM)
- uvicorn
- pytest (+ httpx через TestClient)

---

## Функциональность
- **POST `/shorten`** — создаёт короткую ссылку по длинной
- **GET `/{code}`** — делает редирект на исходную ссылку
- Поддержка **пользовательского кода** (`custom_code`) как бонус
- Корректные HTTP‑коды, валидация входных данных
- Логирование ключевых событий (создание, коллизии, редиректы, 404)
- Тесты на основные сценарии (happy path + ошибки)

---

## HTTP API

### POST `/shorten`
Создаёт короткий код для URL.

**Request body**
```json
{
  "url": "https://example.com/some/path",
  "custom_code": "myShortCode"
}
```

Поля:
- `url` (обязательно) — валидный URL
- `custom_code` (опционально) — короткий код, который хочет задать пользователь  
  Ограничения: 3..32 символа, допустимые символы: `a-zA-Z0-9_-`

**Response — 201 Created**
```json
{
  "code": "myShortCode",
  "short_url": "http://localhost:8000/myShortCode",
  "long_url": "https://example.com/some/path"
}
```

**Возможные ответы**
- `201 Created` — ссылка создана
- `422 Unprocessable Entity` — невалидный JSON/URL/формат `custom_code` (валидация Pydantic/FastAPI)
- `409 Conflict` — `custom_code` уже занят
- `500 Internal Server Error` — не удалось сгенерировать уникальный код (крайний случай)

---

### GET `/{code}`
Редирект на исходный URL.

**Response**
- `307 Temporary Redirect` — успешный редирект, заголовок `Location` содержит исходный URL
- `404 Not Found` — код не найден

---

## Структура проекта

```
.
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app factory + эндпоинты
│   ├── db.py              # Подключение к sqlite3, init schema
│   ├── models.py          # Pydantic модели запросов/ответов
│   ├── settings.py        # BASE_URL / DB_PATH
│   └── logging_config.py  # настройка логирования
├── tests/
│   └── test_api.py        # тесты на API
├── pyproject.toml         # зависимости и настройки pytest
└── README.md
```

Ключевая идея: **разделение ответственности** (API / DB / модели / конфигурация).

---

## Конфигурация

Приложение настраивается через переменные окружения:

- `BASE_URL` — базовый URL, который используется для формирования `short_url` в ответе  
  По умолчанию: `http://localhost:8000`
- `DB_PATH` — путь к файлу sqlite базы  
  По умолчанию: `urls.sqlite3` (в корне проекта)

Пример `.env` (опционально):
```env
BASE_URL=http://localhost:8000
DB_PATH=urls.sqlite3
```

> В текущей реализации `.env` не парсится автоматически.  
> Для локального запуска можно просто экспортировать переменные окружения или задать их в IDE.

---

## Хранилище (sqlite3)

При старте приложения выполняется инициализация схемы (idempotent).

Таблица `urls`:
- `code` — уникальный короткий код (UNIQUE)
- `long_url` — исходный URL
- `created_at` — время создания (ISO 8601, UTC)

Дополнительно создаётся индекс по `code` для быстрого поиска.

Особенности:
- включён режим `WAL` через `PRAGMA journal_mode=WAL;`
- все операции записи идут через `INSERT`, конфликты `code` ловятся как `sqlite3.IntegrityError`

---

## Логирование

Логируются ключевые события:
- `shorten_created` — успешное создание короткой ссылки
- `code_collision` — коллизия сгенерированного кода (редко, но возможно)
- `custom_code_conflict` — конфликт пользовательского `custom_code`
- `redirect` — успешный редирект
- `redirect_not_found` — код не найден

Логи выводятся в stdout в формате:
```
timestamp | level | logger | message
```

---

## Установка и запуск

### 1) Клонировать репозиторий
```bash
git clone <repo_url>
cd boto_test_task
```

### 2) Создать виртуальное окружение
```bash
python -m venv .venv
```

Активировать:

**Windows (PowerShell)**
```powershell
.venv\Scripts\activate
```

**Linux/macOS**
```bash
source .venv/bin/activate
```

### 3) Установить зависимости
```bash
pip install -e .
pip install -e ".[test]"
```

### 4) Запустить приложение
По умолчанию:
- DB: `urls.sqlite3`
- BASE_URL: `http://localhost:8000`

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Тестирование

Запуск всех тестов:
```bash
pytest
```

Короткий вывод:
```bash
pytest -q
```

Важно:
- тесты создают **временную sqlite‑базу** и не трогают рабочий файл `urls.sqlite3`
- для проверки редиректа в тестах используется `follow_redirects=False`, чтобы явно проверить `307` и заголовок `Location`

---

## Типовые сценарии (curl)

### 1) Создать короткую ссылку (автогенерация кода)
```bash
curl -X POST "http://localhost:8000/shorten" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://example.com/path\"}"
```

### 2) Создать короткую ссылку с custom_code
```bash
curl -X POST "http://localhost:8000/shorten" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://example.com/path\", \"custom_code\": \"myCode1\"}"
```

### 3) Конфликт custom_code (ожидаемо 409)
```bash
curl -i -X POST "http://localhost:8000/shorten" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://example.com/other\", \"custom_code\": \"myCode1\"}"
```

### 4) Редирект по коду
```bash
curl -i "http://localhost:8000/myCode1"
```
В ответе будет `307` и заголовок `Location: https://example.com/path`.

---

## Что можно улучшить

Если проектом будут пользоваться люди, логичное развитие:
- **Дедупликация**: одинаковый `long_url` → один и тот же `code` (опционально)
- **TTL/истечение** ссылок и фоновые задачи на очистку
- **Аналитика**: счётчик кликов, last_accessed, базовая статистика
- **Админ-операции**: `DELETE /{code}`, `PATCH /{code}`, `GET /{code}/info`
- **Защита от абьюза**: rate limiting, ограничения на создание ссылок
- Переход на **PostgreSQL** при росте нагрузки + миграции
- Улучшение observability: JSON‑логи, correlation id, метрики, трассировка

---