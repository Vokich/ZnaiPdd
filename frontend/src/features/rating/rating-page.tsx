import { Form, useLocation, useSearchParams } from 'react-router-dom'
import { useState } from 'react'
import * as m from 'motion/react-m'
import { api } from '../../shared/api'
import { Link } from '../../shared/navigation'
import { useResource } from '../../shared/state'
import { Feedback, Loading, LoadError, PortalHeading } from '../../shared/ui'
import { MotionNumber, spring } from '../../shared/motion/motion-ui'
import { Notice, SelectField } from '../../shared/motion/motion-controls'
import { useMotionSettings } from '../../shared/motion/motion-settings'
import './rating.css'

type Rating = {
  entries: { place: number; name: string; organization: string | null; points: number; is_current_user?: boolean; members?: number; municipality?: string }[]
  sections: { id: string; name: string }[]
  organizations: { id: number; name: string; municipality: string }[]
  municipalities: { id: string; name: string }[]
  page: number
  pages: number
  maximum: null
  my_points: number | null
}

export function CompetitionMode({ initialEnabled }: { initialEnabled: boolean }) {
  const [enabled, setEnabled] = useState(initialEnabled)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>()
  const [changed, setChanged] = useState(false)
  const { enabled: animate } = useMotionSettings()

  async function selectMode(next: boolean) {
    if (next === enabled || pending) return
    setPending(true)
    setError(undefined)
    setEnabled(next)
    setChanged(false)
    try {
      const result = await api<{ enabled: boolean }>('competition/', { method: 'PATCH', data: { enabled: next } })
      setEnabled(result.enabled)
      setChanged(true)
    } catch (error) {
      setEnabled(enabled)
      setError(error)
    } finally {
      setPending(false)
    }
  }

  return <section className="panel competition-mode" aria-labelledby="competition-title">
    <h2 id="competition-title">Твой результат в рейтинге</h2>
    <p id="competition-description">В общем зачёте вошедшие участники видят твоё ФИО, организацию и баллы. В режиме «Только мне» твой результат скрыт из таблицы.</p>
    <fieldset disabled={pending} aria-describedby="competition-description">
      <legend className="competition-legend">Режим участия</legend>
      {[{ value: true, label: 'В общем зачёте' }, { value: false, label: 'Только мне' }].map(mode =>
        <label key={mode.label}>
          <input type="radio" name="competition" checked={enabled === mode.value} onChange={() => void selectMode(mode.value)} />
          {mode.label}
          {enabled === mode.value && <m.span className="tab-highlight" layoutId="competition-mode"
            transition={animate ? spring : { duration: 0 }} />}
        </label>)}
    </fieldset>
    {pending && <p role="status">Сохраняем режим…</p>}
    <Feedback error={error} />
    <Notice message={enabled ? 'Результат виден в рейтинге.' : 'Результат скрыт из таблицы.'}
      open={changed} onOpenChange={setChanged} />
  </section>
}

export function RatingPage() {
  const { data, error, retry } = useResource<Rating>()
  const { search } = useLocation()
  const [filters] = useSearchParams()
  const section = filters.get('section') || 'all'
  const organization = filters.get('organization') || ''
  const municipality = filters.get('municipality') || ''
  const teams = filters.get('view') === 'organizations'

  function pageLink(page: number) {
    const next = new URLSearchParams(filters)
    next.set('page', String(page))
    return '/rating/?' + next.toString()
  }

  return <>
    <PortalHeading title="Рейтинг">Общий зачёт и результаты по направлениям.</PortalHeading>
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <div className="rating">
      <section className="panel rating-hero">
        <div>
          <p className="rating-kicker"><span aria-hidden="true">✦</span> Твой результат</p>
          <h2>{data.sections.find(item => item.id === section)?.name ?? 'Общий зачёт'}</h2>
          <p>{data.my_points === null ? 'Баллы появятся после первого результата.' : 'Твои баллы в выбранном направлении.'}</p>
        </div>
        <p className="rating-score"><strong>{data.my_points === null ? '—' : <MotionNumber value={data.my_points} />}</strong><span> баллов</span></p>
      </section>
      <section className="panel rating-panel">
        <Form method="get" className="rating-filters" key={search} preventScrollReset>
          <SelectField label="Зачёт" name="view" defaultValue={teams ? 'organizations' : 'people'}
            options={[{ value: 'people', label: 'Участники' }, { value: 'organizations', label: 'Организации' }]} />
          <SelectField label="Направление" name="section" defaultValue={section}
            options={data.sections.map(item => ({ value: item.id, label: item.name }))} />
          <SelectField label="Организация" name="organization" defaultValue={organization}
            options={[{ value: '', label: 'Все организации' }, { value: 'none', label: 'Без организации' },
              ...data.organizations.map(item => ({ value: String(item.id), label: `${item.name} (${item.municipality})` }))]} />
          <SelectField label="Муниципалитет" name="municipality" defaultValue={municipality}
            options={[{ value: '', label: 'Все муниципалитеты' },
              ...data.municipalities.map(item => ({ value: item.id, label: item.name }))]} />
          <button className="button">Показать</button>
        </Form>
        <p className="rating-explanation">За каждый верный ответ в тесте платформы и каждый изученный знак — 1 балл.
          Маршрут приносит баллы за пройденные ситуации с учётом ошибок. Практика даёт 3 балла за начальное задание
          и 5 за продвинутое. В зачёт идёт лучший результат по каждому заданию платформы.</p>
        {teams && <p>Баллы организации складываются из результатов участников общего зачёта, чью принадлежность подтвердил администратор.</p>}
      </section>
      <section className="panel rating-panel" aria-label="Таблица рейтинга">
        <div className="rating-table-title"><h2>{teams ? 'Организации' : 'Участники'}</h2><Link className="text-link" to="/profile/#competition-title">Режим участия →</Link></div>
        {data.entries.length ? <table className="rating-table">
          <thead><tr><th scope="col">Место</th><th scope="col">{teams ? 'Организация' : 'Участник'}</th><th scope="col">{teams ? 'Участников' : 'Организация'}</th><th scope="col">Баллы</th></tr></thead>
          <tbody>
            {data.entries.map((entry, index) => <tr key={index} className={entry.is_current_user ? 'rating-current' : undefined}>
              <td>{entry.place}</td>
              <th scope="row">{entry.name}{teams && <small>{entry.municipality}</small>}{entry.is_current_user && <small>Ваш результат</small>}</th>
              <td>{teams ? entry.members : entry.organization || '—'}</td>
              <td><strong>{entry.points}</strong></td>
            </tr>)}
          </tbody>
        </table> : <p className="rating-empty">По этим условиям пока нет результатов.</p>}
        {data.pages > 1 && <nav className="rating-pages" aria-label="Страницы рейтинга">
          {data.page > 1 && <Link className="button button-light" to={pageLink(data.page - 1)} preventScrollReset>Назад</Link>}
          <span>{data.page} / {data.pages}</span>
          {data.page < data.pages && <Link className="button button-light" to={pageLink(data.page + 1)} preventScrollReset>Дальше</Link>}
        </nav>}
      </section>
    </div>}
  </>
}
