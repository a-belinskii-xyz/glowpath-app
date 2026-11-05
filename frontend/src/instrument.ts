import { useEffect } from 'react'
import {
  createRoutesFromChildren,
  matchRoutes,
  useLocation,
  useNavigationType,
} from 'react-router-dom'
import * as Sentry from '@sentry/react'

// Imported first in main.tsx so errors during boot are captured too.
// No DSN (local dev without .env) leaves the SDK disabled. A broken init must
// not block the app from booting, so failures only reach the console.
try {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE,
    release: import.meta.env.VITE_SENTRY_RELEASE || undefined,

    integrations: [
      Sentry.reactRouterV6BrowserTracingIntegration({
        useEffect,
        useLocation,
        useNavigationType,
        createRoutesFromChildren,
        matchRoutes,
      }),
    ],

    // API calls go to same-origin /v1, which the SDK traces by default.
    // `||`, not `??`: an empty variable must not turn into Number('') === 0.
    tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || 0.2),
  })
} catch (error) {
  console.error('Sentry init failed; running without it', error)
}
