# Marketplace icons

Каждая **подпапка** = пак в каталоге. Каждый **файл картинки** внутри = иконка. Настройки пака — `pack.json` в этой же папке: цена, мета, сразу ли доступен.

```text
marketplace/
  demo-mocks/          → pack slug `demo-mocks`
    pack.json          ← цена, название, published/granted, мета иконок
    fox-happy.svg      → icon slug `fox-happy`
    rain-cloud.svg
  my-animals/          → новый пак `my-animals`
    pack.json
    cat.png
    dog.webp
```

## Как добавить пак или иконки

1. Создайте папку `backend/app/data/marketplace/<имя-пака>/`.
   Имя папки станет `slug` пака (`My Animals` → `my-animals`). Не используйте `essentials` — этот slug занят базовым набором.
2. Положите туда картинки: `.svg`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`.
   Имя файла без расширения станет `slug` иконки (`Happy Fox.png` → `happy-fox`). Подпапки внутри пака игнорируются.
3. Положите `pack.json` (см. ниже). Без файла seed всё равно подхватит картинки с дефолтами (бесплатный published official, названия из файлов).
4. Поднимите стек (`make up`) и подтяните каталог:

   ```bash
   make seed-marketplace
   ```

Команда идемпотентна: новые файлы создадут иконки, замена файла и правки `pack.json` обновят каталог.

## pack.json

Живой пример: `demo-mocks/pack.json`.

```json
{
  "slug": "foxes",
  "name": {"en": "Foxes", "ru": "Лисы"},
  "description": {"en": "Cute foxes", "ru": "Милые лисы"},
  "price_tokens": 50,
  "official": true,
  "published": true,
  "granted": false,
  "sort_order": 20,
  "cover": "happy-fox",
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

### Поля пака → БД

| Поле | БД | По умолчанию |
|------|-----|----------------|
| `slug` | `icon_packs.slug` | имя папки |
| `name` / `description` | `labels` (`en`/`ru`) | из имени папки |
| `price_tokens` (или `price`) | `price_tokens` | `0` |
| `official` (или `is_official`) | `is_official` | `true` |
| `published` | `status`: `published` / `draft` | `true` |
| `granted` (или `unlocked` / `available`) | сразу доступен всем | `true`, если цена `0` |
| `sort_order` | `sort_order` | 10, 20, 30… по имени папок |
| `cover` (или `cover_icon`) | `cover_icon_id` | первая иконка |
| `tags` / `colors` | дефолты для иконок без своих полей | теги пустые, цвет `#94a3b8` |

`granted: true` — пак сразу у всех (как бесплатный): в БД уйдёт `price_tokens = 0`, иконки можно ставить без покупки. Для платного пака: `"granted": false` и `"price_tokens": 50`.

`published: false` — черновик, в витрине не показывается. Альтернатива: `"status": "draft"` / `"published"` / `"archived"`.

Ключи в `icons` — slug или имя файла. Поля, которых нет, берутся из дефолтов пака / имени файла. `scores` — suggested mood 1–5. `sort_order` у иконки задаёт порядок в паке (иначе — по имени файла).

Готовые теги: `joy`, `sadness`, `calm`, `energy`, `sport`, `fitness`, `animals`, `nature`, `weather`, `night`. Неизвестный тег игнорируется — сначала добавьте его в `DEFAULT_SEARCH_TAGS` в `backend/app/services/marketplace_seed.py`.

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

## Пресеты (перенос каталога на другой инстанс)

Staff может выгрузить паки и ачивки в `/staff` → «Пресеты» или командой `make preset-export`. Архив — это те же сид-папки:

```text
manifest.json
marketplace/search-tags.json
marketplace/<pack>/pack.json + картинки
achievements/catalog.json
```

Загрузка на новом инстансе: импорт в `/staff` или `make preset-import PRESET=../preset.zip`. Можно и распаковать `marketplace/*` сюда, а `achievements/catalog.json` — в `../achievements/`, и выполнить `make seed-marketplace seed-achievements`. Роль staff выдаётся `make staff STAFF_ARGS='grant --user you@example.com'`.
