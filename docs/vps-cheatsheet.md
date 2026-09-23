# VPS шпаргалка — GlowPath

Как поднять prod-стек на ВМ и залить обновления. Локальная разработка (`make up` + Vite) сюда не входит.

Сейчас нет CI/CD: код с ноута → `rsync` → `docker compose up --build`.

## 0. Реквизиты (подставь свои)

В WSL / терминале ноута:

```bash
export VPS_HOST=93.77.163.171
export VPS_USER=mood-tracker
export VPS_SSH_KEY=~/.ssh/id_ed25519_personal
export VPS_DIR=~/mood-tracker
```

SSH:

```bash
ssh -i "$VPS_SSH_KEY" -o IdentitiesOnly=yes -l "$VPS_USER" "$VPS_HOST"
```

Чтобы не таскать флаги, в `~/.ssh/config` на ноуте:

```
Host glowpath-vps
  HostName 93.77.163.171
  User mood-tracker
  IdentityFile ~/.ssh/id_ed25519_personal
  IdentitiesOnly yes
```

Тогда: `ssh glowpath-vps`.

Публичный ключ в форму облака — только `*.pub`, не приватный файл.

## 1. Первый подъём

### Облако / firewall

Входящие TCP:

| Порт | Зачем |
|------|--------|
| 22 | SSH |
| 8080 | сайт |
| 8025 | MailHog (письма при `--profile mail`) |

RAM лучше от 4 ГБ, диск от 30–40 ГБ. На 2 ГБ / 10 ГБ стек может встать, но это песочница.

### Docker на ВМ

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker "$USER"
exit   # и зайти по SSH снова
```

Проверка: `groups` содержит `docker`, `docker ps` без ошибки.

### Код с ноута

Репо на GitHub с ВМ не клонировать (нет ключа). С ноута:

```bash
rsync -avz --exclude .venv --exclude node_modules --exclude .git \
  --exclude __pycache__ --exclude dist --exclude .pytest_cache \
  -e "ssh -i $VPS_SSH_KEY -o IdentitiesOnly=yes" \
  ~/projects/pets/mood-tracker/ \
  "${VPS_USER}@${VPS_HOST}:${VPS_DIR}/"
```

### Env — два файла на ВМ, не с ноута

Локальный `backend/.env` на сервер не копировать.

На ВМ:

```bash
cd ~/mood-tracker
cp .env.prod.example .env.prod
cp backend/.env.example backend/.env
nano .env.prod
```

В `.env.prod` минимум:

```bash
PUBLIC_URL=http://93.77.163.171:8080
HTTP_PORT=8080
DATABASE_URL=postgresql://USER:PASSWORD@HOST/mood_tracker?sslmode=require
DATABASE_URL_UNPOOLED=postgresql://USER:PASSWORD@HOST/mood_tracker?sslmode=require
MINIO_ENDPOINT=storage.example.com
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=mood-tracker
MINIO_SECURE=true
SMTP_HOST=mailhog
SMTP_PORT=1025
MAILHOG_UI_PORT=8025
```

`PUBLIC_URL` — IP (или домен) ВМ, как в браузере. Compose из него ставит `FRONTEND_URL` / CORS / `APP_PUBLIC_URL`.

`frontend/.env` на ВМ не нужен: образ собирается с пустым `VITE_API_BASE_URL`, API на том же хосте через nginx.

`backend/.env` для тыка можно оставить из example. Имеет смысл сменить только `JWT_SECRET_KEY`. Google / Telegram / боевой SMTP — когда будет постоянный сервер.

### Запуск

На ВМ:

```bash
cd ~/mood-tracker
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile mail up --build
```

Фон:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile mail up --build -d
```

Открыть:

- приложение: http://IP:8080
- письма: http://IP:8025 (не Gmail)

Остановить:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile mail down
```

`down` не поднимает и не хранит базу и файлы: Postgres и объектное хранилище внешние.

## 2. Залить обнову

На ноуте (из каталога проекта или с полным путём):

```bash
rsync -avz --exclude .venv --exclude node_modules --exclude .git \
  --exclude __pycache__ --exclude dist --exclude .pytest_cache \
  -e "ssh -i $VPS_SSH_KEY -o IdentitiesOnly=yes" \
  ~/projects/pets/mood-tracker/ \
  "${VPS_USER}@${VPS_HOST}:${VPS_DIR}/"
```

`rsync` может затереть `.env.prod` / `backend/.env` на ВМ, если они есть локально. После синка проверь `PUBLIC_URL` на сервере.

На ВМ пересобрать и поднять:

```bash
cd ~/mood-tracker
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile mail up --build -d
```

Фронт — статика внутри образа. Правка `frontend/src` без `--build` в браузере не появится. После деплоя — Ctrl+F5.

Только бэкенд тоже лучше с `--build`: образ без bind-mount.

Логи:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile mail logs -f --tail=100
```

Статус: `docker compose -f docker-compose.prod.yml --env-file .env.prod ps`

## 3. Что не делать на песочнице Yandex

- Не оставлять ВМ включённой «на всякий случай» — CPU/RAM капают, пока статус RUNNING.
- Выключил ВМ — диск всё равно тарифицируется, пока диск не удалён.
- После тыка: Stop, либо удалить **ВМ и диск**.

Песочница ≠ прод: HTTP по IP, дефолтные пароли, MailHog, без Telegram в `docker-compose.prod.yml`.

## 4. Постоянный VPS (когда дойдём)

1. Домен + HTTPS (Caddy / nginx) на 80/443, не сырой `:8080`.
2. В `.env.prod`: `PUBLIC_URL=https://твой.домен`, боевые `DATABASE_URL` / MinIO / `JWT_SECRET_KEY`.
3. Реальный SMTP, без `--profile mail`.
4. Google OAuth redirect на `https://домен/v1/auth/google/callback`.
5. Telegram — сервис в prod-compose + webhook на HTTPS.

Без HTTPS в Firefox (и др.) нет `crypto.randomUUID()` — загрузка фото падала; в коде есть fallback, но для прода всё равно нужен TLS.

## 5. Частые ошибки

| Симптом | Что сделать |
|---------|-------------|
| `permission denied` на `docker.sock` | `sudo usermod -aG docker $USER`, выйти из SSH, зайти снова |
| `Host key verification failed` | первый SSH: на вопрос fingerprint ответить `yes` (свой сервер) |
| Permission denied (publickey) | ключ тот, что в облаке: `-i ~/.ssh/id_ed25519_personal`, логин не `ubuntu` |
| Сайт не открывается | security group: TCP 8080; `PUBLIC_URL` с этим IP |
| Рега есть, письма нет | MailHog :8025 + порт в firewall |
| После правок UI старый | `up --build` и Ctrl+F5 |
| `No space left` | диск 10 ГБ мало; чистить `docker system prune` или ВМ побольше |
| Всё пропало после фото (старый билд) | HTTP+IP; пересобрать фронт с `randomId` fallback |
