import { useLocale } from '../context/LocaleContext'
import { PRIVACY_CONTACT_EMAIL, PRIVACY_UPDATED_ON, privacyPolicy } from '../i18n/privacy'
import { intlLocale } from '../i18n/t'

export function PrivacyPage() {
  const { locale } = useLocale()
  const policy = privacyPolicy(locale)
  const updatedOn = new Intl.DateTimeFormat(intlLocale(locale), { dateStyle: 'long' }).format(
    new Date(`${PRIVACY_UPDATED_ON}T00:00:00`),
  )

  return (
    <section className="page page-privacy">
      <header className="page-header">
        <h1>{policy.title}</h1>
      </header>
      <div className="card privacy-body">
        <p className="muted">
          {policy.updated}: {updatedOn}
        </p>
        {policy.intro.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
        {policy.sections.map((section) => (
          <section key={section.title}>
            <h2>{section.title}</h2>
            {section.paragraphs?.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            {section.items ? (
              <ul>
                {section.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
        <p>
          {policy.contact}{' '}
          <a href={`mailto:${PRIVACY_CONTACT_EMAIL}`}>{PRIVACY_CONTACT_EMAIL}</a>
        </p>
      </div>
    </section>
  )
}
