import type { ApiLocale } from '../lib/locale'
import { messages, type MessageTree } from './messages'

type Params = Record<string, string | number>

function lookup(tree: MessageTree, path: string): string | undefined {
  const parts = path.split('.')
  let current: string | MessageTree | undefined = tree
  for (const part of parts) {
    if (typeof current !== 'object' || current === null) {
      return undefined
    }
    current = current[part]
  }
  return typeof current === 'string' ? current : undefined
}

function interpolate(template: string, params?: Params): string {
  if (!params) {
    return template
  }
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    params[key] !== undefined ? String(params[key]) : `{${key}}`,
  )
}

/** Russian plural category for cardinal numbers. */
export function pluralCategory(
  locale: ApiLocale,
  count: number,
): 'one' | 'few' | 'many' {
  if (locale === 'en') {
    return count === 1 ? 'one' : 'many'
  }
  const abs = Math.abs(count) % 100
  const last = abs % 10
  if (abs > 10 && abs < 20) {
    return 'many'
  }
  if (last === 1) {
    return 'one'
  }
  if (last >= 2 && last <= 4) {
    return 'few'
  }
  return 'many'
}

export function t(locale: ApiLocale, key: string, params?: Params): string {
  const template =
    lookup(messages[locale] as MessageTree, key) ??
    lookup(messages.en as MessageTree, key) ??
    key
  return interpolate(template, params)
}

/** Pick one/few/many message keys based on locale plural rules. */
export function tp(
  locale: ApiLocale,
  count: number,
  keys: { one: string; few: string; many: string },
  params?: Params,
): string {
  const category = pluralCategory(locale, count)
  const key = category === 'one' ? keys.one : category === 'few' ? keys.few : keys.many
  return t(locale, key, { count, ...params })
}

export function intlLocale(locale: ApiLocale): string {
  return locale === 'ru' ? 'ru-RU' : 'en-GB'
}
