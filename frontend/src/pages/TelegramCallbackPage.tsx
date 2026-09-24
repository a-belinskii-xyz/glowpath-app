import { OAuthCallbackPage } from './OAuthCallbackPage'

export function TelegramCallbackPage() {
  return (
    <OAuthCallbackPage
      titleKey="auth.telegramTitle"
      completingKey="auth.telegramCompleting"
      missingTokensKey="errors.telegramNoTokens"
      failedKey="errors.telegramFailed"
    />
  )
}
