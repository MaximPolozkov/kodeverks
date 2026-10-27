import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { api } from '@/api/client'
import type { User } from '@/api/types'
import { Field } from '@/components/ui/Field'
import { PageHeader } from '@/components/ui/misc'
import { roleLabels } from '@/lib/labels'

import { useMe, useSetMe } from './auth'

const profileSchema = z.object({
  name: z.string().trim().min(2, 'Минимум 2 символа').max(100),
  email: z.string().trim().email('Укажите почту в формате name@example.com'),
  phone: z
    .string()
    .trim()
    .max(32)
    .regex(/^[\d\s()+-]*$/, 'Только цифры, пробелы, скобки, + и -'),
})
type ProfileValues = z.infer<typeof profileSchema>

const passwordSchema = z
  .object({
    old_password: z.string().min(1, 'Введите текущий пароль'),
    new_password: z.string().min(8, 'Минимум 8 символов'),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, { path: ['confirm'], message: 'Пароли не совпадают' })
type PasswordValues = z.infer<typeof passwordSchema>

function Saved({ show, text }: { show: boolean; text: string }) {
  return show ? (
    <span role="status" className="text-[15px] text-ok">
      {text}
    </span>
  ) : null
}

export default function ProfilePage() {
  const { data: me } = useMe()
  const setMe = useSetMe()
  const fileRef = useRef<HTMLInputElement>(null)
  const [profileSaved, setProfileSaved] = useState(false)
  const [passwordSaved, setPasswordSaved] = useState(false)

  const profileForm = useForm<ProfileValues>({ resolver: zodResolver(profileSchema) })
  const passwordForm = useForm<PasswordValues>({ resolver: zodResolver(passwordSchema) })

  useEffect(() => {
    if (me) profileForm.reset({ name: me.name, email: me.email, phone: me.phone ?? '' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.id])

  const saveProfile = useMutation({
    mutationFn: (v: ProfileValues) => api<User>('/api/admin/profile', { method: 'PATCH', json: v }),
    onSuccess: (user) => {
      setMe(user)
      setProfileSaved(true)
    },
  })

  const changePassword = useMutation({
    mutationFn: (v: PasswordValues) =>
      api<User>('/api/admin/profile/password', {
        method: 'POST',
        json: { old_password: v.old_password, new_password: v.new_password },
      }),
    onSuccess: () => {
      passwordForm.reset({ old_password: '', new_password: '', confirm: '' })
      setPasswordSaved(true)
    },
  })

  const uploadAvatar = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData()
      body.append('file', file)
      return api<User>('/api/admin/profile/avatar', { method: 'POST', body })
    },
    onSuccess: setMe,
  })

  if (!me) return null
  const pe = profileForm.formState.errors
  const pwe = passwordForm.formState.errors

  return (
    <>
      <PageHeader title="Профиль" />
      <div className="grid max-w-5xl gap-5 sm:gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <section className="panel flex flex-col items-center p-4 text-center sm:p-5">
          {me.avatar_url ? (
            <img src={me.avatar_url} alt="" className="h-28 w-28 rounded-full object-cover" />
          ) : (
            <div className="flex h-28 w-28 items-center justify-center rounded-full bg-ink font-display text-[34px] font-bold text-marker">
              {me.name.slice(0, 1).toUpperCase()}
            </div>
          )}
          <p className="break-anywhere mt-4 font-semibold">{me.name}</p>
          <p className="text-[15px] text-muted">{roleLabels[me.role]}</p>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) uploadAvatar.mutate(file)
              e.target.value = ''
            }}
          />
          <button className="btn-ghost mt-4" onClick={() => fileRef.current?.click()} disabled={uploadAvatar.isPending}>
            {uploadAvatar.isPending ? 'Загружаем…' : 'Сменить фото'}
          </button>
          <p className="mt-2 text-[13px] text-muted">JPG, PNG или WebP до 2 МБ</p>
          {uploadAvatar.isError && <p className="mt-2 text-[14px] text-danger">{uploadAvatar.error.message}</p>}
        </section>

        <div className="min-w-0 space-y-5 sm:space-y-6">
          <form
            className="panel space-y-4 p-4 sm:p-5"
            noValidate
            onSubmit={profileForm.handleSubmit((v) => {
              setProfileSaved(false)
              saveProfile.mutate(v)
            })}
          >
            <h2 className="font-sans text-[18px] font-semibold">Личные данные</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="p-name" label="Имя" error={pe.name?.message}>
                <input id="p-name" className="input" {...profileForm.register('name')} />
              </Field>
              <Field id="p-phone" label="Телефон" error={pe.phone?.message}>
                <input id="p-phone" className="input" inputMode="tel" {...profileForm.register('phone')} />
              </Field>
            </div>
            <Field id="p-email" label="Почта" error={pe.email?.message}>
              <input id="p-email" type="email" className="input" {...profileForm.register('email')} />
            </Field>
            {saveProfile.isError && <p className="text-danger">{saveProfile.error.message}</p>}
            <div className="flex flex-wrap items-center gap-3 sm:gap-4">
              <button className="btn-primary w-full xs:w-auto" disabled={saveProfile.isPending}>
                Сохранить изменения
              </button>
              <Saved show={profileSaved && !profileForm.formState.isDirty} text="Изменения сохранены" />
            </div>
          </form>

          <form
            className="panel space-y-4 p-4 sm:p-5"
            noValidate
            onSubmit={passwordForm.handleSubmit((v) => {
              setPasswordSaved(false)
              changePassword.mutate(v)
            })}
          >
            <h2 className="font-sans text-[18px] font-semibold">Смена пароля</h2>
            <Field id="pw-old" label="Текущий пароль" error={pwe.old_password?.message}>
              <input
                id="pw-old"
                type="password"
                autoComplete="current-password"
                className="input"
                {...passwordForm.register('old_password')}
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="pw-new" label="Новый пароль" error={pwe.new_password?.message} hint="Минимум 8 символов">
                <input
                  id="pw-new"
                  type="password"
                  autoComplete="new-password"
                  className="input"
                  {...passwordForm.register('new_password')}
                />
              </Field>
              <Field id="pw-confirm" label="Повторите новый пароль" error={pwe.confirm?.message}>
                <input
                  id="pw-confirm"
                  type="password"
                  autoComplete="new-password"
                  className="input"
                  {...passwordForm.register('confirm')}
                />
              </Field>
            </div>
            {changePassword.isError && <p className="text-danger">{changePassword.error.message}</p>}
            <div className="flex flex-wrap items-center gap-3 sm:gap-4">
              <button className="btn-primary w-full xs:w-auto" disabled={changePassword.isPending}>
                Сменить пароль
              </button>
              <Saved show={passwordSaved} text="Пароль изменён, другие сеансы завершены" />
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
