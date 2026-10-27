import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { api } from '@/api/client'
import type { User } from '@/api/types'
import { Field } from '@/components/ui/Field'
import { Logo } from '@/pages/public/SiteChrome'

import { useMe, useSetMe } from './auth'

const schema = z.object({
  email: z.string().trim().email('Укажите почту в формате name@example.com'),
  password: z.string().min(1, 'Введите пароль'),
})
type Values = z.infer<typeof schema>

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const setMe = useSetMe()
  const { data: me } = useMe()
  const from = (location.state as { from?: string } | null)?.from ?? '/admin/orders'

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) })

  const login = useMutation({
    mutationFn: (values: Values) => api<User>('/api/auth/login', { method: 'POST', json: values }),
    onSuccess: (user) => {
      setMe(user)
      navigate(from, { replace: true })
    },
  })

  if (me) return <Navigate to={from} replace />

  return (
    <div className="min-h-screen-safe flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-sm">
        <Logo />
        <form
          onSubmit={handleSubmit((v) => login.mutate(v))}
          className="panel mt-6 space-y-5 p-5 xs:p-6"
          noValidate
        >
          <h1 className="text-[22px] font-bold">Вход в панель</h1>
          <Field id="login-email" label="Почта" error={errors.email?.message}>
            <input id="login-email" type="email" autoComplete="username" className="input" {...register('email')} />
          </Field>
          <Field id="login-password" label="Пароль" error={errors.password?.message}>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              className="input"
              {...register('password')}
            />
          </Field>
          {login.isError && (
            <p role="alert" className="text-[15px] text-danger">
              {login.error.message}
            </p>
          )}
          <button className="btn-primary w-full" disabled={login.isPending}>
            {login.isPending ? 'Входим…' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  )
}
