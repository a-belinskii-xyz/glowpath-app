import { useAuth } from '../context/AuthContext'

function formatDate(value: string | null): string {
  if (!value) {
    return '—'
  }
  return new Date(value).toLocaleString()
}

export function ProfilePage() {
  const { user, refreshUser } = useAuth()

  if (!user) {
    return null
  }

  return (
    <section className="page">
      <div className="page-header">
        <h1>Profile</h1>
        <button type="button" className="button button-secondary" onClick={() => void refreshUser()}>
          Refresh
        </button>
      </div>

      <dl className="profile-list">
        <div>
          <dt>Email</dt>
          <dd>{user.email}</dd>
        </div>
        <div>
          <dt>User ID</dt>
          <dd>
            <code>{user.id}</code>
          </dd>
        </div>
        <div>
          <dt>Timezone</dt>
          <dd>{user.timezone}</dd>
        </div>
        <div>
          <dt>Email verified</dt>
          <dd>{user.email_verified ? 'Yes' : 'No'}</dd>
        </div>
        <div>
          <dt>Verified at</dt>
          <dd>{formatDate(user.email_verified_at)}</dd>
        </div>
      </dl>
    </section>
  )
}
