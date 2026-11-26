import { useState } from 'react'
import type { FormEvent } from 'react'
import type { LoaderFunctionArgs } from 'react-router-dom'
import { Link, useNavigate } from '../../shared/navigation'
import { api } from '../../shared/api'
import type { LessonReport, Organization } from '../../shared/api'
import { useResource } from '../../shared/state'
import { ButtonLink, Feedback, Field, FieldErrors, formatDate, Loading, LoadError, OrganizationField, PortalHeading } from '../../shared/ui'
import { Notice } from '../../shared/motion/motion-controls'

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
        <Notice key={'notice-' + savedCount} message="Отчёт сохранён." open={saved} onOpenChange={setSaved} />
      </div>
      <section className="panel history">
        <h2>Мои отчёты</h2>
        {data.reports.length ? <ul className="data-list">
          {data.reports.map(report => <li key={report.id}><Link to={'/pdd-teacher/' + report.id + '/'}>
            <span>
              <strong>{report.organization?.name || report.location || 'Место не указано'}</strong>
              <small>{formatDate(report.lesson_date)} · {report.participants_count} чел.</small>
              {report.classroom && <small>{report.classroom.title} · {report.classroom.lesson ? 'Разобрали вместе' : 'Тест по QR · отправлено ' + report.classroom.submitted}</small>}
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

type ClassroomReport = NonNullable<LessonReport['classroom']> & { date: string; organization: Organization | null }

export function ReportForm({ report, classroom, options, onSave }: {
  report?: LessonReport; classroom?: ClassroomReport; options: ReportOptions; onSave: (saved: LessonReport) => void
}) {
  const session = report?.classroom || classroom
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
      ...(classroom && { classroom: classroom.id }),
    }
    setPending(true)
    setError(undefined)
    try {
      const path = report ? 'lesson-reports/' + report.id + '/' : 'lesson-reports/'
      onSave(await api<LessonReport>(path, { method: report ? 'PATCH' : 'POST', data }))
    } catch (error) {
      setError(error)
    } finally {
      setPending(false)
    }
  }

  return <form className="panel editor" onSubmit={submit}>
    {!report && <h2>Новый отчёт</h2>}
    {session && <><h2>{session.title}</h2><p>{session.lesson ? 'Разобрали вместе' : 'Тест по QR · отправлены попытки — ' + session.submitted}</p></>}
    <div className="field-grid" data-scroll-fields="">
      <Field label="Дата урока" name="lesson_date" type="date" defaultValue={report?.lesson_date ?? classroom?.date} required error={error} />
      <Field label={session ? 'Присутствовали' : 'Количество участников'} name="participants_count" type="number" min={1} max={2147483647}
        value={participantCount} onChange={event => setParticipantCount(event.target.value)} required error={error} />
      <OrganizationField value={report?.organization ?? classroom?.organization} error={error} />
      <Field label="Площадка или кабинет" name="location" defaultValue={report?.location}
        placeholder="Например, школа № 1, кабинет 204" maxLength={300} wide error={error} />
      {!session && <div className="field">
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
      </div>}
      {(activity || session && !session.lesson) && <Field label={session ? 'Завершили по подсчёту педагога (необязательно)' : 'Сколько участников завершили задание'} name="completed_count" type="number"
        min={0} max={participantCount || undefined} defaultValue={report?.completed_count ?? ''} required={!!activity} error={error} />}
      {session?.submitted != null && participantCount && session.submitted > Number(participantCount) &&
        <p role="status">Попыток больше, чем присутствовавших. Проверьте количество участников перед сохранением.</p>}
      {activityLink && <Link className="text-link" to={activityLink}
        target="_blank" rel="noopener">Открыть задание в новой вкладке ↗</Link>}
    </div>
    <Feedback error={error} />
    <div className="actions" data-scroll-reveal="quiet">
      <button className="button" disabled={pending}>Сохранить отчёт</button>
      {report && <ButtonLink light to="/pdd-teacher/">К отчётам</ButtonLink>}
      {session && <ButtonLink light to={'/classroom/runs/' + session.id + '/'}>К занятию</ButtonLink>}
    </div>
  </form>
}
