# Лабораторная работа 4 — регистрация и дискреционная модель доступа (вариант 2)

Стек: React + Vite + TypeScript, FastAPI, PostgreSQL, SQLAlchemy 2 + Alembic, Docker Compose.

## Быстрый запуск

```bash
cp .env.example .env      # необязательно: у всех переменных есть рабочие значения по умолчанию
docker compose up --build
```

| Сервис   | Адрес                          |
|----------|--------------------------------|
| Frontend | http://localhost:3000          |
| Backend  | http://localhost:8000 (Swagger: `/docs`) |
| БД       | PostgreSQL 16, контейнер `db`  |

Миграции применяются автоматически при старте backend (`alembic upgrade head`).
Страницы UI: `/register` (регистрация), `/access` (вход и работа с ресурсами), `/scenario` (автоматическая демонстрация модели доступа).

## Структура проекта

```
docker-compose.yml        db + backend + frontend
.env.example              переменные окружения без реальных секретов
backend/
  Dockerfile, requirements.txt, alembic.ini
  alembic/versions/0001_initial.py   миграция: users, resources, resource_permissions
  app/
    main.py               приложение, обработчики ошибок (422/500)
    config.py             чтение .env
    security.py           Argon2id/bcrypt, токены
    schemas.py            валидация login/password
    models.py             User, Resource, ResourcePermission
    access.py             ЕДИНОЕ место, где принимается решение о доступе
    deps.py               текущий пользователь по токену
    logging_config.py     JSON-логи
    routers/auth.py       /api/register, /api/login, /api/me
    routers/resources.py  ресурсы и выдача прав
  tests/                  pytest (20 тестов)
frontend/
  Dockerfile, nginx.conf.template (проксирует /api на backend)
  src/pages/              Register, Access, Scenario
```

## Дискреционная модель доступа

* У каждого ресурса есть владелец (`resources.owner_id`).
* Права других пользователей хранятся в `resource_permissions(user_id, resource_id, can_read, can_update, can_delete)`, пара `(user_id, resource_id)` уникальна.
* **Правило, по которому backend принимает решение** (`backend/app/access.py`):
  1. владелец имеет все права на свой ресурс;
  2. остальные — ровно те права, которые владелец им выдал;
  3. при отсутствии записи или нужного флага — `403 Forbidden`.
* Выдавать и отзывать права может **только владелец** (`PUT /api/resources/{id}/permissions`). Все три флага `false` = право отозвано. Выдать права самому себе или другому не-владельцу нельзя (403).
* Права `read/update/delete` независимы: право на изменение не даёт право на чтение.
* Проверка всегда выполняется на backend; frontend только показывает результат.
* Список `GET /api/resources` содержит свои ресурсы и те, где есть хотя бы одно право; содержимое отдаётся только через `GET /api/resources/{id}` после проверки.

## API

| Метод и путь | Описание | Коды |
|---|---|---|
| `POST /api/register` | `{login, password}` → `{"message": "user создан"}` | 201, 409 логин занят, 422 валидация |
| `POST /api/login` | `{login, password}` → `{access_token, token_type, login}` | 200, 401 |
| `GET /api/me` | текущий пользователь | 200, 401 |
| `GET /api/users` | логины пользователей (для выбора при выдаче прав) | 200, 401 |
| `POST /api/resources` | `{title, content}` — создать (вы владелец) | 201, 401, 422 |
| `GET /api/resources` | свои и расшаренные ресурсы + мои права | 200 |
| `GET /api/resources/{id}` | чтение — нужно `can_read` | 200, 403, 404 |
| `PUT /api/resources/{id}` | изменение — нужно `can_update` | 200, 403, 404 |
| `DELETE /api/resources/{id}` | удаление — нужно `can_delete` | 204, 403, 404 |
| `PUT /api/resources/{id}/permissions` | `{login, can_read, can_update, can_delete}` — только владелец | 200, 400, 403, 404 |
| `GET /api/resources/{id}/permissions` | кому что выдано — только владелец | 200, 403 |
| `GET /api/health` | проверка живости | 200 |

### Примеры curl

```bash
API=http://localhost:8000/api

# 1. Регистрация двух пользователей
curl -X POST $API/register -H 'Content-Type: application/json' -d '{"login":"alice","password":"Str0ng!Pass"}'
curl -X POST $API/register -H 'Content-Type: application/json' -d '{"login":"bob","password":"Str0ng!Pass"}'

# 2. Ошибки: слабый пароль (422) и занятый логин (409)
curl -i -X POST $API/register -H 'Content-Type: application/json' -d '{"login":"carol","password":"weak"}'
curl -i -X POST $API/register -H 'Content-Type: application/json' -d '{"login":"alice","password":"Str0ng!Pass"}'

# 3. Вход (токены)
TA=$(curl -s -X POST $API/login -H 'Content-Type: application/json' -d '{"login":"alice","password":"Str0ng!Pass"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
TB=$(curl -s -X POST $API/login -H 'Content-Type: application/json' -d '{"login":"bob","password":"Str0ng!Pass"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 4. alice создаёт ресурс (id=1 в чистой БД)
curl -X POST $API/resources -H "Authorization: Bearer $TA" -H 'Content-Type: application/json' -d '{"title":"Отчёт","content":"секрет"}'

# 5. bob без права — отказ 403
curl -i $API/resources/1 -H "Authorization: Bearer $TB"

# 6. alice выдаёт bob право на чтение
curl -X PUT $API/resources/1/permissions -H "Authorization: Bearer $TA" -H 'Content-Type: application/json' \
     -d '{"login":"bob","can_read":true,"can_update":false,"can_delete":false}'

# 7. bob читает — 200; пытается изменить — 403
curl -i $API/resources/1 -H "Authorization: Bearer $TB"
curl -i -X PUT $API/resources/1 -H "Authorization: Bearer $TB" -H 'Content-Type: application/json' -d '{"title":"x","content":"y"}'
```

## Безопасность: что сделано

* Пароли хранятся только как хэш **Argon2id** (`argon2-cffi`) со случайной солью, входящей в строку хэша; поддерживается и `bcrypt` (`HASH_SCHEME=bcrypt`).
* Параметры хэширования вынесены в конфигурацию: `ARGON2_TIME_COST`, `ARGON2_MEMORY_COST`, `ARGON2_PARALLELISM` (и `BCRYPT_ROUNDS`).
* Пароль не сохраняется, не логируется и не возвращается в ответах: ответ 422 формируется собственным обработчиком без поля `input`; в лог пишется только список полей с ошибкой. Это проверяют тесты.
* Уникальность логина обеспечена **уникальным индексом** `ix_users_login` в БД; гонка двух одновременных регистраций ловится через `IntegrityError` → 409.
* Валидация на backend: логин `^[A-Za-z0-9._-]{3,32}$`; пароль ≥ 8 символов, заглавная, строчная, цифра, спецсимвол.
* Модель доступа проверяется только на backend (`access.py`); все эндпоинты ресурсов требуют токен (401 без него).
* Токены — JWT (HS256), подпись `SECRET_KEY`, срок жизни `TOKEN_TTL_MINUTES`.
* При входе неизвестный логин и неверный пароль дают одинаковый ответ и сопоставимое время (защита от перебора логинов).
* Секреты — только в `.env` (в `.gitignore`); в репозитории лежит `.env.example` с заглушками. Backend в контейнере работает не от root.

## Логирование

JSON-строки в stdout, уровни INFO и ERROR. События: `user_registered`, `register_login_taken`, `validation_error`, `login_ok`, `login_failed`, `access_denied`, `permission_granted`, `resource_*`, `unhandled_error` (ERROR).

```bash
docker compose logs backend
```

## Тесты

```bash
cd backend
pip install -r requirements.txt
python -m pytest -v
```

20 тестов: регистрация (успех, дубликат, 5 вариантов слабого пароля, 5 вариантов неверного логина, разная соль у хэшей, отсутствие пароля в логах) и модель доступа (владелец, отказ без права, выдача права, независимость прав, отзыв, выдавать может только владелец, список ресурсов, 401/404). Тесты используют SQLite в памяти, чтобы запускаться без Docker; приложение в Docker работает на PostgreSQL.

## Что сдать (чек-лист)

- [ ] ссылка на репозиторий/архив;
- [ ] скриншоты: форма `/register` (успех, 422, 409) и страница `/scenario` после запуска (все шаги совпали);
- [ ] скриншот ветки Git (`git log --graph --oneline --all`);
- [ ] вклад участников — заполните таблицу:

| Участник | Вклад |
|---|---|
| Потылицына Дарья | backend (API, access.py) |
| Беленькая Полина | frontend (React-страницы) |
| Потылицына Дарья | database (модели, миграции, docker-compose) |
| Беленькая Полина | тесты |
| Потылицына Дарья | документация (README, скриншоты) |
