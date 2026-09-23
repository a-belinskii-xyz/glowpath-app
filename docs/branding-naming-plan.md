# Branding & naming — план

**Статус:** имя **выбрано** — **GlowPath**  
**Дата:** 2026-07-23 (решение) · идеи 2026-07-23  
**Связь:** [[Mood Tracker.md]] · визуальная система `frontend/src/design/`

---

## Решение

| | |
|--|--|
| **Имя** | **GlowPath** |
| **Лого-марка (текст)** | `glowpath:\` |
| **Смысл** | Glow — эмоциональный / visual слой (glow в UI); Path — путь жизни, квесты, рост. Суффикс `:\` — отсылка к path в разных ОС (Windows `C:\…`, URI-like scheme). |
| **Копирайт в продукте** | Играть с путём: «строим путь», «ваш путь», «путь дня» и т.п. |
| **UI сейчас** | Текст `glowpath:\` в header / лендинге / `document.title`. Графический логотип — позже. |

---

## 1. Позиционирование (направление)

**Якорь продукта:** цвет не декорация, а core-фича — кастомные цвета score, wash, glow, day gradient. Это отличает продукт от Daylio / generic mood apps.

**Долгосрочная рамка:** платформа «жизненного баланса» и самопознания:
- сейчас: mood + goals (+ tags, templates, reminders, Telegram);
- далее (бэклог видения): геймификация (уровни, квесты, персонаж), finance / food / habits / состояния.

**Тон:** спокойный, приватный, empowering — без агрессивного growth-hacking.

**Вход:** начинай с mood (простой onboarding) → углубляйся в геймификацию и другие треки по желанию. Расширение фич = «палитра жизни становится богаче», а не «ещё дашборд».

Имя передаёт:

1. Glow / цвета / эмоции / персонализацию.
2. Path — путешествие / рост / игру.
3. Целостность жизни (mood + goals + будущие треки).
4. Спокойный, приватный, empowering тон + tech-отсылка через `:\`.

---

## 2. Архив кандидатов (не выбраны)

Топ ранее: ChromaLife / ChromaQuest, HueForge, PalettePath, VividQuest / VividLife.  
Также: ColorBloom, AuraPalette, GlowForge, SpectrumLife, QuestHue, Lumora, Kolora, Moodora, Elyra и др.

---

## 3. Слоганы / hero (черновик)

- «Твой цвет дня. Твой путь к балансу.»
- «Строй свой путь. Уровень за уровнем.»
- «От цвета настроения — к полной картине жизни.»
- Path-play: «ваш путь», «строим путь», `glowpath:\mood`, …

Лендинг (когда дойдём): hero с градиентом дня + (позже) персонаж + teaser `Mood → Habits → Finance → Full Life Path`.

---

## 4. Брендинг vs текущая design-система

| Слой | Роль в бренде |
|------|----------------|
| **Chrome** | Нейтральный, спокойный UI kit. Бренд-цвета chrome — не mood hex пользователя. |
| **Semantic Mood** | Главный эмоциональный акцент: палитра score, wash, **glow**, day gradient. |
| **Gamification (бэклог)** | Персонаж / квесты вдоль «пути»; color-themes. |
| **Typography / марка** | Текст `glowpath:\` → позже графический логотип. |

Принцип: брендинг в chrome + лендинг; mood-цвета остаются данными пользователя.

---

## 5. Следующие шаги

1. [x] Зафиксировать имя в планах / README / i18n / user-facing copy.
2. [ ] Проверить домены `.com` / `.app`, Telegram / X handles (glowpath).
3. [ ] Графический логотип на базе `glowpath:\`.
4. [ ] Слоган, mockup лендинга, path-метафоры в копирайте.
5. [ ] Геймификация и новые треки — отдельные планы.

---

## 6. Связанное

- Визуальная система: `frontend/src/design/` (`chrome`, `moodTheme`, `gradientEngine`, `motion`)
- Описание wash / day gradient: раздел «Фон дня…» в `Mood Tracker.md`
- Telegram / reminders: `docs/telegram-integration-plan.md`
