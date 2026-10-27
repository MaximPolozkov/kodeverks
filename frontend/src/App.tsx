import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { Spinner } from '@/components/ui/misc'
import HomePage from '@/pages/public/HomePage'
import PrivacyPage from '@/pages/public/PrivacyPage'

// Админка грузится отдельным чанком — посетителям главной она не нужна
const AdminLayout = lazy(() => import('@/pages/admin/AdminLayout'))
const LoginPage = lazy(() => import('@/pages/admin/LoginPage'))
const OrdersPage = lazy(() => import('@/pages/admin/OrdersPage'))
const OrderDetailPage = lazy(() => import('@/pages/admin/OrderDetailPage'))
const ProfilePage = lazy(() => import('@/pages/admin/ProfilePage'))
const UsersPage = lazy(() => import('@/pages/admin/UsersPage'))
const BotPage = lazy(() => import('@/pages/admin/BotPage'))
const LeadPage = lazy(() => import('@/pages/admin/LeadPage'))
const RequireAuth = lazy(() => import('@/pages/admin/auth').then((m) => ({ default: m.RequireAuth })))

function NotFound() {
  return (
    <div className="page py-24">
      <h1 className="text-[30px] font-bold">Страница не найдена</h1>
      <a href="/" className="btn-primary mt-6">
        На главную
      </a>
    </div>
  )
}

export default function App() {
  return (
    <Suspense fallback={<Spinner />}>
      {/* Маршруты регистронезависимы: /Admin и /admin ведут в одну панель */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/admin/login" element={<LoginPage />} />
        <Route
          path="/admin"
          element={
            <RequireAuth>
              <AdminLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="orders" replace />} />
          <Route path="orders" element={<OrdersPage />} />
          <Route path="orders/:id" element={<OrderDetailPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="bot" element={<BotPage />} />
          <Route path="bot/leads/:id" element={<LeadPage />} />
          <Route
            path="users"
            element={
              <RequireAuth roles={['admin']}>
                <UsersPage />
              </RequireAuth>
            }
          />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}
