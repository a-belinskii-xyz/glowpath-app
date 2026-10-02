import { useLocale } from '../../context/LocaleContext'
import type { CriteriaParamSpec, CriteriaSpec } from '../../types/achievement'
import { defaultParams, type AchievementDraft } from './achievementDraft'

type StaffCriteriaFieldsProps = {
  specs: CriteriaSpec[]
  draft: AchievementDraft
  onChange: (patch: Pick<AchievementDraft, 'criteriaType' | 'params'>) => void
}

/** Condition form generated from the server's criteria specs. */
export function StaffCriteriaFields({ specs, draft, onChange }: StaffCriteriaFieldsProps) {
  const { t } = useLocale()
  const spec = specs.find((item) => item.type === draft.criteriaType)

  const choiceLabel = (param: CriteriaParamSpec, choice: string | number) =>
    param.name === 'weekday'
      ? t(`staffAchievements.choices.weekday${choice}`)
      : typeof choice === 'string'
        ? t(`staffAchievements.choices.${choice}`)
        : String(choice)

  const setParam = (name: string, value: string) =>
    onChange({ criteriaType: draft.criteriaType, params: { ...draft.params, [name]: value } })

  return (
    <div className="staff-form-grid">
      <label className="form-field staff-form-wide">
        <span className="form-label">{t('staffAchievements.conditionType')}</span>
        <select
          className="form-input"
          value={draft.criteriaType}
          onChange={(event) => {
            const next = specs.find((item) => item.type === event.target.value)
            onChange({ criteriaType: event.target.value, params: defaultParams(next) })
          }}
        >
          {specs.map((item) => (
            <option key={item.type} value={item.type}>
              {t(`staffAchievements.criteria.${item.type}`)}
            </option>
          ))}
        </select>
        {spec && spec.require_any_of.length > 0 ? (
          <span className="form-hint">{t('staffAchievements.anyOfHint')}</span>
        ) : null}
      </label>
      {spec?.params.map((param) => {
        const id = `achievement-param-${param.name}`
        const value = draft.params[param.name] ?? ''
        return (
          <label key={param.name} className="form-field" htmlFor={id}>
            <span className="form-label">{t(`staffAchievements.params.${param.name}`)}</span>
            {param.kind === 'choice' ? (
              <select
                id={id}
                className="form-input"
                value={value}
                required={param.required}
                onChange={(event) => setParam(param.name, event.target.value)}
              >
                {param.required ? null : <option value="">{t('staffAchievements.any')}</option>}
                {param.choices.map((choice) => (
                  <option key={choice} value={String(choice)}>
                    {choiceLabel(param, choice)}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id={id}
                className="form-input"
                type="number"
                inputMode="numeric"
                min={param.minimum ?? undefined}
                max={param.maximum ?? undefined}
                step={1}
                required={param.required}
                placeholder={param.required ? undefined : t('staffAchievements.any')}
                value={value}
                onChange={(event) => setParam(param.name, event.target.value)}
              />
            )}
          </label>
        )
      })}
    </div>
  )
}
