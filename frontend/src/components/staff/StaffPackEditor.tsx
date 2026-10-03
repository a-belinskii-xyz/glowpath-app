import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import {
  deleteStudioIcon,
  fetchCatalogIconBlob,
  getMarketplacePack,
  getMarketplaceSearchTags,
  patchStudioIcon,
  patchStudioPack,
  publishStaffPack,
  rejectStaffPack,
  reorderStudioIcons,
  replaceStudioIconImage,
  uploadStudioIcon,
} from '../../api/marketplace'
import { archiveStaffPack, setStaffPackSort } from '../../api/staff'
import { useLocale } from '../../context/LocaleContext'
import { invalidateCatalogIcon } from '../../lib/catalogIconBlobUrl'
import { formatApiError } from '../../lib/errors'
import { readMoodIconBlobForCrop } from '../../lib/imageCrop'
import type {
  CatalogIconPublic,
  IconCrop,
  PackDetailPublic,
  SearchTagPublic,
} from '../../types/marketplace'
import { Alert } from '../Alert'
import { CatalogIconThumb } from '../CatalogIconThumb'
import { ConfirmDialog } from '../ConfirmDialog'
import { ChevronLeftIcon } from '../icons'
import { PageErrorAlert } from '../PageErrorAlert'
import { PackStatusPill } from './PackStatusPill'
import { ACCEPTED_ICON_TYPES } from './iconFields'
import { StaffIconDialog, type IconImage } from './StaffIconDialog'
import {
  draftFromIcon,
  emptyIconDraft,
  iconFieldsFromDraft,
  type IconDraft,
} from './StaffIconFields'

/** One dialog at a time: a new file from the upload queue, or an existing icon. */
type IconSession =
  | { mode: 'new'; file: File; source: IconImage; index: number; total: number }
  | { mode: 'edit'; icon: CatalogIconPublic; source: IconImage }

async function readIconImage(blob: Blob, fileName: string): Promise<IconImage | null> {
  const loaded = await readMoodIconBlobForCrop(blob)
  return 'error' in loaded ? null : { ...loaded, fileName }
}

type Details = {
  nameEn: string
  nameRu: string
  descriptionEn: string
  descriptionRu: string
  price: string
  sortOrder: string
}

function detailsFromPack(pack: PackDetailPublic): Details {
  return {
    nameEn: pack.labels.name?.en ?? pack.name,
    nameRu: pack.labels.name?.ru ?? '',
    descriptionEn: pack.labels.description?.en ?? '',
    descriptionRu: pack.labels.description?.ru ?? '',
    price: String(pack.price_tokens),
    sortOrder: String(pack.sort_order),
  }
}

export function StaffPackEditor({ packId, onBack }: { packId: string; onBack: () => void }) {
  const { t } = useLocale()
  const [pack, setPack] = useState<PackDetailPublic | null>(null)
  const [searchTags, setSearchTags] = useState<SearchTagPublic[]>([])
  const [details, setDetails] = useState<Details | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [rejectNote, setRejectNote] = useState('')

  const [fileInputKey, setFileInputKey] = useState(0)
  const [queue, setQueue] = useState<File[]>([])
  const [session, setSession] = useState<IconSession | null>(null)
  // Usage, scores, colors and tags carry over to the next file of one upload.
  const [lastDraft, setLastDraft] = useState<IconDraft | undefined>(undefined)
  const [uploadedCount, setUploadedCount] = useState(0)
  const [uploadErrors, setUploadErrors] = useState<string[]>([])
  const [pendingDelete, setPendingDelete] = useState<CatalogIconPublic | null>(null)

  const load = useCallback(async () => {
    const [detail, tagsResponse] = await Promise.all([
      getMarketplacePack(packId),
      getMarketplaceSearchTags(),
    ])
    setPack(detail)
    setDetails(detailsFromPack(detail))
    setSearchTags(tagsResponse.items)
  }, [packId])

  useEffect(() => {
    void load().catch((err) => setError(formatApiError(err, t, 'errors.failedLoadMarket')))
  }, [load, t])

  const run = async (key: string, action: () => Promise<unknown>, successMessage?: string) => {
    if (busy) return
    setBusy(key)
    setError(null)
    setNotice(null)
    try {
      await action()
      await load()
      if (successMessage) setNotice(successMessage)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setBusy(null)
    }
  }

  if (!pack || !details) {
    return (
      <div className="staff-panel">
        <PageErrorAlert error={error} />
        {error ? null : <p className="muted">{t('common.loadingMarket')}</p>}
      </div>
    )
  }

  // Staff may edit official packs in any status; community packs are moderated only.
  const editable = pack.is_official || pack.status === 'draft' || pack.status === 'rejected'

  const saveDetails = (event: FormEvent) => {
    event.preventDefault()
    const descriptionEn = details.descriptionEn.trim()
    const sortOrder = Number.parseInt(details.sortOrder, 10) || 0
    void run(
      'details',
      async () => {
        if (!editable) {
          await setStaffPackSort(pack.id, sortOrder)
          return
        }
        await patchStudioPack(pack.id, {
          labels: {
            name: { en: details.nameEn.trim(), ru: details.nameRu.trim() || details.nameEn.trim() },
            description: descriptionEn
              ? { en: descriptionEn, ru: details.descriptionRu.trim() || descriptionEn }
              : null,
          },
          price_tokens: Math.max(0, Number.parseInt(details.price, 10) || 0),
        })
        if (sortOrder !== pack.sort_order) {
          await setStaffPackSort(pack.id, sortOrder)
        }
      },
      t('staff.saved'),
    )
  }

  const closeSession = () => {
    if (session) URL.revokeObjectURL(session.source.objectUrl)
    setSession(null)
  }

  /** Opens the next readable file of the upload; files the browser can't read are reported. */
  const openNext = async (files: File[], done: number, total: number, failures: string[]) => {
    let rest = files
    while (rest.length > 0) {
      const [file, ...others] = rest
      const source = await readIconImage(file, file.name)
      if (source) {
        setQueue(others)
        setUploadErrors(failures)
        setSession({ mode: 'new', file, source, index: total - others.length, total })
        return
      }
      failures = [...failures, t('staff.uploadFailed', { file: file.name, error: t('staff.cropUnavailable') })]
      rest = others
    }
    setQueue([])
    setUploadErrors(failures)
    setSession(null)
    if (done > 0) {
      setNotice(t('staff.uploaded', { count: done }))
      await load().catch((err) => setError(formatApiError(err, t, 'errors.failedLoadMarket')))
    }
  }

  const startUpload = (files: File[]) => {
    setFileInputKey((key) => key + 1)
    if (files.length === 0) return
    setError(null)
    setNotice(null)
    setUploadedCount(0)
    setLastDraft(undefined)
    void openNext(files, 0, files.length, [])
  }

  const finishFile = (uploaded: boolean, failure?: string) => {
    if (!session || session.mode !== 'new') return
    URL.revokeObjectURL(session.source.objectUrl)
    const done = uploadedCount + (uploaded ? 1 : 0)
    setUploadedCount(done)
    void openNext(queue, done, session.total, failure ? [...uploadErrors, failure] : uploadErrors)
  }

  const saveNew = async (draft: IconDraft, crop: IconCrop) => {
    if (!session || session.mode !== 'new' || busy) return
    setBusy('upload')
    setLastDraft(draft)
    try {
      const icon = await uploadStudioIcon(pack.id, session.file, iconFieldsFromDraft(draft))
      await patchStudioIcon(icon.id, { crop })
      finishFile(true)
    } catch (err) {
      setError(
        t('staff.uploadFailed', {
          file: session.file.name,
          error: formatApiError(err, t, 'errors.requestFailed'),
        }),
      )
    } finally {
      setBusy(null)
    }
  }

  const stopUpload = () => {
    closeSession()
    setQueue([])
    if (uploadedCount > 0) {
      setNotice(t('staff.uploaded', { count: uploadedCount }))
      void load().catch((err) => setError(formatApiError(err, t, 'errors.failedLoadMarket')))
    }
  }

  const openIcon = (icon: CatalogIconPublic) =>
    void run('icon-load', async () => {
      const { blob } = await fetchCatalogIconBlob(icon.id)
      const source = await readIconImage(blob, icon.slug)
      if (!source) {
        setError(t('staff.cropUnavailable'))
        return
      }
      setSession({ mode: 'edit', icon, source })
    })

  const saveEdit = (icon: CatalogIconPublic, draft: IconDraft, crop: IconCrop | null) =>
    run(
      'icon',
      async () => {
        await patchStudioIcon(icon.id, {
          ...iconFieldsFromDraft(draft),
          ...(crop ? { crop } : { clear_crop: true }),
        })
        invalidateCatalogIcon(icon.id)
        closeSession()
      },
      t('staff.iconSaved'),
    )

  const replaceFile = (icon: CatalogIconPublic, file: File | undefined) => {
    if (!file) return
    void run('replace', async () => {
      await replaceStudioIconImage(icon.id, file)
      invalidateCatalogIcon(icon.id)
      closeSession()
    })
  }

  const moveIcon = (index: number, delta: number) => {
    const ids = pack.icons.map((icon) => icon.id)
    const target = index + delta
    if (target < 0 || target >= ids.length) return
    ;[ids[index], ids[target]] = [ids[target], ids[index]]
    void run('order', () => reorderStudioIcons(pack.id, ids))
  }

  const detailField = (field: keyof Details, label: string, type = 'text') => (
    <label className="form-field" htmlFor={`staff-edit-${field}`}>
      <span className="form-label">{label}</span>
      <input
        id={`staff-edit-${field}`}
        className="form-input"
        type={type}
        min={type === 'number' && field === 'price' ? 0 : undefined}
        value={details[field]}
        disabled={!editable && field !== 'sortOrder'}
        required={field === 'nameEn'}
        onChange={(event) => setDetails({ ...details, [field]: event.target.value })}
      />
    </label>
  )

  return (
    <div className="staff-panel">
      <button type="button" className="settings-back-link staff-back" onClick={onBack}>
        <ChevronLeftIcon aria-hidden="true" />
        {t('staff.backToPacks')}
      </button>

      <header className="staff-pack-header">
        <div>
          <h2 className="staff-card-title">
            {pack.name} <PackStatusPill status={pack.status} />
          </h2>
          <p className="muted staff-card-meta">
            {pack.slug} · {pack.is_official ? t('staff.official') : t('staff.community')} ·{' '}
            {t('staff.iconCount', { count: pack.icon_count })}
          </p>
        </div>
        <div className="staff-pack-actions">
          <Link
            className="button button-secondary button-small"
            to={`/market/packs/${pack.id}/preview`}
          >
            {t('market.preview')}
          </Link>
          {pack.status !== 'published' ? (
            <button
              type="button"
              className="button button-small"
              disabled={busy !== null || pack.icon_count === 0}
              onClick={() => void run('publish', () => publishStaffPack(pack.id))}
            >
              {t('staff.publish')}
            </button>
          ) : null}
          {pack.status !== 'archived' && pack.is_official ? (
            <button
              type="button"
              className="button button-secondary button-small"
              disabled={busy !== null}
              onClick={() => void run('archive', () => archiveStaffPack(pack.id))}
            >
              {t('staff.archive')}
            </button>
          ) : null}
        </div>
      </header>

      <PageErrorAlert error={error} />
      {notice ? <Alert variant="success">{notice}</Alert> : null}
      {pack.moderation_note ? (
        <Alert variant="warning">{t('staff.moderationNote', { note: pack.moderation_note })}</Alert>
      ) : null}

      {!pack.is_official && pack.status !== 'rejected' ? (
        <div className="card staff-card">
          <p className="muted">{t('staff.readOnly')}</p>
          <div className="staff-inline-form">
            <input
              className="form-input"
              value={rejectNote}
              maxLength={1000}
              placeholder={t('staff.rejectNote')}
              onChange={(event) => setRejectNote(event.target.value)}
            />
            <button
              type="button"
              className="button button-danger button-small"
              disabled={busy !== null}
              onClick={() =>
                void run('reject', () =>
                  rejectStaffPack(pack.id, { note: rejectNote.trim() || null }),
                )
              }
            >
              {t('staff.reject')}
            </button>
          </div>
        </div>
      ) : null}

      <form className="card form staff-card staff-form-grid" onSubmit={saveDetails}>
        <h3 className="staff-subtitle staff-form-wide">{t('staff.packDetails')}</h3>
        {detailField('nameEn', t('staff.nameEn'))}
        {detailField('nameRu', t('staff.nameRu'))}
        {detailField('descriptionEn', t('staff.descriptionEn'))}
        {detailField('descriptionRu', t('staff.descriptionRu'))}
        {detailField('price', t('staff.price'), 'number')}
        {detailField('sortOrder', t('staff.sortOrder'), 'number')}
        <div className="staff-form-actions">
          <button type="submit" className="button" disabled={busy !== null}>
            {busy === 'details' ? t('common.saving') : t('staff.saveDetails')}
          </button>
        </div>
      </form>

      {editable ? (
        <div className="card staff-card">
          <h3 className="staff-subtitle">{t('staff.uploadTitle')}</h3>
          <p className="muted staff-card-meta">{t('staff.uploadHint')}</p>
          <label className="button button-secondary staff-file-button">
            {t('staff.chooseFiles')}
            <input
              key={fileInputKey}
              type="file"
              accept={ACCEPTED_ICON_TYPES}
              multiple
              className="visually-hidden"
              disabled={busy !== null || session !== null}
              onChange={(event) => startUpload(Array.from(event.target.files ?? []))}
            />
          </label>
          {uploadErrors.length > 0 ? (
            <Alert variant="error">
              <ul className="staff-error-list">
                {uploadErrors.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </Alert>
          ) : null}
        </div>
      ) : null}

      <h3 className="staff-subtitle">{t('staff.iconsTitle')}</h3>
      {pack.icons.length === 0 ? (
        <p className="muted">{t('staff.noIcons')}</p>
      ) : (
        <ul className="staff-icon-grid">
          {pack.icons.map((icon, index) => {
            const isCover = pack.cover_icon_id === icon.id
            const meta = [
              isCover ? t('staff.cover') : null,
              ...icon.suggested_usage.map((value) => t(`staff.usageOptions.${value}`)),
            ].filter(Boolean)
            const body = (
              <>
                <CatalogIconThumb
                  iconId={icon.id}
                  label={icon.label}
                  glowColor={icon.suggested_colors[0] ?? null}
                />
                <span className="staff-icon-label">{icon.label}</span>
                {meta.length > 0 ? (
                  <span className="muted staff-icon-slug">{meta.join(' · ')}</span>
                ) : null}
              </>
            )
            return (
              <li key={icon.id} className="staff-icon-card">
                {editable ? (
                  <button
                    type="button"
                    className="staff-icon-open"
                    disabled={busy !== null}
                    title={t('staff.editIconTitle', { name: icon.label })}
                    onClick={() => openIcon(icon)}
                  >
                    {body}
                  </button>
                ) : (
                  <div className="staff-icon-open">{body}</div>
                )}
                {editable ? (
                  <div className="staff-icon-order">
                    <button
                      type="button"
                      className="button button-secondary button-small"
                      disabled={busy !== null || index === 0}
                      aria-label={t('staff.moveUp')}
                      title={t('staff.moveUp')}
                      onClick={() => moveIcon(index, -1)}
                    >
                      ←
                    </button>
                    <button
                      type="button"
                      className="button button-secondary button-small"
                      disabled={busy !== null || index === pack.icons.length - 1}
                      aria-label={t('staff.moveDown')}
                      title={t('staff.moveDown')}
                      onClick={() => moveIcon(index, 1)}
                    >
                      →
                    </button>
                  </div>
                ) : null}
              </li>
            )
          })}
        </ul>
      )}

      {session?.mode === 'new' ? (
        <StaffIconDialog
          key={`new-${session.index}-${session.file.name}`}
          source={session.source}
          initialDraft={emptyIconDraft(lastDraft)}
          title={t('staff.newIconTitle', { index: session.index, total: session.total })}
          hint={t('staff.newIconHint', { file: session.file.name })}
          searchTags={searchTags}
          busy={busy === 'upload'}
          onSave={(draft, crop) => void saveNew(draft, crop)}
          onCancel={stopUpload}
          secondaryLabel={session.total > 1 ? t('staff.skipFile') : undefined}
          onSecondary={() => finishFile(false)}
        />
      ) : null}

      {session?.mode === 'edit' ? (
        <StaffIconDialog
          key={`edit-${session.icon.id}`}
          source={session.source}
          initialDraft={draftFromIcon(session.icon)}
          initialCrop={session.icon.crop}
          title={t('staff.editIconTitle', { name: session.icon.label })}
          searchTags={searchTags}
          busy={busy !== null}
          onSave={(draft, crop) => void saveEdit(session.icon, draft, crop)}
          onCancel={closeSession}
          secondaryLabel={session.icon.crop ? t('staff.cropReset') : undefined}
          onSecondary={(draft) => void saveEdit(session.icon, draft, null)}
          footer={
            <div className="staff-icon-dialog-actions">
              {pack.cover_icon_id === session.icon.id ? null : (
                <button
                  type="button"
                  className="button button-secondary button-small"
                  disabled={busy !== null}
                  onClick={() =>
                    void run('cover', async () => {
                      await patchStudioPack(pack.id, { cover_icon_id: session.icon.id })
                      closeSession()
                    })
                  }
                >
                  {t('staff.makeCover')}
                </button>
              )}
              <label className="button button-secondary button-small staff-file-button">
                {t('staff.replaceFile')}
                <input
                  type="file"
                  accept={ACCEPTED_ICON_TYPES}
                  className="visually-hidden"
                  disabled={busy !== null}
                  onChange={(event) => replaceFile(session.icon, event.target.files?.[0])}
                />
              </label>
              <button
                type="button"
                className="button button-danger-ghost button-small"
                disabled={busy !== null}
                onClick={() => {
                  const icon = session.icon
                  closeSession()
                  setPendingDelete(icon)
                }}
              >
                {t('common.delete')}
              </button>
            </div>
          }
        />
      ) : null}

      {pendingDelete ? (
        <ConfirmDialog
          open
          title={t('staff.deleteIconTitle')}
          message={t('staff.deleteIcon', { name: pendingDelete.label })}
          confirmLabel={t('common.delete')}
          busyLabel={t('common.deleting')}
          isBusy={busy === 'delete'}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => {
            const icon = pendingDelete
            void run('delete', async () => {
              await deleteStudioIcon(icon.id)
              setPendingDelete(null)
            })
          }}
        />
      ) : null}
    </div>
  )
}
