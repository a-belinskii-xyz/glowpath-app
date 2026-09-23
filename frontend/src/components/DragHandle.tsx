import { IconButton } from './IconButton'
import { DragHandleIcon } from './icons'

type DragHandleProps = {
  label: string
  onMoveUp?: () => void
  onMoveDown?: () => void
  onDragStart?: () => void
  onDragEnd?: () => void
}

export function DragHandle({
  label,
  onMoveUp,
  onMoveDown,
  onDragStart,
  onDragEnd,
}: DragHandleProps) {
  return (
    <IconButton
      label={label}
      className="drag-handle"
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onKeyDown={(event) => {
        if (event.key === 'ArrowUp') {
          event.preventDefault()
          onMoveUp?.()
        } else if (event.key === 'ArrowDown') {
          event.preventDefault()
          onMoveDown?.()
        }
      }}
    >
      <DragHandleIcon />
    </IconButton>
  )
}
