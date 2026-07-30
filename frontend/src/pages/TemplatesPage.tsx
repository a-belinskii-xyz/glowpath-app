import { type DragEvent, type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  createNoteTemplate,
  deleteNoteTemplate,
  listNoteTemplates,
  patchNoteTemplate,
  reorderNoteTemplates,
} from '../api/noteTemplates'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { DragHandle } from '../components/DragHandle'
import { EditorDrawer } from '../components/EditorDrawer'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { FormField } from '../components/FormField'
import { IconButton } from '../components/IconButton'
import { ArrowDownIcon, ArrowUpIcon, DeleteIcon, EditIcon } from '../components/icons'
import { MarkdownNote } from '../components/MarkdownNote'
import { MarkdownNoteEditor } from '../components/MarkdownNoteEditor'
import { useLocale } from '../context/LocaleContext'
import { ApiError, formatApiError } from '../lib/errors'
import {
  dropEdgeFromClientY,
  dropIndexForEdge,
  moveItem,
  moveItemById,
  type DropEdge,
} from '../lib/listReorder'
import type { NoteTemplatePublic } from '../types/noteTemplate'

type EditorMode = { kind: 'create' } | { kind: 'edit'; template: NoteTemplatePublic }

type TemplatesPageProps = {
  embedded?: boolean
}

export function TemplatesPage({ embedded = false }: TemplatesPageProps) {
  const { locale, t } = useLocale()
  const [templates, setTemplates] = useState<NoteTemplatePublic[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [editor, setEditor] = useState<EditorMode | null>(null)
  const [name, setName] = useState('')
  const [body, setBody] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [dropTarget, setDropTarget] = useState<{ id: string; edge: DropEdge } | null>(null)
  const [pendingDelete, setPendingDelete] = useState<NoteTemplatePublic | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

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
          setError(formatApiError(err, t, 'errors.failedLoadTemplates'))
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

  const closeEditor = useCallback(() => {
    setEditor(null)
    setName('')
    setBody('')
  }, [])

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
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (template: NoteTemplatePublic) => {
    setDeleteError(null)
    setIsDeleting(true)
    try {
      await deleteNoteTemplate(template.id)
      await reload()
      setPendingDelete(null)
      if (editor?.kind === 'edit' && editor.template.id === template.id) {
        closeEditor()
      }
    } catch (err) {
      setDeleteError(formatApiError(err, t, 'errors.failedDeleteTemplate'))
    } finally {
      setIsDeleting(false)
    }
  }

  const persistOrder = async (next: NoteTemplatePublic[], previous: NoteTemplatePublic[]) => {
    setTemplates(next)
    try {
      const response = await reorderNoteTemplates({
        ordered_ids: next.map((item) => item.id),
      })
      setTemplates(response.items)
    } catch (err) {
      setTemplates(previous)
      setError(formatApiError(err, t, 'errors.failedReorderTemplates'))
    }
  }

  const clearDrag = () => {
    setDraggingId(null)
    setDropTarget(null)
  }

  const handleDrop = async (targetId: string, edge: DropEdge) => {
    if (!draggingId || draggingId === targetId) {
      clearDrag()
      return
    }
    const fromIndex = templates.findIndex((item) => item.id === draggingId)
    const targetIndex = templates.findIndex((item) => item.id === targetId)
    clearDrag()
    if (fromIndex < 0 || targetIndex < 0) return
    const toIndex = dropIndexForEdge(fromIndex, targetIndex, edge)
    if (toIndex === fromIndex) return
    await persistOrder(moveItem(templates, fromIndex, toIndex), templates)
  }

  const handleMove = async (templateId: string, direction: 'up' | 'down') => {
    const next = moveItemById(templates, templateId, direction)
    if (next === templates) return
    await persistOrder(next, templates)
  }

  const editorTitle =
    editor?.kind === 'create'
      ? t('templatesPage.addTemplate')
      : editor?.kind === 'edit'
        ? t('templatesPage.editTemplate', { label: editor.template.label })
        : null
  const selectedId = editor?.kind === 'edit' ? editor.template.id : null

  return (
    <section className={embedded ? undefined : 'page'}>
      {embedded ? null : <EmailVerificationBanner />}

      <header className="page-header">
        <h1>{t('templatesPage.title')}</h1>
        <button type="button" className="button" onClick={() => openEditor({ kind: 'create' })}>
          {t('templatesPage.addTemplate')}
        </button>
      </header>

      <p className="muted">{t('templatesPage.hint')}</p>

      <PageErrorAlert error={error} />
      {pendingDelete ? (
        <ConfirmDialog
          open
          title={t('confirm.deleteTemplateTitle')}
          message={t('confirm.deleteTemplate', { label: pendingDelete.label })}
          confirmLabel={t('common.delete')}
          isBusy={isDeleting}
          error={deleteError}
          onCancel={() => {
            if (isDeleting) return
            setPendingDelete(null)
            setDeleteError(null)
          }}
          onConfirm={() => {
            void handleDelete(pendingDelete)
          }}
        />
      ) : null}
      {isLoading ? <p className="muted">{t('common.loadingTemplates')}</p> : null}

      <EditorDrawer open={Boolean(editor && editorTitle)} title={editorTitle ?? ''} onClose={closeEditor}>
        <form className="form appearance-form-drawer" onSubmit={(event) => void handleSubmit(event)}>
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
      </EditorDrawer>

      <div className="note-templates-list">
        {templates.map((template, index) => (
          <article
            key={template.id}
            className={[
              'card',
              'note-template-card',
              draggingId === template.id ? 'is-dragging' : '',
              selectedId === template.id ? 'is-selected' : '',
              dropTarget?.id === template.id ? `is-drop-${dropTarget.edge}` : '',
            ]
              .filter(Boolean)
              .join(' ')}
            onDragOver={(event: DragEvent) => {
              if (!draggingId || draggingId === template.id) return
              event.preventDefault()
              const edge = dropEdgeFromClientY(event.clientY, event.currentTarget)
              setDropTarget((current) =>
                current?.id === template.id && current.edge === edge
                  ? current
                  : { id: template.id, edge },
              )
            }}
            onDragLeave={(event: DragEvent) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node)) {
                setDropTarget((current) => (current?.id === template.id ? null : current))
              }
            }}
            onDrop={(event: DragEvent) => {
              event.preventDefault()
              const edge =
                dropTarget?.id === template.id
                  ? dropTarget.edge
                  : dropEdgeFromClientY(event.clientY, event.currentTarget)
              void handleDrop(template.id, edge)
            }}
          >
            <header className="note-template-card-header">
              <div className="note-template-title-row">
                <h2>{template.label}</h2>
                <div className="list-row-actions">
                  <IconButton
                    label={t('common.edit')}
                    size="sm"
                    onClick={() => openEditor({ kind: 'edit', template })}
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    label={t('templatesPage.moveUp')}
                    size="sm"
                    disabled={index === 0}
                    onClick={() => void handleMove(template.id, 'up')}
                  >
                    <ArrowUpIcon />
                  </IconButton>
                  <IconButton
                    label={t('templatesPage.moveDown')}
                    size="sm"
                    disabled={index === templates.length - 1}
                    onClick={() => void handleMove(template.id, 'down')}
                  >
                    <ArrowDownIcon />
                  </IconButton>
                  <IconButton
                    label={t('common.delete')}
                    size="sm"
                    variant="danger"
                    onClick={() => {
                      setDeleteError(null)
                      setPendingDelete(template)
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                  <DragHandle
                    label={t('templatesPage.dragTemplate', { label: template.label })}
                    onDragStart={() => {
                      setDraggingId(template.id)
                      setDropTarget(null)
                    }}
                    onDragEnd={clearDrag}
                    onMoveUp={() => void handleMove(template.id, 'up')}
                    onMoveDown={() => void handleMove(template.id, 'down')}
                  />
                </div>
              </div>
            </header>
            <button
              type="button"
              className="note-template-preview-button"
              onClick={() => openEditor({ kind: 'edit', template })}
            >
              <MarkdownNote content={template.body} compact className="note-template-preview" />
            </button>
          </article>
        ))}
      </div>

      {embedded ? null : (
        <p className="muted">
          <Link to="/">{t('common.backToEntries')}</Link>
        </p>
      )}
    </section>
  )
}
