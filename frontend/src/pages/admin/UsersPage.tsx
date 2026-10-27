import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { api } from '@/api/client'
import type { User, UserRole } from '@/api/types'
import { Field } from '@/components/ui/Field'
import { Badge, ErrorNote, PageHeader, Spinner } from '@/components/ui/misc'
import { formatDateTime, roleLabels } from '@/lib/labels'

import { useMe } from './auth'

const schema = z.object({
  name: z.string().trim().min(2, 'Минимум 2 символа'),
  email: z.string().trim().email('Укажите почту в формате name@example.com'),
  password: z.string().min(8, 'Минимум 8 символов'),
  role: z.enum(['manager', 'admin']),
})
type Values = z.infer<typeof schema>

export default function UsersPage() {
  const client = useQueryClient()
  const { data: me } = useMe()
  const users = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/api/admin/users') })
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { role: 'manager' } })

  const create = useMutation({
    mutationFn: (v: Values) => api<User>('/api/admin/users', { method: 'POST', json: v }),
    onSuccess: () => {
      form.reset({ name: '', email: '', password: '', role: 'manager' })
      client.invalidateQueries({ queryKey: ['users'] })
    },
  })

  const update = useMutation({
    mutationFn: ({ id, ...patch }: { id: number; role?: UserRole; is_active?: boolean }) =>
      api<User>(`/api/admin/users/${id}`, { method: 'PATCH', json: patch }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['users'] }),
  })

  const e = form.formState.errors

  return (
    <>
      <PageHeader title="Пользователи панели" />
      {update.isError && (
        <div className="mb-4">
          <ErrorNote error={update.error} />
        </div>
      )}
      {users.isLoading && <Spinner />}
      {users.isError && <ErrorNote error={users.error} />}
      {users.data && (
        <ul className="mb-8 space-y-3 md:hidden">
          {users.data.map((u) => (
            <li key={u.id} className="panel space-y-3 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="break-anywhere font-semibold">
                    {u.name}
                    {u.id === me?.id && <span className="font-normal text-muted"> (вы)</span>}
                  </p>
                  <p className="break-anywhere text-[14px] text-muted">{u.email}</p>
                </div>
                {u.is_active ? (
                  <Badge tone="bg-ok/10 text-ok border-ok/30">Активен</Badge>
                ) : (
                  <Badge tone="bg-danger/5 text-danger border-danger/30">Заблокирован</Badge>
                )}
              </div>
              <label className="block text-[13px] text-muted">
                Роль
                <select
                  className="input mt-1"
                  value={u.role}
                  onChange={(ev) => update.mutate({ id: u.id, role: ev.target.value as UserRole })}
                >
                  <option value="manager">{roleLabels.manager}</option>
                  <option value="admin">{roleLabels.admin}</option>
                </select>
              </label>
              <button
                type="button"
                className={`${u.is_active ? 'btn-danger' : 'btn-ghost'} w-full`}
                onClick={() => update.mutate({ id: u.id, is_active: !u.is_active })}
              >
                {u.is_active ? 'Заблокировать' : 'Разблокировать'}
              </button>
            </li>
          ))}
        </ul>
      )}
      {users.data && (
        <div className="panel mb-8 hidden overflow-x-auto md:block">
          <table className="w-full text-left text-[15px]">
            <thead className="border-b border-line text-[14px] text-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Пользователь</th>
                <th className="px-4 py-3 font-semibold">Роль</th>
                <th className="px-4 py-3 font-semibold">Создан</th>
                <th className="px-4 py-3 font-semibold">Доступ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {users.data.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-3">
                    <span className="break-anywhere font-semibold">{u.name}</span>
                    {u.id === me?.id && <span className="text-muted"> (вы)</span>}
                    <div className="break-anywhere text-[14px] text-muted">{u.email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <select
                      className="input py-1.5"
                      aria-label={`Роль: ${u.name}`}
                      value={u.role}
                      onChange={(ev) => update.mutate({ id: u.id, role: ev.target.value as UserRole })}
                    >
                      <option value="manager">{roleLabels.manager}</option>
                      <option value="admin">{roleLabels.admin}</option>
                    </select>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-muted">{formatDateTime(u.created_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {u.is_active ? (
                        <Badge tone="bg-ok/10 text-ok border-ok/30">Активен</Badge>
                      ) : (
                        <Badge tone="bg-danger/5 text-danger border-danger/30">Заблокирован</Badge>
                      )}
                      <button
                        className={u.is_active ? 'btn-danger py-1.5' : 'btn-ghost py-1.5'}
                        onClick={() => update.mutate({ id: u.id, is_active: !u.is_active })}
                      >
                        {u.is_active ? 'Заблокировать' : 'Разблокировать'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form
        className="panel max-w-3xl space-y-4 p-4 sm:p-5"
        noValidate
        onSubmit={form.handleSubmit((v) => create.mutate(v))}
      >
        <h2 className="font-sans text-[18px] font-semibold">Добавить пользователя</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="u-name" label="Имя" error={e.name?.message}>
            <input id="u-name" className="input" {...form.register('name')} />
          </Field>
          <Field id="u-email" label="Почта" error={e.email?.message}>
            <input id="u-email" type="email" className="input" {...form.register('email')} />
          </Field>
          <Field id="u-password" label="Временный пароль" error={e.password?.message}>
            <input id="u-password" type="text" autoComplete="off" className="input" {...form.register('password')} />
          </Field>
          <Field id="u-role" label="Роль">
            <select id="u-role" className="input" {...form.register('role')}>
              <option value="manager">{roleLabels.manager}</option>
              <option value="admin">{roleLabels.admin}</option>
            </select>
          </Field>
        </div>
        {create.isError && <p className="text-danger">{create.error.message}</p>}
        <button className="btn-primary w-full sm:w-auto" disabled={create.isPending}>
          Добавить пользователя
        </button>
      </form>
    </>
  )
}
