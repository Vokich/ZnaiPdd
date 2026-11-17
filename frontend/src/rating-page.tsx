import { Form, useLocation, useSearchParams } from 'react-router-dom'
import { useState } from 'react'
import * as m from 'motion/react-m'
import { api } from './api'
import { Link } from './navigation'
import { useResource } from './state'
import { Feedback, Loading, LoadError, PortalHeading } from './ui'
import { MotionNumber, spring } from './motion-ui'
import { Notice, SelectField } from './motion-controls'
import { useMotionSettings } from './motion-settings'
import './rating.css'

type Rating = {
  entries: { place: number; name: string; organization: string | null; points: number; is_current_user: boolean }[]
  sections: { id: string; name: string }[]
  organizations: { id: number; name: string; municipality: string }[]
  municipalities: { id: string; name: string }[]
  page: number
  pages: number
  maximum: number
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
        <p className="rating-score"><strong>{data.my_points === null ? '—' : <MotionNumber value={data.my_points} />}</strong><span> / {data.maximum}</span></p>
      </section>
      <section className="panel rating-panel">
        <Form method="get" className="rating-filters" key={search} preventScrollReset>
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
        <p className="rating-explanation">{section === 'all'
          ? (data.maximum === 300 ? 'До 100 баллов за каждое направление: маршруты, тесты и практика.' : 'До 100 баллов за маршруты и до 100 за тесты.')
          : section === 'practice' ? 'Баллы равны проценту выполненных заданий из открытой практики.'
          : section.startsWith('route-') ? 'Засчитывается лучший завершённый маршрут этого уровня.'
          : section === 'routes' ? 'Лучшие результаты трёх уровней в сумме дают до 100 баллов.'
          : 'Засчитывается наибольший процент правильных ответов.'}</p>
      </section>
      <section className="panel rating-panel" aria-label="Таблица рейтинга">
        <div className="rating-table-title"><h2>Участники</h2><Link className="text-link" to="/profile/#competition-title">Режим участия →</Link></div>
        {data.entries.length ? <table className="rating-table">
          <thead><tr><th scope="col">Место</th><th scope="col">Участник</th><th scope="col">Организация</th><th scope="col">Баллы</th></tr></thead>
          <tbody>
            {data.entries.map((entry, index) => <tr key={index} className={entry.is_current_user ? 'rating-current' : undefined}>
              <td>{entry.place}</td>
              <th scope="row">{entry.name}{entry.is_current_user && <small>Ваш результат</small>}</th>
              <td>{entry.organization || '—'}</td>
              <td><strong>{entry.points}</strong><small>из {data.maximum}</small></td>
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
