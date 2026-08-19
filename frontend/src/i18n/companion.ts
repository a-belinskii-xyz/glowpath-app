import type { CompanionDaypart } from '../lib/companion'

type Variant3 = { '0': string; '1': string; '2': string }
type Variant2 = { '0': string; '1': string }
type DaypartMap<T> = Record<CompanionDaypart, T>
type MoodPhrases = { '1': string; '2': string; '3': string; '4': string; '5': string }

export type CompanionMessages = {
  greeting: DaypartMap<Variant3>
  kicker: DaypartMap<Variant2>
  howAreYou: DaypartMap<Variant3>
  pickMoodHint: DaypartMap<Variant2>
  whatsOnYourMind: DaypartMap<Variant2>
  notePlaceholder: DaypartMap<Variant2>
  whatHappened: DaypartMap<Variant2>
  contextLead: DaypartMap<Variant2>
  goals: DaypartMap<Variant2>
  emptyMonth: DaypartMap<Variant2>
  emptyPrompt: DaypartMap<Variant2>
  moodPhrase: DaypartMap<MoodPhrases>
}

export const companionEn: CompanionMessages = {
  greeting: {
    lateNight: {
      '0': 'Quiet hours.',
      '1': 'Still up? A short note is enough.',
      '2': 'A late check-in, if you want.',
    },
    morning: {
      '0': 'Good morning.',
      '1': 'A new day. No hurry.',
      '2': 'Morning. Whenever you’re ready.',
    },
    midday: {
      '0': 'Midday. A short pause.',
      '1': 'Halfway through the day.',
      '2': 'A midday note, if you want.',
    },
    afternoon: {
      '0': 'How is the day going?',
      '1': 'Afternoon. A check-in if you want.',
      '2': 'The day is underway.',
    },
    evening: {
      '0': 'Evening. How did the day feel?',
      '1': 'The day is winding down.',
      '2': 'A note about today, if you want.',
    },
    night: {
      '0': 'The day is almost over.',
      '1': 'Before rest. A last note if you want.',
      '2': 'Tonight, whenever you’re ready.',
    },
  },
  kicker: {
    lateNight: {
      '0': 'Just for you.',
      '1': 'No one else has to see this.',
    },
    morning: {
      '0': 'A small start is enough.',
      '1': 'Even a short note counts.',
    },
    midday: {
      '0': 'A minute is enough.',
      '1': 'It can be short.',
    },
    afternoon: {
      '0': 'As it is.',
      '1': 'No need to explain.',
    },
    evening: {
      '0': 'About today.',
      '1': 'A few words are enough.',
    },
    night: {
      '0': 'You can stop here.',
      '1': 'A last note, if you want.',
    },
  },
  howAreYou: {
    lateNight: {
      '0': 'How are you at this hour?',
      '1': 'Still up? How are you feeling?',
      '2': 'Quiet hours. How are you feeling?',
    },
    morning: {
      '0': 'Good morning. How are you feeling?',
      '1': 'How did you wake up today?',
      '2': 'Morning check-in. How are you feeling?',
    },
    midday: {
      '0': 'How are you feeling right now?',
      '1': 'Midday. How are you feeling?',
      '2': 'Halfway through the day. How are you feeling?',
    },
    afternoon: {
      '0': 'How are you feeling this afternoon?',
      '1': 'How is the day going?',
      '2': 'Afternoon check-in. How are you feeling?',
    },
    evening: {
      '0': 'How are you feeling this evening?',
      '1': 'How did your day feel?',
      '2': 'Evening check-in. How are you feeling?',
    },
    night: {
      '0': 'How are you feeling tonight?',
      '1': 'Before you rest — how are you feeling?',
      '2': 'The day is almost over. How are you feeling?',
    },
  },
  pickMoodHint: {
    lateNight: {
      '0': 'Just pick how it feels.',
      '1': 'A mood is enough.',
    },
    morning: {
      '0': 'Start with a mood.',
      '1': 'Choose how you feel.',
    },
    midday: {
      '0': 'One tap is enough.',
      '1': 'Start with a mood.',
    },
    afternoon: {
      '0': 'Pick what fits.',
      '1': 'How does it feel right now?',
    },
    evening: {
      '0': 'How does the evening feel?',
      '1': 'Start with a mood.',
    },
    night: {
      '0': 'How does tonight feel?',
      '1': 'Just the mood.',
    },
  },
  whatsOnYourMind: {
    lateNight: {
      '0': 'If something is on your mind.',
      '1': 'A night note, if you want.',
    },
    morning: {
      '0': 'A few words about the morning.',
      '1': 'How the day is starting.',
    },
    midday: {
      '0': 'A thought from midday.',
      '1': 'A short note.',
    },
    afternoon: {
      '0': 'What’s been on your mind?',
      '1': 'A line or two.',
    },
    evening: {
      '0': 'A few words about today.',
      '1': 'How the day felt.',
    },
    night: {
      '0': 'A last note, if you want.',
      '1': 'Anything from today.',
    },
  },
  notePlaceholder: {
    lateNight: {
      '0': 'Even a sentence is enough…',
      '1': 'What’s on your mind…',
    },
    morning: {
      '0': 'A morning note…',
      '1': 'How the day is starting…',
    },
    midday: {
      '0': 'A midday thought…',
      '1': 'A few words…',
    },
    afternoon: {
      '0': 'What’s on your mind…',
      '1': 'A line or two…',
    },
    evening: {
      '0': 'How the day felt…',
      '1': 'A few words about today…',
    },
    night: {
      '0': 'A last thought…',
      '1': 'Tonight, in a few words…',
    },
  },
  whatHappened: {
    lateNight: {
      '0': 'Anything left from the day?',
      '1': 'What else is still around?',
    },
    morning: {
      '0': 'What already happened this morning?',
      '1': 'Coffee, commute, people — if you want.',
    },
    midday: {
      '0': 'What’s been around so far?',
      '1': 'People, places, plans.',
    },
    afternoon: {
      '0': 'What happened this afternoon?',
      '1': 'Add a bit of context, if you want.',
    },
    evening: {
      '0': 'What happened today?',
      '1': 'Rain, friends, gym — whatever you like.',
    },
    night: {
      '0': 'What stayed from the day?',
      '1': 'Add a tag if you want.',
    },
  },
  contextLead: {
    lateNight: {
      '0': 'Optional. A tag or two is enough.',
      '1': 'You can skip this.',
    },
    morning: {
      '0': 'Optional. Whatever already showed up.',
      '1': 'Only if you want to.',
    },
    midday: {
      '0': 'A little context, if you want.',
      '1': 'Optional.',
    },
    afternoon: {
      '0': 'Mark what was going on, if you want.',
      '1': 'No need to list everything.',
    },
    evening: {
      '0': 'Rain, friends, gym — add whatever you like.',
      '1': 'Optional. Whatever belonged to the day.',
    },
    night: {
      '0': 'A tag for tonight, if you want.',
      '1': 'Optional.',
    },
  },
  goals: {
    lateNight: {
      '0': 'Any goals in this hour?',
      '1': 'Optional.',
    },
    morning: {
      '0': 'Any goals already today?',
      '1': 'Optional — only if something’s started.',
    },
    midday: {
      '0': 'Any goals so far?',
      '1': 'Optional.',
    },
    afternoon: {
      '0': 'Any goals this afternoon?',
      '1': 'Mark them if you want.',
    },
    evening: {
      '0': 'Any goals done today?',
      '1': 'Optional.',
    },
    night: {
      '0': 'Anything to mark before the day ends?',
      '1': 'Optional.',
    },
  },
  emptyMonth: {
    lateNight: {
      '0': 'Nothing this month yet. Tonight is a fine time to start.',
      '1': 'No entries yet. A first note whenever you’re ready.',
    },
    morning: {
      '0': 'No notes this month yet. Morning is a good time to begin.',
      '1': 'Empty so far. One mood is enough to start.',
    },
    midday: {
      '0': 'Nothing this month yet. A midday note can open it.',
      '1': 'No entries yet. One note is enough.',
    },
    afternoon: {
      '0': 'No entries this month yet. Afternoon is a fine time.',
      '1': 'Still empty. You can just begin.',
    },
    evening: {
      '0': 'No entries this month yet. Evening is a good time to start.',
      '1': 'The month is quiet so far.',
    },
    night: {
      '0': 'Nothing this month yet. A night note still counts.',
      '1': 'Empty page. One line is enough to begin.',
    },
  },
  emptyPrompt: {
    lateNight: {
      '0': 'Tap a mood to begin.',
      '1': 'A night check-in starts with a mood.',
    },
    morning: {
      '0': 'Start with a mood.',
      '1': 'Tap how the morning feels.',
    },
    midday: {
      '0': 'Tap a mood for this hour.',
      '1': 'A midday mood is enough to begin.',
    },
    afternoon: {
      '0': 'Tap how the afternoon feels.',
      '1': 'One mood opens the first entry.',
    },
    evening: {
      '0': 'Tap a mood for this evening.',
      '1': 'Start with how today felt.',
    },
    night: {
      '0': 'Tap a mood before the day ends.',
      '1': 'One tap. Then a note, or not.',
    },
  },
  moodPhrase: {
    lateNight: {
      '1': 'A heavy hour. That’s okay.',
      '2': 'A bit off. That’s okay.',
      '3': 'Somewhere in the middle.',
      '4': 'Pretty good.',
      '5': 'Feeling light.',
    },
    morning: {
      '1': 'A hard morning. That’s okay.',
      '2': 'Not an easy start. That’s okay.',
      '3': 'A middling morning.',
      '4': 'A pretty good morning.',
      '5': 'A bright start.',
    },
    midday: {
      '1': 'Midday feels heavy. That’s okay.',
      '2': 'A bit off. That’s okay.',
      '3': 'In the middle.',
      '4': 'Pretty good.',
      '5': 'Feeling good.',
    },
    afternoon: {
      '1': 'A hard afternoon. That’s okay.',
      '2': 'A bit uneven. That’s okay.',
      '3': 'Somewhere in the middle.',
      '4': 'The afternoon is going well.',
      '5': 'Feeling good this afternoon.',
    },
    evening: {
      '1': 'A heavy evening. That’s okay.',
      '2': 'A bit rough. That’s okay.',
      '3': 'An ordinary evening.',
      '4': 'A pretty good evening.',
      '5': 'Feeling good this evening.',
    },
    night: {
      '1': 'A hard close. That’s okay.',
      '2': 'A bit rough. That’s okay.',
      '3': 'Neither high nor low.',
      '4': 'A pretty good night.',
      '5': 'Feeling light tonight.',
    },
  },
}

export const companionRu: CompanionMessages = {
  greeting: {
    lateNight: {
      '0': 'Тихие часы.',
      '1': 'Ещё не спится? Короткой отметки достаточно.',
      '2': 'Поздняя заметка — если хочется.',
    },
    morning: {
      '0': 'Доброе утро.',
      '1': 'Новый день. Без спешки.',
      '2': 'Утро. Можно отметиться, когда будет время.',
    },
    midday: {
      '0': 'Середина дня. Короткая пауза.',
      '1': 'Половина дня позади.',
      '2': 'Можно оставить короткую заметку.',
    },
    afternoon: {
      '0': 'Как проходит день?',
      '1': 'Дневная отметка — если хочется.',
      '2': 'День уже идёт.',
    },
    evening: {
      '0': 'Вечер. Как прошёл день?',
      '1': 'День почти закончился.',
      '2': 'Можно оставить пару слов про сегодня.',
    },
    night: {
      '0': 'День почти закончился.',
      '1': 'Перед отдыхом. Последняя заметка — если хочется.',
      '2': 'Сегодня вечером — когда будет время.',
    },
  },
  kicker: {
    lateNight: {
      '0': 'Только для тебя.',
      '1': 'Это никому больше не видно.',
    },
    morning: {
      '0': 'Можно начать с малого.',
      '1': 'Даже короткой заметки хватит.',
    },
    midday: {
      '0': 'Минуты достаточно.',
      '1': 'Можно коротко.',
    },
    afternoon: {
      '0': 'Как есть.',
      '1': 'Не обязательно объяснять.',
    },
    evening: {
      '0': 'Про сегодня.',
      '1': 'Пары слов достаточно.',
    },
    night: {
      '0': 'На этом можно остановиться.',
      '1': 'Последняя заметка — если хочется.',
    },
  },
  howAreYou: {
    lateNight: {
      '0': 'Как ты в этот час?',
      '1': 'Ещё не спится? Как ты?',
      '2': 'Тихие часы. Как ты?',
    },
    morning: {
      '0': 'Доброе утро. Как ты?',
      '1': 'С каким настроением началось утро?',
      '2': 'Утренняя отметка. Как ты?',
    },
    midday: {
      '0': 'Как ты сейчас?',
      '1': 'Середина дня. Как ты?',
      '2': 'Половина дня позади. Как ты?',
    },
    afternoon: {
      '0': 'Как ты себя чувствуешь днём?',
      '1': 'Как проходит день?',
      '2': 'Дневная отметка. Как ты?',
    },
    evening: {
      '0': 'Как ты этим вечером?',
      '1': 'Как прошёл день?',
      '2': 'Вечерняя отметка. Как ты?',
    },
    night: {
      '0': 'Как ты сегодня вечером?',
      '1': 'Перед отдыхом — как ты?',
      '2': 'День почти закончился. Как ты?',
    },
  },
  pickMoodHint: {
    lateNight: {
      '0': 'Просто выбери, как есть.',
      '1': 'Достаточно настроения.',
    },
    morning: {
      '0': 'Сначала настроение.',
      '1': 'Выбери, как ты.',
    },
    midday: {
      '0': 'Одного нажатия достаточно.',
      '1': 'Сначала настроение.',
    },
    afternoon: {
      '0': 'Выбери то, что ближе.',
      '1': 'Как сейчас?',
    },
    evening: {
      '0': 'Как ощущается вечер?',
      '1': 'Сначала настроение.',
    },
    night: {
      '0': 'Как сейчас?',
      '1': 'Только настроение.',
    },
  },
  whatsOnYourMind: {
    lateNight: {
      '0': 'Если что-то не выходит из головы.',
      '1': 'Ночная заметка — если хочется.',
    },
    morning: {
      '0': 'Пара слов про утро.',
      '1': 'Как начинается день.',
    },
    midday: {
      '0': 'Мысль из середины дня.',
      '1': 'Короткая заметка.',
    },
    afternoon: {
      '0': 'Что сегодня на уме.',
      '1': 'Пара строк.',
    },
    evening: {
      '0': 'Пара слов про сегодня.',
      '1': 'Как прошёл день.',
    },
    night: {
      '0': 'Последняя заметка — если хочется.',
      '1': 'Что-нибудь от сегодня.',
    },
  },
  notePlaceholder: {
    lateNight: {
      '0': 'Даже одного предложения хватит…',
      '1': 'Что у тебя на уме…',
    },
    morning: {
      '0': 'Утренняя заметка…',
      '1': 'Как начинается день…',
    },
    midday: {
      '0': 'Мысль из середины дня…',
      '1': 'Пара слов…',
    },
    afternoon: {
      '0': 'Что у тебя на уме…',
      '1': 'Пары строк достаточно…',
    },
    evening: {
      '0': 'Как прошёл день…',
      '1': 'Пара слов про сегодня…',
    },
    night: {
      '0': 'Последняя мысль…',
      '1': 'Сегодня вечером, в нескольких словах…',
    },
  },
  whatHappened: {
    lateNight: {
      '0': 'Что ещё осталось от дня?',
      '1': 'Можно отметить, если есть.',
    },
    morning: {
      '0': 'Что уже было утром?',
      '1': 'Кофе, дорога, люди — по желанию.',
    },
    midday: {
      '0': 'Что было до сих пор?',
      '1': 'Люди, места, дела.',
    },
    afternoon: {
      '0': 'Что было днём?',
      '1': 'Можно добавить контекст.',
    },
    evening: {
      '0': 'Что сегодня было?',
      '1': 'Дождь, друзья, зал — что угодно.',
    },
    night: {
      '0': 'Что осталось от дня?',
      '1': 'Можно отметить тег.',
    },
  },
  contextLead: {
    lateNight: {
      '0': 'Необязательно. Пары тегов достаточно.',
      '1': 'Можно пропустить.',
    },
    morning: {
      '0': 'Необязательно. Только то, что уже было.',
      '1': 'Если хочется.',
    },
    midday: {
      '0': 'Немного контекста — если хочется.',
      '1': 'Необязательно.',
    },
    afternoon: {
      '0': 'Можно отметить, что происходило.',
      '1': 'Не обязательно перечислять всё.',
    },
    evening: {
      '0': 'Дождь, друзья, зал — что угодно.',
      '1': 'Необязательно. То, что относилось к дню.',
    },
    night: {
      '0': 'Тег на вечер — если хочется.',
      '1': 'Необязательно.',
    },
  },
  goals: {
    lateNight: {
      '0': 'Цели за этот час?',
      '1': 'Необязательно.',
    },
    morning: {
      '0': 'Что-то из целей уже сегодня?',
      '1': 'Необязательно — только если что-то началось.',
    },
    midday: {
      '0': 'Есть отмеченные цели?',
      '1': 'Необязательно.',
    },
    afternoon: {
      '0': 'Какие цели уже сегодня?',
      '1': 'Можно отметить.',
    },
    evening: {
      '0': 'Какие цели на сегодня?',
      '1': 'Необязательно.',
    },
    night: {
      '0': 'Есть что отметить, пока день не закончился?',
      '1': 'Необязательно.',
    },
  },
  emptyMonth: {
    lateNight: {
      '0': 'В этом месяце пока пусто. Можно начать сейчас.',
      '1': 'Записей ещё нет. Первую можно оставить, когда будет время.',
    },
    morning: {
      '0': 'В этом месяце ещё нет записей. Утро — нормальное время начать.',
      '1': 'Пока пусто. Одного настроения хватит.',
    },
    midday: {
      '0': 'В этом месяце ещё пусто. Дневная заметка его откроет.',
      '1': 'Записей нет. Одной заметки достаточно.',
    },
    afternoon: {
      '0': 'В этом месяце ещё нет записей. День — нормальное время.',
      '1': 'Пока пусто. Можно просто начать.',
    },
    evening: {
      '0': 'В этом месяце записей пока нет. Вечер — хорошее время начать.',
      '1': 'Месяц пока тихий.',
    },
    night: {
      '0': 'В этом месяце ещё пусто. Вечерняя заметка тоже считается.',
      '1': 'Чистая страница. Одной строки хватит.',
    },
  },
  emptyPrompt: {
    lateNight: {
      '0': 'Выбери настроение.',
      '1': 'Ночная отметка начинается с настроения.',
    },
    morning: {
      '0': 'Начни с настроения.',
      '1': 'Выбери, каким ощущается утро.',
    },
    midday: {
      '0': 'Выбери настроение.',
      '1': 'Дневного настроения достаточно, чтобы начать.',
    },
    afternoon: {
      '0': 'Выбери, каким ощущается день.',
      '1': 'Одно настроение открывает первую запись.',
    },
    evening: {
      '0': 'Выбери настроение на вечер.',
      '1': 'Начни с того, как прошёл день.',
    },
    night: {
      '0': 'Выбери настроение, пока день не закончился.',
      '1': 'Одно нажатие. Дальше можно писать — или нет.',
    },
  },
  moodPhrase: {
    lateNight: {
      '1': 'Тяжеловато. Так тоже бывает.',
      '2': 'Не очень. Так тоже бывает.',
      '3': 'Середина.',
      '4': 'Вполне нормально.',
      '5': 'Легко.',
    },
    morning: {
      '1': 'Тяжёлое утро. Так тоже бывает.',
      '2': 'Старт нелёгкий. Так тоже бывает.',
      '3': 'Обычное утро.',
      '4': 'Утро вполне хорошее.',
      '5': 'Светлое утро.',
    },
    midday: {
      '1': 'Середина дня тяжеловата. Так тоже бывает.',
      '2': 'Не очень. Так тоже бывает.',
      '3': 'Середина.',
      '4': 'Вполне нормально.',
      '5': 'Хорошо.',
    },
    afternoon: {
      '1': 'Тяжеловатый день. Так тоже бывает.',
      '2': 'Немного неровно. Так тоже бывает.',
      '3': 'Середина.',
      '4': 'День идёт нормально.',
      '5': 'Днём хорошо.',
    },
    evening: {
      '1': 'Тяжёлый вечер. Так тоже бывает.',
      '2': 'Не очень. Так тоже бывает.',
      '3': 'Обычный вечер.',
      '4': 'Вечер вполне хороший.',
      '5': 'Хороший вечер.',
    },
    night: {
      '1': 'Тяжеловато. Так тоже бывает.',
      '2': 'Не очень. Так тоже бывает.',
      '3': 'Ни туда, ни сюда.',
      '4': 'Вполне нормально.',
      '5': 'Легко.',
    },
  },
}
