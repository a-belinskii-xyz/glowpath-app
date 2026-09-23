import type { MoodEntryPublic } from '../types/mood'
import type { ComposerBlockPreference } from '../types/moodPreferences'

export type EntryComposerBlockId = 'mood' | 'note' | 'tags' | 'goals' | 'attachments'

export type EntryComposerBlockMeta = {
  id: EntryComposerBlockId
  defaultEnabled: boolean
  /** Pinned blocks stay first and cannot be disabled or reordered. */
  pinned: boolean
  labelKey: string
  hintKey?: string
  hasData: (entry: MoodEntryPublic | undefined) => boolean
}

export type ResolvedComposerBlock = {
  id: EntryComposerBlockId
  enabled: boolean
  pinned: boolean
  labelKey: string
  hintKey?: string
}

const BLOCK_ORDER: EntryComposerBlockId[] = ['mood', 'note', 'tags', 'goals', 'attachments']

export const ENTRY_COMPOSER_BLOCKS: Record<EntryComposerBlockId, EntryComposerBlockMeta> = {
  mood: {
    id: 'mood',
    defaultEnabled: true,
    pinned: true,
    labelKey: 'entryComposer.blocks.mood',
    hintKey: 'entryComposer.blocks.moodHint',
    hasData: () => true,
  },
  note: {
    id: 'note',
    defaultEnabled: true,
    pinned: false,
    labelKey: 'entryComposer.blocks.note',
    hintKey: 'entryComposer.blocks.noteHint',
    hasData: (entry) => Boolean(entry?.note?.trim()),
  },
  tags: {
    id: 'tags',
    defaultEnabled: true,
    pinned: false,
    labelKey: 'entryComposer.blocks.tags',
    hintKey: 'entryComposer.blocks.tagsHint',
    hasData: (entry) => (entry?.tags.length ?? 0) > 0,
  },
  goals: {
    id: 'goals',
    defaultEnabled: true,
    pinned: false,
    labelKey: 'entryComposer.blocks.goals',
    hintKey: 'entryComposer.blocks.goalsHint',
    hasData: (entry) => (entry?.goals.length ?? 0) > 0,
  },
  attachments: {
    id: 'attachments',
    defaultEnabled: true,
    pinned: false,
    labelKey: 'entryComposer.blocks.attachments',
    hintKey: 'entryComposer.blocks.attachmentsHint',
    hasData: (entry) => (entry?.attachments.length ?? 0) > 0,
  },
}

function isKnownBlockId(id: string): id is EntryComposerBlockId {
  return id in ENTRY_COMPOSER_BLOCKS
}

export function defaultComposerLayout(): ResolvedComposerBlock[] {
  return BLOCK_ORDER.map((id) => {
    const meta = ENTRY_COMPOSER_BLOCKS[id]
    return {
      id: meta.id,
      enabled: meta.defaultEnabled,
      pinned: meta.pinned,
      labelKey: meta.labelKey,
      hintKey: meta.hintKey,
    }
  })
}

/**
 * Merge saved preferences with the current registry.
 * - Unknown ids are dropped.
 * - Missing registry ids are appended with defaultEnabled.
 * - Mood is always first and enabled.
 */
export function resolveComposerLayout(
  saved: ComposerBlockPreference[] | null | undefined,
): ResolvedComposerBlock[] {
  if (!saved || saved.length === 0) {
    return defaultComposerLayout()
  }

  const seen = new Set<EntryComposerBlockId>()
  const ordered: ResolvedComposerBlock[] = []

  for (const item of saved) {
    if (!item || typeof item.id !== 'string' || !isKnownBlockId(item.id)) {
      continue
    }
    if (seen.has(item.id)) {
      continue
    }
    seen.add(item.id)
    const meta = ENTRY_COMPOSER_BLOCKS[item.id]
    ordered.push({
      id: meta.id,
      enabled: meta.pinned ? true : Boolean(item.enabled),
      pinned: meta.pinned,
      labelKey: meta.labelKey,
      hintKey: meta.hintKey,
    })
  }

  for (const id of BLOCK_ORDER) {
    if (seen.has(id)) {
      continue
    }
    const meta = ENTRY_COMPOSER_BLOCKS[id]
    ordered.push({
      id: meta.id,
      enabled: meta.defaultEnabled,
      pinned: meta.pinned,
      labelKey: meta.labelKey,
      hintKey: meta.hintKey,
    })
  }

  const mood = ordered.find((block) => block.id === 'mood') ?? {
    id: 'mood' as const,
    enabled: true,
    pinned: true,
    labelKey: ENTRY_COMPOSER_BLOCKS.mood.labelKey,
    hintKey: ENTRY_COMPOSER_BLOCKS.mood.hintKey,
  }
  const rest = ordered.filter((block) => block.id !== 'mood')
  return [{ ...mood, enabled: true, pinned: true }, ...rest]
}

export function composerLayoutToPreferences(
  layout: ResolvedComposerBlock[],
): ComposerBlockPreference[] {
  return resolveComposerLayout(layout).map((block) => ({
    id: block.id,
    enabled: block.enabled,
  }))
}

export function isComposerBlockVisible(
  block: ResolvedComposerBlock,
  mode: 'create' | 'edit',
  entry: MoodEntryPublic | undefined,
): boolean {
  if (block.id === 'mood' || block.pinned) {
    return true
  }
  if (block.enabled) {
    return true
  }
  if (mode === 'edit') {
    return ENTRY_COMPOSER_BLOCKS[block.id].hasData(entry)
  }
  return false
}

export function isComposerBlockEnabled(
  layout: ResolvedComposerBlock[],
  id: EntryComposerBlockId,
): boolean {
  return layout.find((block) => block.id === id)?.enabled ?? ENTRY_COMPOSER_BLOCKS[id].defaultEnabled
}
