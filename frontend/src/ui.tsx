import { useEffect, useId, useRef, useState } from 'react'
import type { ComponentProps, ReactNode } from 'react'
import { Link, NavLink, useNavigate } from './navigation'
import { api, ApiError } from './api'
import type { GalleryImage, Organization } from './api'
import { useSession } from './state'
import { useMotionSettings } from './motion-settings'
import * as Switch from '@radix-ui/react-switch'
import * as m from 'motion/react-m'
import { spring } from './motion-ui'

export function ButtonLink({ to, children, light = false }: { to: string; children: ReactNode; light?: boolean }) {
  return <Link className={light ? 'button button-light' : 'button'} to={to}>{children}</Link>
}

function Wordmark() {
  return <Link className="wordmark" to="/" aria-label="Знай ПДД — главная">
    <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>знай пдд
  </Link>
}

function MotionToggle() {
  const { enabled, reduced, toggle } = useMotionSettings()
  return <Switch.Root checked={enabled} disabled={reduced} onCheckedChange={toggle} className="site-motion-toggle"
    aria-label="Анимация на сайте" title={reduced ? 'Движение ограничено настройками устройства' : undefined}>
    <Switch.Thumb className="motion-switch-track" asChild>
      <m.span><m.i animate={{ x: enabled ? 9 : 0 }} transition={enabled ? spring : { duration: 0 }} /></m.span>
    </Switch.Thumb>
    <span>Движение <span>{enabled ? 'вкл.' : 'выкл.'}</span></span>
  </Switch.Root>
}

function HeaderLink({ to, children, onClick }: { to: string; children: ReactNode; onClick: () => void }) {
  const { enabled } = useMotionSettings()
  return <NavLink className="motion-header-link" to={to} onClick={onClick}>
    {({ isActive }) => <>
      {isActive && <m.span aria-hidden="true" className="header-active" layoutId={enabled ? 'header-active' : undefined}
        transition={enabled ? spring : { duration: 0 }} />}
      {children}
    </>}
  </NavLink>
}

export function Header({ kind }: { kind: 'home' | 'auth' | 'portal' }) {
  const { user, setUser } = useSession()
  const navigate = useNavigate()
  const [signingOut, setSigningOut] = useState(false)
  const [error, setError] = useState<unknown>()
  const [menu, setMenu] = useState(false)
  const header = useRef<HTMLElement>(null)
  const menuToggle = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!menu) return
    function onPointerDown(event: PointerEvent) {
      if (event.target instanceof Node && !header.current?.contains(event.target)) setMenu(false)
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      setMenu(false)
      menuToggle.current?.focus()
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [menu])
  async function signOut() {
    setError(undefined)
    setSigningOut(true)
    try {
      await api('session/', { method: 'DELETE' })
      setUser(null)
      setMenu(false)
      navigate('/')
    } catch (error) { setError(error) }
    finally { setSigningOut(false) }
  }
  return <header ref={header} className={`site-header header-${kind}`}>
    <div className="header-inner">
      <Wordmark />
      {kind !== 'auth' && <>
        <nav id="portal-navigation" className={menu ? 'portal-nav open' : 'portal-nav'} aria-label="Разделы портала">
          {kind === 'home' ? <>
            <a href="#project" onClick={() => setMenu(false)}>О проекте</a>
            <a href="#shtrikh" onClick={() => setMenu(false)}>Штрих</a>
            <a href="#audience" onClick={() => setMenu(false)}>Для кого</a>
          </> : <>
            <HeaderLink to="/profile/" onClick={() => setMenu(false)}>Кабинет</HeaderLink>
            <HeaderLink to="/signs/" onClick={() => setMenu(false)}>Знаки ПДД</HeaderLink>
            <HeaderLink to="/practice/" onClick={() => setMenu(false)}>Практика</HeaderLink>
            <HeaderLink to="/safe-route/" onClick={() => setMenu(false)}>Маршрут</HeaderLink>
          </>}
          <HeaderLink to="/news/" onClick={() => setMenu(false)}>Новости</HeaderLink>
          {kind === 'portal' && <>
            <HeaderLink to="/rating/" onClick={() => setMenu(false)}>Рейтинг</HeaderLink>
            {user?.role === 'child' && <HeaderLink to="/age/" onClick={() => setMenu(false)}>Тесты</HeaderLink>}
            {user?.role === 'teacher' && <HeaderLink to="/pdd-teacher/" onClick={() => setMenu(false)}>Отчёты</HeaderLink>}
            {user && <button className="button button-light mobile-signout" type="button" disabled={signingOut} onClick={signOut}>Выйти</button>}
          </>}
        </nav>
      </>}
      <div className="header-actions">
        {kind === 'portal' ? <>
          <MotionToggle />
          {user && <button className="button button-light signout" type="button" disabled={signingOut} onClick={signOut}>Выйти</button>}
        </> : <ButtonLink to={user ? '/profile/' : '/login/'}>{user ? 'В кабинет' : 'Войти'} <span aria-hidden="true">→</span></ButtonLink>}
        {kind !== 'auth' && <button ref={menuToggle} className="button button-light menu-toggle" type="button"
          aria-label={menu ? 'Закрыть меню' : 'Открыть меню'} aria-expanded={menu} aria-controls="portal-navigation"
          onClick={() => setMenu(!menu)}><span aria-hidden="true">{menu ? '×' : '≡'}</span></button>}
      </div>
    </div>
    <Feedback error={error} />
  </header>
}

export function Footer() {
  return <footer className="site-footer">
    <div className="footer-inner" data-scroll-reveal="quiet">
      <Wordmark />
      <div className="footer-links">
        <nav aria-label="Социальные сети">
          <a href="https://vk.ru/media_uid_lo" target="_blank" rel="noreferrer">Медиа ЮИД ↗</a>
          <a href="https://vk.ru/lab48" target="_blank" rel="noreferrer">Лаборатория 48 ↗</a>
        </nav>
        <MotionToggle />
      </div>
    </div>
  </footer>
}

export function PracticeIcon({ kind }: { kind: string }) {
  return kind === 'plates' ? <span className="stop-icon" aria-hidden="true" />
    : <img className="practice-icon" src="/art/practice.webp" width="114" height="73" alt="" />
}

export function MediaGallery({ images }: { images?: GalleryImage[] }) {
  if (!images?.length) return null
  return <div className="media-gallery">
    {images.map(image => <figure key={image.id}>
      <a href={image.url} target="_blank" rel="noopener noreferrer"
        aria-label={['Открыть изображение в новой вкладке', image.alt || image.caption].filter(Boolean).join('. ')}>
        <img src={image.url} alt={image.alt} loading="lazy" />
      </a>
      {image.caption && <figcaption>{image.caption}</figcaption>}
    </figure>)}
  </div>
}

export function Character({ role, className = '' }: { role: 'student' | 'teacher'; className?: string }) {
  return <img className={`character ${className}`} src={`/art/${role}.png`} alt="" aria-hidden="true" />
}

export function Feedback({ error }: { error?: unknown }) {
  if (!error) return null
  const message = error instanceof Error ? error.message : 'Возникла ошибка. Попробуйте ещё раз.'
  const formErrors = error instanceof ApiError ? error.fields.__all__ : undefined
  if (error instanceof ApiError && error.fields.code === 'not_authenticated') {
    return <p className="feedback" role="alert">Время сеанса истекло. <Link to="/login/">Войдите снова</Link>.</p>
  }
  return <p className="feedback" role="alert">{formErrors ? [formErrors].flat().join(' ') : message}</p>
}

export function FieldErrors({ error, name }: { error?: unknown; name: string }) {
  const messages = error instanceof ApiError ? error.fields[name] : undefined
  return messages ? <span className="field-error" id={`${name}-error`}>{[messages].flat().join(' ')}</span> : null
}

type FieldProps = ComponentProps<'input'> & {
  name: string
  label: string
  error?: unknown
  wide?: boolean
}

export function Field({ name, label, error, wide, ...input }: FieldProps) {
  const invalid = error instanceof ApiError && Boolean(error.fields[name])
  return <label className={wide ? 'field wide' : 'field'}>
    <span>{label}</span>
    <input {...input} name={name} aria-invalid={invalid || undefined} aria-describedby={invalid ? name + '-error' : undefined} />
    <FieldErrors error={error} name={name} />
  </label>
}

export function OrganizationField({ value, error }: { value?: Organization | null; error?: unknown }) {
  const id = useId()
  const [selected, setSelected] = useState(value ?? null)
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState<Organization[]>()
  const [searchFailed, setSearchFailed] = useState(false)
  const searching = query.trim().length >= 2

  useEffect(() => {
    if (!searching) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      api<Organization[]>('organizations/?q=' + encodeURIComponent(query.trim()), { signal: controller.signal })
        .then(setMatches)
        .catch(() => { if (!controller.signal.aborted) setSearchFailed(true) })
    }, 180)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [query, searching])

  return <div className="field wide">
    <input type="hidden" name="organization" value={selected?.id ?? ''} />
    <label htmlFor={id}>Организация (необязательно)</label>
    {selected ? <div className="actions">
      <span>{selected.name}, {selected.municipality}</span>
      <button className="text-link" type="button" onClick={() => setSelected(null)}>Снять выбор</button>
    </div> : <>
      <input id={id} value={query} autoComplete="off" maxLength={300} placeholder="Введите название организации"
        onChange={event => { setQuery(event.target.value); setMatches(undefined); setSearchFailed(false) }}
        onKeyDown={event => { if (event.key === 'Enter') event.preventDefault() }} />
      {searching && <div>
        <span role="status">{searchFailed ? 'Поиск временно недоступен.' : !matches ? 'Ищем…' : !matches.length ? 'Ничего не найдено.' : ''}</span>
        {matches && matches.length > 0 && <ul className="organization-results">
          {matches.map(organization => <li key={organization.id}>
            <button className="text-link" type="button" onClick={() => { setSelected(organization); setQuery('') }}>
              {organization.name}, {organization.municipality}
            </button>
          </li>)}
        </ul>}
      </div>}
    </>}
    <FieldErrors error={error} name="organization" />
  </div>
}

export function Loading() {
  return <div className="panel status-panel" role="status"><span className="loading-dot" />Загрузка…</div>
}

export function LoadError({ error, retry }: { error: unknown; retry: () => void }) {
  return <div className="panel status-panel"><Feedback error={error} /><button className="button button-light" onClick={retry}>Повторить</button></div>
}

export function PortalHeading({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="portal-heading"><h1>{title}</h1>{children && <p>{children}</p>}</div>
}

export const formatDate = (value: string) => new Intl.DateTimeFormat('ru', { dateStyle: 'medium', timeZone: 'Europe/Moscow' }).format(new Date(value))
