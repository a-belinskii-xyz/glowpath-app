import { type DragEvent, type FormEvent, useCallback, useEffect, useState } from 'react'
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
import { ConfirmDialog } from '../components/ConfirmDialog'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { DragHandle } from '../components/DragHandle'
import { EditorDrawer } from '../components/EditorDrawer'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { FormField } from '../components/FormField'
import { IconButton } from '../components/IconButton'
import { ArrowDownIcon, ArrowUpIcon, DeleteIcon, EditIcon } from '../components/icons'
import { OverflowMenu } from '../components/OverflowMenu'
import { TagIcon } from '../components/TagIcon'
import { TagIconEditor, type PendingIconUpload } from '../components/TagIconEditor'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useLocale } from '../context/LocaleContext'
import { moodGlowFilter } from '../design'
import { ApiError, formatApiError } from '../lib/errors'
import {
  dropEdgeFromClientY,
  dropIndexForEdge,
  moveItem,
  moveItemById,
  type DropEdge,
} from '../lib/listReorder'
import { isValidHexColor } from '../lib/moodScale'
import { DEFAULT_TAG_STYLE, type TagGroupPublic, type TagPublic } from '../types/tag'

type EditorMode =
  | { kind: 'create-group' }
  | { kind: 'edit-group'; group: TagGroupPublic }
  | { kind: 'create-tag'; group: TagGroupPublic }
  | { kind: 'edit-tag'; group: TagGroupPublic; tag: TagPublic }

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
  const [pendingUpload, setPendingUpload] = useState<PendingIconUpload | null>(null)
  const [pendingCatalogIconId, setPendingCatalogIconId] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [togglingGroupId, setTogglingGroupId] = useState<string | null>(null)
  const [draggingGroupId, setDraggingGroupId] = useState<string | null>(null)
  const [draggingTag, setDraggingTag] = useState<{ groupId: string; tagId: string } | null>(null)
  const [groupDropTarget, setGroupDropTarget] = useState<{
    id: string
    edge: DropEdge
  } | null>(null)
  const [tagDropTarget, setTagDropTarget] = useState<{
    groupId: string
    tagId: string
    edge: DropEdge
  } | null>(null)
  const [pendingDelete, setPendingDelete] = useState<
    | { kind: 'group'; group: TagGroupPublic }
    | { kind: 'tag'; group: TagGroupPublic; tag: TagPublic }
    | null
  >(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

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
          setError(formatApiError(err, t, 'errors.failedLoadTags'))
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
      setPendingCatalogIconId(null)
    } else if (mode.kind === 'edit-group') {
      setName(mode.group.label)
      setPendingUpload(null)
      setPendingCatalogIconId(null)
    } else {
      setName(mode.tag.label)
      setDraftColor(mode.tag.color)
      setDraftEmoji(mode.tag.icon_type === 'emoji' ? mode.tag.icon : DEFAULT_TAG_STYLE.icon)
      setPendingUpload(null)
      setPendingCatalogIconId(null)
    }
  }

  const closeEditor = useCallback(() => {
    setEditor(null)
    setName('')
    setDraftColor(DEFAULT_TAG_STYLE.color)
    setDraftEmoji(DEFAULT_TAG_STYLE.icon)
    setPendingUpload(null)
    setPendingCatalogIconId(null)
  }, [])

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
      const usingCatalog =
        (editor.kind === 'edit-tag' && editor.tag.icon_type === 'catalog') ||
        (editor.kind === 'create-tag' && pendingCatalogIconId !== null)
      if (!usingUpload && !usingCatalog && !emoji) {
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
          icon_type: pendingCatalogIconId ? 'catalog' : 'emoji',
          icon: pendingCatalogIconId ?? (draftEmoji.trim() || DEFAULT_TAG_STYLE.icon),
        })
        if (pendingUpload) {
          await uploadTagIcon(
            editor.group.id,
            created.id,
            pendingUpload.cropped,
            pendingUpload.source,
          )
        }
      } else {
        const keepAssignedIcon =
          editor.tag.icon_type === 'upload' || editor.tag.icon_type === 'catalog'
        await patchTag(editor.group.id, editor.tag.id, {
          labels,
          color: draftColor,
          ...(keepAssignedIcon ? {} : { icon_type: 'emoji' as const, icon: draftEmoji.trim() }),
        })
      }
      await reload()
      closeEditor()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteGroup = async (group: TagGroupPublic) => {
    setDeleteError(null)
    setIsDeleting(true)
    try {
      await deleteTagGroup(group.id)
      await reload()
      setPendingDelete(null)
      if (editor && 'group' in editor && editor.group.id === group.id) {
        closeEditor()
      }
    } catch (err) {
      setDeleteError(formatApiError(err, t, 'errors.failedDeleteGroup'))
    } finally {
      setIsDeleting(false)
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
      setError(formatApiError(err, t, 'errors.failedUpdateVisibility'))
    } finally {
      setTogglingGroupId(null)
    }
  }

  const handleDeleteTag = async (group: TagGroupPublic, tag: TagPublic) => {
    setDeleteError(null)
    setIsDeleting(true)
    try {
      await deleteTag(group.id, tag.id)
      await reload()
      setPendingDelete(null)
      if (editor?.kind === 'edit-tag' && editor.tag.id === tag.id) {
        closeEditor()
      }
    } catch (err) {
      setDeleteError(formatApiError(err, t, 'errors.failedDeleteTag'))
    } finally {
      setIsDeleting(false)
    }
  }

  const persistGroupOrder = async (next: TagGroupPublic[], previous: TagGroupPublic[]) => {
    setGroups(next)
    try {
      const response = await reorderTagGroups({ ordered_ids: next.map((group) => group.id) })
      setGroups(response.items)
    } catch (err) {
      setGroups(previous)
      setError(formatApiError(err, t, 'errors.failedReorderGroups'))
    }
  }

  const clearGroupDrag = () => {
    setDraggingGroupId(null)
    setGroupDropTarget(null)
  }

  const clearTagDrag = () => {
    setDraggingTag(null)
    setTagDropTarget(null)
  }

  const handleGroupDrop = async (targetGroupId: string, edge: DropEdge) => {
    if (!draggingGroupId || draggingGroupId === targetGroupId) {
      clearGroupDrag()
      return
    }
    const fromIndex = groups.findIndex((group) => group.id === draggingGroupId)
    const targetIndex = groups.findIndex((group) => group.id === targetGroupId)
    clearGroupDrag()
    if (fromIndex < 0 || targetIndex < 0) return
    const toIndex = dropIndexForEdge(fromIndex, targetIndex, edge)
    if (toIndex === fromIndex) return
    await persistGroupOrder(moveItem(groups, fromIndex, toIndex), groups)
  }

  const handleMoveGroup = async (groupId: string, direction: 'up' | 'down') => {
    const next = moveItemById(groups, groupId, direction)
    if (next === groups) return
    await persistGroupOrder(next, groups)
  }

  const handleTagDrop = async (
    group: TagGroupPublic,
    targetTagId: string,
    edge: DropEdge,
  ) => {
    if (!draggingTag || draggingTag.groupId !== group.id || draggingTag.tagId === targetTagId) {
      clearTagDrag()
      return
    }
    const fromIndex = group.tags.findIndex((tag) => tag.id === draggingTag.tagId)
    const targetIndex = group.tags.findIndex((tag) => tag.id === targetTagId)
    clearTagDrag()
    if (fromIndex < 0 || targetIndex < 0) return
    const toIndex = dropIndexForEdge(fromIndex, targetIndex, edge)
    if (toIndex === fromIndex) return

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
      setError(formatApiError(err, t, 'errors.failedReorderTags'))
    }
  }

  const handleMoveTag = async (
    group: TagGroupPublic,
    tagId: string,
    direction: 'up' | 'down',
  ) => {
    const nextTags = moveItemById(group.tags, tagId, direction)
    if (nextTags === group.tags) return
    const previous = groups
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
      setError(formatApiError(err, t, 'errors.failedReorderTags'))
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

  const selectedGroupId =
    editor && 'group' in editor
      ? editor.group.id
      : editor?.kind === 'create-group'
        ? null
        : null
  const selectedTagId = editor?.kind === 'edit-tag' ? editor.tag.id : null
  const drawerColors = groups.flatMap((group) => group.tags.map((tag) => tag.color))
  usePageAmbientGlow(drawerColors)

  return (
    <section className="page">
      <EmailVerificationBanner />

      <header className="page-header">
        <h1>{t('tagsPage.title')}</h1>
        <button type="button" className="button" onClick={() => openEditor({ kind: 'create-group' })}>
          {t('tagsPage.addGroup')}
        </button>
      </header>

      <div className="limit-pills">
        <span className="limit-pill">
          {t('tagsPage.hintCompact', { limit: visibleLimit, count: visibleCount })}
        </span>
      </div>

      <PageErrorAlert error={error} />
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
          isBusy={isDeleting}
          error={deleteError}
          onCancel={() => {
            if (isDeleting) return
            setPendingDelete(null)
            setDeleteError(null)
          }}
          onConfirm={() => {
            if (pendingDelete.kind === 'group') {
              void handleDeleteGroup(pendingDelete.group)
            } else {
              void handleDeleteTag(pendingDelete.group, pendingDelete.tag)
            }
          }}
        />
      ) : null}
      {isLoading ? <p className="muted">{t('common.loadingTags')}</p> : null}

      <EditorDrawer
        open={Boolean(editor && editorTitle)}
        title={editorTitle ?? ''}
        onClose={closeEditor}
        accentColors={drawerColors}
      >
        <form className="form appearance-form-drawer" onSubmit={(event) => void handleSubmit(event)}>
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
              groupId={
                editor.kind === 'edit-tag' || editor.kind === 'create-tag'
                  ? editor.group.id
                  : undefined
              }
              tag={editor.kind === 'edit-tag' ? editor.tag : undefined}
              pendingUpload={editor.kind === 'create-tag' ? pendingUpload : null}
              onPendingUploadChange={
                editor.kind === 'create-tag' ? setPendingUpload : undefined
              }
              pendingCatalogIconId={
                editor.kind === 'create-tag' ? pendingCatalogIconId : null
              }
              onPendingCatalogChange={
                editor.kind === 'create-tag' ? setPendingCatalogIconId : undefined
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
              <StableButtonLabel
                active={isSaving ? t('common.saving') : t('common.save')}
                labels={[t('common.save'), t('common.saving')]}
              />
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

      <div className="tag-groups-list">
        {groups.map((group, groupIndex) => (
          <article
            key={group.id}
            className={[
              'card',
              'tag-group-card',
              draggingGroupId === group.id ? 'is-dragging' : '',
              selectedGroupId === group.id ? 'is-selected' : '',
              groupDropTarget?.id === group.id ? `is-drop-${groupDropTarget.edge}` : '',
            ]
              .filter(Boolean)
              .join(' ')}
            onDragOver={(event: DragEvent) => {
              if (!draggingGroupId || draggingGroupId === group.id) return
              event.preventDefault()
              const edge = dropEdgeFromClientY(event.clientY, event.currentTarget)
              setGroupDropTarget((current) =>
                current?.id === group.id && current.edge === edge
                  ? current
                  : { id: group.id, edge },
              )
            }}
            onDragLeave={(event: DragEvent) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node)) {
                setGroupDropTarget((current) => (current?.id === group.id ? null : current))
              }
            }}
            onDrop={(event: DragEvent) => {
              event.preventDefault()
              const edge =
                groupDropTarget?.id === group.id
                  ? groupDropTarget.edge
                  : dropEdgeFromClientY(event.clientY, event.currentTarget)
              void handleGroupDrop(group.id, edge)
            }}
          >
            <header className="tag-group-card-header">
              <div className="tag-group-title-row">
                <h2>{group.label}</h2>
                <div className="list-row-actions">
                  <IconButton
                    label={t('common.edit')}
                    size="sm"
                    onClick={() => openEditor({ kind: 'edit-group', group })}
                  >
                    <EditIcon />
                  </IconButton>
                  <div className="list-row-actions-extra">
                    <IconButton
                      label={t('tagsPage.moveUp')}
                      size="sm"
                      disabled={groupIndex === 0}
                      onClick={() => void handleMoveGroup(group.id, 'up')}
                    >
                      <ArrowUpIcon />
                    </IconButton>
                    <IconButton
                      label={t('tagsPage.moveDown')}
                      size="sm"
                      disabled={groupIndex === groups.length - 1}
                      onClick={() => void handleMoveGroup(group.id, 'down')}
                    >
                      <ArrowDownIcon />
                    </IconButton>
                    <IconButton
                      label={t('common.delete')}
                      size="sm"
                      variant="danger"
                      onClick={() => {
                        setDeleteError(null)
                        setPendingDelete({ kind: 'group', group })
                      }}
                    >
                      <DeleteIcon />
                    </IconButton>
                    <DragHandle
                      label={t('tagsPage.dragGroup', { label: group.label })}
                      onDragStart={() => {
                        setDraggingGroupId(group.id)
                        setGroupDropTarget(null)
                      }}
                      onDragEnd={clearGroupDrag}
                      onMoveUp={() => void handleMoveGroup(group.id, 'up')}
                      onMoveDown={() => void handleMoveGroup(group.id, 'down')}
                    />
                  </div>
                  <OverflowMenu
                    className="list-row-actions-menu"
                    items={[
                      {
                        label: t('tagsPage.moveUp'),
                        disabled: groupIndex === 0,
                        onClick: () => void handleMoveGroup(group.id, 'up'),
                      },
                      {
                        label: t('tagsPage.moveDown'),
                        disabled: groupIndex === groups.length - 1,
                        onClick: () => void handleMoveGroup(group.id, 'down'),
                      },
                      {
                        label: t('common.delete'),
                        danger: true,
                        onClick: () => {
                          setDeleteError(null)
                          setPendingDelete({ kind: 'group', group })
                        },
                      },
                    ]}
                  />
                </div>
              </div>
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
              {group.tags.map((tag, tagIndex) => {
                const isDraggingTag =
                  draggingTag?.tagId === tag.id && draggingTag.groupId === group.id
                const dropEdge =
                  tagDropTarget?.groupId === group.id && tagDropTarget.tagId === tag.id
                    ? tagDropTarget.edge
                    : null
                return (
                  <li
                    key={tag.id}
                    className={[
                      isDraggingTag ? 'is-dragging' : '',
                      selectedTagId === tag.id ? 'is-selected' : '',
                      dropEdge ? `is-drop-${dropEdge}` : '',
                    ]
                      .filter(Boolean)
                      .join(' ') || undefined}
                    onDragOver={(event: DragEvent) => {
                      if (
                        !draggingTag ||
                        draggingTag.groupId !== group.id ||
                        draggingTag.tagId === tag.id
                      ) {
                        return
                      }
                      event.preventDefault()
                      event.stopPropagation()
                      const edge = dropEdgeFromClientY(event.clientY, event.currentTarget)
                      setTagDropTarget((current) =>
                        current?.groupId === group.id &&
                        current.tagId === tag.id &&
                        current.edge === edge
                          ? current
                          : { groupId: group.id, tagId: tag.id, edge },
                      )
                    }}
                    onDragLeave={(event: DragEvent) => {
                      if (!event.currentTarget.contains(event.relatedTarget as Node)) {
                        setTagDropTarget((current) =>
                          current?.groupId === group.id && current.tagId === tag.id
                            ? null
                            : current,
                        )
                      }
                    }}
                    onDrop={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                      const edge =
                        tagDropTarget?.groupId === group.id && tagDropTarget.tagId === tag.id
                          ? tagDropTarget.edge
                          : dropEdgeFromClientY(event.clientY, event.currentTarget)
                      void handleTagDrop(group, tag.id, edge)
                    }}
                  >
                    <span className="tag-list-item-label">
                      <span
                        className="mood-preferences-swatch"
                        style={{ backgroundColor: tag.color }}
                        aria-hidden
                      />
                      <span
                        className="tag-list-item-icon"
                        style={{ filter: moodGlowFilter(tag.color) }}
                      >
                        <TagIcon
                          style={{
                            color: tag.color,
                            icon_type: tag.icon_type,
                            icon: tag.icon,
                          }}
                        />
                      </span>
                      <span className="tag-list-item-text">{tag.label}</span>
                    </span>
                    <div className="list-row-actions">
                      <IconButton
                        label={t('common.edit')}
                        size="sm"
                        onClick={() => openEditor({ kind: 'edit-tag', group, tag })}
                      >
                        <EditIcon />
                      </IconButton>
                      <div className="list-row-actions-extra">
                        <IconButton
                          label={t('tagsPage.moveUp')}
                          size="sm"
                          disabled={tagIndex === 0}
                          onClick={() => void handleMoveTag(group, tag.id, 'up')}
                        >
                          <ArrowUpIcon />
                        </IconButton>
                        <IconButton
                          label={t('tagsPage.moveDown')}
                          size="sm"
                          disabled={tagIndex === group.tags.length - 1}
                          onClick={() => void handleMoveTag(group, tag.id, 'down')}
                        >
                          <ArrowDownIcon />
                        </IconButton>
                        <IconButton
                          label={t('common.delete')}
                          size="sm"
                          variant="danger"
                          onClick={() => {
                            setDeleteError(null)
                            setPendingDelete({ kind: 'tag', group, tag })
                          }}
                        >
                          <DeleteIcon />
                        </IconButton>
                        <DragHandle
                          label={t('tagsPage.dragTag', { label: tag.label })}
                          onDragStart={() => {
                            setDraggingTag({ groupId: group.id, tagId: tag.id })
                            setTagDropTarget(null)
                          }}
                          onDragEnd={clearTagDrag}
                          onMoveUp={() => void handleMoveTag(group, tag.id, 'up')}
                          onMoveDown={() => void handleMoveTag(group, tag.id, 'down')}
                        />
                      </div>
                      <OverflowMenu
                        className="list-row-actions-menu"
                        items={[
                          {
                            label: t('tagsPage.moveUp'),
                            disabled: tagIndex === 0,
                            onClick: () => void handleMoveTag(group, tag.id, 'up'),
                          },
                          {
                            label: t('tagsPage.moveDown'),
                            disabled: tagIndex === group.tags.length - 1,
                            onClick: () => void handleMoveTag(group, tag.id, 'down'),
                          },
                          {
                            label: t('common.delete'),
                            danger: true,
                            onClick: () => {
                              setDeleteError(null)
                              setPendingDelete({ kind: 'tag', group, tag })
                            },
                          },
                        ]}
                      />
                    </div>
                  </li>
                )
              })}
              <li className="tag-list-add">
                <button
                  type="button"
                  className="button button-secondary button-small tag-list-add-button"
                  onClick={() => openEditor({ kind: 'create-tag', group })}
                >
                  <span aria-hidden="true">+</span>
                  {t('tagsPage.addTag')}
                </button>
              </li>
            </ul>
          </article>
        ))}
      </div>

      <p className="muted page-back-link">
        <Link to="/">{t('common.backToEntries')}</Link>
      </p>
    </section>
  )
}
