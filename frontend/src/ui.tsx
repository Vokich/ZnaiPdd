import { useEffect, useId, useRef, useState } from 'react'
import type { ComponentProps, ReactNode } from 'react'
import { Link, NavLink, useNavigate } from './navigation'
import { api, ApiError } from './api'
import { useSession } from './state'

export function ButtonLink({ to, children, light = false }: { to: string; children: ReactNode; light?: boolean }) {
  return <Link className={light ? 'button button-light' : 'button'} to={to}>{children}</Link>
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
      <Link className="wordmark" to="/" aria-label="Знай ПДД — главная">{kind === 'auth' && <span aria-hidden="true">→</span>}знай пдд</Link>
      {kind === 'home' && <a className="about-link" href="#audience">Для кого этот сайт</a>}
      {kind === 'portal' && user ? <>
        <button ref={menuToggle} className="button button-light menu-toggle" type="button" aria-expanded={menu} aria-controls="portal-navigation" onClick={() => setMenu(!menu)}>{menu ? 'Закрыть' : 'Меню'}</button>
        <nav id="portal-navigation" className={menu ? 'portal-nav open' : 'portal-nav'} aria-label="Разделы портала">
          <NavLink to="/profile/" onClick={() => setMenu(false)}>Кабинет</NavLink>
          {user.role === 'child' && <NavLink to="/age/" onClick={() => setMenu(false)}>Тесты</NavLink>}
          <NavLink to="/signs/" onClick={() => setMenu(false)}>Знаки ПДД</NavLink>
          {user.role === 'teacher' && <NavLink to="/pdd-teacher/" onClick={() => setMenu(false)}>Отчёты</NavLink>}
          <button className="button button-light" type="button" disabled={signingOut} onClick={signOut}>Выйти</button>
        </nav>
      </> : <ButtonLink to={user ? '/profile/' : '/login/'}>{user ? 'Мой кабинет' : kind === 'home' ? 'Войти →' : 'Войти'}</ButtonLink>}
    </div>
    <Feedback error={error} />
  </header>
}

export function Footer() {
  return <footer className="site-footer">
    <div className="footer-inner" data-scroll-reveal="quiet">
      <Link className="wordmark" to="/">знай пдд</Link>
      <nav aria-label="Социальные сети">
        <a href="https://vk.ru/media_uid_lo" target="_blank" rel="noreferrer">VK Медиа ЮИД →</a>
        <a href="https://vk.ru/lab48" target="_blank" rel="noreferrer">VK Лаборатория 48 →</a>
      </nav>
    </div>
  </footer>
}

export function Character({ role, className = '' }: { role: 'student' | 'teacher'; className?: string }) {
  return <img className={`character ${className}`} src={`/art/${role}.png`} alt="" aria-hidden="true" />
}

export function Feedback({ error }: { error?: unknown }) {
  if (!error) return null
  const message = error instanceof Error ? error.message : 'Возникла ошибка. Попробуйте ещё раз.'
  return <p className="feedback" role="alert">{message}</p>
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

export function Municipality({ value = '', error }: { value?: string; error?: unknown }) {
  const id = useId()
  const [query, setQuery] = useState(value)
  const [open, setOpen] = useState(false)
  const [matches, setMatches] = useState<{ results: string[]; more: boolean }>()
  const [searchFailed, setSearchFailed] = useState(false)
  const [active, setActive] = useState(-1)
  const invalid = error instanceof ApiError && Boolean(error.fields.region)

  useEffect(() => {
    if (!open || query.trim().length < 2) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      api<{ results: string[]; more: boolean }>('municipalities/?q=' + encodeURIComponent(query), { signal: controller.signal })
        .then(setMatches)
        .catch(() => { if (!controller.signal.aborted) setSearchFailed(true) })
    }, 180)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [query, open])

  function choose(municipality: string) {
    setQuery(municipality)
    setOpen(false)
    setActive(-1)
  }
  const options = matches?.results ?? []
  const expanded = open && query.trim().length >= 2
  return <div className="field municipality">
    <label htmlFor={id}>Муниципалитет</label>
    <input id={id} name="region" role="combobox" autoComplete="off" required maxLength={400}
      placeholder="Введите муниципалитет" value={query} aria-expanded={expanded} aria-controls={id + '-options'}
      aria-autocomplete="list" aria-invalid={invalid || undefined}
      aria-describedby={invalid ? 'region-error' : undefined}
      aria-activedescendant={expanded && active >= 0 ? id + '-' + active : undefined}
      onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}
      onChange={event => { setQuery(event.target.value); setOpen(true); setMatches(undefined); setSearchFailed(false); setActive(-1) }}
      onKeyDown={event => {
        if (event.key === 'Escape') { setOpen(false); return }
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault()
          setOpen(true)
          if (!options.length) return
          const index = event.key === 'ArrowDown' ? (active + 1) % options.length : (active < 0 ? options.length - 1 : (active - 1 + options.length) % options.length)
          setActive(index)
          document.getElementById(id + '-' + index)?.scrollIntoView({ block: 'nearest', behavior: 'instant' })
        }
        if (event.key === 'Enter' && expanded && options[active]) { event.preventDefault(); choose(options[active]) }
      }} />
    <FieldErrors error={error} name="region" />
    <div inert={!expanded} aria-hidden={!expanded} className={expanded ? 'municipality-menu open' : 'municipality-menu'}>
      <div role="listbox" id={id + '-options'} aria-label="Найденные муниципалитеты">
        {options.map((option, index) => <div id={id + '-' + index} key={option} role="option" aria-selected={active === index}
          onMouseDown={event => event.preventDefault()} onClick={() => choose(option)}>{option}</div>)}
      </div>
      <span className="municipality-status" role="status">
        {searchFailed ? 'Поиск недоступен. Попробуйте ещё раз.' : !matches ? 'Ищем…' : !options.length ? 'Ничего не найдено.' : matches.more ? 'Уточните название для поиска.' : ''}
      </span>
    </div>
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
