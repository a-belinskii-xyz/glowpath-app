import { useLocale } from '../context/LocaleContext'

/** Chart periods shared by the weight, sleep and exercise drawers, in days. */
export const BODY_RANGES = { month: 31, quarter: 92, year: 365 } as const
export type BodyRange = keyof typeof BODY_RANGES

type BodyRangeSwitchProps = {
  value: BodyRange
  onChange: (range: BodyRange) => void
}

export function BodyRangeSwitch({ value, onChange }: BodyRangeSwitchProps) {
  const { t } = useLocale()
  return (
    <div className="body-range" role="radiogroup" aria-label={t('body.chartRange')}>
      {(Object.keys(BODY_RANGES) as BodyRange[]).map((key) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={value === key}
          className={value === key ? 'is-selected' : ''}
          onClick={() => onChange(key)}
        >
          {t(`body.range.${key}`)}
        </button>
      ))}
    </div>
  )
}
