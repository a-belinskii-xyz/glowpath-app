import { type DragEvent, type FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  createNoteTemplate,
  deleteNoteTemplate,
  listNoteTemplates,
  patchNoteTemplate,
  reorderNoteTemplates,
} from '../api/noteTemplates'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { FormField } from '../components/FormField'
import { MarkdownNoteEditor } from '../components/MarkdownNoteEditor'
import { MarkdownNote } from '../components/MarkdownNote'
import { PopupMenu } from '../components/PopupMenu'
import { useLocale } from '../context/LocaleContext'
import { ApiError } from '../lib/errors'
import type { NoteTemplatePublic } from '../types/noteTemplate'

type EditorMode =
  | { kind: 'create' }
  | { kind: 'edit'; template: NoteTemplatePublic }

function moveItem<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  const next = [...items]
  const [item] = next.splice(fromIndex, 1)
  next.splice(toIndex, 0, item)
  return next
}

export function TemplatesPage() {
  const { locale, t } = useLocale()
  const [templates, setTemplates] = useState<NoteTemplatePublic[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [editor, setEditor] = useState<EditorMode | null>(null)
  const [name, setName] = useState('')
  const [body, setBody] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [draggingId, setDraggingId] = useState<string | null>(null)

  const reload = async () => {
    const response = await listNoteTemplates()
    setTemplates(response.items)
  }

  useEffect(() => {
    const load = async () => {
      setIsLoading(true)
      try {
        await reload()
        setError(null)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToViewTemplates'))
        } else {
          setError(err instanceof Error ? err.message : t('errors.failedLoadTemplates'))
        }
      } finally {
        setIsLoading(false)
      }
    }
    void load()
  }, [locale, t])

  const openEditor = (mode: EditorMode) => {
    setError(null)
    setEditor(mode)
    if (mode.kind === 'create') {
      setName('')
      setBody('')
    } else {
      setName(mode.template.label)
      setBody(mode.template.body)
    }
  }

  const closeEditor = () => {
    setEditor(null)
    setName('')
    setBody('')
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!editor) return

    const trimmedName = name.trim()
    const trimmedBody = body.trim()
    if (!trimmedName) {
      setError(t('templatesPage.nameRequired'))
      return
    }
    if (!trimmedBody) {
      setError(t('templatesPage.bodyRequired'))
      return
    }

    const existingLabels = editor.kind === 'edit' ? editor.template.labels : {}
    const existingBodies = editor.kind === 'edit' ? editor.template.bodies : {}
    const labels = { ...existingLabels, [locale]: trimmedName }
    const bodies = { ...existingBodies, [locale]: trimmedBody }

    setIsSaving(true)
    setError(null)
    try {
      if (editor.kind === 'create') {
        await createNoteTemplate({ labels, bodies })
      } else {
        await patchNoteTemplate(editor.template.id, { labels, bodies })
      }
      await reload()
      closeEditor()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (template: NoteTemplatePublic) => {
    if (!window.confirm(t('confirm.deleteTemplate', { label: template.label }))) return
    setError(null)
    try {
      await deleteNoteTemplate(template.id)
      await reload()
      if (editor?.kind === 'edit' && editor.template.id === template.id) {
        closeEditor()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedDeleteTemplate'))
    }
  }

  const handleDrop = async (targetId: string) => {
    if (!draggingId || draggingId === targetId) {
      setDraggingId(null)
      return
    }
    const fromIndex = templates.findIndex((item) => item.id === draggingId)
    const toIndex = templates.findIndex((item) => item.id === targetId)
    setDraggingId(null)
    if (fromIndex < 0 || toIndex < 0) return

    const previous = templates
    const next = moveItem(templates, fromIndex, toIndex)
    setTemplates(next)
    try {
      const response = await reorderNoteTemplates({
        ordered_ids: next.map((item) => item.id),
      })
      setTemplates(response.items)
    } catch (err) {
      setTemplates(previous)
      setError(err instanceof Error ? err.message : t('errors.failedReorderTemplates'))
    }
  }

  const editorTitle =
    editor?.kind === 'create'
      ? t('templatesPage.addTemplate')
      : editor?.kind === 'edit'
        ? t('templatesPage.editTemplate', { label: editor.template.label })
        : null

  return (
    <section className="page">
      <EmailVerificationBanner />

      <header className="page-header">
        <h1>{t('templatesPage.title')}</h1>
        <button type="button" className="button" onClick={() => openEditor({ kind: 'create' })}>
          {t('templatesPage.addTemplate')}
        </button>
      </header>

      <p className="muted">{t('templatesPage.hint')}</p>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {isLoading ? <p className="muted">{t('common.loadingTemplates')}</p> : null}

      {editor && editorTitle ? (
        <form className="card form tag-editor" onSubmit={(event) => void handleSubmit(event)}>
          <h2>{editorTitle}</h2>
          <FormField
            id="template-name"
            label={t('common.name')}
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            autoFocus
            maxLength={64}
          />
          <MarkdownNoteEditor
            value={body}
            onChange={setBody}
            label={t('templatesPage.body')}
            placeholder={t('templatesPage.bodyPlaceholder')}
          />
          <div className="button-row">
            <button type="submit" className="button" disabled={isSaving}>
              {isSaving ? t('common.saving') : t('common.save')}
            </button>
            <button
              type="button"
              className="button button-secondary"
              onClick={closeEditor}
              disabled={isSaving}
            >
              {t('common.cancel')}
            </button>
          </div>
        </form>
      ) : null}

      <div className="note-templates-list">
        {templates.map((template) => (
          <article
            key={template.id}
            className={`card note-template-card${draggingId === template.id ? ' is-dragging' : ''}`}
            draggable
            onDragStart={() => setDraggingId(template.id)}
            onDragOver={(event: DragEvent) => event.preventDefault()}
            onDrop={() => void handleDrop(template.id)}
            onDragEnd={() => setDraggingId(null)}
          >
            <header className="note-template-card-header">
              <PopupMenu
                label={<h2>{template.label}</h2>}
                ariaLabel={t('templatesPage.actionsFor', { label: template.label })}
                onEdit={() => openEditor({ kind: 'edit', template })}
                onDelete={() => void handleDelete(template)}
              />
              <span className="tag-drag-hint muted" aria-hidden="true">
                ⋮⋮
              </span>
            </header>
            <MarkdownNote content={template.body} compact className="note-template-preview" />
          </article>
        ))}
      </div>

      <p className="muted">
        <Link to="/">{t('common.backToEntries')}</Link>
      </p>
    </section>
  )
}
