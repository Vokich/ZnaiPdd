import { useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { Link, useNavigate } from './navigation'
import { api } from './api'
import type { User } from './api'
import { useSession } from './state'
import { Feedback, Field, FieldErrors } from './ui'
import { Mascot } from './mascot'

function AuthArtwork({ registration = false }: { registration?: boolean }) {
  return <aside className="auth-artwork" aria-hidden="true">
    {registration ? <>
      <p className="auth-display">Твой маршрут<br />к безопасной<br />дороге</p>
      <p className="auth-caption">Создай аккаунт на портале<br />«Знай ПДД»</p>
    </> : <p className="auth-display">С возвращением<br />на знакомый маршрут</p>}
    <div className="auth-portraits"><Mascot mood="wave" /></div>
  </aside>
}

function useAuthenticationForm(registration: boolean) {
  const { setUser } = useSession()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<unknown>()
  const [submitting, setSubmitting] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    const data: Record<string, unknown> = Object.fromEntries(new FormData(event.currentTarget))
    if (registration) data.consent = data.consent === 'on'
    setSubmitting(true)
    setError(undefined)
    try {
      const { user } = await api<{ user: User }>(registration ? 'users/' : 'session/', { method: 'POST', data })
      setUser(user)
      const next = location.state?.next
      navigate(typeof next === 'string' && next.startsWith('/') && !next.startsWith('//') ? next : '/profile/', { replace: true })
    } catch (error) { setError(error) }
    finally { setSubmitting(false) }
  }
  return { submit, error, submitting, returnState: location.state }
}

export function LoginPage() {
  const { submit, error, submitting, returnState } = useAuthenticationForm(false)
  return <div className="auth-layout login-layout">
    <AuthArtwork />
    <section className="auth-card login-card">
      <h1>Войти</h1>
      <p className="auth-intro">Продолжим изучать правила</p>
      <form onSubmit={submit}>
        <Field name="username" label="Логин" autoComplete="username" placeholder="Введите логин" maxLength={150} required error={error} />
        <Field name="password" label="Пароль" type="password" autoComplete="current-password" placeholder="Введите пароль" required error={error} />
        <Feedback error={error} />
        <button className="button" disabled={submitting}>{submitting ? 'Входим…' : 'Далее →'}</button>
      </form>
      <p className="auth-alternate">Нет учётной записи?</p>
      <Link className="text-link" to="/reg/" state={returnState}>Зарегистрироваться →</Link>
    </section>
  </div>
}

export function RegisterPage() {
  const { submit, error, submitting, returnState } = useAuthenticationForm(true)
  return <div className="auth-layout registration-layout">
    <AuthArtwork registration />
    <section className="auth-card registration-card">
      <h1>Регистрация</h1>
      <p className="auth-intro"><Link to="/login/" state={returnState}>Уже есть аккаунт? Войти →</Link></p>
      <form onSubmit={submit}>
        <fieldset className="form-section" data-scroll-reveal="quiet">
          <legend>Данные для входа</legend>
          <div className="field-grid">
            <Field name="username" label="Логин" placeholder="Придумайте логин" autoComplete="username" maxLength={150} required error={error} />
            <Field name="password" label="Пароль" placeholder="Придумайте пароль" type="password" autoComplete="new-password" minLength={8} required error={error} />
            <Field name="email" label="Почта" placeholder="name@example.ru" type="email" autoComplete="email" maxLength={254} wide error={error} />
          </div>
        </fieldset>
        <fieldset className="form-section" data-scroll-reveal="quiet">
          <legend>Данные профиля</legend>
          <div className="field-grid">
            <Field name="surname1" label="Фамилия" placeholder="Введите фамилию" autoComplete="family-name" maxLength={50} required error={error} />
            <Field name="name" label="Имя" placeholder="Введите имя" autoComplete="given-name" maxLength={50} required error={error} />
            <Field name="surname2" label="Отчество (при наличии)" autoComplete="additional-name" maxLength={50} error={error} />
          </div>

        </fieldset>
        <div className="consent" data-scroll-reveal="quiet">
          <label><input type="checkbox" name="consent" required />
            <span>Я даю согласие на <Link to="/privacy-policy/" target="_blank">обработку персональных данных</Link></span>
          </label>
          <FieldErrors error={error} name="consent" />
        </div>
        <Feedback error={error} />
        <button className="button" data-scroll-reveal="quiet" disabled={submitting}>{submitting ? 'Регистрируем…' : 'Зарегистрироваться →'}</button>
      </form>
    </section>
  </div>
}
