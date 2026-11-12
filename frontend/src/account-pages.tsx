import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from './navigation'
import { api } from './api'
import type { LessonReport, Profile, ProfileResponse } from './api'
import { useResource, useSession } from './state'
import { ButtonLink, Character, Feedback, Field, FieldErrors, formatDate, Loading, LoadError, Municipality, PortalHeading } from './ui'
import { quizInfo } from './quiz-pages'

export function AccountPage() {
  const { data, error, retry } = useResource<ProfileResponse>()
  if (error) return <LoadError error={error} retry={retry} />
  if (!data) return <Loading />
  const { profile, results, reports_count } = data
  return <>
    <PortalHeading title={`Привет, ${profile.name}!`}>Продолжайте свой маршрут по правилам дорожного движения.</PortalHeading>
    <div className="panel profile-summary">
      <div>
        <span className="tag">{profile.role === 'teacher' ? 'Педагог' : 'Школьник'}</span>
        <h2>{[profile.surname1, profile.name, profile.surname2].filter(Boolean).join(' ')}</h2>
        <dl className="profile-details">
          <div><dt>Учебное заведение</dt><dd>{profile.school}</dd></div>
          <div><dt>Муниципалитет</dt><dd>{profile.region}</dd></div>
          <div><dt>Дата рождения</dt><dd>{formatDate(profile.birth_date)}</dd></div>
          <div><dt>Почта</dt><dd>{profile.email || '—'}</dd></div>
          {profile.role === 'teacher' && <><div><dt>Должность</dt><dd>{profile.position || '—'}</dd></div><div><dt>Отчётов</dt><dd>{reports_count}</dd></div></>}
        </dl>
        <div className="actions"><ButtonLink to="/profile/edit/">Редактировать</ButtonLink><ButtonLink to="/profile/password/" light>Сменить пароль</ButtonLink></div>
      </div>
      <Character role={profile.role === 'teacher' ? 'teacher' : 'student'} />
    </div>
    <div className="portal-grid account-links">
      {profile.role === 'child' && <Link className="panel route-card" data-scroll-reveal="card" to="/age/"><h2>Тесты по ПДД</h2><p>Выберите тест для своей возрастной группы.</p><span aria-hidden="true">→</span></Link>}
      {profile.role === 'teacher' && <Link className="panel route-card" data-scroll-reveal="card" to="/pdd-teacher/"><h2>Отчёты об уроках</h2><p>Добавьте отчёт и посмотрите историю занятий.</p><span aria-hidden="true">→</span></Link>}
      <Link className="panel route-card" data-scroll-reveal="card" to="/signs/"><h2>Знаки ПДД</h2><p>Открывайте знаки, отвечая на вопросы.</p><span aria-hidden="true">→</span></Link>
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
      const { id, username, name, role } = updated.profile
      setUser({ id, username, name, role })
      navigate('/profile/')
    } catch (error) { setError(error) }
    finally { setPending(false) }
  }
  return <>
    <PortalHeading title="Редактирование профиля" />
    <form className="panel editor" onSubmit={submit}>
      <div className="field-grid" data-scroll-fields="">
        <Field label="Логин" name="username" defaultValue={profile.username} autoComplete="username" maxLength={150} required error={error} />
        <Field label="Почта" name="email" type="email" defaultValue={profile.email} autoComplete="email" maxLength={254} required error={error} />
        <Field label="Фамилия" name="surname1" defaultValue={profile.surname1} autoComplete="family-name" maxLength={50} required error={error} />
        <Field label="Имя" name="name" defaultValue={profile.name} autoComplete="given-name" maxLength={50} required error={error} />
        <Field label="Отчество" name="surname2" defaultValue={profile.surname2} autoComplete="additional-name" maxLength={50} error={error} />
        <Field label="Дата рождения" name="birth_date" type="date" defaultValue={profile.birth_date} autoComplete="bday" required error={error} />
        <Field label="Учебное заведение" name="school" defaultValue={profile.school} maxLength={100} required error={error} />
        <Municipality value={profile.region} error={error} />
        {profile.role === 'teacher' && <Field label="Должность" name="position" defaultValue={profile.position} maxLength={100} required error={error} />}
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
      <Field label="Новый пароль" name="new_password" type="password" autoComplete="new-password" minLength={6} required error={error} />
      <Field label="Повторите новый пароль" name="confirm_password" type="password" autoComplete="new-password" minLength={6} required error={error} />
      <Feedback error={error} />
      <div className="actions" data-scroll-reveal="quiet"><button className="button" disabled={pending}>Сменить пароль →</button><ButtonLink to="/profile/" light>Отмена</ButtonLink></div>
    </form>
  </>
}

export function TeacherPage() {
  const { data: reports, error: loadError, retry } = useResource<LessonReport[]>()
  const [pending, setPending] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<unknown>()
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = Object.fromEntries(new FormData(form))
    setPending(true)
    setSaved(false)
    setError(undefined)
    try {
      await api('lesson-reports/', { method: 'POST', data })
      form.reset()
      setSaved(true)
      retry()
    } catch (error) { setError(error) }
    finally { setPending(false) }
  }
  return <>
    <PortalHeading title="Отчёты об уроках ПДД">Запишите, когда и где прошёл урок, и добавьте ссылку на фотоотчёт.</PortalHeading>
    <div className="teacher-layout">
      <form className="panel editor" onSubmit={submit}>
        <h2>Новый отчёт</h2>
        <div className="field-grid" data-scroll-fields="">
          <Field label="Дата урока" name="lesson_date" type="date" required error={error} />
          <Field label="Количество детей" name="children_count" type="number" min="1" required error={error} />
          <Field label="Место проведения" name="location" placeholder="Название школы и кабинет" maxLength={300} required wide error={error} />
          <label className="field wide">Список детей
            <textarea name="children_list" placeholder="Укажите имена через запятую или с новой строки" rows={4} required />
            <FieldErrors error={error} name="children_list" />
          </label>
          <Field label="Ссылка на фотоотчёт" name="photo_link" type="url" placeholder="https://…" maxLength={200} wide error={error} />
        </div>
        <Feedback error={error} />
        {saved && <p className="success" role="status">Отчёт сохранён.</p>}
        <div className="actions" data-scroll-reveal="quiet"><button className="button" disabled={pending}>Сохранить отчёт →</button></div>
      </form>
      <section className="panel history">
        <h2 data-scroll-reveal="quiet">Мои отчёты</h2>
        {loadError ? <LoadError error={loadError} retry={retry} /> : !reports ? <Loading /> : reports.length ? <ul className="data-list">
          {reports.map(report => <li key={report.id} data-scroll-reveal="quiet"><div className="report-row">
            <span><strong>{report.location}</strong><small>{formatDate(report.lesson_date)} · {report.children_count} чел.</small></span>
            {/^https?:\/\//i.test(report.photo_link) && <a href={report.photo_link} target="_blank" rel="noreferrer">Фото ↗</a>}
          </div></li>)}
        </ul> : <p>Здесь появятся отчёты о ваших уроках.</p>}
      </section>
    </div>
  </>
}
