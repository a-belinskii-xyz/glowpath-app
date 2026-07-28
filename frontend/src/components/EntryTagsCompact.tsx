import { moodSubtleFill } from '../design'
import type { MoodEntryGoal, MoodEntryTag } from '../types/mood'
import { GoalIcon } from './GoalIcon'
import { TagIcon } from './TagIcon'

type EntryTagsCompactProps = {
  tags?: MoodEntryTag[]
  goals?: MoodEntryGoal[]
  maxVisible?: number
}

function CompactChips({
  items,
  kind,
}: {
  items: MoodEntryTag[] | MoodEntryGoal[]
  kind: 'tag' | 'goal'
}) {
  return (
    <>
      {items.map((item) => (
        <span
          key={item.id}
          className={`entry-tag entry-tag-compact${kind === 'goal' ? ' entry-goal' : ''}`}
          style={
            kind === 'tag'
              ? { background: moodSubtleFill(item.color), color: item.color }
              : undefined
          }
        >
          {kind === 'tag' ? (
            <TagIcon
              style={{ color: item.color, icon_type: item.icon_type, icon: item.icon }}
              className="entry-tag-icon"
            />
          ) : (
            <GoalIcon
              style={{ color: item.color, icon_type: item.icon_type, icon: item.icon }}
              className="entry-goal-icon"
            />
          )}
          <span className="entry-tag-compact-label">{item.label}</span>
        </span>
      ))}
    </>
  )
}

export function EntryTagsCompact({
  tags = [],
  goals = [],
  maxVisible = 9,
}: EntryTagsCompactProps) {
  const total = tags.length + goals.length
  const visibleTags = tags.slice(0, maxVisible)
  const remainingBudget = Math.max(0, maxVisible - visibleTags.length)
  const visibleGoals = goals.slice(0, remainingBudget)
  const hasMore = total > maxVisible

  if (total === 0) {
    return null
  }

  return (
    <div className="entry-tags">
      <CompactChips items={visibleTags} kind="tag" />
      <CompactChips items={visibleGoals} kind="goal" />
      {hasMore ? <span className="entry-tag entry-tag-ellipsis">…</span> : null}
    </div>
  )
}
