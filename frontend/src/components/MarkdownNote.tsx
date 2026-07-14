import type { Components } from 'react-markdown'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type MarkdownNoteProps = {
  content: string
  /** Compact layout for feed rows (clamped height, non-interactive links). */
  compact?: boolean
  className?: string
}

const compactComponents: Components = {
  a: ({ children }) => <span className="markdown-note-link-plain">{children}</span>,
}

export function MarkdownNote({ content, compact = false, className }: MarkdownNoteProps) {
  const classes = [
    'markdown-note',
    compact ? 'markdown-note-compact' : null,
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={classes}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={compact ? compactComponents : undefined}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
