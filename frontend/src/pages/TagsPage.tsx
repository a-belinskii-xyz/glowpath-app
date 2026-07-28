import { type DragEvent, type FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  createTag,
  createTagGroup,
  deleteTag,
  deleteTagGroup,
  listTagGroups,
  patchTag,
  patchTagGroup,
  reorderTagGroups,
  reorderTags,
  uploadTagIcon,
} from '../api/tagGroups'
import { Alert } from '../components/Alert'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { FormField } from '../components/FormField'
import { PopupMenu } from '../components/PopupMenu'
import { TagIcon } from '../components/TagIcon'
import { TagIconEditor } from '../components/TagIconEditor'
import { useLocale } from '../context/LocaleContext'
import { moodGlowFilter, moodSubtleFill } from '../design'
import { ApiError } from '../lib/errors'
import { isValidHexColor } from '../lib/moodScale'
import { DEFAULT_TAG_STYLE, type TagGroupPublic, type TagPublic } from '../types/tag'

type EditorMode =
  | { kind: 'create-group' }
  | { kind: 'edit-group'; group: TagGroupPublic }
  | { kind: 'create-tag'; group: TagGroupPublic }
  | { kind: 'edit-tag'; group: TagGroupPublic; tag: TagPublic }

function moveItem<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  const next = [...items]
  const [item] = next.splice(fromIndex, 1)
  next.splice(toIndex, 0, item)
  return next
}

export function TagsPage() {
  const { locale, t } = useLocale()
  const [groups, setGroups] = useState<TagGroupPublic[]>([])
  const [visibleLimit, setVisibleLimit] = useState(6)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [editor, setEditor] = useState<EditorMode | null>(null)
  const [name, setName] = useState('')
  const [draftColor, setDraftColor] = useState(DEFAULT_TAG_STYLE.color)
  const [draftEmoji, setDraftEmoji] = useState(DEFAULT_TAG_STYLE.icon)
  const [pendingUpload, setPendingUpload] = useState<File | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [togglingGroupId, setTogglingGroupId] = useState<string | null>(null)
  const [draggingGroupId, setDraggingGroupId] = useState<string | null>(null)
  const [draggingTag, setDraggingTag] = useState<{ groupId: string; tagId: string } | null>(null)
  const [pendingDelete, setPendingDelete] = useState<
    | { kind: 'group'; group: TagGroupPublic }
    | { kind: 'tag'; group: TagGroupPublic; tag: TagPublic }
    | null
  >(null)

  const reload = async () => {
    const response = await listTagGroups()
    setGroups(response.items)
    setVisibleLimit(response.entry_visible_tag_group_limit)
  }

  const visibleCount = groups.filter((group) => group.show_on_entry).length
  const atVisibleLimit = visibleCount >= visibleLimit
  const editingTag = editor?.kind === 'edit-tag' || editor?.kind === 'create-tag'

  useEffect(() => {
    const load = async () => {
      setIsLoading(true)
      try {
        await reload()
        setError(null)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToViewTags'))
        } else {
          setError(err instanceof Error ? err.message : t('errors.failedLoadTags'))
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
    if (mode.kind === 'create-group' || mode.kind === 'create-tag') {
      setName('')
      setDraftColor(DEFAULT_TAG_STYLE.color)
      setDraftEmoji(DEFAULT_TAG_STYLE.icon)
      setPendingUpload(null)
    } else if (mode.kind === 'edit-group') {
      setName(mode.group.label)
      setPendingUpload(null)
    } else {
      setName(mode.tag.label)
      setDraftColor(mode.tag.color)
      setDraftEmoji(mode.tag.icon_type === 'emoji' ? mode.tag.icon : DEFAULT_TAG_STYLE.icon)
      setPendingUpload(null)
    }
  }

  const closeEditor = () => {
    setEditor(null)
    setName('')
    setDraftColor(DEFAULT_TAG_STYLE.color)
    setDraftEmoji(DEFAULT_TAG_STYLE.icon)
    setPendingUpload(null)
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!editor) return

    const trimmed = name.trim()
    if (!trimmed) {
      setError(t('tagsPage.nameRequired'))
      return
    }

    if (editingTag) {
      if (!isValidHexColor(draftColor)) {
        setError(t('tagsPage.invalidColor'))
        return
      }
      const emoji = draftEmoji.trim()
      const usingUpload =
        (editor.kind === 'edit-tag' && editor.tag.icon_type === 'upload') ||
        (editor.kind === 'create-tag' && pendingUpload !== null)
      if (!usingUpload && !emoji) {
        setError(t('tagsPage.emojiRequired'))
        return
      }
    }

    const existingLabels =
      editor.kind === 'edit-group'
        ? editor.group.labels
        : editor.kind === 'edit-tag'
          ? editor.tag.labels
          : {}
    const labels = { ...existingLabels, [locale]: trimmed }
    setIsSaving(true)
    setError(null)
    try {
      if (editor.kind === 'create-group') {
        await createTagGroup({ labels })
      } else if (editor.kind === 'edit-group') {
        await patchTagGroup(editor.group.id, { labels })
      } else if (editor.kind === 'create-tag') {
        const created = await createTag(editor.group.id, {
          labels,
          color: draftColor,
          icon_type: 'emoji',
          icon: draftEmoji.trim() || DEFAULT_TAG_STYLE.icon,
        })
        if (pendingUpload) {
          await uploadTagIcon(editor.group.id, created.id, pendingUpload)
        }
      } else {
        const usingUpload = editor.tag.icon_type === 'upload'
        await patchTag(editor.group.id, editor.tag.id, {
          labels,
          color: draftColor,
          ...(usingUpload
            ? {}
            : { icon_type: 'emoji' as const, icon: draftEmoji.trim() }),
        })
      }
      await reload()
      closeEditor()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteGroup = async (group: TagGroupPublic) => {
    setError(null)
    try {
      await deleteTagGroup(group.id)
      await reload()
      if (editor && 'group' in editor && editor.group.id === group.id) {
        closeEditor()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedDeleteGroup'))
    }
  }

  const handleToggleShowOnEntry = async (group: TagGroupPublic) => {
    const nextValue = !group.show_on_entry
    if (nextValue && atVisibleLimit) {
      setError(t('tagsPage.visibilityLimit', { limit: visibleLimit }))
      return
    }
    setError(null)
    setTogglingGroupId(group.id)
    const previous = groups
    setGroups((current) =>
      current.map((item) =>
        item.id === group.id ? { ...item, show_on_entry: nextValue } : item,
      ),
    )
    try {
      const updated = await patchTagGroup(group.id, { show_on_entry: nextValue })
      setGroups((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setGroups(previous)
      setError(err instanceof Error ? err.message : t('errors.failedUpdateVisibility'))
    } finally {
      setTogglingGroupId(null)
    }
  }

  const handleDeleteTag = async (group: TagGroupPublic, tag: TagPublic) => {
    setError(null)
    try {
      await deleteTag(group.id, tag.id)
      await reload()
      if (editor?.kind === 'edit-tag' && editor.tag.id === tag.id) {
        closeEditor()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedDeleteTag'))
    }
  }

  const handleGroupDrop = async (targetGroupId: string) => {
    if (!draggingGroupId || draggingGroupId === targetGroupId) {
      setDraggingGroupId(null)
      return
    }
    const fromIndex = groups.findIndex((group) => group.id === draggingGroupId)
    const toIndex = groups.findIndex((group) => group.id === targetGroupId)
    setDraggingGroupId(null)
    if (fromIndex < 0 || toIndex < 0) return

    const previous = groups
    const next = moveItem(groups, fromIndex, toIndex)
    setGroups(next)
    try {
      const response = await reorderTagGroups({ ordered_ids: next.map((group) => group.id) })
      setGroups(response.items)
    } catch (err) {
      setGroups(previous)
      setError(err instanceof Error ? err.message : t('errors.failedReorderGroups'))
    }
  }

  const handleTagDrop = async (group: TagGroupPublic, targetTagId: string) => {
    if (!draggingTag || draggingTag.groupId !== group.id || draggingTag.tagId === targetTagId) {
      setDraggingTag(null)
      return
    }
    const fromIndex = group.tags.findIndex((tag) => tag.id === draggingTag.tagId)
    const toIndex = group.tags.findIndex((tag) => tag.id === targetTagId)
    setDraggingTag(null)
    if (fromIndex < 0 || toIndex < 0) return

    const previous = groups
    const nextTags = moveItem(group.tags, fromIndex, toIndex)
    setGroups((current) =>
      current.map((item) => (item.id === group.id ? { ...item, tags: nextTags } : item)),
    )
    try {
      const updated = await reorderTags(group.id, {
        ordered_ids: nextTags.map((tag) => tag.id),
      })
      setGroups((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setGroups(previous)
      setError(err instanceof Error ? err.message : t('errors.failedReorderTags'))
    }
  }

  const editorTitle =
    editor?.kind === 'create-group'
      ? t('tagsPage.addGroup')
      : editor?.kind === 'edit-group'
        ? t('tagsPage.editGroup')
        : editor?.kind === 'create-tag'
          ? t('tagsPage.addTagTo', { label: editor.group.label })
          : editor?.kind === 'edit-tag'
            ? t('tagsPage.editTag', { label: editor.tag.label })
            : null

  return (
    <section className="page">
      <EmailVerificationBanner />

      <header className="page-header">
        <h1>{t('tagsPage.title')}</h1>
        <button type="button" className="button" onClick={() => openEditor({ kind: 'create-group' })}>
          {t('tagsPage.addGroup')}
        </button>
      </header>

      <p className="muted tag-visibility-hint">
        {t('tagsPage.hint', { limit: visibleLimit, count: visibleCount })}
      </p>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {pendingDelete ? (
        <ConfirmDialog
          open
          title={
            pendingDelete.kind === 'group'
              ? t('confirm.deleteGroupTitle')
              : t('confirm.deleteTagTitle')
          }
          message={
            pendingDelete.kind === 'group'
              ? t('confirm.deleteGroup', { label: pendingDelete.group.label })
              : t('confirm.deleteTag', { label: pendingDelete.tag.label })
          }
          confirmLabel={t('common.delete')}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => {
            const action = pendingDelete
            setPendingDelete(null)
            if (action.kind === 'group') {
              void handleDeleteGroup(action.group)
            } else {
              void handleDeleteTag(action.group, action.tag)
            }
          }}
        />
      ) : null}
      {isLoading ? <p className="muted">{t('common.loadingTags')}</p> : null}

      {editor && editorTitle ? (
        <form className="card form appearance-form" onSubmit={(event) => void handleSubmit(event)}>
          <h2>{editorTitle}</h2>
          <FormField
            id="tag-name"
            label={t('common.name')}
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            autoFocus
            maxLength={64}
          />
          {editingTag ? (
            <TagIconEditor
              color={draftColor}
              onColorChange={setDraftColor}
              emoji={draftEmoji}
              onEmojiChange={setDraftEmoji}
              groupId={editor.kind === 'edit-tag' || editor.kind === 'create-tag' ? editor.group.id : undefined}
              tag={editor.kind === 'edit-tag' ? editor.tag : undefined}
              pendingUpload={editor.kind === 'create-tag' ? pendingUpload : null}
              onPendingUploadChange={
                editor.kind === 'create-tag' ? setPendingUpload : undefined
              }
              onTagChange={
                editor.kind === 'edit-tag'
                  ? (updated) => {
                      if (updated.icon_type === 'emoji') {
                        setDraftEmoji(updated.icon)
                      }
                      setDraftColor(updated.color)
                      setEditor({ kind: 'edit-tag', group: editor.group, tag: updated })
                      setGroups((current) =>
                        current.map((group) =>
                          group.id === editor.group.id
                            ? {
                                ...group,
                                tags: group.tags.map((item) =>
                                  item.id === updated.id ? updated : item,
                                ),
                              }
                            : group,
                        ),
                      )
                    }
                  : undefined
              }
              disabled={isSaving}
            />
          ) : null}
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

      <div className="tag-groups-list">
        {groups.map((group) => (
          <article
            key={group.id}
            className={`card tag-group-card${draggingGroupId === group.id ? ' is-dragging' : ''}`}
            draggable
            onDragStart={() => setDraggingGroupId(group.id)}
            onDragOver={(event: DragEvent) => event.preventDefault()}
            onDrop={() => void handleGroupDrop(group.id)}
            onDragEnd={() => setDraggingGroupId(null)}
          >
            <header className="tag-group-card-header">
              <PopupMenu
                label={<h2>{group.label}</h2>}
                ariaLabel={t('tagsPage.actionsFor', { label: group.label })}
                onEdit={() => openEditor({ kind: 'edit-group', group })}
                onDelete={() => setPendingDelete({ kind: 'group', group })}
              />
              <label className="tag-visibility-toggle">
                <input
                  type="checkbox"
                  checked={group.show_on_entry}
                  disabled={
                    togglingGroupId === group.id || (!group.show_on_entry && atVisibleLimit)
                  }
                  onChange={() => void handleToggleShowOnEntry(group)}
                />
                <span>{t('tagsPage.showOnEntry')}</span>
              </label>
            </header>
            <ul className="tag-list">
              {group.tags.map((tag) => (
                <li
                  key={tag.id}
                  className={
                    draggingTag?.tagId === tag.id && draggingTag.groupId === group.id
                      ? 'is-dragging'
                      : undefined
                  }
                  draggable
                  onDragStart={(event) => {
                    event.stopPropagation()
                    setDraggingTag({ groupId: group.id, tagId: tag.id })
                  }}
                  onDragOver={(event: DragEvent) => {
                    event.preventDefault()
                    event.stopPropagation()
                  }}
                  onDrop={(event) => {
                    event.stopPropagation()
                    void handleTagDrop(group, tag.id)
                  }}
                  onDragEnd={() => setDraggingTag(null)}
                >
                  <PopupMenu
                    label={
                      <span className="tag-list-item-label">
                        <span
                          className="tag-list-item-icon"
                          style={{
                            background: moodSubtleFill(tag.color),
                            filter: moodGlowFilter(tag.color, 'xs'),
                          }}
                        >
                          <TagIcon
                            style={{
                              color: tag.color,
                              icon_type: tag.icon_type,
                              icon: tag.icon,
                            }}
                          />
                        </span>
                        {tag.label}
                      </span>
                    }
                    ariaLabel={t('tagsPage.actionsFor', { label: tag.label })}
                    onEdit={() => openEditor({ kind: 'edit-tag', group, tag })}
                    onDelete={() => setPendingDelete({ kind: 'tag', group, tag })}
                  />
                  <span className="tag-drag-hint muted" aria-hidden="true">
                    ⋮⋮
                  </span>
                </li>
              ))}
              <li className="tag-list-add">
                <button
                  type="button"
                  className="icon-button-add"
                  aria-label={t('tagsPage.addTagTo', { label: group.label })}
                  onClick={() => openEditor({ kind: 'create-tag', group })}
                >
                  +
                </button>
              </li>
            </ul>
          </article>
        ))}
      </div>

      <p className="muted">
        <Link to="/">{t('common.backToEntries')}</Link>
      </p>
    </section>
  )
}
