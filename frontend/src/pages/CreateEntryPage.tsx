import { Link } from 'react-router-dom'

import { MoodEntryForm } from '../components/MoodEntryForm'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'

export function CreateEntryPage() {
  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>New mood entry</h1>
        <Link className="button button-secondary" to="/">
          Back to entries
        </Link>
      </header>
      <MoodEntryForm mode="create" />
    </section>
  )
}
