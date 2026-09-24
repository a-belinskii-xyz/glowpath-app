import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AppBootGate } from './components/AppBootGate'
import { AuthCardLayout } from './components/AuthCardLayout'
import { AppRoute, AccountRoute } from './components/AppRoute'
import { GuestRoute } from './components/GuestRoute'
import { Layout } from './components/Layout'
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
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { ProfilePage } from './pages/ProfilePage'
import { RegisterPage } from './pages/RegisterPage'
import { ResendVerificationPage } from './pages/ResendVerificationPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { TagsPage } from './pages/TagsPage'
import { MarketPage } from './pages/MarketPage'
import { AchievementsPage } from './pages/AchievementsPage'
import { PlansPage } from './pages/PlansPage'
import { TemplatesRedirect, TrackerSettingsPage } from './pages/TrackerSettingsPage'
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
                <Routes>
                  <Route element={<Layout />}>
                    <Route index element={<HomePage />} />
                    <Route path="plans" element={<PlansPage />} />
                    <Route path="verify-email" element={<VerifyEmailPage />} />
                    <Route path="auth/google/callback" element={<GoogleCallbackPage />} />

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
                      <Route path="tags" element={<TagsPage />} />
                      <Route path="goals" element={<GoalsPage />} />
                      <Route path="tracker-settings" element={<TrackerSettingsPage />} />
                      <Route path="templates" element={<TemplatesRedirect />} />
                    </Route>

                    <Route element={<AccountRoute />}>
                      <Route path="market" element={<MarketPage />} />
                      <Route path="achievements" element={<AchievementsPage />} />
                      <Route path="profile" element={<ProfilePage />} />
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
