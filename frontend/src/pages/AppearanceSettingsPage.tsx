import { CalendarStartSetting } from '../components/CalendarStartSetting'
import { HistoricalColorsSetting } from '../components/HistoricalColorsSetting'
import { SettingsSection } from '../components/SettingsSection'
import { StreakDisplaySetting } from '../components/StreakDisplaySetting'
import { ThemeSetting } from '../components/ThemeSetting'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'

export function AppearanceSettingsPage() {
  const { t } = useLocale()
  const { isLoading } = useMoodPreferences()

  return (
    <SettingsSection title={t('profile.appearanceTitle')} lead={t('profile.appearanceLead')}>
      <div className="appearance-settings">
        <ThemeSetting />
        {isLoading ? (
          <p className="muted">{t('common.loadingMoodPreferences')}</p>
        ) : (
          <>
            <StreakDisplaySetting />
            <CalendarStartSetting />
            <HistoricalColorsSetting />
          </>
        )}
      </div>
    </SettingsSection>
  )
}
