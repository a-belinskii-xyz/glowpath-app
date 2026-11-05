import './instrument'

import * as Sentry from '@sentry/react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'
import { CrashFallback } from './components/CrashFallback'
import { initAppTheme } from './design/appTheme'
import { rememberSignupSourceFromUrl } from './lib/signupSource'
import { applyTelegramChrome } from './platform/telegram'
import './index.css'

applyTelegramChrome()
rememberSignupSourceFromUrl()
initAppTheme()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Sentry.ErrorBoundary fallback={<CrashFallback />}>
      <App />
    </Sentry.ErrorBoundary>
  </StrictMode>,
)
