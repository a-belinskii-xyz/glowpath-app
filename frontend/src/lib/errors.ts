import { t as translate } from '../i18n/t'
import { getApiLocale } from './locale'

export type ApiErrorParams = Record<string, string>

export type ParsedApiError = {
  message: string
  code?: string
  params?: ApiErrorParams
}

export class ApiError extends Error {
  status: number
  code?: string
  params?: ApiErrorParams

  constructor(parsed: ParsedApiError | string, status: number) {
    const payload = typeof parsed === 'string' ? { message: parsed } : parsed
    super(payload.message)
    this.name = 'ApiError'
    this.status = status
    this.code = payload.code
    this.params = payload.params
  }
}

function snakeToCamel(code: string): string {
  return code.replace(/_([a-z0-9])/g, (_, char: string) => char.toUpperCase())
}

export function parseApiError(status: number, payload: unknown): ParsedApiError {
  if (payload && typeof payload === 'object') {
    const detail = (payload as { detail?: unknown }).detail
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      const row = detail as { code?: unknown; message?: unknown; params?: unknown }
      const code = typeof row.code === 'string' && row.code.trim() ? row.code.trim() : undefined
      const message =
        typeof row.message === 'string' && row.message.trim() ? row.message.trim() : undefined
      const params =
        row.params && typeof row.params === 'object' && !Array.isArray(row.params)
          ? Object.fromEntries(
              Object.entries(row.params as Record<string, unknown>)
                .filter(([, value]) => value !== undefined && value !== null)
                .map(([key, value]) => [key, String(value)]),
            )
          : undefined
      if (code || message) {
        return {
          code,
          message:
            message ??
            translate(getApiLocale(), 'errors.requestFailedStatus', { status }),
          params: params && Object.keys(params).length > 0 ? params : undefined,
        }
      }
    }
    if (typeof detail === 'string' && detail.trim()) {
      return { message: detail }
    }
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (!item || typeof item !== 'object') {
            return null
          }
          const row = item as { loc?: unknown[]; msg?: unknown }
          const field = Array.isArray(row.loc) ? String(row.loc[row.loc.length - 1] ?? '') : ''
          const msg = typeof row.msg === 'string' ? row.msg : ''
          if (!msg) {
            return null
          }
          return field ? `${field}: ${msg}` : msg
        })
        .filter((part): part is string => Boolean(part))
      if (parts.length > 0) {
        return { message: parts.join('; ') }
      }
    }
  }
  return {
    message: translate(getApiLocale(), 'errors.requestFailedStatus', { status }),
  }
}

type TranslateFn = (key: string, params?: Record<string, string | number>) => string

export function formatApiError(err: unknown, t: TranslateFn, fallbackKey: string): string {
  if (err instanceof ApiError && err.code) {
    const key = `apiErrors.${snakeToCamel(err.code)}`
    const translated = t(key, err.params)
    if (translated !== key) {
      return translated
    }
  }
  if (err instanceof Error && err.message.trim()) {
    return err.message
  }
  return t(fallbackKey)
}
