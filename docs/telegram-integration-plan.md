# Telegram integration — план

**Статус:** этапы 0–2 ✅ · далее этап 3 (catalog + entries API)  
**Дата:** 2026-07-18  
**Решения:** webhook · bot-facing API в том же FastAPI · бот — отдельный контейнер

---

## 1. Цель MVP

1. Напоминания «отметиться» / goals в Telegram (как email, тот же worker).
2. Создание mood entry из бота: score, теги/лейблы как на сайте, goals, текст.
3. Голосовые сообщения → audio attachment к записи (существующий `AttachmentKind.AUDIO` + MinIO).

**Вне MVP (бэклог):** фото из TG, quick check-in одной кнопкой, `/today`, правка последней записи, Whisper-транскрипт, quiet hours, статистика недели в боте.

---

## 2. Архитектура

```text
                         ┌─────────────────────────────┐
  Telegram servers ──webhook──► │  telegram-bot (container)  │
                         │  FSM, кнопки, Bot API I/O   │
                         └──────────────┬──────────────┘
                                        │ HTTP (service token)
                                        ▼
                         ┌─────────────────────────────┐
                         │  app (FastAPI /v1)          │
                         │  bot + user APIs, services  │
                         └──────────────┬──────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
         PostgreSQL                   MinIO              reminders worker
                                                              │
                                                              │ TelegramNotifier
                                                              ▼
                                                         Telegram Bot API
                                                         (sendMessage)
```

### Роли

| Компонент | Отвечает за |
|-----------|-------------|
| **`telegram-bot`** | Приём webhook от Telegram, разбор update, FSM wizard, inline/reply keyboard, вызовы Bot API (`answerCallbackQuery`, `sendMessage`, `getFile`). **Без** прямой работы с БД/MinIO. |
| **`app` (FastAPI)** | Связка аккаунта, catalog (tags/goals/mood scale), создание entry + attachments, sessions FSM в Postgres, профильные endpoints для UI. Вся бизнес-логика — существующие services. |
| **`reminders`** | Как сейчас `process_due_reminders`; для канала `telegram` — `TelegramNotifier` → Bot API. Бот-контейнер для напоминаний **не нужен**. |

### Почему так

- Webhook держит бот: Telegram-протокол и UX изолированы, API остаётся REST/domain.
- Один API = те же правила валидации, `source`, лимиты вложений, ownership тегов.
- Reminders уже крутятся отдельным процессом — доставка в TG симметрична email.

### Сеть / webhook URL

- Prod: reverse proxy → `telegram-bot:PORT`; `setWebhook` на публичный HTTPS URL бота.
- Local: `cloudflared` / `ngrok` на порт бота **или** compose profile `telegram` + tunnel. Без публичного URL webhook не заработает.
- Секрет: Telegram `secret_token` на webhook; бот отклоняет запросы без него.

---

## 3. Связка аккаунта (linking)

Без chat id напоминания и bot API бесполезны.

### Данные

На `User` (или отдельная `mt_telegram_links`):

| Поле | Назначение |
|------|------------|
| `telegram_user_id` | Unique, id пользователя TG |
| `telegram_chat_id` | Recipient для sendMessage |
| `telegram_linked_at` | Когда связали |
| `telegram_locale` | Опционально `ru`/`en` из TG `language_code` |

Одноразовые коды:

| Таблица / сущность | Поля |
|-------------------|------|
| `mt_telegram_link_codes` | `user_id`, `code` (hash), `expires_at`, `used_at` |

### Поток

1. Профиль (frontend): «Подключить Telegram» → `POST /v1/telegram/link-codes` → код + deep link `https://t.me/<bot>?start=<code>`.
2. Пользователь открывает бота → `/start <code>`.
3. Бот → `POST /v1/telegram/bot/link` (service auth) с `code` + `telegram_user_id` + `chat_id`.
4. API привязывает, инвалидирует код.
5. Отвязка: `DELETE /v1/telegram/link` (user JWT) и/или `/unlink` в боте.

### Правила

- Один TG-аккаунт ↔ один user.
- Включать канал `telegram` в notification settings **только** если link есть.
- Reminders: если в `channels` есть telegram, но link нет — skip + лог (не падать на всём батче).

---

## 4. Bot-facing API (внутри того же FastAPI)

Префикс: `/v1/telegram/bot/...`  
Auth: shared secret / service token (`TELEGRAM_BOT_SERVICE_TOKEN`), **не** user JWT.  
User context: всегда по `telegram_user_id` → linked `User` (404/403 если не связан).

| Метод | Путь | Назначение |
|-------|------|------------|
| `POST` | `/link` | Привязка по коду |
| `POST` | `/unlink` | Отвязка из бота |
| `GET` | `/me` | Проверка link + locale/timezone |
| `GET` | `/catalog` | Mood scale + tag groups (`show_on_entry`) + active goals, labels под locale |
| `POST` | `/entries` | Создание mood entry (`score`, `tag_ids`, `goal_ids`, `note`, `recorded_at`, `source=telegram:bot`) |
| `POST` | `/entries/{id}/attachments` | Upload audio (и позже photo) — обёртка над `upload_attachment` |
| `GET`/`PUT` | `/sessions/{telegram_user_id}` | FSM state (JSON) |
| `DELETE` | `/sessions/{telegram_user_id}` | Сброс wizard |

User-facing (JWT, профиль):

| Метод | Путь | Назначение |
|-------|------|------------|
| `POST` | `/v1/telegram/link-codes` | Выдать код / deep link |
| `GET` | `/v1/telegram/link` | Статус связи |
| `DELETE` | `/v1/telegram/link` | Отвязать |

Webhook **не** живёт на FastAPI — только на бот-контейнере.

---

## 5. Напоминания

Переиспользовать текущий пайплайн:

```text
jobs/reminders → process_due_reminders → NotificationDispatcher
  → EmailNotifier | TelegramNotifier
```

### Работы

1. Модель/колонки link → `_recipient_for(user, TELEGRAM)` → `str(chat_id)`.
2. `TelegramNotifier(BaseNotifier)`: `sendMessage`, parse_mode по необходимости; текст из `messages.py` с адаптацией под TG (короче, без HTML-письма).
3. Inline-кнопка в напоминании: «Отметиться» → открывает wizard в боте (`callback_data` / deep link `t.me/bot?start=log`), не только ссылка на сайт. Сайт с `?from=telegram:daily_mood_reminder` — fallback в тексте.
4. `build_notification_dispatcher()` — зарегистрировать Telegram, если задан bot token.
5. `_IMPLEMENTED_CHANNELS` += `TELEGRAM` (при наличии link-валидации на PATCH).
6. Frontend: убрать «coming soon», чекбокс Telegram; блок «подключить бота» если нет link.
7. Сообщения: `daily_mood_reminder_message` / `goal_reminder_message` уже принимают `channel` — metadata/source остаётся `telegram:…`.

### Условия отправки (как email)

- settings enabled, verified user, timezone ok, time window, dedup `last_*_on`.
- Для telegram-канала дополнительно: активный link.

---

## 6. Wizard создания записи в боте

### FSM (состояние в Postgres через `/sessions`)

```text
idle
  → choose_score          (кнопки 1–5 + лейблы/эмодзи из catalog)
  → choose_tags           (по группам show_on_entry; multi-select; «Далее»)
  → choose_goals          (если есть active goals; можно skip)
  → note_or_voice         (текст / voice / skip)
  → confirm               (summary → создать entry [+ attachment])
  → done | idle
```

Команды: `/start`, `/log` (или «Отметиться»), `/cancel`, `/unlink`, `/help`.

### Catalog

Один `GET /catalog?locale=ru`:

- scores: label + emoji (mood preferences пользователя или дефолт);
- tag_groups + tags с `labels`;
- goals (active на сегодня).

Бот только рисует кнопки; UUID тегов/goals приходят с API.

### Создание

1. `POST /entries` с `source=telegram:bot` (или `telegram:daily_mood_reminder`, если пришли из reminder callback).
2. Если было voice: `getFile` → скачать → `POST .../attachments` `kind=audio`.
3. Лимиты те же: 1 audio, note ≤500 plain / markdown rules API.

### Голос

- Формат TG: OGG/Opus — принять как есть, если storage/API уже допускает; иначе конверт (решение на этапе реализации, проверить `upload_attachment` MIME).
- `transcript` — **не** в MVP (поле в модели уже есть под Whisper позже).

---

## 7. Контейнер `telegram-bot`

### Compose

Новый сервис рядом с `app` / `reminders`:

```yaml
telegram-bot:
  build: ./telegram-bot   # или ./backend с другим command — предпочтительно отдельный пакет
  env_file: backend/.env
  environment:
    API_BASE_URL: http://app:8000
    TELEGRAM_BOT_TOKEN: ...
    TELEGRAM_BOT_SERVICE_TOKEN: ...
    TELEGRAM_WEBHOOK_SECRET: ...
    TELEGRAM_WEBHOOK_PATH: /telegram/webhook
  depends_on:
    - app
  ports:
    - "${TELEGRAM_BOT_PORT:-8081}:8081"
  # command: запуск webhook-сервера (aiohttp / fastapi-slim / aiogram webhook)
```

### Структура репо (предложение)

```text
telegram-bot/
  pyproject.toml / requirements
  src/
    main.py           # webhook server, setWebhook on startup (opt-in)
    handlers/         # start, log wizard, unlink
    api_client.py     # HTTP к /v1/telegram/bot/*
    keyboards.py
    config.py
  Dockerfile
```

Стек: **aiogram 3** или **python-telegram-bot** — на выбор при старте этапа; важнее тонкий клиент к API, чем фреймворк.

### Конфиг (новые env)

| Переменная | Кто читает | Зачем |
|------------|------------|--------|
| `TELEGRAM_BOT_TOKEN` | bot, app (notifier), reminders | Bot API |
| `TELEGRAM_BOT_SERVICE_TOKEN` | bot → app, app validates | Service auth |
| `TELEGRAM_WEBHOOK_SECRET` | bot | Header от Telegram |
| `TELEGRAM_WEBHOOK_URL` | bot (startup) | Публичный URL для `setWebhook` (local tunnel) |
| `TELEGRAM_BOT_USERNAME` | app (deep links в профиле) | `t.me/...` |
| `API_BASE_URL` | bot | `http://app:8000` |

---

## 8. Frontend

- Профиль / notification settings:
  - статус Telegram (linked / not);
  - кнопка подключить (deep link + код);
  - отвязать;
  - чекбокс канала `telegram` (disabled пока нет link).
- i18n `en`/`ru` для новых строк.
- Убрать stub «coming soon».

---

## 9. Этапы реализации

| # | Этап | Результат | Зависимости |
|---|------|-----------|-------------|
| **0** | Инфра и модели | Миграция link + link_codes + sessions; env; скелет `telegram-bot` + compose; healthcheck | ✅ |
| **1** | Linking | User API + bot `/link`; профиль UI; `/start CODE` | ✅ |
| **2** | Reminders | `TelegramNotifier`, dispatcher, settings channel, тексты/кнопка | ✅ |
| **3** | Catalog + bot API entries | `GET /catalog`, `POST /entries`, sessions, service auth | ✅ |
| **4** | Wizard | FSM sessions, score→tags→goals→note, confirm; `/log` `/cancel` | ✅ |
| **5** | Voice | getFile → upload audio attachment | ✅ |
| **6** | Polish | ошибки, `/cancel`, i18n бота, тесты, README (tunnel) | ✅ |

После каждого этапа — зелёные тесты на затронутый слой (API unit/integration; bot — с моком API).

---

## 10. Тестирование

| Слой | Что |
|------|-----|
| API | link/unlink, catalog ownership, create entry `source`, attachment limits, service token 401 |
| Notifier | Fake/mock Bot API; recipient mapping; skip without link |
| Reminders | integration: user with telegram channel + link получает send |
| Bot | handlers с mock `api_client`; FSM transitions |
| E2E local | tunnel + реальный бот (ручной чеклист в README) |

---

## 11. Безопасность

- Webhook только с `X-Telegram-Bot-Api-Secret-Token`.
- Bot routes только с service token (не светить в frontend).
- Link codes: короткий TTL (напр. 15 мин), одноразовые, хранить hash.
- Не логировать bot token / service token.
- Rate-limit bot endpoints по `telegram_user_id` (простой) — желательно до prod.

---

## 12. Бэклог после MVP

1. Quick check-in из reminder (score → сохранить с дефолтными тегами).
2. Фото из Telegram (до 5).
3. `/today`, список последних записей.
4. Edit last entry.
5. Whisper → `transcript` + поиск.
6. Quiet hours / «не сегодня».
7. Недельная статистика в боте.
8. Отдельный reverse-proxy path и prod deploy checklist.

---

## 13. Открытые мелочи (решить в коде, не блокеры плана)

- MIME/контейнер voice: OGG as-is vs ffmpeg → mp3/m4a.
- `setWebhook` на старте бота vs отдельная make-цель `make telegram-webhook`.
- Locale бота: из `User` / TG `language_code` / оба с fallback `ru`.
- Где жить пакет бота: `telegram-bot/` в корне (предпочтительно) vs `backend/bot/`.

---

## 14. Критерий готовности MVP

- [ ] Пользователь связывает TG из профиля.
- [ ] Reminder в выбранное время приходит в Telegram.
- [ ] Из бота можно создать запись с score + тегами (+ goals) + текстом.
- [ ] Voice из TG сохраняется как audio attachment и видно на сайте.
- [ ] Канал `telegram` в settings работает только при активном link.
- [ ] Compose: `app` + `reminders` + `telegram-bot` поднимаются вместе.
