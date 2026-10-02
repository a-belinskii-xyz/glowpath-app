import { useCallback, useEffect, useState, type FormEvent } from 'react'

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
  IconUsage,
  PackDetailPublic,
  SearchTagPublic,
} from '../../types/marketplace'
import { Alert } from '../Alert'
import { CatalogIconThumb } from '../CatalogIconThumb'
import { ConfirmDialog } from '../ConfirmDialog'
import { ChevronLeftIcon } from '../icons'
import { ImageCropModal } from '../ImageCropModal'
import { PageErrorAlert } from '../PageErrorAlert'
import { PackStatusPill } from './PackStatusPill'
import { ChipToggleRow } from './ChipToggleRow'
import { ACCEPTED_ICON_TYPES, ICON_USAGES, MOOD_SCORES } from './iconFields'
import { StaffIconEditor } from './StaffIconEditor'

type CropSession = {
  icon: CatalogIconPublic
  image: HTMLImageElement
  objectUrl: string
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

function labelFromFileName(name: string): string {
  const stem = name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' ').trim()
  return stem ? stem.charAt(0).toUpperCase() + stem.slice(1) : 'Icon'
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

  const [files, setFiles] = useState<File[]>([])
  const [fileInputKey, setFileInputKey] = useState(0)
  const [color, setColor] = useState('#94a3b8')
  const [scores, setScores] = useState<number[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [usage, setUsage] = useState<IconUsage[]>([])
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null)
  const [uploadErrors, setUploadErrors] = useState<string[]>([])

  const [editingIconId, setEditingIconId] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<CatalogIconPublic | null>(null)
  const [cropSession, setCropSession] = useState<CropSession | null>(null)

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

  const handleUpload = async () => {
    if (files.length === 0 || busy) return
    setBusy('upload')
    setError(null)
    setNotice(null)
    setUploadErrors([])
    const failures: string[] = []
    let uploaded = 0
    for (const [index, file] of files.entries()) {
      setProgress({ done: index, total: files.length })
      const label = labelFromFileName(file.name)
      try {
        await uploadStudioIcon(pack.id, file, {
          labels: { en: label, ru: label },
          suggested_colors: [color],
          suggested_mood_scores: scores,
          suggested_usage: usage,
          search_tag_slugs: tags,
        })
        uploaded += 1
      } catch (err) {
        failures.push(
          t('staff.uploadFailed', {
            file: file.name,
            error: formatApiError(err, t, 'errors.requestFailed'),
          }),
        )
      }
    }
    setProgress(null)
    setUploadErrors(failures)
    setFiles([])
    setFileInputKey((key) => key + 1)
    try {
      await load()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedLoadMarket'))
    }
    if (uploaded > 0) setNotice(t('staff.uploaded', { count: uploaded }))
    setBusy(null)
  }

  const openCrop = (icon: CatalogIconPublic) =>
    void run('crop-load', async () => {
      const { blob } = await fetchCatalogIconBlob(icon.id)
      const loaded = await readMoodIconBlobForCrop(blob)
      if ('error' in loaded) {
        setError(t('staff.cropUnavailable'))
        return
      }
      setCropSession({ icon, image: loaded.image, objectUrl: loaded.objectUrl })
    })

  const closeCrop = () => {
    if (cropSession) URL.revokeObjectURL(cropSession.objectUrl)
    setCropSession(null)
  }

  const saveCrop = (icon: CatalogIconPublic, crop: IconCrop | null) =>
    run('crop', async () => {
      await patchStudioIcon(icon.id, crop ? { crop } : { clear_crop: true })
      invalidateCatalogIcon(icon.id)
      closeCrop()
    })

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
              onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
            />
          </label>
          {files.length > 0 ? (
            <p className="staff-card-meta">{t('staff.filesSelected', { count: files.length })}</p>
          ) : null}

          <fieldset className="staff-fieldset">
            <legend className="form-hint">{t('staff.uploadDefaults')}</legend>
            <label className="staff-color-field">
              <span className="form-label">{t('staff.color')}</span>
              <input type="color" value={color} onChange={(event) => setColor(event.target.value)} />
            </label>
            <div>
              <span className="form-label">{t('staff.usage')}</span>
              <ChipToggleRow
                options={ICON_USAGES}
                selected={usage}
                label={(value) => t(`staff.usageOptions.${value}`)}
                onChange={setUsage}
              />
            </div>
            <div>
              <span className="form-label">{t('staff.scores')}</span>
              <ChipToggleRow
                options={MOOD_SCORES}
                selected={scores}
                label={(score) => String(score)}
                onChange={setScores}
              />
            </div>
            {searchTags.length > 0 ? (
              <div>
                <span className="form-label">{t('staff.tags')}</span>
                <ChipToggleRow
                  options={searchTags.map((tag) => tag.slug)}
                  selected={tags}
                  label={(slug) => searchTags.find((tag) => tag.slug === slug)?.label ?? slug}
                  onChange={setTags}
                />
              </div>
            ) : null}
          </fieldset>

          <button
            type="button"
            className="button"
            disabled={files.length === 0 || busy !== null}
            onClick={() => void handleUpload()}
          >
            {progress ? t('staff.uploading', progress) : t('staff.upload')}
          </button>
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
            if (editingIconId === icon.id) {
              return (
                <li key={icon.id} className="staff-icon-card staff-icon-card-editing">
                  <CatalogIconThumb
                    iconId={icon.id}
                    label={icon.label}
                    glowColor={icon.suggested_colors[0] ?? null}
                  />
                  <StaffIconEditor
                    icon={icon}
                    searchTags={searchTags}
                    busy={busy !== null}
                    run={run}
                    onImageChanged={() => invalidateCatalogIcon(icon.id)}
                    onClose={() => setEditingIconId(null)}
                  />
                </li>
              )
            }
            return (
              <li key={icon.id} className="staff-icon-card">
                <CatalogIconThumb
                  iconId={icon.id}
                  label={icon.label}
                  glowColor={icon.suggested_colors[0] ?? null}
                />
                <p className="staff-icon-label">{icon.label}</p>
                <p className="muted staff-icon-slug">
                  {[
                    icon.slug,
                    isCover ? t('staff.cover') : null,
                    icon.crop ? t('staff.cropped') : null,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </p>
                {icon.suggested_usage.length > 0 ? (
                  <p className="muted staff-icon-slug">
                    {icon.suggested_usage
                      .map((value) => t(`staff.usageOptions.${value}`))
                      .join(', ')}
                  </p>
                ) : null}
                {editable ? (
                  <div className="staff-icon-actions">
                    <button
                      type="button"
                      className="button button-secondary button-small"
                      onClick={() => setEditingIconId(icon.id)}
                    >
                      {t('common.edit')}
                    </button>
                    <button
                      type="button"
                      className="button button-secondary button-small"
                      disabled={busy !== null}
                      onClick={() => openCrop(icon)}
                    >
                      {t('staff.crop')}
                    </button>
                    {isCover ? null : (
                      <button
                        type="button"
                        className="button button-secondary button-small"
                        disabled={busy !== null}
                        onClick={() =>
                          void run('cover', () =>
                            patchStudioPack(pack.id, { cover_icon_id: icon.id }),
                          )
                        }
                      >
                        {t('staff.makeCover')}
                      </button>
                    )}
                    <button
                      type="button"
                      className="button button-secondary button-small"
                      disabled={busy !== null || index === 0}
                      aria-label={t('staff.moveUp')}
                      title={t('staff.moveUp')}
                      onClick={() => moveIcon(index, -1)}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className="button button-secondary button-small"
                      disabled={busy !== null || index === pack.icons.length - 1}
                      aria-label={t('staff.moveDown')}
                      title={t('staff.moveDown')}
                      onClick={() => moveIcon(index, 1)}
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      className="button button-danger-ghost button-small"
                      onClick={() => setPendingDelete(icon)}
                    >
                      {t('common.delete')}
                    </button>
                  </div>
                ) : null}
              </li>
            )
          })}
        </ul>
      )}

      {cropSession ? (
        <ImageCropModal
          image={cropSession.image}
          imageUrl={cropSession.objectUrl}
          fileName={cropSession.icon.slug}
          initialRegion={cropSession.icon.crop}
          isSaving={busy === 'crop'}
          onCancel={closeCrop}
          onSaveRegion={(region) => saveCrop(cropSession.icon, region)}
          resetLabel={cropSession.icon.crop ? t('staff.cropReset') : undefined}
          onReset={() => saveCrop(cropSession.icon, null)}
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
