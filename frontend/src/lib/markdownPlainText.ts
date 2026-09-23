/** Visible note length: markdown markers and link/image targets do not count. */

const FENCED_CODE = /```[^\n]*\n?([\s\S]*?)```/g
const INLINE_CODE = /`([^`]+)`/g
const IMAGE = /!\[([^\]]*)\]\([^)]*\)/g
const LINK = /\[([^\]]+)\]\([^)]*\)/g
const HEADING = /^#{1,6}\s+/gm
const BLOCKQUOTE = /^>\s?/gm
const UNORDERED_LIST = /^\s*[-*+]\s+/gm
const ORDERED_LIST = /^\s*\d+\.\s+/gm
const BOLD = /(\*\*|__)(.+?)\1/g
const ITALIC = /(\*|_)(.+?)\1/g
const STRIKE = /~~(.+?)~~/g
const HORIZONTAL_RULE = /^([-*_]){3,}\s*$/gm

export const NOTE_CONTENT_MAX_LENGTH = 500
/** Raw markdown may be longer than visible content because of formatting markers. */
export const NOTE_RAW_MAX_LENGTH = 4000

export function markdownToPlainText(markdown: string): string {
  let text = markdown.replace(/\r\n/g, '\n')
  text = text.replace(FENCED_CODE, '$1')
  text = text.replace(INLINE_CODE, '$1')
  text = text.replace(IMAGE, '$1')
  text = text.replace(LINK, '$1')
  text = text.replace(HEADING, '')
  text = text.replace(BLOCKQUOTE, '')
  text = text.replace(UNORDERED_LIST, '')
  text = text.replace(ORDERED_LIST, '')
  text = text.replace(HORIZONTAL_RULE, '')
  text = text.replace(BOLD, '$2')
  text = text.replace(ITALIC, '$2')
  text = text.replace(STRIKE, '$1')
  return text
}

export function markdownContentLength(markdown: string): number {
  return markdownToPlainText(markdown).length
}
