from __future__ import annotations

# Flavor -> locale -> note templates (keep under 500 chars).
NOTES: dict[str, dict[str, tuple[str, ...]]] = {
    "active": {
        "en": (
            "Morning run cleared my head. Legs sore but mood lifted.",
            "Tried a new hiking trail — legs tired, brain quiet.",
            "Picked up groceries and cooked something simple.",
            "Forgot lunch, compensated with a long walk later.",
            "Yoga session was short but enough to reset.",
            "Cycled to the café; rain started halfway — still worth it.",
        ),
        "ru": (
            "Утренняя пробежка разгрузила голову. Ноги ноют, но легче.",
            "Новый маршрут — устал телом, спокойнее внутри.",
            "Закупился и приготовил простой ужин.",
            "Пропустил обед, вечером компенсировал прогулкой.",
            "Короткая йога — хватило, чтобы перезагрузиться.",
        ),
    },
    "calm": {
        "en": (
            "Slow morning with coffee and silence. No rush today.",
            "Watched the rain from the window for a while.",
            "Cancelled evening plans, stayed in with a book.",
            "Felt neutral most of the day — not bad, not great.",
            "Early night. Sleep mattered more than productivity.",
        ),
        "ru": (
            "Медленное утро с кофе и тишиной. Без спешки.",
            "Долго смотрел на дождь из окна.",
            "Отменил планы, остался дома с книгой.",
            "Большую часть дня нейтрально — нормально.",
            "Лёг раньше: сон важнее продуктивности.",
        ),
    },
    "work": {
        "en": (
            "Back-to-back meetings drained me by mid-afternoon.",
            "Shipped a small fix; quiet pride.",
            "Context-switching all day. Hard to focus.",
            "Pair session went well — left feeling competent.",
            "Deadline next week. Anxiety humming in the background.",
            "Inbox zero for an hour. Brief relief.",
        ),
        "ru": (
            "Созвоны подряд — к обеду уже пусто.",
            "Выкатил маленький фикс; тихая гордость.",
            "Весь день переключения контекста. Сложно сосредоточиться.",
            "Спарринг-сессия прошла хорошо — ощущение компетенции.",
            "Дедлайн на следующей неделе. Тревога на фоне.",
        ),
    },
    "social": {
        "en": (
            "Lunch with a friend I hadn't seen in months.",
            "Family call lasted longer than expected — in a good way.",
            "Awkward small talk at the party; left early.",
            "Helped a neighbour move a sofa. Oddly satisfying.",
            "Group chat energy was chaotic but funny.",
        ),
        "ru": (
            "Обед с другом, которого не видел месяцами.",
            "Звонок семье затянулся — в хорошем смысле.",
            "Неловкий small talk на вечеринке; ушёл рано.",
            "Помог соседу перетащить диван. Странно приятно.",
            "В чате хаос, но смешно.",
        ),
    },
    "reflective": {
        "en": (
            "Journaled for twenty minutes. Patterns starting to show.",
            "Wondering if I'm avoiding something. Tired, not sad.",
            "Listened to a long podcast on walks and attention.",
            "Compared today to last month — slight improvement.",
            "Short gratitude list before bed. Three items, all ordinary.",
        ),
        "ru": (
            "Двадцать минут дневника. Начинают проступать паттерны.",
            "Кажется, чего-то избегаю. Устал, не грустно.",
            "Долгий подкаст про прогулки и внимание.",
            "Сравнил с прошлым месяцем — чуть лучше.",
            "Короткий список благодарности. Три обычных пункта.",
        ),
    },
}


SCORE_WEIGHTS = {
    # Slight bias toward 3–4 for more “realistic” diaries
    1: 8,
    2: 15,
    3: 30,
    4: 30,
    5: 17,
}


def weighted_score(rng_random: float) -> int:
    """Map [0,1) to score using SCORE_WEIGHTS."""
    total = sum(SCORE_WEIGHTS.values())
    threshold = rng_random * total
    cumulative = 0.0
    for score, weight in SCORE_WEIGHTS.items():
        cumulative += weight
        if threshold < cumulative:
            return score
    return 3
