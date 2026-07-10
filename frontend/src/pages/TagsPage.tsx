import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { listTagGroups } from '../api/tagGroups'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { ApiError } from '../lib/errors'
import type { TagGroupPublic } from '../types/tag'

export function TagsPage() {
  const [groups, setGroups] = useState<TagGroupPublic[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const response = await listTagGroups()
        setGroups(response.items)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError('Verify your email to view tags.')
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load tags')
        }
      } finally {
        setIsLoading(false)
      }
    }
    void load()
  }, [])

  return (
    <section className="page">
      <EmailVerificationBanner />

      <header className="page-header">
        <h1>Tags</h1>
        {/* TODO: implement when tag CRUD API exists */}
        <button type="button" className="button" disabled title="TODO: tag CRUD API">
          Add group
        </button>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {isLoading ? <p className="muted">Loading tags…</p> : null}

      <div className="tag-groups-list">
        {groups.map((group) => (
          <article key={group.id} className="card tag-group-card">
            <header className="tag-group-card-header">
              <h2>{group.label}</h2>
              <div className="button-row">
                {/* TODO: implement when tag CRUD API exists */}
                <button type="button" className="button button-secondary button-small" disabled title="TODO: tag CRUD API">
                  Add tag
                </button>
                <button type="button" className="button button-secondary button-small" disabled title="TODO: tag CRUD API">
                  Edit
                </button>
                <button type="button" className="button button-danger button-small" disabled title="TODO: tag CRUD API">
                  Delete
                </button>
              </div>
            </header>
            <ul className="tag-list">
              {group.tags.map((tag) => (
                <li key={tag.id}>
                  <span>{tag.label}</span>
                  <code className="muted">{tag.slug}</code>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>

      <p className="muted">
        <Link to="/">Back to entries</Link>
      </p>
    </section>
  )
}
