import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { sentryVitePlugin } from '@sentry/vite-plugin'

export default defineConfig(({ mode }) => {
  // '' prefix: also read non-VITE_ vars (SENTRY_AUTH_TOKEN) from env and .env files.
  const env = loadEnv(mode, '.', '')
  // Source maps go to Sentry only, never to the nginx image. Without an auth
  // token (local builds) the plugin is skipped and nothing is uploaded.
  const sentryAuthToken = env.SENTRY_AUTH_TOKEN

  return {
    build: {
      sourcemap: sentryAuthToken ? 'hidden' : false,
    },
    plugins: [
      react(),
      !!sentryAuthToken &&
        sentryVitePlugin({
          org: 'andrei-belinskii',
          project: 'glowpath-web',
          url: 'https://de.sentry.io',
          authToken: sentryAuthToken,
          // Must match the release the SDK tags events with (instrument.ts).
          release: { name: env.VITE_SENTRY_RELEASE || undefined },
          sourcemaps: { filesToDeleteAfterUpload: ['./dist/**/*.map'] },
        }),
    ],
    server: {
      host: true,
      // HTTPS tunnels (cloudflared / ngrok) send a public Host header; Vite 6 blocks it otherwise.
      allowedHosts: ['.trycloudflare.com', '.ngrok-free.app', '.ngrok.io', '.loca.lt'],
      proxy: {
        '/v1': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
