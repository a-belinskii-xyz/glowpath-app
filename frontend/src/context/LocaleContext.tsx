import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { guestHeartbeatSync, setGuestLocale } from '../guest/store'
import { t as translate, tp as translatePlural } from '../i18n/t'
import { isGuestDiaryMode } from '../lib/guestMode'
import {
  getApiLocale,
  setApiLocale as persistApiLocale,
  type ApiLocale,
} from '../lib/locale'

type Translate = (key: string, params?: Record<string, string | number>) => string
type TranslatePlural = (
  count: number,
  keys: { one: string; few: string; many: string },
  params?: Record<string, string | number>,
) => string

type LocaleContextValue = {
  locale: ApiLocale
  setLocale: (locale: ApiLocale) => void
  t: Translate
  tp: TranslatePlural
}

const LocaleContext = createContext<LocaleContextValue | null>(null)

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<ApiLocale>(() => getApiLocale())

  const setLocale = useCallback((next: ApiLocale) => {
    persistApiLocale(next)
    setLocaleState(next)
    if (isGuestDiaryMode()) {
      void setGuestLocale(next).then(() => guestHeartbeatSync())
    }
  }, [])

  useEffect(() => {
    document.documentElement.lang = locale
    document.title = translate(locale, 'brand')
  }, [locale])

  const t = useCallback<Translate>(
    (key, params) => translate(locale, key, params),
    [locale],
  )

  const tp = useCallback<TranslatePlural>(
    (count, keys, params) => translatePlural(locale, count, keys, params),
    [locale],
  )

  const value = useMemo(() => ({ locale, setLocale, t, tp }), [locale, setLocale, t, tp])

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext)
  if (!context) {
    throw new Error('useLocale must be used within LocaleProvider')
  }
  return context
}
