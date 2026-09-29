import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { listStaffPacks } from '../../api/marketplace'
import { createStaffPack } from '../../api/staff'
import { useLocale } from '../../context/LocaleContext'
import { formatApiError } from '../../lib/errors'
import type { PackCardPublic } from '../../types/marketplace'
import { PageErrorAlert } from '../PageErrorAlert'
import { StaffPackEditor } from './StaffPackEditor'
import { PackStatusPill } from './PackStatusPill'

const STATUS_FILTERS = ['', 'draft', 'pending_review', 'published', 'rejected', 'archived'] as const

type PackForm = {
  nameEn: string
  nameRu: string
  descriptionEn: string
  descriptionRu: string
  slug: string
  price: string
  sortOrder: string
}

const EMPTY_FORM: PackForm = {
  nameEn: '',
  nameRu: '',
  descriptionEn: '',
  descriptionRu: '',
  slug: '',
  price: '0',
  sortOrder: '100',
}

export function StaffPacksPanel() {
  const { t } = useLocale()
  const [status, setStatus] = useState<string>('')
  const [packs, setPacks] = useState<PackCardPublic[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [openPackId, setOpenPackId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<PackForm>(EMPTY_FORM)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await listStaffPacks({ status: status || undefined, limit: 100 })
      setPacks(response.items)
      setError(null)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedLoadMarket'))
    } finally {
      setIsLoading(false)
    }
  }, [status, t])

  useEffect(() => {
    void reload()
  }, [reload])

  const update = (field: keyof PackForm) => (value: string) =>
    setForm((current) => ({ ...current, [field]: value }))

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault()
    if (isCreating) return
    setIsCreating(true)
    setError(null)
    const nameRu = form.nameRu.trim() || form.nameEn.trim()
    const descriptionEn = form.descriptionEn.trim()
    const descriptionRu = form.descriptionRu.trim() || descriptionEn
    try {
      const pack = await createStaffPack({
        labels: {
          name: { en: form.nameEn.trim(), ru: nameRu },
          description: descriptionEn ? { en: descriptionEn, ru: descriptionRu } : null,
        },
        slug: form.slug.trim() || null,
        price_tokens: Math.max(0, Number.parseInt(form.price, 10) || 0),
        sort_order: Number.parseInt(form.sortOrder, 10) || 0,
      })
      setForm(EMPTY_FORM)
      setShowCreate(false)
      setOpenPackId(pack.id)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsCreating(false)
    }
  }

  if (openPackId) {
    return (
      <StaffPackEditor
        packId={openPackId}
        onBack={() => {
          setOpenPackId(null)
          void reload()
        }}
      />
    )
  }

  const textField = (field: keyof PackForm, label: string, props: { required?: boolean } = {}) => (
    <label className="form-field" htmlFor={`staff-pack-${field}`}>
      <span className="form-label">{label}</span>
      <input
        id={`staff-pack-${field}`}
        className="form-input"
        value={form[field]}
        maxLength={200}
        onChange={(event) => update(field)(event.target.value)}
        {...props}
      />
    </label>
  )

  return (
    <div className="staff-panel">
      <PageErrorAlert error={error} />
      <div className="staff-toolbar">
        <div className="staff-chip-row" role="toolbar">
          {STATUS_FILTERS.map((value) => (
            <button
              key={value || 'all'}
              type="button"
              className={`market-tag-chip${status === value ? ' is-active' : ''}`}
              onClick={() => setStatus(value)}
            >
              {value ? t(`staff.status.${value}`) : t('staff.statusAll')}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="button button-small"
          onClick={() => setShowCreate((current) => !current)}
          aria-expanded={showCreate}
        >
          {t('staff.newPack')}
        </button>
      </div>

      {showCreate ? (
        <form className="card form staff-card staff-form-grid" onSubmit={handleCreate}>
          {textField('nameEn', t('staff.nameEn'), { required: true })}
          {textField('nameRu', t('staff.nameRu'))}
          {textField('descriptionEn', t('staff.descriptionEn'))}
          {textField('descriptionRu', t('staff.descriptionRu'))}
          <label className="form-field" htmlFor="staff-pack-slug">
            <span className="form-label">{t('staff.slug')}</span>
            <input
              id="staff-pack-slug"
              className="form-input"
              value={form.slug}
              maxLength={64}
              pattern="[a-z][a-z0-9-]*"
              onChange={(event) => update('slug')(event.target.value)}
            />
            <span className="form-hint">{t('staff.slugHint')}</span>
          </label>
          <label className="form-field" htmlFor="staff-pack-price">
            <span className="form-label">{t('staff.price')}</span>
            <input
              id="staff-pack-price"
              className="form-input"
              type="number"
              min={0}
              value={form.price}
              onChange={(event) => update('price')(event.target.value)}
            />
            <span className="form-hint">{t('staff.priceHint')}</span>
          </label>
          <label className="form-field" htmlFor="staff-pack-sort">
            <span className="form-label">{t('staff.sortOrder')}</span>
            <input
              id="staff-pack-sort"
              className="form-input"
              type="number"
              value={form.sortOrder}
              onChange={(event) => update('sortOrder')(event.target.value)}
            />
          </label>
          <div className="staff-form-actions">
            <button type="submit" className="button" disabled={isCreating}>
              {isCreating ? t('staff.creatingPack') : t('staff.createPack')}
            </button>
          </div>
        </form>
      ) : null}

      {isLoading ? (
        <p className="muted">{t('common.loadingMarket')}</p>
      ) : packs.length === 0 ? (
        <p className="muted">{t('staff.noPacks')}</p>
      ) : (
        <ul className="staff-list">
          {packs.map((pack) => (
            <li key={pack.id}>
              <button
                type="button"
                className="staff-list-row"
                onClick={() => setOpenPackId(pack.id)}
              >
                <span className="staff-list-title">
                  {pack.name}
                  <PackStatusPill status={pack.status} />
                </span>
                <span className="staff-list-meta">
                  {pack.slug} · {pack.is_official ? t('staff.official') : t('staff.community')} ·{' '}
                  {t('staff.iconCount', { count: pack.icon_count })} ·{' '}
                  {pack.price_tokens > 0
                    ? t('market.priceTokens', { count: String(pack.price_tokens) })
                    : t('staff.free')}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
