import { useRef, useState, type ChangeEvent } from 'react'

import {
  addDiaryRestoreParts,
  applyDiaryRestore,
  cancelDiaryRestore,
  startDiaryRestore,
} from '../api/account'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { formatApiError } from '../lib/errors'
import type { DiaryRestore, RestoreSummary, RestoreWarning } from '../types/restore'
import { Alert } from './Alert'
import { PageErrorAlert } from './PageErrorAlert'
import { StableButtonLabel } from './StableButtonLabel'

type Busy = 'upload' | 'apply' | 'cancel' | null

function warningKey(warning: RestoreWarning): string {
  switch (warning.code) {
    case 'ambiguous_tag':
      return 'restore.warningAmbiguousTag'
    case 'unknown_tag':
      return 'restore.warningUnknownTag'
    case 'unknown_goal':
      return 'restore.warningUnknownGoal'
    case 'invalid_attachment':
      return 'restore.warningInvalidFile'
    default:
      return 'restore.warningOther'
  }
}

function fileName(path: string | null): string {
  return path ? (path.split('/').pop() ?? path) : ''
}

/** Restore the diary from an export archive: upload, review the preview, confirm (GP-20). */
export function DiaryRestoreCard() {
  const { t, locale } = useLocale()
  const inputRef = useRef<HTMLInputElement>(null)
  const addPartsRef = useRef(false)
  const [restore, setRestore] = useState<DiaryRestore | null>(null)
  const [result, setResult] = useState<RestoreSummary | null>(null)
  const [busy, setBusy] = useState<Busy>(null)
  const [error, setError] = useState<string | null>(null)

  const formatDate = (value: string | null) =>
    value
      ? new Intl.DateTimeFormat(intlLocale(locale), { dateStyle: 'medium' }).format(new Date(value))
      : ''

  const pickFiles = (addParts: boolean) => {
    addPartsRef.current = addParts
    inputRef.current?.click()
  }

  const handleFiles = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (files.length === 0) return
    setBusy('upload')
    setError(null)
    setResult(null)
    try {
      const next =
        addPartsRef.current && restore
          ? await addDiaryRestoreParts(restore.id, files)
          : await startDiaryRestore(files)
      setRestore(next)
    } catch (err) {
      setError(formatApiError(err, t, 'restore.uploadFailed'))
    } finally {
      setBusy(null)
    }
  }

  const handleApply = async () => {
    if (!restore) return
    setBusy('apply')
    setError(null)
    try {
      const applied = await applyDiaryRestore(restore.id)
      setRestore(null)
      setResult(applied.summary)
    } catch (err) {
      setError(formatApiError(err, t, 'restore.applyFailed'))
    } finally {
      setBusy(null)
    }
  }

  const handleCancel = async () => {
    if (!restore) return
    setBusy('cancel')
    setError(null)
    try {
      await cancelDiaryRestore(restore.id)
    } catch {
      // A preview that cannot be cancelled expires on its own; just close it here.
    } finally {
      setRestore(null)
      setBusy(null)
    }
  }

  const summary = restore?.summary
  const created = summary
    ? [
        ['restore.createdGroups', summary.tag_groups_new],
        ['restore.createdTags', summary.tags_new],
        ['restore.createdGoals', summary.goals_new],
        ['restore.createdTemplates', summary.note_templates_new],
      ].filter(([, count]) => Number(count) > 0)
    : []

  return (
    <div className="profile-account-password diary-restore">
      <input
        ref={inputRef}
        type="file"
        accept=".zip,application/zip"
        multiple
        hidden
        onChange={(event) => void handleFiles(event)}
      />
      <PageErrorAlert error={error} />
      {result ? (
        <Alert variant="success">
          {t('restore.done', {
            entries: result.entries_new,
            files: result.attachments_ready,
          })}
        </Alert>
      ) : null}

      {restore && summary ? (
        <div className="diary-restore-preview" aria-live="polite">
          <h3 className="diary-restore-title">{t('restore.previewTitle')}</h3>
          <ul className="diary-restore-facts">
            <li>
              {t('restore.archiveInfo', {
                total: summary.entries_total,
                date: formatDate(restore.exported_at),
              })}
            </li>
            {summary.entries_new > 0 ? (
              <li>
                <strong>
                  {t('restore.newEntries', {
                    count: summary.entries_new,
                    from: formatDate(summary.first_recorded_at),
                    to: formatDate(summary.last_recorded_at),
                  })}
                </strong>
              </li>
            ) : (
              <li>
                <strong>{t('restore.nothingNew')}</strong>
              </li>
            )}
            {summary.entries_existing > 0 ? (
              <li>{t('restore.existingEntries', { count: summary.entries_existing })}</li>
            ) : null}
            {created.length > 0 ? (
              <li>
                {t('restore.willCreate')}{' '}
                {created
                  .map(([key, count]) => t(String(key), { count: Number(count) }))
                  .join(', ')}
              </li>
            ) : null}
            {summary.attachments_total > 0 ? (
              <li>
                {t('restore.files', {
                  ready: summary.attachments_ready,
                  total: summary.attachments_total,
                })}
              </li>
            ) : null}
            {summary.attachments_lost > 0 ? (
              <li>{t('restore.filesLost', { count: summary.attachments_lost })}</li>
            ) : null}
          </ul>

          {summary.missing_parts.length > 0 ? (
            <Alert variant="warning">
              {t('restore.missingParts', {
                parts: summary.missing_parts.join(', '),
                total: summary.parts_total,
              })}
            </Alert>
          ) : null}
          {restore.warnings.length > 0 ? (
            <ul className="diary-restore-warnings">
              {restore.warnings.map((warning) => (
                <li key={`${warning.code}:${warning.slug ?? ''}:${warning.file ?? ''}`}>
                  {t(warningKey(warning), {
                    slug: warning.slug ?? '',
                    file: fileName(warning.file),
                  })}
                </li>
              ))}
            </ul>
          ) : null}

          <p className="profile-field-hint">{t('restore.safeNote')}</p>
          <div className="button-row">
            <button
              type="button"
              className="button"
              disabled={busy !== null || summary.entries_new === 0}
              onClick={() => void handleApply()}
            >
              <StableButtonLabel
                active={busy === 'apply' ? t('restore.applying') : t('restore.apply')}
                labels={[t('restore.apply'), t('restore.applying')]}
              />
            </button>
            {summary.missing_parts.length > 0 ? (
              <button
                type="button"
                className="button button-secondary"
                disabled={busy !== null}
                onClick={() => pickFiles(true)}
              >
                <StableButtonLabel
                  active={busy === 'upload' ? t('restore.uploading') : t('restore.addParts')}
                  labels={[t('restore.addParts'), t('restore.uploading')]}
                />
              </button>
            ) : null}
            <button
              type="button"
              className="button button-secondary"
              disabled={busy !== null}
              onClick={() => void handleCancel()}
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      ) : (
        <>
          <button
            type="button"
            className="button button-secondary"
            disabled={busy !== null}
            onClick={() => pickFiles(false)}
          >
            <StableButtonLabel
              active={busy === 'upload' ? t('restore.uploading') : t('restore.button')}
              labels={[t('restore.button'), t('restore.uploading')]}
            />
          </button>
          <p className="profile-field-hint">{t('restore.hint')}</p>
        </>
      )}
    </div>
  )
}
