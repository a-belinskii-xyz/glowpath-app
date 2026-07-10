import { Link, Outlet } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

export function Layout() {
  const { isAuthenticated, logout } = useAuth()

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand">
          Mood Tracker
        </Link>
        <nav className="nav-links">
          {isAuthenticated ? (
            <>
              <Link to="/profile">Profile</Link>
              <button type="button" className="link-button" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login">Log in</Link>
              <Link to="/register">Register</Link>
            </>
          )}
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
