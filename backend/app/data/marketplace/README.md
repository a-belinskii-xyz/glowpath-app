# Marketplace icons

Каждая **подпапка** = пак в каталоге. Каждый **файл картинки** внутри = иконка. Seed сканирует папки сам: править Python не нужно.

```text
marketplace/
  demo-mocks/          → pack slug `demo-mocks`
    pack.json          ← необязательно: названия, теги, цвета
    fox-happy.svg      → icon slug `fox-happy`
    rain-cloud.svg
  my-animals/          → новый пак `my-animals`
    cat.png
    dog.webp
```

## Как добавить пак или иконки

1. Создайте папку `backend/app/data/marketplace/<имя-пака>/`.
   Имя папки станет `slug` пака (`My Animals` → `my-animals`). Не используйте `essentials` — этот slug занят базовым набором.
2. Положите туда картинки: `.svg`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`.
   Имя файла без расширения станет `slug` иконки (`Happy Fox.png` → `happy-fox`). Подпапки внутри пака игнорируются.
3. По желанию добавьте `pack.json` (см. ниже). Без него названия возьмутся из имён папки/файлов, теги будут пустые, цвет `#94a3b8`.
4. Поднимите стек (`make up`) и подтяните каталог:

   ```bash
   make seed-marketplace
   ```

Команда идемпотентна: новые файлы создадут иконки, замена файла обновит картинку в MinIO.

## pack.json (необязательно)

См. `demo-mocks/pack.json`. Ключи `icons` — slug или имя файла. Поля, которых нет, берутся из дефолтов пака / имени файла.

```json
{
  "name": {"en": "Foxes", "ru": "Лисы"},
  "description": {"en": "Cute foxes", "ru": "Милые лисы"},
  "price_tokens": 0,
  "sort_order": 10,
  "tags": ["animals"],
  "colors": ["#f97316"],
  "icons": {
    "happy-fox": {
      "labels": {"en": "Happy fox", "ru": "Весёлый лис"},
      "tags": ["joy", "animals"],
      "colors": ["#f97316", "#f59e0b"],
      "scores": [4, 5]
    }
  }
}
```

Готовые теги: `joy`, `sadness`, `calm`, `energy`, `sport`, `fitness`, `animals`, `nature`, `weather`, `night`. Неизвестный тег в `"tags"` игнорируется — сначала добавьте его в `DEFAULT_SEARCH_TAGS` в `backend/app/services/marketplace_seed.py`.

`scores` — suggested mood 1–5. `price_tokens: 0` = бесплатный официальный пак (разблокирован у всех).

## Что не подхватывается

- Файлы в корне `marketplace/` — только подпапки.
- Вложенные папки внутри пака.
- Папка `essentials`.
- Файлы > 512 KB или с неподдерживаемым расширением.
- Удаление файла с диска **не удаляет** уже засиженную иконку из БД.

Базовый пак `essentials` по-прежнему берётся из `frontend/public/mood-icons/`, не из этой папки.

## Формат файлов

Иконки рисуются **кругом**. Экспортируйте квадрат **1:1**.

| | Рекомендация |
|---|---|
| **Цель** | **512×512 px** (для растра) |
| Минимум | 256×256 px |
| Размер | **≤ 512 KB** |
| Формат | SVG предпочтителен; PNG если нужна прозрачность; JPEG/WebP для фото |
| Safe area | объект в центре ~90% — углы обрежет круг |
