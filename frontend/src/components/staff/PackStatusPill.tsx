import { useLocale } from '../../context/LocaleContext'

const TONE: Record<string, string> = {
  published: 'status-pill--ok',
  rejected: 'status-pill--warn',
}

export function PackStatusPill({ status }: { status: string }) {
  const { t } = useLocale()
  return (
    <span className={`status-pill status-pill--sm ${TONE[status] ?? 'status-pill--muted'}`}>
      {t(`staff.status.${status}`)}
    </span>
  )
}
