import { Link, Outlet } from 'react-router-dom'

export function AuthCardLayout() {
  return (
    <div className="auth-card">
      <Outlet />
    </div>
  )
}

export function AuthFooterLink({ to, children }: { to: string; children: string }) {
  return (
    <p className="auth-footer">
      <Link to={to}>{children}</Link>
    </p>
  )
}
