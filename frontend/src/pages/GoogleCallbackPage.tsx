import { OAuthCallbackPage } from './OAuthCallbackPage'

export function GoogleCallbackPage() {
  return (
    <OAuthCallbackPage
      titleKey="auth.googleTitle"
      completingKey="auth.googleCompleting"
      missingTokensKey="errors.googleNoTokens"
      failedKey="errors.googleFailed"
    />
  )
}
