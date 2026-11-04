import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../app/AuthContext'
import { DataProvider } from '../app/DataContext'
import { LoginPage } from '../features/LoginPage'
import { ReportsPage } from '../features/ReportsPage'
import { DashboardPage } from '../features/DashboardPage'

describe('vista demo', () => {
  it('permite entrar sin solicitar un token a la API', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<div>Panel de demostración</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole('button', { name: /ver demostración/i }))

    expect(await screen.findByText('Panel de demostración')).toBeTruthy()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('mantiene deshabilitadas las descargas en el modo de solo lectura', async () => {
    sessionStorage.setItem('gridwatch-session', JSON.stringify({ mode: 'demo' }))
    render(
      <MemoryRouter initialEntries={['/reports']}>
        <AuthProvider><DataProvider><ReportsPage /></DataProvider></AuthProvider>
      </MemoryRouter>,
    )

    const summary = await screen.findByRole('button', { name: /descargar resumen/i }) as HTMLButtonElement
    const detail = screen.getByRole('button', { name: /descargar detalle/i }) as HTMLButtonElement
    const pdf = screen.getByRole('button', { name: /descargar pdf/i }) as HTMLButtonElement
    expect(summary.disabled).toBe(true)
    expect(detail.disabled).toBe(true)
    expect(pdf.disabled).toBe(true)
    expect(screen.getByText(/vista demo solo presenta datos de muestra/i)).toBeTruthy()
  })

  it('muestra indicadores e instalaciones de ejemplo sin consultar la API', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    sessionStorage.setItem('gridwatch-session', JSON.stringify({ mode: 'demo' }))
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider><DataProvider><DashboardPage /></DataProvider></AuthProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Complejo Minero Norte')).toBeTruthy()
    expect(screen.getByText('Resumen eléctrico')).toBeTruthy()
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
