import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'
import { initAppTheme } from './design/appTheme'
import { rememberSignupSourceFromUrl } from './lib/signupSource'
import { applyTelegramChrome } from './platform/telegram'
import './index.css'

applyTelegramChrome()
rememberSignupSourceFromUrl()
initAppTheme()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
