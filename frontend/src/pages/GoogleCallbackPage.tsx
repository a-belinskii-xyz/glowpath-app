import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Alert } from '../components/Alert'
import { useAuth } from '../context/AuthContext'

function parseHashTokens(): { accessToken: string; refreshToken: string } | null {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const accessToken = params.get('access_token')
  const refreshToken = params.get('refresh_token')

  if (!accessToken || !refreshToken) {
    return null
  }

  return { accessToken, refreshToken }
}

export function GoogleCallbackPage() {
  const navigate = useNavigate()
  const { completeLogin } = useAuth()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const tokens = parseHashTokens()
    if (!tokens) {
      setError('Google sign-in did not return tokens')
      return
    }

    const run = async () => {
      try {
        await completeLogin(tokens.accessToken, tokens.refreshToken)
        navigate('/profile', { replace: true })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Google sign-in failed')
      }
    }

    void run()
  }, [completeLogin, navigate])

  return (
    <section className="page narrow">
      <h1>Google sign-in</h1>
      {error ? <Alert variant="error">{error}</Alert> : <p className="muted">Completing sign-in…</p>}
    </section>
  )
}
