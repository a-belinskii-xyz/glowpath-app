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
      '0': 'Still awake? You can leave a note if you like.',
      '1': 'It’s quiet out. No rush.',
      '2': 'A late note is fine — even a short one.',
    },
    morning: {
      '0': 'Good morning.',
      '1': 'New day. Start whenever you’re ready.',
      '2': 'How’s the morning so far?',
    },
    midday: {
      '0': 'How’s the day going so far?',
      '1': 'Middle of the day. Want to jot something down?',
      '2': 'Around lunch. How are you?',
    },
    afternoon: {
      '0': 'How’s the afternoon going?',
      '1': 'How’s the day going?',
      '2': 'A short note doesn’t take long.',
    },
    evening: {
      '0': 'Evening. How did today go?',
      '1': 'The day’s slowing down.',
      '2': 'Want to leave a few words about today?',
    },
    night: {
      '0': 'Almost done with the day.',
      '1': 'A last note, if you want one.',
      '2': 'How are you tonight?',
    },
  },
  kicker: {
    lateNight: {
      '0': 'A few words is enough.',
      '1': 'This is just for you.',
    },
    morning: {
      '0': 'A short note is plenty.',
      '1': 'You can start small.',
    },
    midday: {
      '0': 'It doesn’t have to be long.',
      '1': 'A minute is enough.',
    },
    afternoon: {
      '0': 'A line or two is plenty.',
      '1': 'As it is — that’s fine.',
    },
    evening: {
      '0': 'A few words will do.',
      '1': 'Just how it was.',
    },
    night: {
      '0': 'That’s enough for today.',
      '1': 'One last note, if you feel like it.',
    },
  },
  howAreYou: {
    lateNight: {
      '0': 'How are you at this hour?',
      '1': 'Still awake? How are you?',
      '2': 'How are you this late?',
    },
    morning: {
      '0': 'How are you this morning?',
      '1': 'How did you wake up?',
      '2': 'What’s the morning like?',
    },
    midday: {
      '0': 'How are you right now?',
      '1': 'How are you around noon?',
      '2': 'How are you in the middle of the day?',
    },
    afternoon: {
      '0': 'How are you this afternoon?',
      '1': 'How’s the day going?',
      '2': 'How are you so far?',
    },
    evening: {
      '0': 'How are you this evening?',
      '1': 'How did today go?',
      '2': 'How’s the evening?',
    },
    night: {
      '0': 'How are you tonight?',
      '1': 'How did today go?',
      '2': 'How are you this late?',
    },
  },
  pickMoodHint: {
    lateNight: {
      '0': 'Just pick how it feels. The rest can wait.',
      '1': 'One mood is enough for now.',
    },
    morning: {
      '0': 'Choose a mood — everything else comes after.',
      '1': 'Start with how you feel.',
    },
    midday: {
      '0': 'Tap how you are. The rest can wait.',
      '1': 'One mood, then you can add more if you want.',
    },
    afternoon: {
      '0': 'Pick whatever fits.',
      '1': 'Choose a mood — everything else comes after.',
    },
    evening: {
      '0': 'Choose a mood for this evening.',
      '1': 'Start with how today felt.',
    },
    night: {
      '0': 'One tap is enough.',
      '1': 'Just the mood. That’s enough.',
    },
  },
  whatsOnYourMind: {
    lateNight: {
      '0': 'A few words',
      '1': 'What’s on your mind',
    },
    morning: {
      '0': 'A few words',
      '1': 'The morning',
    },
    midday: {
      '0': 'A few words',
      '1': 'Around now',
    },
    afternoon: {
      '0': 'A few words',
      '1': 'What’s on your mind',
    },
    evening: {
      '0': 'A few words',
      '1': 'About today',
    },
    night: {
      '0': 'A few words',
      '1': 'Tonight',
    },
  },
  notePlaceholder: {
    lateNight: {
      '0': 'What’s still on your mind…',
      '1': 'Even a sentence is enough…',
    },
    morning: {
      '0': 'How the morning’s going…',
      '1': 'A few words about the morning…',
    },
    midday: {
      '0': 'What’s on your mind…',
      '1': 'A thought from around now…',
    },
    afternoon: {
      '0': 'What’s on your mind this afternoon…',
      '1': 'A line or two is plenty…',
    },
    evening: {
      '0': 'How today felt…',
      '1': 'A few words about today…',
    },
    night: {
      '0': 'A last thought…',
      '1': 'Tonight, in a few words…',
    },
  },
  whatHappened: {
    lateNight: {
      '0': 'What happened today?',
      '1': 'What’s still with you?',
    },
    morning: {
      '0': 'What happened this morning?',
      '1': 'What’s already happened?',
    },
    midday: {
      '0': 'What’s been going on?',
      '1': 'What happened so far?',
    },
    afternoon: {
      '0': 'What happened today?',
      '1': 'What happened this afternoon?',
    },
    evening: {
      '0': 'What happened today?',
      '1': 'What stayed with you?',
    },
    night: {
      '0': 'What happened today?',
      '1': 'What stayed with you tonight?',
    },
  },
  contextLead: {
    lateNight: {
      '0': 'Rain, friends, gym — or skip it. Both are fine.',
      '1': 'A tag or two is enough if you don’t feel like writing.',
    },
    morning: {
      '0': 'Rain, friends, gym — whatever already colored the morning.',
      '1': 'Only if you want.',
    },
    midday: {
      '0': 'Rain, friends, gym — add whatever colored the day so far.',
      '1': 'Skip it if you’d rather not.',
    },
    afternoon: {
      '0': 'Rain, friends, gym — add whatever colored the day.',
      '1': 'No need to list everything — just what stood out.',
    },
    evening: {
      '0': 'Rain, friends, gym — add whatever colored the day.',
      '1': 'Mark what mattered, if you want.',
    },
    night: {
      '0': 'Rain, friends, gym — add whatever colored the day.',
      '1': 'Only if you want.',
    },
  },
  goals: {
    lateNight: {
      '0': 'Any goals done today?',
      '1': 'Anything to mark this late?',
    },
    morning: {
      '0': 'Any goals this morning?',
      '1': 'Any goals started yet?',
    },
    midday: {
      '0': 'Any goals done so far?',
      '1': 'Anything to mark by now?',
    },
    afternoon: {
      '0': 'Any goals done this afternoon?',
      '1': 'Any goals done today?',
    },
    evening: {
      '0': 'Any goals done today?',
      '1': 'Any habits to mark?',
    },
    night: {
      '0': 'Any goals done today?',
      '1': 'Anything to mark tonight?',
    },
  },
  emptyMonth: {
    lateNight: {
      '0': 'Nothing this month yet. You can start tonight if you like.',
      '1': 'No entries yet. The first one can wait until you’re ready.',
    },
    morning: {
      '0': 'No notes this month yet. Morning’s a fine time to begin.',
      '1': 'Empty so far. One mood is enough to open the month.',
    },
    midday: {
      '0': 'Nothing this month yet. A midday note can open it.',
      '1': 'Nothing this month yet. You can start now.',
    },
    afternoon: {
      '0': 'No entries this month yet. Afternoon is a perfectly fine time.',
      '1': 'Still empty. You can just begin.',
    },
    evening: {
      '0': 'No entries this month yet. Evening is a good time to start.',
      '1': 'The month is quiet so far. You can start tonight.',
    },
    night: {
      '0': 'Nothing this month yet. A night note still counts.',
      '1': 'Nothing this month yet. One line is enough to begin.',
    },
  },
  emptyPrompt: {
    lateNight: {
      '0': 'Tap a mood whenever you’re ready.',
      '1': 'Start with how you feel.',
    },
    morning: {
      '0': 'Start with a mood.',
      '1': 'Tap how the morning feels.',
    },
    midday: {
      '0': 'Tap a mood for right now.',
      '1': 'Start with how you are.',
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
      '0': 'Tap a mood, then write — or don’t.',
      '1': 'One tap is enough to start.',
    },
  },
  moodPhrase: {
    lateNight: {
      '1': 'Heavy night. That’s okay.',
      '2': 'A bit rough around the edges.',
      '3': 'Somewhere in the middle.',
      '4': 'Pretty good, for this hour.',
      '5': 'Light, even this late.',
    },
    morning: {
      '1': 'A hard morning. That’s okay.',
      '2': 'A bit rough around the edges.',
      '3': 'Somewhere in the middle.',
      '4': 'I feel pretty good this morning.',
      '5': 'Light, bright start.',
    },
    midday: {
      '1': 'Midday feels heavy. That’s okay.',
      '2': 'A bit off, around noon.',
      '3': 'Somewhere in the middle.',
      '4': 'I feel pretty good right now.',
      '5': 'Feeling good in the middle of the day.',
    },
    afternoon: {
      '1': 'A hard afternoon. That’s okay.',
      '2': 'A bit rough around the edges.',
      '3': 'Somewhere in the middle.',
      '4': 'I feel pretty good this afternoon.',
      '5': 'Light, bright, alive.',
    },
    evening: {
      '1': 'A heavy evening. That’s okay.',
      '2': 'A bit rough around the edges.',
      '3': 'Somewhere in the middle.',
      '4': 'I feel pretty good this evening.',
      '5': 'Light, bright evening.',
    },
    night: {
      '1': 'Heavy night. That’s okay.',
      '2': 'A bit rough around the edges.',
      '3': 'Somewhere in the middle.',
      '4': 'Pretty good, tonight.',
      '5': 'Light tonight.',
    },
  },
}

export const companionRu: CompanionMessages = {
  greeting: {
    lateNight: {
      '0': 'Ещё не спишь? Можно оставить пару слов.',
      '1': 'Сейчас тихо. Можно просто написать пару слов.',
      '2': 'Поздняя заметка — тоже нормально, даже короткая.',
    },
    morning: {
      '0': 'Доброе утро.',
      '1': 'Новый день. Можно начать, когда захочется.',
      '2': 'Как утро?',
    },
    midday: {
      '0': 'Как день идёт?',
      '1': 'Середина дня. Хочешь что-нибудь записать?',
      '2': 'Обед. Как ты?',
    },
    afternoon: {
      '0': 'Как там день?',
      '1': 'Как идёт день?',
      '2': 'Короткой записи вполне хватит.',
    },
    evening: {
      '0': 'Вечер. Как прошёл день?',
      '1': 'День потихоньку заканчивается.',
      '2': 'Хочешь оставить пару слов про сегодня?',
    },
    night: {
      '0': 'День почти кончился.',
      '1': 'Последняя заметка — если хочется.',
      '2': 'Как ты сегодня вечером?',
    },
  },
  kicker: {
    lateNight: {
      '0': 'Пары слов хватит.',
      '1': 'Это только твоё.',
    },
    morning: {
      '0': 'Короткой заметки хватит.',
      '1': 'Можно начать с малого.',
    },
    midday: {
      '0': 'Много писать не нужно.',
      '1': 'Минуты достаточно.',
    },
    afternoon: {
      '0': 'Пары строк хватит.',
      '1': 'Как есть — и ладно.',
    },
    evening: {
      '0': 'Пары слов хватит.',
      '1': 'Просто как было.',
    },
    night: {
      '0': 'На сегодня хватит.',
      '1': 'Последняя заметка — если хочется.',
    },
  },
  howAreYou: {
    lateNight: {
      '0': 'Как ты в этот час?',
      '1': 'Ещё не спишь? Как ты?',
      '2': 'Как ты так поздно?',
    },
    morning: {
      '0': 'Как ты сегодня утром?',
      '1': 'Как началось утро?',
      '2': 'Ну что, какое утро?',
    },
    midday: {
      '0': 'Как ты сейчас?',
      '1': 'Как ты в середине дня?',
      '2': 'Ну что, как оно?',
    },
    afternoon: {
      '0': 'Как ты после обеда?',
      '1': 'Как день идёт?',
      '2': 'Как ты к этому часу?',
    },
    evening: {
      '0': 'Как ты сегодня вечером?',
      '1': 'Как прошёл день?',
      '2': 'Ну что, как ты к вечеру?',
    },
    night: {
      '0': 'Как ты сегодня вечером?',
      '1': 'Как прошёл день?',
      '2': 'Уже поздно. Как ты?',
    },
  },
  pickMoodHint: {
    lateNight: {
      '0': 'Просто выбери, как есть. Остальное подождёт.',
      '1': 'Одного настроения пока хватит.',
    },
    morning: {
      '0': 'Сначала настроение — остальное появится ниже.',
      '1': 'Начни с того, как ты.',
    },
    midday: {
      '0': 'Нажми, как ты. Остальное подождёт.',
      '1': 'Сначала настроение, потом можно добавить остальное.',
    },
    afternoon: {
      '0': 'Выбери то, что ближе.',
      '1': 'Сначала настроение — остальное появится ниже.',
    },
    evening: {
      '0': 'Выбери настроение на вечер.',
      '1': 'Начни с того, как прошёл день.',
    },
    night: {
      '0': 'Одного нажатия хватит.',
      '1': 'Сначала настроение.',
    },
  },
  whatsOnYourMind: {
    lateNight: {
      '0': 'Пара слов',
      '1': 'Что на уме',
    },
    morning: {
      '0': 'Пара слов',
      '1': 'Про утро',
    },
    midday: {
      '0': 'Пара слов',
      '1': 'Сейчас',
    },
    afternoon: {
      '0': 'Пара слов',
      '1': 'Что на уме',
    },
    evening: {
      '0': 'Пара слов',
      '1': 'Про сегодня',
    },
    night: {
      '0': 'Пара слов',
      '1': 'На вечер',
    },
  },
  notePlaceholder: {
    lateNight: {
      '0': 'Что ещё на уме…',
      '1': 'Даже одного предложения хватит…',
    },
    morning: {
      '0': 'Как идёт утро…',
      '1': 'Пара слов про утро…',
    },
    midday: {
      '0': 'Что у тебя на уме…',
      '1': 'Мысль откуда-то с обеда…',
    },
    afternoon: {
      '0': 'Что у тебя на уме…',
      '1': 'Пары строк хватит…',
    },
    evening: {
      '0': 'Как прошёл день…',
      '1': 'Пара слов про сегодня…',
    },
    night: {
      '0': 'Последняя мысль…',
      '1': 'Сегодняшний вечер в нескольких словах…',
    },
  },
  whatHappened: {
    lateNight: {
      '0': 'Что сегодня было?',
      '1': 'Что ещё осталось с дня?',
    },
    morning: {
      '0': 'Что уже было утром?',
      '1': 'Что уже успело случиться?',
    },
    midday: {
      '0': 'Что было до сих пор?',
      '1': 'Что было за первую половину дня?',
    },
    afternoon: {
      '0': 'Что сегодня было?',
      '1': 'Что было днём?',
    },
    evening: {
      '0': 'Что сегодня было?',
      '1': 'Что ушло с тобой в вечер?',
    },
    night: {
      '0': 'Что сегодня было?',
      '1': 'Что осталось с сегодня?',
    },
  },
  contextLead: {
    lateNight: {
      '0': 'Можно отметить — или пропустить. Оба варианта нормальны.',
      '1': 'Пары тегов хватит, если писать не хочется.',
    },
    morning: {
      '0': 'Дождь, друзья, зал — что уже окрасило утро.',
      '1': 'Только если хочется.',
    },
    midday: {
      '0': 'Дождь, друзья, зал — отметь то, что уже окрасило день.',
      '1': 'Можно пропустить, если не хочется.',
    },
    afternoon: {
      '0': 'Дождь, друзья, зал — отметь то, что окрасило день.',
      '1': 'Не обязательно всё — только то, что запомнилось.',
    },
    evening: {
      '0': 'Дождь, друзья, зал — отметь то, что окрасило день.',
      '1': 'Отметь важное, если хочется.',
    },
    night: {
      '0': 'Дождь, друзья, зал — отметь то, что окрасило день.',
      '1': 'Только если хочется.',
    },
  },
  goals: {
    lateNight: {
      '0': 'Какие цели на сегодня?',
      '1': 'Есть что отметить в этот час?',
    },
    morning: {
      '0': 'Какие цели с утра?',
      '1': 'Какие цели уже с утра?',
    },
    midday: {
      '0': 'Что-то из целей уже отмечено?',
      '1': 'Есть что отметить к середине дня?',
    },
    afternoon: {
      '0': 'Какие цели уже закрыты днём?',
      '1': 'Какие цели на сегодня?',
    },
    evening: {
      '0': 'Какие цели на сегодня?',
      '1': 'Есть привычки, которые хочется отметить?',
    },
    night: {
      '0': 'Какие цели на сегодня?',
      '1': 'Есть что отметить за сегодня?',
    },
  },
  emptyMonth: {
    lateNight: {
      '0': 'В этом месяце записей пока нет. Можно начать сегодня ночью.',
      '1': 'Записей пока нет. Первую можно оставить, когда захочется.',
    },
    morning: {
      '0': 'В этом месяце ещё тихо. Утро — нормальное время начать.',
      '1': 'Пока пусто. Одного настроения хватит, чтобы открыть месяц.',
    },
    midday: {
      '0': 'В этом месяце ещё нет записей. Дневная заметка его откроет.',
      '1': 'В этом месяце ещё пусто. Можно начать сейчас.',
    },
    afternoon: {
      '0': 'Записей в этом месяце ещё нет. День — самое обычное время начать.',
      '1': 'Пока пусто. Не нужно догонять — можно просто начать.',
    },
    evening: {
      '0': 'В этом месяце записей пока нет. Вечер — хорошее время начать.',
      '1': 'Месяц пока тихий. Можно начать сегодня вечером.',
    },
    night: {
      '0': 'В этом месяце ещё пусто. Ночная заметка тоже считается.',
      '1': 'В этом месяце ещё пусто. Одной строки хватит, чтобы начать.',
    },
  },
  emptyPrompt: {
    lateNight: {
      '0': 'Выбери настроение, когда захочется.',
      '1': 'Начни с того, как ты.',
    },
    morning: {
      '0': 'Начни с настроения.',
      '1': 'Выбери, как ты этим утром.',
    },
    midday: {
      '0': 'Выбери настроение на сейчас.',
      '1': 'Начни с того, как ты.',
    },
    afternoon: {
      '0': 'Выбери, как ты сейчас.',
      '1': 'Одного настроения хватит для первой записи.',
    },
    evening: {
      '0': 'Выбери настроение на вечер.',
      '1': 'Начни с того, как прошёл день.',
    },
    night: {
      '0': 'Выбери настроение — а дальше можно писать или нет.',
      '1': 'Одного нажатия хватит, чтобы начать.',
    },
  },
  moodPhrase: {
    lateNight: {
      '1': 'Тяжёлая ночь. Так тоже бывает.',
      '2': 'Немного не в своей тарелке.',
      '3': 'Где-то посередине.',
      '4': 'Для такого часа — вполне хорошо.',
      '5': 'Легко, даже так поздно.',
    },
    morning: {
      '1': 'Тяжёлое утро. Так тоже бывает.',
      '2': 'Немного не в своей тарелке.',
      '3': 'Где-то посередине.',
      '4': 'Сегодня утром довольно хорошо.',
      '5': 'Легко, ярко, с самого утра.',
    },
    midday: {
      '1': 'Тяжёлая середина дня. Так тоже бывает.',
      '2': 'Немного не в своей тарелке.',
      '3': 'Где-то посередине.',
      '4': 'Сейчас довольно хорошо.',
      '5': 'В середине дня легко и хорошо.',
    },
    afternoon: {
      '1': 'Тяжёлый день. Так тоже бывает.',
      '2': 'Немного не в своей тарелке.',
      '3': 'Где-то посередине.',
      '4': 'Сегодня довольно хорошо.',
      '5': 'Легко, ярко, живо.',
    },
    evening: {
      '1': 'Тяжёлый вечер. Так тоже бывает.',
      '2': 'Немного не в своей тарелке.',
      '3': 'Где-то посередине.',
      '4': 'Сегодня вечером довольно хорошо.',
      '5': 'Легко, ярко, к вечеру.',
    },
    night: {
      '1': 'Тяжёлая ночь. Так тоже бывает.',
      '2': 'Немного не в своей тарелке.',
      '3': 'Где-то посередине.',
      '4': 'Сегодня вечером довольно хорошо.',
      '5': 'Легко сегодня вечером.',
    },
  },
}
