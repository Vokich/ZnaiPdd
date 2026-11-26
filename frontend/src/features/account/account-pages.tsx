import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from '../../shared/navigation'
import { api } from '../../shared/api'
import type { Profile, ProfileResponse, QuizResult } from '../../shared/api'
import { useResource, useSession } from '../../shared/state'
import { ButtonLink, Feedback, Field, formatDate, Loading, LoadError, PortalHeading, PracticeIcon } from '../../shared/ui'
import { quizInfo } from '../quizzes/quiz-info'
import { CompetitionMode } from '../rating/rating-page'
import { Mascot } from '../../shared/mascot'
import { MotionNumber } from '../../shared/motion/motion-ui'

const scoreLabels = { routes: 'За маршруты', tests: 'За тесты', practice: 'За практику', signs: 'За знаки', qr: 'За QR-тесты платформы' }

export function AccountPage() {
  const { data, error, retry } = useResource<ProfileResponse>()
  if (error) return <LoadError error={error} retry={retry} />
  if (!data) return <Loading />
  const { profile, results, reports_count, rating, suggested_practice } = data
  if (!profile.role) return <>
    <PortalHeading title="Завершите настройку профиля" />
    <div className="panel status-panel">
      <p>Укажите имя и фамилию, чтобы открыть свой кабинет.</p>
      <ButtonLink to="/profile/edit/">Заполнить профиль</ButtonLink>
    </div>
  </>
  return <>
    <PortalHeading title={profile.role === 'teacher' ? 'Кабинет педагога' : 'Твой кабинет'}>
      Здесь видно, что уже получилось и куда пойти дальше.
    </PortalHeading>
    <div className="dashboard">
      <section className="panel dashboard-score">
        <h2>Общий зачёт</h2>
        <p className="dashboard-number"><strong><MotionNumber value={rating.points} /></strong> баллов</p>
        <dl className="dashboard-breakdown">{rating.directions.map(item => <div key={item.id}>
          <dd><strong>{item.points}</strong></dd><dt>{scoreLabels[item.id]}</dt>
        </div>)}</dl>
        <ButtonLink to="/rating/" light>Место в рейтинге <span aria-hidden="true">→</span></ButtonLink>
      </section>
      <section className="panel dashboard-next">
        <img src="/art/signal.webp" alt="" />
        <div>
          <p className="eyebrow">Следующий шаг</p>
          <h2>Пора на маршрут</h2>
          <p>У дома тебя ждёт первая ситуация. Рассмотри улицу и выбери безопасный шаг.</p>
          <ButtonLink to="/safe-route/">Открыть маршрут <span aria-hidden="true">→</span></ButtonLink>
        </div>
      </section>
      <section className="panel dashboard-practice">
        <h2>Попробуй в практике</h2>
        {suggested_practice.length ? <ul>{suggested_practice.map(item => <li key={item.slug}>
          <Link to={'/practice/' + item.slug + '/'}><PracticeIcon kind={item.kind_id} />
            <span><strong>{item.title}</strong><small>{item.topic}</small></span><span aria-hidden="true">→</span></Link>
        </li>)}</ul> : <ButtonLink to="/practice/" light>К заданиям →</ButtonLink>}
      </section>
      <CompetitionMode initialEnabled={profile.competition_enabled} />
    </div>
    <div className="panel profile-summary">
      <div>
        <span className="tag">{{ teacher: 'Педагог', child: 'Пользователь', admin: 'Администратор' }[profile.role]}</span>
        <h2>{[profile.surname1, profile.name, profile.surname2].filter(Boolean).join(' ') || profile.username}</h2>
        <dl className="profile-details">
          {(profile.organization || profile.school) && <div><dt>Организация</dt><dd>{profile.organization?.name || profile.school}{profile.organization && !profile.organization_confirmed && ' · ожидает подтверждения'}</dd></div>}
          {(profile.organization?.municipality || profile.region) && <div><dt>Муниципалитет</dt><dd>{profile.organization?.municipality || profile.region}</dd></div>}
          <div><dt>Почта</dt><dd>{profile.email || '—'}</dd></div>
          {profile.role === 'teacher' && profile.position && <div><dt>Должность</dt><dd>{profile.position}</dd></div>}
        </dl>
        <div className="actions"><ButtonLink to="/profile/edit/">Редактировать</ButtonLink><ButtonLink to="/profile/password/" light>Сменить пароль</ButtonLink></div>
      </div>
      <Mascot className="profile-mascot" />
    </div>
    <div className="portal-grid account-links">
      {profile.role === 'teacher' && <>
        <Link className="panel route-card" to="/classroom/"><h2>Провести урок</h2><p>Разберите дорожную ситуацию вместе с классом.</p><span aria-hidden="true">→</span></Link>
        <Link className="panel route-card" to="/classroom/tests/"><h2>Мои тесты</h2><p>Подготовьте вопросы и запустите тест по QR.</p><span aria-hidden="true">→</span></Link>
        <Link className="panel route-card" to="/classroom/history/"><h2>История запусков</h2><p>Откройте занятие, его сводку или отчёт.</p><span aria-hidden="true">→</span></Link>
      </>}
      {profile.role === 'child' && <Link className="panel route-card" data-scroll-reveal="card" to="/age/"><h2>Тесты по ПДД</h2><p>Выберите тест для своей возрастной группы.</p><span aria-hidden="true">→</span></Link>}
      {profile.role === 'teacher' && <Link className="panel route-card" data-scroll-reveal="card" to="/pdd-teacher/"><h2>Отчёты об уроках</h2><p>Мои отчёты · {reports_count}</p><span aria-hidden="true">→</span></Link>}
      {profile.role === 'admin' && <a className="panel route-card" href="/admin/"><h2>Админ-панель</h2><span aria-hidden="true">→</span></a>}
      <Link className="panel route-card" data-scroll-reveal="card" to="/signs/"><h2>Знаки ПДД</h2><p>Справочник и личная коллекция.</p><span aria-hidden="true">→</span></Link>
      <Link className="panel route-card" to="/practice/history/"><h2>Моя практика</h2><p>Посмотреть выполненные задания.</p><span aria-hidden="true">→</span></Link>
      {profile.role === 'teacher' && <a className="panel route-card" data-scroll-reveal="card" href="/api/training-material/"><h2>Материалы для уроков</h2><p>Скачать учебный документ.</p><span aria-hidden="true">↓</span></a>}
    </div>
    {profile.role === 'child' && <ResultHistory key={profile.id + ':' + (results[0]?.id ?? '')} initial={results} cursor={data.next_results} />}
  </>
}

function ResultHistory({ initial, cursor }: { initial: QuizResult[]; cursor: number | null }) {
  const [results, setResults] = useState(initial)
  const [next, setNext] = useState(cursor)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  async function more() {
    if (busy || next === null) return
    setBusy(true)
    setError(undefined)
    try {
      const page = await api<{ results: QuizResult[]; next: number | null }>('profile/results/?before=' + next)
      setResults(previous => [...previous, ...page.results])
      setNext(page.next)
    } catch (failure) { setError(failure) }
    finally { setBusy(false) }
  }
  return <section className="panel history">
      <h2 data-scroll-reveal="quiet">Мои результаты</h2>
      {results.length ? <ul className="data-list">
        {results.map(result => <li key={result.id} data-scroll-reveal="quiet"><Link to={quizInfo[result.test_type].result + '?id=' + result.id}>
          <span><strong>{quizInfo[result.test_type].ages}</strong><small>{formatDate(result.completed_at)}</small></span>
          <span className={result.passed ? 'tag' : 'tag tag-muted'}>{result.score} / {result.total}</span>
        </Link></li>)}
      </ul> : <p>Результаты появятся после первого теста.</p>}
      {next !== null && <button className="button button-light" type="button" disabled={busy} onClick={() => void more()}>
        {busy ? 'Загрузка…' : 'Показать ещё'}</button>}
      <Feedback error={error} />
    </section>
}

export function EditProfilePage() {
  const { data, error, retry } = useResource<ProfileResponse>()
  if (error) return <LoadError error={error} retry={retry} />
  return data ? <EditProfileForm profile={data.profile} /> : <Loading />
}

function EditProfileForm({ profile }: { profile: Profile }) {
  const { setUser } = useSession()
  const navigate = useNavigate()
  const [error, setError] = useState<unknown>()
  const [pending, setPending] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget))
    setPending(true)
    setError(undefined)
    try {
      const updated = await api<ProfileResponse>('profile/', { method: 'PATCH', data })
      const { id, username, name, role, can_submit_reports } = updated.profile
      setUser({ id, username, name: name || username, role, can_submit_reports })
      navigate('/profile/')
    } catch (error) { setError(error) }
    finally { setPending(false) }
  }
  return <>
    <PortalHeading title={profile.role ? "Редактирование профиля" : "Настройка профиля"} />
    <form className="panel editor" onSubmit={submit}>
      <div className="field-grid" data-scroll-fields="">
        <Field label="Логин" name="username" defaultValue={profile.username} autoComplete="username" maxLength={150} required error={error} />
        <Field label="Почта" name="email" type="email" defaultValue={profile.email} autoComplete="email" maxLength={254} error={error} />
        <Field label="Фамилия" name="surname1" defaultValue={profile.surname1} autoComplete="family-name" maxLength={50} required error={error} />
        <Field label="Имя" name="name" defaultValue={profile.name} autoComplete="given-name" maxLength={50} required error={error} />
        <Field label="Отчество (при наличии)" name="surname2" defaultValue={profile.surname2} autoComplete="additional-name" maxLength={50} error={error} />
        {profile.role === 'teacher' &&
          <Field label="Должность" name="position" defaultValue={profile.position} maxLength={100} error={error} />
        }
        <p>Организация: {profile.organization?.name ?? 'не указана'}. Для привязки или перевода напишите <Link to="/#teacher-contact">администратору в личные сообщения</Link>.</p>
      </div>
      <Feedback error={error} />
      <div className="actions" data-scroll-reveal="quiet"><button className="button" disabled={pending}>Сохранить →</button><ButtonLink to="/profile/" light>Отмена</ButtonLink></div>
    </form>
  </>
}

export function PasswordPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<unknown>()
  const [pending, setPending] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget))
    setPending(true)
    setError(undefined)
    try {
      await api('profile/password/', { method: 'POST', data })
      navigate('/profile/')
    } catch (error) { setError(error) }
    finally { setPending(false) }
  }
  return <>
    <PortalHeading title="Смена пароля" />
    <form className="panel editor editor-narrow" data-scroll-fields="" onSubmit={submit}>
      <Field label="Текущий пароль" name="old_password" type="password" autoComplete="current-password" required error={error} />
      <Field label="Новый пароль" name="new_password" type="password" autoComplete="new-password" minLength={8} required error={error} />
      <Field label="Повторите новый пароль" name="confirm_password" type="password" autoComplete="new-password" minLength={8} required error={error} />
      <Feedback error={error} />
      <div className="actions" data-scroll-reveal="quiet"><button className="button" disabled={pending}>Сменить пароль →</button><ButtonLink to="/profile/" light>Отмена</ButtonLink></div>
    </form>
  </>
}
