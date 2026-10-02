import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { listStaffPacks } from '../../api/marketplace'
import { downloadPresetExport, importPreset, seedStarterContent } from '../../api/staff'
import { useLocale } from '../../context/LocaleContext'
import { saveBlob } from '../../lib/download'
import { formatApiError } from '../../lib/errors'
import type { PackCardPublic } from '../../types/marketplace'
import { Alert } from '../Alert'
import { PageErrorAlert } from '../PageErrorAlert'
import { PackStatusPill } from './PackStatusPill'

// Every instance seeds essentials from builtin icons, so it never goes into a preset.
const ESSENTIALS_SLUG = 'essentials'

export function StaffPresetsPanel() {
  const { t } = useLocale()
  const [packs, setPacks] = useState<PackCardPublic[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [includeAchievements, setIncludeAchievements] = useState(true)
  const [isExporting, setIsExporting] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importKey, setImportKey] = useState(0)
  const [isImporting, setIsImporting] = useState(false)
  const [importResult, setImportResult] = useState<string | null>(null)
  const [isSeeding, setIsSeeding] = useState(false)
  const [starterResult, setStarterResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadPacks = useCallback(async () => {
    const response = await listStaffPacks({ limit: 100 })
    const exportable = response.items.filter((pack) => pack.slug !== ESSENTIALS_SLUG)
    setPacks(exportable)
    setSelected(
      new Set(
        exportable
          .filter((pack) => pack.is_official && pack.status === 'published')
          .map((pack) => pack.id),
      ),
    )
  }, [])

  useEffect(() => {
    void loadPacks().catch((err) => setError(formatApiError(err, t, 'errors.failedLoadMarket')))
  }, [loadPacks, t])

  const togglePack = (id: string) =>
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const handleExport = async () => {
    if (isExporting) return
    setIsExporting(true)
    setError(null)
    try {
      const { blob, filename } = await downloadPresetExport({
        packIds: [...selected],
        includeAchievements,
      })
      saveBlob(blob, filename)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsExporting(false)
    }
  }

  const handleImport = async (event: FormEvent) => {
    event.preventDefault()
    if (!importFile || isImporting) return
    setIsImporting(true)
    setError(null)
    setImportResult(null)
    try {
      const report = await importPreset(importFile)
      setImportResult(
        t('staff.imported', {
          packs: report.packs.length,
          icons: report.icons,
          achievements: report.achievements.length,
          tags: report.search_tags,
        }),
      )
      setImportFile(null)
      setImportKey((key) => key + 1)
      await loadPacks()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsImporting(false)
    }
  }

  const handleStarter = async () => {
    if (isSeeding) return
    setIsSeeding(true)
    setError(null)
    setStarterResult(null)
    try {
      const report = await seedStarterContent()
      setStarterResult(
        t('staff.starterDone', {
          icons: report.icons,
          tags: report.search_tags,
          achievements: report.achievements.length,
        }),
      )
      await loadPacks()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsSeeding(false)
    }
  }

  const nothingSelected = selected.size === 0 && !includeAchievements

  return (
    <div className="staff-panel">
      <PageErrorAlert error={error} />

      <section className="card staff-card" aria-labelledby="staff-starter-title">
        <h2 id="staff-starter-title" className="staff-card-title">
          {t('staff.starterTitle')}
        </h2>
        <p className="muted staff-card-meta">{t('staff.starterLead')}</p>
        {starterResult ? <Alert variant="success">{starterResult}</Alert> : null}
        <button
          type="button"
          className="button"
          disabled={isSeeding}
          onClick={() => void handleStarter()}
        >
          {isSeeding ? t('staff.starterRunning') : t('staff.starterRun')}
        </button>
      </section>

      <section className="card staff-card" aria-labelledby="staff-export-title">
        <h2 id="staff-export-title" className="staff-card-title">
          {t('staff.exportTitle')}
        </h2>
        <p className="muted staff-card-meta">{t('staff.exportLead')}</p>

        <div className="staff-toolbar">
          <span className="form-label">{t('staff.exportPacks')}</span>
          <div className="staff-chip-row">
            <button
              type="button"
              className="market-tag-chip"
              onClick={() => setSelected(new Set(packs.map((pack) => pack.id)))}
            >
              {t('staff.selectAll')}
            </button>
            <button type="button" className="market-tag-chip" onClick={() => setSelected(new Set())}>
              {t('staff.selectNone')}
            </button>
          </div>
        </div>
        <ul className="staff-checklist">
          {packs.map((pack) => (
            <li key={pack.id}>
              <label className="staff-check-row">
                <input
                  type="checkbox"
                  checked={selected.has(pack.id)}
                  onChange={() => togglePack(pack.id)}
                />
                <span className="staff-list-title">
                  {pack.name}
                  <PackStatusPill status={pack.status} />
                </span>
                <span className="muted staff-list-meta">
                  {pack.slug} · {t('staff.iconCount', { count: pack.icon_count })}
                </span>
              </label>
            </li>
          ))}
        </ul>

        <label className="staff-check-row">
          <input
            type="checkbox"
            checked={includeAchievements}
            onChange={(event) => setIncludeAchievements(event.target.checked)}
          />
          <span className="staff-list-title">{t('staff.includeAchievements')}</span>
          <span className="muted staff-list-meta">{t('staff.includeAchievementsHint')}</span>
        </label>

        <button
          type="button"
          className="button"
          disabled={isExporting || nothingSelected}
          onClick={() => void handleExport()}
        >
          {isExporting ? t('staff.downloading') : t('staff.download')}
        </button>
      </section>

      <form className="card staff-card" onSubmit={handleImport} aria-labelledby="staff-import-title">
        <h2 id="staff-import-title" className="staff-card-title">
          {t('staff.importTitle')}
        </h2>
        <p className="muted staff-card-meta">{t('staff.importLead')}</p>
        {importResult ? <Alert variant="success">{importResult}</Alert> : null}
        <label className="form-field" htmlFor="staff-import-file">
          <span className="form-label">{t('staff.importFile')}</span>
          <input
            key={importKey}
            id="staff-import-file"
            className="form-input"
            type="file"
            accept=".zip,application/zip"
            onChange={(event) => setImportFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <button type="submit" className="button" disabled={!importFile || isImporting}>
          {isImporting ? t('staff.importing') : t('staff.import')}
        </button>
      </form>
    </div>
  )
}
