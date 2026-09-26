export type ColorScheme = 'light' | 'dark'

export function getColorScheme(): ColorScheme {
  if (typeof document === 'undefined') {
    return 'light'
  }
  return document.documentElement.dataset.colorScheme === 'dark' ? 'dark' : 'light'
}

export function subscribeColorScheme(onChange: () => void): () => void {
  if (typeof document === 'undefined' || typeof MutationObserver === 'undefined') {
    return () => undefined
  }
  const root = document.documentElement
  const observer = new MutationObserver(() => {
    onChange()
  })
  observer.observe(root, { attributes: true, attributeFilter: ['data-color-scheme'] })
  return () => observer.disconnect()
}
