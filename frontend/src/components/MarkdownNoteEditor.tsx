import { Extension } from '@tiptap/core'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import { Markdown } from '@tiptap/markdown'
import { Plugin } from '@tiptap/pm/state'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { useEffect, useId, useRef } from 'react'

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
}

function plainTextFromDoc(doc: { textBetween: (from: number, to: number, blockSep?: string, leafSep?: string) => string; content: { size: number } }) {
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

export function MarkdownNoteEditor({
  value,
  onChange,
  maxLength = NOTE_CONTENT_MAX_LENGTH,
  placeholder = 'Write a note…',
  label = 'Note',
}: MarkdownNoteEditorProps) {
  const labelId = useId()
  const lastEmittedRef = useRef(value)

  const editor = useEditor({
    immediatelyRender: false,
    shouldRerenderOnTransaction: true,
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        horizontalRule: false,
      }),
      Link.configure({
        openOnClick: false,
        autolink: true,
        defaultProtocol: 'https',
        HTMLAttributes: {
          rel: 'noopener noreferrer',
          target: '_blank',
        },
      }),
      Placeholder.configure({ placeholder }),
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

  const contentLength = editor ? plainTextFromDoc(editor.state.doc).length : 0

  const setLink = () => {
    if (!editor) {
      return
    }
    const previous = editor.getAttributes('link').href as string | undefined
    const url = window.prompt('Link URL', previous ?? 'https://')
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

  return (
    <div className="form-field markdown-editor">
      <div className="markdown-editor-header">
        <span className="form-label" id={labelId}>
          {label}
        </span>
        <span className="form-hint markdown-editor-counter" aria-live="polite">
          {contentLength}/{maxLength}
        </span>
      </div>

      <div className="markdown-editor-toolbar" role="toolbar" aria-label="Text formatting">
        <button
          type="button"
          className={`markdown-toolbar-btn${editor?.isActive('bold') ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor?.chain().focus().toggleBold().run()}
          disabled={!editor}
          title="Bold"
          aria-pressed={editor?.isActive('bold') ?? false}
        >
          <strong>B</strong>
        </button>
        <button
          type="button"
          className={`markdown-toolbar-btn${editor?.isActive('italic') ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor?.chain().focus().toggleItalic().run()}
          disabled={!editor}
          title="Italic"
          aria-pressed={editor?.isActive('italic') ?? false}
        >
          <em>I</em>
        </button>
        <button
          type="button"
          className={`markdown-toolbar-btn${editor?.isActive('code') ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor?.chain().focus().toggleCode().run()}
          disabled={!editor}
          title="Code"
          aria-pressed={editor?.isActive('code') ?? false}
        >
          {'</>'}
        </button>
        <button
          type="button"
          className={`markdown-toolbar-btn${editor?.isActive('link') ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={setLink}
          disabled={!editor}
          title="Link"
          aria-pressed={editor?.isActive('link') ?? false}
        >
          Link
        </button>
        <button
          type="button"
          className={`markdown-toolbar-btn${editor?.isActive('bulletList') ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor?.chain().focus().toggleBulletList().run()}
          disabled={!editor}
          title="Bullet list"
          aria-pressed={editor?.isActive('bulletList') ?? false}
        >
          List
        </button>
        <button
          type="button"
          className={`markdown-toolbar-btn${editor?.isActive('blockquote') ? ' markdown-toolbar-btn-active' : ''}`}
          onClick={() => editor?.chain().focus().toggleBlockquote().run()}
          disabled={!editor}
          title="Quote"
          aria-pressed={editor?.isActive('blockquote') ?? false}
        >
          Quote
        </button>
      </div>

      <div
        className="form-input markdown-wysiwyg"
        onClick={() => editor?.chain().focus().run()}
      >
        <EditorContent editor={editor} />
      </div>
    </div>
  )
}

export { NOTE_CONTENT_MAX_LENGTH as NOTE_MAX_LENGTH }
