import { useEffect, useState } from 'react'

// Inputs that open a picker rather than the text keyboard.
const NON_TEXT_INPUT_TYPES = new Set([
  'button',
  'checkbox',
  'color',
  'date',
  'datetime-local',
  'file',
  'hidden',
  'image',
  'month',
  'radio',
  'range',
  'reset',
  'submit',
  'time',
  'week',
])

// Shrink of the visible viewport that means the keyboard is up.
const KEYBOARD_MIN_SHRINK_PX = 120

function isTextField(element: Element | null): boolean {
  if (!(element instanceof HTMLElement)) {
    return false
  }
  if (element.isContentEditable || element instanceof HTMLTextAreaElement) {
    return true
  }
  return element instanceof HTMLInputElement && !NON_TEXT_INPUT_TYPES.has(element.type)
}

function viewportHeight(): number {
  return window.visualViewport?.height ?? window.innerHeight
}

/**
 * True while a text field is focused and the keyboard is up. Android may close
 * the keyboard without blurring the field, so a viewport that grows back to its
 * full height also counts as closed.
 */
export function useSoftKeyboardOpen(enabled = true): boolean {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!enabled) {
      setOpen(false)
      return
    }
    let fullHeight = viewportHeight()
    let shrunk = false
    let frame = 0

    const update = () => {
      frame = 0
      const height = viewportHeight()
      const focused = isTextField(document.activeElement)
      if (!focused) {
        fullHeight = Math.max(height, fullHeight)
        shrunk = false
        setOpen(false)
        return
      }
      if (height < fullHeight - KEYBOARD_MIN_SHRINK_PX) {
        shrunk = true
        setOpen(true)
        return
      }
      // Viewport is full height: keyboard not up yet, or dismissed with focus kept.
      setOpen(!shrunk)
    }
    const schedule = () => {
      if (!frame) {
        frame = window.requestAnimationFrame(update)
      }
    }

    document.addEventListener('focusin', schedule)
    document.addEventListener('focusout', schedule)
    window.addEventListener('resize', schedule)
    window.visualViewport?.addEventListener('resize', schedule)
    update()
    return () => {
      if (frame) {
        window.cancelAnimationFrame(frame)
      }
      document.removeEventListener('focusin', schedule)
      document.removeEventListener('focusout', schedule)
      window.removeEventListener('resize', schedule)
      window.visualViewport?.removeEventListener('resize', schedule)
    }
  }, [enabled])

  return open
}
