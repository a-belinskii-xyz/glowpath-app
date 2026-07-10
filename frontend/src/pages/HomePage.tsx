import { Link } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { EntriesPage } from './EntriesPage'

export function HomePage() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <section className="page">
        <p className="muted">Loading…</p>
      </section>
    )
  }

  if (isAuthenticated) {
    return <EntriesPage />
  }

  return (
    <section className="page">
      <h1>Mood Tracker</h1>
      <p className="lead">Track your mood day by day.</p>
      <div className="button-row">
        <Link className="button" to="/login">
          Log in
        </Link>
        <Link className="button button-secondary" to="/register">
          Create account
        </Link>
      </div>
    </section>
  )
}
