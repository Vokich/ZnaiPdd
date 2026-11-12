import { useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { Link, useNavigate } from './navigation'
import { api } from './api'
import type { Role, User } from './api'
import { useSession } from './state'
import { ButtonLink, Character, Feedback, Field, FieldErrors, Municipality } from './ui'
import { useLandingMotion } from './landing-motion'
import { RoadCircuit } from './road-circuit'

const ribbonText = 'ЗНАЙ ПДД · ДВИГАЙСЯ УВЕРЕННО ·'
const heroLead = 'Скажи «да»'
const heroSubtitle = 'безопасным дорогам'

const tiles = [
  { icon: 'book', text: 'проверяй знания' },
  { icon: 'arrow', text: 'разбирай ситуации' },
  { icon: 'crossing', text: 'изучай правила' },
  { icon: 'check', text: 'береги себя' },
]

const audiences = [
  {
    label: '01 / ШКОЛЬНИКАМ', role: 'student',
    title: <>Увереннее<br />на каждой улице</>,
    text: 'Дорога — зона ответственности. Проверяй знания правил и чувствуй себя увереннее на улице.',
  },
  {
    label: '02 / ПЕДАГОГАМ', role: 'teacher',
    title: <>Уроки, которые<br />запоминаются</>,
    text: 'Делайте уроки по ПДД интересными и эффективными. «Знай ПДД» поможет вам в этой важной миссии.',
  },
] as const

export function HomePage() {
  const { user } = useSession()
  const { landing, paused, intro, toggle } = useLandingMotion()
  return <div className="landing" ref={landing} data-paused={paused ? '' : undefined} data-intro={intro ? '' : undefined}>
    <section className="hero" data-loop="" aria-labelledby="hero-title">
      <h1 id="hero-title" aria-label={`${heroLead} ${heroSubtitle}`}>
        <span className="hero-lead" aria-hidden="true">
          {Array.from(heroLead, (letter, index) => <span className="hero-letter" key={index} style={{ animationDelay: `${78 + index * 51}ms` }}>{letter}</span>)}
        </span>{' '}<span className="hero-subtitle">{heroSubtitle}</span>
      </h1>
      <div className="hero-ribbon" aria-hidden="true">
        <div className="ribbon-track">
          {[0, 1].map(copy => <div className="ribbon-run" key={copy}>
            {Array.from({ length: 12 }, (_, index) => <span key={index}>{ribbonText}</span>)}
          </div>)}
        </div>
      </div>
      <div className="hero-portrait portrait-student"><Character role="student" /></div>
      <div className="hero-portrait portrait-teacher"><Character role="teacher" /></div>
      <button type="button" className="motion-toggle" aria-label={paused ? 'Включить анимацию' : 'Приостановить анимацию'} title={paused ? 'Включить анимацию' : 'Приостановить анимацию'} onClick={toggle}>
        <span aria-hidden="true" />
      </button>
    </section>
    <section className="welcome" aria-labelledby="welcome-title">
      <div className="welcome-copy" data-reveal="">
        <h2 id="welcome-title">Добро пожаловать<br />на портал «Знай ПДД»</h2>
        <p>Проходи тесты, разбирай сложные ситуации и делай свои дороги ясными и безопасными.</p>
        <a className="circuit-anchor" href="#road-circuit">К дорожным карточкам <span aria-hidden="true">↓</span></a>
      </div>
      <ul className="welcome-tiles" data-reveal="" data-loop="">
        {tiles.map(({ icon, text }) => <li key={icon}>
          <span className={`tile-icon icon-${icon}`} aria-hidden="true">{icon === 'check' ? '✓' : ''}</span>
          <span>{text}</span>
        </li>)}
      </ul>
      <div className="welcome-action" data-reveal=""><ButtonLink to={user ? '/profile/' : '/login/'}>{user ? 'Перейти в кабинет →' : 'Войти на портал →'}</ButtonLink></div>
      <div className="welcome-badge-slot" data-reveal="" data-loop="" aria-hidden="true"><div className="welcome-badge"><div><span /></div></div></div>
    </section>
    <section className="audience" id="audience" aria-labelledby="audience-title">
      <div className="audience-background" data-reveal="" aria-hidden="true" />
      <div className="audience-heading" data-reveal="">
        <p className="audience-kicker">для каждого</p>
        <h2 id="audience-title">Для кого<br />этот сайт?</h2>
      </div>
      <div className="audience-grid">
        {audiences.map(({ label, title, text, role }) => <article key={role} className="audience-card" data-reveal="">
          <div className="audience-text"><p className="audience-label">{label}</p><h3>{title}</h3><p>{text}</p></div>
          <Character role={role} />
        </article>)}
      </div>
    </section>
    <RoadCircuit paused={paused} toggle={toggle} />
  </div>
}

function AuthArtwork({ registration = false }: { registration?: boolean }) {
  return <aside className="auth-artwork" aria-hidden="true">
    {registration ? <>
      <p className="auth-display">Твой маршрут<br />к безопасной<br />дороге</p>
      <p className="auth-caption">Создай аккаунт на портале<br />«Знай ПДД»</p>
    </> : <p className="auth-display">С возвращением<br />на знакомый маршрут</p>}
    <div className="auth-portraits"><Character role="student" /><Character role="teacher" /></div>
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
  const [role, setRole] = useState<Role>('child')
  const teacher = role === 'teacher'
  const { submit, error, submitting, returnState } = useAuthenticationForm(true)
  return <div className="auth-layout registration-layout">
    <AuthArtwork registration />
    <section className="auth-card registration-card">
      <h1>Регистрация</h1>
      <p className="auth-intro"><Link to="/login/" state={returnState}>Уже есть аккаунт? Войти →</Link></p>
      <form onSubmit={submit}>
        <fieldset className="form-section" data-scroll-reveal="quiet">
          <legend>01 Данные для входа</legend>
          <div className="field-grid">
            <Field name="username" label="Логин" placeholder="Придумайте логин" autoComplete="username" maxLength={150} required error={error} />
            <Field name="password" label="Пароль" placeholder="Придумайте пароль" type="password" autoComplete="new-password" required error={error} />
            <Field name="email" label="Почта" placeholder="name@example.ru" type="email" autoComplete="email" maxLength={254} required wide error={error} />
          </div>
        </fieldset>
        <fieldset className="form-section" data-scroll-reveal="quiet">
          <legend>02 О себе</legend>
          <div className="field-grid">
            <Field name="surname1" label="Фамилия" placeholder="Введите фамилию" autoComplete="family-name" maxLength={50} required error={error} />
            <Field name="name" label="Имя" placeholder="Введите имя" autoComplete="given-name" maxLength={50} required error={error} />
            <Field name="surname2" label="Отчество" placeholder="Введите отчество" autoComplete="additional-name" maxLength={50} error={error} />
            <Field name="birth_date" label="Дата рождения" type="date" autoComplete="bday" required error={error} />
          </div>
        </fieldset>
        <fieldset className="form-section" data-scroll-reveal="quiet">
          <legend>03 Учёба и роль</legend>
          <div className="field-grid">
            <Field name="school" label="Учебное заведение" placeholder="Название учебного заведения" autoComplete="organization" maxLength={100} required wide error={error} />
            <Municipality error={error} />
            <div className="field">
              <label htmlFor="registration-role">Роль</label>
              <select id="registration-role" name="role" value={role} onChange={event => setRole(event.target.value as Role)}>
                <option value="child">Школьник</option>
                <option value="teacher">Педагог</option>
              </select>
              <FieldErrors error={error} name="role" />
            </div>
          </div>
          <div className={teacher ? 'role-field open' : 'role-field'} inert={!teacher} aria-hidden={!teacher}>
            <div><Field name="position" label="Должность" placeholder="Введите должность" autoComplete="organization-title" maxLength={100} required={teacher} disabled={!teacher} error={error} /></div>
          </div>
        </fieldset>
        <div className="consent" data-scroll-reveal="quiet">
          <label><input type="checkbox" name="consent" required />
            <span>Я согласен(сна) на <Link to="/privacy-policy/" target="_blank">обработку персональных данных</Link></span>
          </label>
          <FieldErrors error={error} name="consent" />
        </div>
        <Feedback error={error} />
        <button className="button" data-scroll-reveal="quiet" disabled={submitting}>{submitting ? 'Регистрируем…' : 'Зарегистрироваться →'}</button>
      </form>
    </section>
  </div>
}
