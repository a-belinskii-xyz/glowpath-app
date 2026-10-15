/** Day helpers shared by the body card, the sleep section and the copy drawer. */

export function dayNumber(day: string): number {
  const [year, month, date] = day.split('-').map(Number)
  return Date.UTC(year, month - 1, date) / 86_400_000
}

export function formatDay(day: string, dateLocale: string, options: Intl.DateTimeFormatOptions): string {
  const [year, month, date] = day.split('-').map(Number)
  return new Intl.DateTimeFormat(dateLocale, { ...options, timeZone: 'UTC' }).format(
    new Date(Date.UTC(year, month - 1, date)),
  )
}

/** Body mass index from kilograms and centimetres, one decimal. */
export function bodyMassIndex(weightKg: number, heightCm: number): number {
  const metres = heightCm / 100
  return Math.round((weightKg / (metres * metres)) * 10) / 10
}

export async function copyToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // Some webviews block the async clipboard; fall back to a selected textarea.
    const area = document.createElement('textarea')
    area.value = text
    area.setAttribute('readonly', '')
    area.style.position = 'fixed'
    area.style.opacity = '0'
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
}
