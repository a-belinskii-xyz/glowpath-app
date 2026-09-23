import { moodChipStyle } from '../design'
import { useColorScheme } from '../hooks/useColorScheme'
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
  const colorScheme = useColorScheme()
  return (
    <>
      {items.map((item) => {
        const chip = moodChipStyle(item.color, colorScheme)
        return (
        <span
          key={item.id}
          className={`entry-tag entry-tag-compact${kind === 'goal' ? ' entry-goal' : ''}`}
          style={chip}
        >
          {kind === 'tag' ? (
            <TagIcon
              style={{ color: chip.color, icon_type: item.icon_type, icon: item.icon }}
              className="entry-tag-icon"
            />
          ) : (
            <GoalIcon
              style={{ color: chip.color, icon_type: item.icon_type, icon: item.icon }}
              className="entry-goal-icon"
            />
          )}
          <span className="entry-tag-compact-label">
            {item.label}
            {kind === 'goal' && 'amount' in item && item.amount != null
              ? ` · ${item.amount}${item.unit ? ` ${item.unit}` : ''}`
              : ''}
          </span>
        </span>
        )
      })}
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
