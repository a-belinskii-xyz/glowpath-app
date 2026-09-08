export type TelegramLinkPublic = {
  linked: boolean
  telegram_user_id: number | null
  telegram_linked_at: string | null
  bot_username: string | null
  bot_configured: boolean
  can_unlink?: boolean
}

export type TelegramLinkCodeCreateResponse = {
  code: string
  expires_at: string
  deep_link: string
}

export type TelegramEntryPointPublic = {
  bot_username: string | null
  bot_url: string | null
}
