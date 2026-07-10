import { Link } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

export function HomePage() {
  const { isAuthenticated, user } = useAuth()

  return (
    <section className="page">
      <h1>Mood Tracker</h1>
      <p className="lead">
        Track your mood day by day. Auth flows are wired up; mood entries come next.
      </p>

      {isAuthenticated && user ? (
        <div className="card">
          <p>
            Signed in as <strong>{user.email}</strong>
          </p>
          <Link className="button" to="/profile">
            View profile
          </Link>
        </div>
      ) : (
        <div className="button-row">
          <Link className="button" to="/login">
            Log in
          </Link>
          <Link className="button button-secondary" to="/register">
            Create account
          </Link>
        </div>
      )}
    </section>
  )
}
