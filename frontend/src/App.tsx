import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AuthCardLayout } from './components/AuthCardLayout'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AuthProvider } from './context/AuthContext'
import { LocaleProvider } from './context/LocaleContext'
import { CreateEntryPage } from './pages/CreateEntryPage'
import { EditEntryPage } from './pages/EditEntryPage'
import { EntryDetailPage } from './pages/EntryDetailPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { GoalsPage } from './pages/GoalsPage'
import { GoogleCallbackPage } from './pages/GoogleCallbackPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { ProfilePage } from './pages/ProfilePage'
import { RegisterPage } from './pages/RegisterPage'
import { ResendVerificationPage } from './pages/ResendVerificationPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { TagsPage } from './pages/TagsPage'
import { TemplatesPage } from './pages/TemplatesPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'

function App() {
  return (
    <LocaleProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<HomePage />} />
              <Route path="verify-email" element={<VerifyEmailPage />} />
              <Route path="auth/google/callback" element={<GoogleCallbackPage />} />

              <Route element={<AuthCardLayout />}>
                <Route path="login" element={<LoginPage />} />
                <Route path="register" element={<RegisterPage />} />
                <Route path="forgot-password" element={<ForgotPasswordPage />} />
                <Route path="reset-password" element={<ResetPasswordPage />} />
                <Route path="resend-verification" element={<ResendVerificationPage />} />
              </Route>

              <Route element={<ProtectedRoute />}>
                <Route path="entries/new" element={<CreateEntryPage />} />
                <Route path="entries/:id/edit" element={<EditEntryPage />} />
                <Route path="entries/:id" element={<EntryDetailPage />} />
                <Route path="tags" element={<TagsPage />} />
                <Route path="goals" element={<GoalsPage />} />
                <Route path="templates" element={<TemplatesPage />} />
                <Route path="profile" element={<ProfilePage />} />
              </Route>

              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </LocaleProvider>
  )
}

export default App
