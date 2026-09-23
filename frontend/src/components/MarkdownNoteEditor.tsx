import { Extension } from '@tiptap/core'
import type { Editor } from '@tiptap/react'
import Placeholder from '@tiptap/extension-placeholder'
import { Markdown } from '@tiptap/markdown'
import { Plugin } from '@tiptap/pm/state'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { useLocale } from '../context/LocaleContext'
import {
  NOTE_CONTENT_MAX_LENGTH,
  NOTE_RAW_MAX_LENGTH,
} from '../lib/markdownPlainText'

type MarkdownNoteEditorProps = {
  value: string
  onChange: (value: string) => void
  maxLength?: number
  placeholder?: string
  label?: string
  /** `full` always visible; `simple` compact always; `selection` Notion-style bubble. */
  toolbar?: 'full' | 'simple' | 'selection'
  /** Where to put a static toolbar. Default: before the field. */
  toolbarPlacement?: 'before' | 'after'
  size?: 'default' | 'large'
  actions?: ReactNode
}

function plainTextFromDoc(doc: {
  textBetween: (from: number, to: number, blockSep?: string, leafSep?: string) => string
  content: { size: number }
}) {
  return doc.textBetween(0, doc.content.size, '\n', '\n')
}

function createContentLimitExtension(maxContentLength: number) {
  return Extension.create({
    name: 'noteContentLimit',
    addProseMirrorPlugins() {
      return [
        new Plugin({
          filterTransaction: (transaction) => {
            if (!transaction.docChanged) {
              return true
            }
            return plainTextFromDoc(transaction.doc).length <= maxContentLength
          },
        }),
      ]
    },
  })
}

type BubblePos = { top: number; left: number }

function SelectionToolbar({
  editor,
  toolbar,
  onSetLink,
}: {
  editor: Editor
  toolbar: 'full' | 'simple'
  onSetLink: () => void
}) {
  const { t } = useLocale()
  const [pos, setPos] = useState<BubblePos | null>(null)
  const bubbleRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const update = () => {
      const { from, to, empty } = editor.state.selection
      if (empty || from === to) {
        setPos(null)
        return
      }
      const start = editor.view.coordsAtPos(from)
      const end = editor.view.coordsAtPos(to)
      const left = (start.left + end.right) / 2
      const top = Math.min(start.top, end.top) - 8
      setPos({ top, left })
    }

    update()
    editor.on('selectionUpdate', update)
    editor.on('transaction', update)
    window.addEventListener('scroll', update, true)
    window.addEventListener('resize', update)
    return () => {
      editor.off('selectionUpdate', update)
      editor.off('transaction', update)
      window.removeEventListener('scroll', update, true)
      window.removeEventListener('resize', update)
    }
  }, [editor])

  if (!pos) {
    return null
  }

  return createPortal(
    <div
      ref={bubbleRef}
      className="markdown-selection-toolbar"
      role="toolbar"
      aria-label={t('markdown.formatting')}
      style={{
        top: `${pos.top}px`,
        left: `${pos.left}px`,
      }}
      onMouseDown={(event) => {
        // Keep editor selection while clicking toolbar buttons.
        event.preventDefault()
      }}
    >
      {toolbar === 'full' ? (
        <button
          type="button"
          className={`markdown-toolbar-btn${editor.isActive('heading', { level: 2 }) ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          title={t('markdown.heading')}
          aria-pressed={editor.isActive('heading', { level: 2 })}
        >
          H
        </button>
      ) : null}
      <button
        type="button"
        className={`markdown-toolbar-btn${editor.isActive('bold') ? ' markdown-toolbar-btn-active' : ''}`}
        onClick={() => editor.chain().focus().toggleBold().run()}
        title={t('markdown.bold')}
        aria-pressed={editor.isActive('bold')}
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        className={`markdown-toolbar-btn${editor.isActive('italic') ? ' markdown-toolbar-btn-active' : ''}`}
        onClick={() => editor.chain().focus().toggleItalic().run()}
        title={t('markdown.italic')}
        aria-pressed={editor.isActive('italic')}
      >
        <em>I</em>
      </button>
      <button
        type="button"
        className={`markdown-toolbar-btn${editor.isActive('link') ? ' markdown-toolbar-btn-active' : ''}`}
        onClick={onSetLink}
        title={t('markdown.link')}
        aria-pressed={editor.isActive('link')}
      >
        {t('markdown.link')}
      </button>
      <button
        type="button"
        className={`markdown-toolbar-btn${editor.isActive('bulletList') ? ' markdown-toolbar-btn-active' : ''}`}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        title={t('markdown.bulletList')}
        aria-pressed={editor.isActive('bulletList')}
      >
        {t('markdown.list')}
      </button>
      {toolbar === 'full' ? (
        <button
          type="button"
          className={`markdown-toolbar-btn${editor.isActive('blockquote') ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          title={t('markdown.quote')}
          aria-pressed={editor.isActive('blockquote')}
        >
          {t('markdown.quote')}
        </button>
      ) : null}
    </div>,
    document.body,
  )
}

function StaticToolbar({
  editor,
  toolbar,
  onSetLink,
}: {
  editor: Editor | null
  toolbar: 'full' | 'simple'
  onSetLink: () => void
}) {
  const { t } = useLocale()
  return (
    <div className="markdown-editor-toolbar" role="toolbar" aria-label={t('markdown.formatting')}>
      {toolbar === 'full' ? (
        <button
          type="button"
          className={`markdown-toolbar-btn${editor?.isActive('heading', { level: 2 }) ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
          disabled={!editor}
          title={t('markdown.heading')}
          aria-pressed={editor?.isActive('heading', { level: 2 }) ?? false}
        >
          H
        </button>
      ) : null}
      <button
        type="button"
        className={`markdown-toolbar-btn${editor?.isActive('bold') ? ' markdown-toolbar-btn-active' : ''}`}
        onClick={() => editor?.chain().focus().toggleBold().run()}
        disabled={!editor}
        title={t('markdown.bold')}
        aria-pressed={editor?.isActive('bold') ?? false}
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        className={`markdown-toolbar-btn${editor?.isActive('italic') ? ' markdown-toolbar-btn-active' : ''}`}
        onClick={() => editor?.chain().focus().toggleItalic().run()}
        disabled={!editor}
        title={t('markdown.italic')}
        aria-pressed={editor?.isActive('italic') ?? false}
      >
        <em>I</em>
      </button>
      {toolbar === 'full' ? (
        <button
          type="button"
          className={`markdown-toolbar-btn${editor?.isActive('code') ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor?.chain().focus().toggleCode().run()}
          disabled={!editor}
          title={t('markdown.code')}
          aria-pressed={editor?.isActive('code') ?? false}
        >
          {'</>'}
        </button>
      ) : null}
      <button
        type="button"
        className={`markdown-toolbar-btn${editor?.isActive('link') ? ' markdown-toolbar-btn-active' : ''}`}
        onClick={onSetLink}
        disabled={!editor}
        title={t('markdown.link')}
        aria-pressed={editor?.isActive('link') ?? false}
      >
        {t('markdown.link')}
      </button>
      <button
        type="button"
        className={`markdown-toolbar-btn${editor?.isActive('bulletList') ? ' markdown-toolbar-btn-active' : ''}`}
        onClick={() => editor?.chain().focus().toggleBulletList().run()}
        disabled={!editor}
        title={t('markdown.bulletList')}
        aria-pressed={editor?.isActive('bulletList') ?? false}
      >
        {t('markdown.list')}
      </button>
      {toolbar === 'full' ? (
        <button
          type="button"
          className={`markdown-toolbar-btn${editor?.isActive('blockquote') ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor?.chain().focus().toggleBlockquote().run()}
          disabled={!editor}
          title={t('markdown.quote')}
          aria-pressed={editor?.isActive('blockquote') ?? false}
        >
          {t('markdown.quote')}
        </button>
      ) : null}
    </div>
  )
}

export function MarkdownNoteEditor({
  value,
  onChange,
  maxLength = NOTE_CONTENT_MAX_LENGTH,
  placeholder,
  label,
  toolbar = 'full',
  toolbarPlacement = 'before',
  size = 'default',
  actions,
}: MarkdownNoteEditorProps) {
  const { t } = useLocale()
  const resolvedPlaceholder = placeholder ?? t('markdown.placeholder')
  const resolvedLabel = label ?? t('common.note')
  const placeholderRef = useRef(resolvedPlaceholder)
  placeholderRef.current = resolvedPlaceholder

  const labelId = useId()
  const lastEmittedRef = useRef(value)

  const editor = useEditor({
    immediatelyRender: false,
    shouldRerenderOnTransaction: true,
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3] },
        codeBlock: false,
        horizontalRule: false,
        link: {
          openOnClick: false,
          autolink: true,
          defaultProtocol: 'https',
          HTMLAttributes: {
            rel: 'noopener noreferrer',
            target: '_blank',
          },
        },
      }),
      Placeholder.configure({
        placeholder: () => placeholderRef.current,
      }),
      Markdown,
      createContentLimitExtension(maxLength),
    ],
    content: value || '',
    contentType: 'markdown',
    editorProps: {
      attributes: {
        class: 'markdown-wysiwyg-content',
        'aria-labelledby': labelId,
        role: 'textbox',
        'aria-multiline': 'true',
      },
    },
    onUpdate: ({ editor: current }) => {
      const markdown = current.getMarkdown()
      if (markdown.length > NOTE_RAW_MAX_LENGTH) {
        current.commands.undo()
        return
      }
      lastEmittedRef.current = markdown
      onChange(markdown)
    },
  })

  useEffect(() => {
    if (!editor) {
      return
    }
    if (value === lastEmittedRef.current) {
      return
    }
    editor.commands.setContent(value || '', { contentType: 'markdown' })
    lastEmittedRef.current = value
  }, [editor, value])

  useEffect(() => {
    if (!editor) {
      return
    }
    editor.view.dispatch(editor.state.tr)
  }, [editor, resolvedPlaceholder])

  const contentLength = editor ? plainTextFromDoc(editor.state.doc).length : 0

  const setLink = () => {
    if (!editor) {
      return
    }
    const previous = editor.getAttributes('link').href as string | undefined
    const url = window.prompt(t('markdown.linkUrlPrompt'), previous ?? 'https://')
    if (url === null) {
      return
    }
    const trimmed = url.trim()
    if (trimmed === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: trimmed }).run()
  }

  const selectionMode = toolbar === 'selection'
  const staticToolbarMode = toolbar === 'full' || toolbar === 'simple' ? toolbar : null
  const staticToolbar = staticToolbarMode ? (
    <StaticToolbar editor={editor} toolbar={staticToolbarMode} onSetLink={setLink} />
  ) : null

  return (
    <div
      className={`form-field markdown-editor${size === 'large' ? ' markdown-editor-large' : ''}${selectionMode ? ' markdown-editor-selection-toolbar' : ''}`}
    >
      <div className="markdown-editor-header">
        <span className="form-label" id={labelId}>
          {resolvedLabel}
        </span>
        <div className="markdown-editor-header-meta">
          {actions}
          <span className="form-hint markdown-editor-counter" aria-live="polite">
            {contentLength}/{maxLength}
          </span>
        </div>
      </div>

      {toolbarPlacement === 'before' ? staticToolbar : null}

      <div
        className="form-input markdown-wysiwyg"
        onClick={() => editor?.chain().focus().run()}
      >
        <EditorContent editor={editor} />
      </div>

      {toolbarPlacement === 'after' ? staticToolbar : null}

      {selectionMode && editor ? (
        <SelectionToolbar editor={editor} toolbar="simple" onSetLink={setLink} />
      ) : null}
    </div>
  )
}

export { NOTE_CONTENT_MAX_LENGTH as NOTE_MAX_LENGTH }
