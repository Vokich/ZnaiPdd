import { useState } from 'react'
import type { FormEvent } from 'react'
import type { LoaderFunctionArgs } from 'react-router-dom'
import { Link, useNavigate } from './navigation'
import { api } from './api'
import type { LessonReport, Profile, ProfileResponse } from './api'
import { useResource, useSession } from './state'
import { ButtonLink, Feedback, Field, FieldErrors, formatDate, Loading, LoadError, OrganizationField, PortalHeading, PracticeIcon } from './ui'
import { quizInfo } from './quiz-info'
import { CompetitionMode } from './rating-page'
import { Mascot } from './mascot'
import { Notice } from './motion-controls'
import { MotionNumber } from './motion-ui'

const scoreLabels = { routes: 'За маршруты', tests: 'За тесты', practice: 'За практику' }

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
        <p className="dashboard-number"><strong><MotionNumber value={rating.points} /></strong> из {rating.maximum}</p>
        <div className="dashboard-progress">
          <progress value={rating.points} max={rating.maximum} aria-label="Баллы в общем зачёте" />
          <span style={{ width: `${100 * rating.points / rating.maximum}%` }} aria-hidden="true" />
        </div>
        <dl className="dashboard-breakdown">{rating.directions.map(item => <div key={item.id}>
          <dd><strong>{item.points}</strong> / 100</dd><dt>{scoreLabels[item.id]}</dt>
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
          {(profile.organization || profile.school) && <div><dt>Организация</dt><dd>{profile.organization?.name || profile.school}</dd></div>}
          {(profile.organization?.municipality || profile.region) && <div><dt>Муниципалитет</dt><dd>{profile.organization?.municipality || profile.region}</dd></div>}
          <div><dt>Почта</dt><dd>{profile.email || '—'}</dd></div>
          {profile.role === 'teacher' && profile.position && <div><dt>Должность</dt><dd>{profile.position}</dd></div>}
        </dl>
        <div className="actions"><ButtonLink to="/profile/edit/">Редактировать</ButtonLink><ButtonLink to="/profile/password/" light>Сменить пароль</ButtonLink></div>
      </div>
      <Mascot className="profile-mascot" />
    </div>
    <div className="portal-grid account-links">
      {profile.role === 'child' && <Link className="panel route-card" data-scroll-reveal="card" to="/age/"><h2>Тесты по ПДД</h2><p>Выберите тест для своей возрастной группы.</p><span aria-hidden="true">→</span></Link>}
      {profile.role === 'teacher' && <Link className="panel route-card" data-scroll-reveal="card" to="/pdd-teacher/"><h2>Отчёты об уроках</h2><p>Мои отчёты · {reports_count}</p><span aria-hidden="true">→</span></Link>}
      {profile.role === 'admin' && <a className="panel route-card" href="/admin/"><h2>Админ-панель</h2><span aria-hidden="true">→</span></a>}
      <Link className="panel route-card" data-scroll-reveal="card" to="/signs/"><h2>Знаки ПДД</h2><p>Справочник и личная коллекция.</p><span aria-hidden="true">→</span></Link>
      <Link className="panel route-card" to="/practice/history/"><h2>Моя практика</h2><p>Посмотреть выполненные задания.</p><span aria-hidden="true">→</span></Link>
      {profile.role === 'teacher' && <a className="panel route-card" data-scroll-reveal="card" href="/api/training-material/"><h2>Материалы для уроков</h2><p>Скачать учебный документ.</p><span aria-hidden="true">↓</span></a>}
    </div>
    {profile.role === 'child' && <section className="panel history">
      <h2 data-scroll-reveal="quiet">Мои результаты</h2>
      {results.length ? <ul className="data-list">
        {results.map(result => <li key={result.id} data-scroll-reveal="quiet"><Link to={quizInfo[result.test_type].result + '?id=' + result.id}>
          <span><strong>{quizInfo[result.test_type].ages}</strong><small>{formatDate(result.completed_at)}</small></span>
          <span className={result.passed ? 'tag' : 'tag tag-muted'}>{result.score} / {result.total}</span>
        </Link></li>)}
      </ul> : <p>Результаты появятся после первого теста.</p>}
    </section>}
  </>
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
        <OrganizationField value={profile.organization} error={error} />
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

type LessonRoute = { id: string; title: string }
type ReportOptions = { routes: LessonRoute[]; practice: NonNullable<LessonReport['practice']>[] }
type LessonReportResource<T> = { reports: T; options: ReportOptions }

export async function loadLessonReports({ request, params }: LoaderFunctionArgs) {
  const path = params.id ? 'lesson-reports/' + encodeURIComponent(params.id) + '/' : 'lesson-reports/'
  const options = { signal: request.signal }
  try {
    const [reports, activities] = await Promise.all([
      api<LessonReport | LessonReport[]>(path, options),
      api<ReportOptions>('lesson-reports/options/?include=practice', options),
    ])
    return { data: { reports, options: activities } }
  } catch (error) {
    return { error }
  }
}

export function TeacherPage() {
  const { data, error, retry } = useResource<LessonReportResource<LessonReport[]>>()
  const [savedCount, setSavedCount] = useState(0)
  const [saved, setSaved] = useState(false)
  return <>
    <PortalHeading title="Отчёты об уроках ПДД" />
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <div className="teacher-layout">
      <div>
        <ReportForm key={savedCount} options={data.options} onSave={() => { setSavedCount(count => count + 1); setSaved(true); retry() }} />
        <Notice key={savedCount} message="Отчёт сохранён." open={saved} onOpenChange={setSaved} />
      </div>
      <section className="panel history">
        <h2>Мои отчёты</h2>
        {data.reports.length ? <ul className="data-list">
          {data.reports.map(report => <li key={report.id}><Link to={'/pdd-teacher/' + report.id + '/'}>
            <span>
              <strong>{report.organization?.name || report.location || 'Место не указано'}</strong>
              <small>{formatDate(report.lesson_date)} · {report.participants_count} чел.</small>
              {(report.route_level || report.practice) && <small>
                {report.practice?.title ?? data.options.routes.find(route => route.id === report.route_level)?.title} · завершили {report.completed_count} чел.
              </small>}
            </span>
            <span aria-hidden="true">→</span>
          </Link></li>)}
        </ul> : <p>У вас пока нет отчётов.</p>}
      </section>
    </div>}
  </>
}

export function TeacherReportPage() {
  const { data, error, retry } = useResource<LessonReportResource<LessonReport>>()
  const navigate = useNavigate()
  return <>
    <PortalHeading title="Просмотр и исправление отчёта" />
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> :
      <ReportForm report={data.reports} options={data.options} onSave={() => navigate('/pdd-teacher/')} />}
  </>
}

function ReportForm({ report, options, onSave }: { report?: LessonReport; options: ReportOptions; onSave: () => void }) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>()
  const [activity, setActivity] = useState(report?.practice ? 'practice:' + report.practice.id
    : report?.route_level ? 'route:' + report.route_level : '')
  const [participantCount, setParticipantCount] = useState(report?.participants_count.toString() ?? '')
  const oldPractice = report?.practice
  const retiredPractice = oldPractice && !options.practice.some(item => item.id === oldPractice.id) ? oldPractice : null
  const route = activity.startsWith('route:') ? activity.slice(6) : ''
  const practice = options.practice.find(item => 'practice:' + item.id === activity)
  const activityLink = route ? '/safe-route/?level=' + encodeURIComponent(route)
    : practice ? '/practice/' + practice.slug + '/' : null

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = {
      ...Object.fromEntries(new FormData(event.currentTarget)), route_level: route,
      practice: activity.startsWith('practice:') ? Number(activity.slice(9)) : null,
    }
    setPending(true)
    setError(undefined)
    try {
      const path = report ? 'lesson-reports/' + report.id + '/' : 'lesson-reports/'
      await api<LessonReport>(path, { method: report ? 'PATCH' : 'POST', data })
      onSave()
    } catch (error) {
      setError(error)
    } finally {
      setPending(false)
    }
  }

  return <form className="panel editor" onSubmit={submit}>
    {!report && <h2>Новый отчёт</h2>}
    <div className="field-grid" data-scroll-fields="">
      <Field label="Дата урока" name="lesson_date" type="date" defaultValue={report?.lesson_date} required error={error} />
      <Field label="Количество участников" name="participants_count" type="number" min={1} max={2147483647}
        value={participantCount} onChange={event => setParticipantCount(event.target.value)} required error={error} />
      <OrganizationField value={report?.organization} error={error} />
      <Field label="Площадка или кабинет" name="location" defaultValue={report?.location}
        placeholder="Например, школа № 1, кабинет 204" maxLength={300} wide error={error} />
      <div className="field">
        <label htmlFor="lesson-activity">Что проходили на уроке</label>
        <select id="lesson-activity" value={activity} onChange={event => setActivity(event.target.value)}>
          <option value="">Урок без задания</option>
          <optgroup label="Безопасный маршрут">{options.routes.map(level =>
            <option key={level.id} value={'route:' + level.id}>{level.title}</option>)}</optgroup>
          <optgroup label="Практика ПДД">{options.practice.map(item =>
            <option key={item.id} value={'practice:' + item.id}>{item.title}</option>)}
            {retiredPractice && <option value={'practice:' + retiredPractice.id}>{retiredPractice.title} (снято)</option>}
          </optgroup>
        </select>
        <FieldErrors name="route_level" error={error} />
        <FieldErrors name="practice" error={error} />
      </div>
      {activity && <Field label="Сколько участников завершили задание" name="completed_count" type="number"
        min={0} max={participantCount || undefined} defaultValue={report?.completed_count ?? ''} required error={error} />}
      {activityLink && <Link className="text-link" to={activityLink}
        target="_blank" rel="noopener">Открыть задание в новой вкладке ↗</Link>}
    </div>
    <Feedback error={error} />
    <div className="actions" data-scroll-reveal="quiet">
      <button className="button" disabled={pending}>Сохранить отчёт</button>
      {report && <ButtonLink light to="/pdd-teacher/">К отчётам</ButtonLink>}
    </div>
  </form>
}
