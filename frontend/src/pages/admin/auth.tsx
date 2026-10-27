import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { api, ApiError } from '@/api/client'
import type { User, UserRole } from '@/api/types'
import { Spinner } from '@/components/ui/misc'

const ME_KEY = ['me']

async function fetchMe(): Promise<User | null> {
  try {
    return await api<User>('/api/auth/me')
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      // Пробуем продлить сессию по refresh-токену
      try {
        return await api<User>('/api/auth/refresh', { method: 'POST' })
      } catch {
        return null
      }
    }
    throw error
  }
}

export function useMe() {
  return useQuery({ queryKey: ME_KEY, queryFn: fetchMe, staleTime: 60_000, retry: false })
}

export function useSetMe() {
  const client = useQueryClient()
  return (user: User | null) => client.setQueryData(ME_KEY, user)
}

export function useLogout() {
  const client = useQueryClient()
  return async () => {
    await api('/api/auth/logout', { method: 'POST' }).catch(() => undefined)
    client.clear()
    client.setQueryData(ME_KEY, null)
  }
}

export function RequireAuth({ children, roles }: { children: ReactNode; roles?: UserRole[] }) {
  const { data: user, isLoading } = useMe()
  const location = useLocation()
  if (isLoading) return <Spinner label="Проверяем вход" />
  if (!user) return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="p-8">
        <p className="font-semibold">Раздел доступен только администраторам.</p>
      </div>
    )
  }
  return <>{children}</>
}
