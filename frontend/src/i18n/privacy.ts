import type { ApiLocale } from '../lib/locale'

/** Where people send questions about their data. Change it here only. */
export const PRIVACY_CONTACT_EMAIL = 'a.belinskii.xyz@gmail.com'

/** Bump when the text below changes. */
export const PRIVACY_UPDATED_ON = '2026-10-01'

export type PrivacySection = {
  title: string
  paragraphs?: string[]
  items?: string[]
}

export type PrivacyPolicy = {
  title: string
  updated: string
  intro: string[]
  sections: PrivacySection[]
  contact: string
}

const ru: PrivacyPolicy = {
  title: 'Политика конфиденциальности',
  updated: 'Обновлено',
  intro: [
    'GlowPath — личный дневник настроения. Здесь коротко и честно о том, какие данные мы храним, зачем и как ими управлять.',
    'Дневник — это ваши записи. Мы не продаём их, не показываем рекламу и не используем записи для обучения сторонних моделей.',
  ],
  sections: [
    {
      title: 'Какие данные мы храним',
      items: [
        'Аккаунт: email и хэш пароля (если вы регистрируетесь по почте), идентификатор Google (если входите через Google), идентификатор пользователя и чата Telegram (если входите или привязываете Telegram), часовой пояс, язык и тема оформления.',
        'Дневник: записи настроения, заметки, теги, цели, шаблоны заметок, отметки «избранное», фото и голосовые заметки, которые вы прикрепляете.',
        'Настройки напоминаний: каналы, время и расписание.',
        'Технические данные: cookie входа, случайный идентификатор посетителя в cookie и хэш простых признаков браузера (часовой пояс, размер экрана, платформа) — чтобы узнавать того же посетителя в экспериментах интерфейса. Хостинг хранит журналы запросов (IP-адрес, время, адрес страницы) для работы и защиты сервиса.',
        'В браузере (localStorage и IndexedDB) хранятся язык, черновики записей и, в гостевом режиме, сам гостевой дневник до регистрации.',
      ],
    },
    {
      title: 'Зачем',
      items: [
        'Чтобы показывать ваш дневник, статистику и подсказки на любом устройстве после входа.',
        'Чтобы отправлять напоминания, которые вы включили, в Telegram или на почту.',
        'Чтобы отправлять служебные письма: подтверждение почты и сброс пароля.',
        'Чтобы поддерживать работу и безопасность сервиса.',
      ],
    },
    {
      title: 'Кто ещё участвует в обработке',
      paragraphs: [
        'Мы пользуемся сторонними сервисами только для работы GlowPath:',
      ],
      items: [
        'облачный хостинг приложения и база данных (серверы в Европейском союзе);',
        'объектное хранилище для фото и голосовых заметок;',
        'почтовый сервис для отправки писем;',
        'Telegram — если вы пользуетесь ботом или Mini App: через него приходят напоминания, картинки заметок и архивы экспорта, которые вы сами запросили;',
        'Google — если вы входите через Google.',
      ],
    },
    {
      title: 'Ваши данные под вашим контролем',
      items: [
        'Экспорт: «Настройки → Аккаунт → Скачать дневник» (ZIP с записями, фото и голосовыми). В Telegram архив можно получить в чат.',
        'Удаление: «Настройки → Аккаунт → Удалить аккаунт» сразу удаляет аккаунт, записи и файлы. Резервные копии у провайдеров могут хранить данные ещё ограниченное время, после чего они удаляются.',
        'Отдельную запись, фото или заметку можно удалить в любой момент.',
      ],
    },
    {
      title: 'Изменения',
      paragraphs: [
        'Если политика изменится, мы обновим эту страницу и дату вверху.',
      ],
    },
  ],
  contact: 'Вопросы о данных — пишите на',
}

const en: PrivacyPolicy = {
  title: 'Privacy policy',
  updated: 'Updated',
  intro: [
    'GlowPath is a personal mood diary. This page explains, briefly and plainly, what data we keep, why, and how you control it.',
    'Your diary is yours. We do not sell it, show ads, or use your entries to train third-party models.',
  ],
  sections: [
    {
      title: 'What we keep',
      items: [
        'Account: email and a password hash (if you sign up by email), your Google ID (if you sign in with Google), your Telegram user and chat IDs (if you sign in with or link Telegram), time zone, language and theme.',
        'Diary: mood entries, notes, tags, goals, note templates, favourites, and the photos and voice notes you attach.',
        'Reminder settings: channels, times and schedule.',
        'Technical data: sign-in cookies, a random visitor ID in a cookie, and a hash of simple browser signals (time zone, screen size, platform) to recognise the same visitor in interface experiments. Our hosting keeps request logs (IP address, time, page) to run and protect the service.',
        'Your browser (localStorage and IndexedDB) keeps your language, entry drafts and, in guest mode, the guest diary itself until you sign up.',
      ],
    },
    {
      title: 'Why',
      items: [
        'To show your diary, stats and insights on any device after you sign in.',
        'To send the reminders you turned on, in Telegram or by email.',
        'To send service emails: email confirmation and password reset.',
        'To keep the service running and secure.',
      ],
    },
    {
      title: 'Who else is involved',
      paragraphs: ['We use third-party services only to run GlowPath:'],
      items: [
        'cloud hosting for the app and the database (servers in the European Union);',
        'object storage for photos and voice notes;',
        'an email service to send emails;',
        'Telegram, if you use the bot or the Mini App: reminders, note images and the exports you request arrive through it;',
        'Google, if you sign in with Google.',
      ],
    },
    {
      title: 'You stay in control',
      items: [
        'Export: Settings → Account → Download my diary (a ZIP with entries, photos and voice notes). In Telegram you can get the archive in your chat.',
        'Deletion: Settings → Account → Delete account removes the account, entries and files right away. Provider backups may keep data for a limited time before it is erased.',
        'You can delete any single entry, photo or note at any time.',
      ],
    },
    {
      title: 'Changes',
      paragraphs: ['If this policy changes, we will update this page and the date at the top.'],
    },
  ],
  contact: 'Questions about your data? Write to',
}

export function privacyPolicy(locale: ApiLocale): PrivacyPolicy {
  return locale === 'ru' ? ru : en
}
