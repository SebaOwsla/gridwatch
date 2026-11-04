import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { AuthProvider, useAuth } from './app/AuthContext'
import { DataProvider } from './app/DataContext'
import { AppShell } from './app/AppShell'
import { LoginPage } from './features/LoginPage'
import './style.css'

const DashboardPage = lazy(() => import('./features/DashboardPage').then((module) => ({ default: module.DashboardPage })))
const InstallationsPage = lazy(() => import('./features/InstallationsPage').then((module) => ({ default: module.InstallationsPage })))
const HistoryPage = lazy(() => import('./features/HistoryPage').then((module) => ({ default: module.HistoryPage })))
const AlertsPage = lazy(() => import('./features/AlertsPage').then((module) => ({ default: module.AlertsPage })))
const ReportsPage = lazy(() => import('./features/ReportsPage').then((module) => ({ default: module.ReportsPage })))
const AdminPage = lazy(() => import('./features/AdminPage').then((module) => ({ default: module.AdminPage })))

function PrivateLayout() {
  const { auth, checking } = useAuth()
  if (checking) return <div className="flex min-h-screen items-center justify-center text-sm text-muted">Verificando sesión…</div>
  if (!auth) return <Navigate to="/login" replace />
  return <DataProvider><AppShell /></DataProvider>
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-sm text-muted">Cargando vista…</div>}><Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<PrivateLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/installations" element={<InstallationsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes></Suspense>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
