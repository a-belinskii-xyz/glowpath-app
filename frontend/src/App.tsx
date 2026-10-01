import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AppBootGate } from './components/AppBootGate'
import { AuthCardLayout } from './components/AuthCardLayout'
import { AppRoute, AccountRoute, BillingOnly, RegisteredOnly } from './components/AppRoute'
import { GuestRoute } from './components/GuestRoute'
import { Layout } from './components/Layout'
import { NotificationLinkTracker } from './components/NotificationLinkTracker'
import { AmbientGlowProvider } from './context/AmbientGlowContext'
import { AuthProvider } from './context/AuthContext'
import { GuestExperimentProvider } from './context/GuestExperimentContext'
import { LocaleProvider } from './context/LocaleContext'
import { MoodPreferencesProvider } from './context/MoodPreferencesContext'
import { CreateEntryPage } from './pages/CreateEntryPage'
import { EditEntryPage } from './pages/EditEntryPage'
import { EntryDetailPage } from './pages/EntryDetailPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { GalleryPage } from './pages/GalleryPage'
import { GoalsPage } from './pages/GoalsPage'
import { GoogleCallbackPage } from './pages/GoogleCallbackPage'
import { TelegramCallbackPage } from './pages/TelegramCallbackPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { ProfilePage } from './pages/ProfilePage'
import { RegisterPage } from './pages/RegisterPage'
import { ResendVerificationPage } from './pages/ResendVerificationPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { MarketPage } from './pages/MarketPage'
import { AchievementsPage } from './pages/AchievementsPage'
import { PlansPage } from './pages/PlansPage'
import { PrivacyPage } from './pages/PrivacyPage'
import { AccountSettingsPage } from './pages/AccountSettingsPage'
import { AppearanceSettingsPage } from './pages/AppearanceSettingsPage'
import {
  DiarySettingsPage,
  TagsRedirect,
  TemplatesRedirect,
  TrackerSettingsRedirect,
} from './pages/DiarySettingsPage'
import { NotificationSettingsPage } from './pages/NotificationSettingsPage'
import { SettingsPage } from './pages/SettingsPage'
import { StaffPage } from './pages/StaffPage'
import { UnsubscribePage } from './pages/UnsubscribePage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'
import { TelegramNavigation } from './platform/TelegramNavigation'

function App() {
  return (
    <LocaleProvider>
      <AuthProvider>
        <GuestExperimentProvider>
          <AppBootGate>
          <MoodPreferencesProvider>
            <AmbientGlowProvider>
              <BrowserRouter>
                <TelegramNavigation />
                <NotificationLinkTracker />
                <Routes>
                  <Route element={<Layout />}>
                    <Route index element={<HomePage />} />
                    <Route element={<BillingOnly />}>
                      <Route path="plans" element={<PlansPage />} />
                    </Route>
                    <Route path="privacy" element={<PrivacyPage />} />
                    <Route path="verify-email" element={<VerifyEmailPage />} />
                    <Route path="unsubscribe" element={<UnsubscribePage />} />
                    <Route path="auth/google/callback" element={<GoogleCallbackPage />} />
                    <Route path="auth/telegram/callback" element={<TelegramCallbackPage />} />

                    <Route element={<GuestRoute />}>
                      <Route element={<AuthCardLayout />}>
                        <Route path="login" element={<LoginPage />} />
                        <Route path="register" element={<RegisterPage />} />
                        <Route path="forgot-password" element={<ForgotPasswordPage />} />
                        <Route path="resend-verification" element={<ResendVerificationPage />} />
                      </Route>
                    </Route>

                    <Route element={<AuthCardLayout />}>
                      <Route path="reset-password" element={<ResetPasswordPage />} />
                    </Route>

                    <Route element={<AppRoute />}>
                      <Route path="onboarding" element={<OnboardingPage />} />
                      <Route path="entries/new" element={<CreateEntryPage />} />
                      <Route path="entries/:id/edit" element={<EditEntryPage />} />
                      <Route path="entries/:id" element={<EntryDetailPage />} />
                      <Route path="gallery" element={<GalleryPage />} />
                      <Route path="goals" element={<GoalsPage />} />
                      <Route path="settings" element={<SettingsPage />} />
                      <Route path="settings/diary" element={<DiarySettingsPage />} />
                      <Route path="tags" element={<TagsRedirect />} />
                      <Route path="templates" element={<TemplatesRedirect />} />
                      <Route path="tracker-settings" element={<TrackerSettingsRedirect />} />
                    </Route>

                    <Route element={<AccountRoute />}>
                      <Route path="market" element={<MarketPage />} />
                      <Route path="achievements" element={<AchievementsPage />} />
                      <Route path="profile" element={<ProfilePage />} />
                      <Route element={<RegisteredOnly />}>
                        <Route path="settings/notifications" element={<NotificationSettingsPage />} />
                        <Route path="settings/appearance" element={<AppearanceSettingsPage />} />
                        <Route path="settings/account" element={<AccountSettingsPage />} />
                        <Route path="staff" element={<StaffPage />} />
                      </Route>
                    </Route>

                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Route>
                </Routes>
              </BrowserRouter>
            </AmbientGlowProvider>
          </MoodPreferencesProvider>
          </AppBootGate>
        </GuestExperimentProvider>
      </AuthProvider>
    </LocaleProvider>
  )
}

export default App
