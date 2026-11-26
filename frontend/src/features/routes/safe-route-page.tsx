import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import * as m from 'motion/react-m'
import { api, ApiError, csrfToken } from '../../shared/api'
import { Link, useSharedArt } from '../../shared/navigation'
import { RouteStreet, walkTime } from './route-street'
import type { RouteScene } from './route-street'
import { useResource, useSession } from '../../shared/state'
import { Feedback, Loading, LoadError, PortalHeading } from '../../shared/ui'
import { FeedbackMotion, livelySpring, sceneEase, spring, useCelebrate } from '../../shared/motion/motion-ui'
import { SelectField } from '../../shared/motion/motion-controls'
import { useMotionSettings } from '../../shared/motion/motion-settings'
import { Mascot } from '../../shared/mascot'
import { JourneyTrail } from '../home/journey-trail'
import './safe-route.css'

type Point = { id: string; label: string; x: number; y: number }
type Route = {
  id: string; level: string; revision: number; current: string
  points: Point[]; edges: [string, string][]; path: string[]
  scene: RouteScene; choices: { id: string; label: string }[]
  feedback: { accepted: boolean; text: string; rule: string; url: string } | null
  required_rule: string; completed: boolean; score: number; total: number
  solved: number; mistakes: number; rules_opened: number; ranked_version: boolean
}
type RouteResponse = {
  levels: { id: string; title: string; description: string }[]
  route: Route | null; guest_route: Route | null; older_version: boolean
}

function RouteMap({ route, movingTo, paused }: { route: Route; movingTo: string | null; paused: boolean }) {
  const [expanded, setExpanded] = useState(() => matchMedia('(min-width: 761px)').matches)
  const points = new Map(route.points.map(point => [point.id, point]))
  const marker = points.get(movingTo || route.current)!
  const current = points.get(route.current)!
  return <details className="route-map" open={expanded} onToggle={event => setExpanded(event.currentTarget.open)}>
    <summary>Карта района</summary>
    <div className="district" aria-hidden="true">
      {route.points.filter(point => point.id === 'home' || point.id === 'school').map(point =>
        <span key={point.id} className="district-building" style={{ left: point.x + '%', top: point.y + '%' }} />)}
      <svg className="district-lines" viewBox="0 0 100 100" preserveAspectRatio="none">
        {route.edges.map(([first, second]) => {
          const start = points.get(first)!
          const end = points.get(second)!
          return <line key={first + second} className="district-edge" x1={start.x} y1={start.y} x2={end.x} y2={end.y} />
        })}
        <polyline className="district-walked" points={route.path.map(id => points.get(id)!).map(point => `${point.x},${point.y}`).join(' ')} />
        {movingTo && <m.line key={current.id + movingTo} className="district-walked district-drawing"
          x1={current.x} y1={current.y} x2={marker.x} y2={marker.y} initial={paused ? false : { pathLength: 0 }}
          animate={{ pathLength: 1 }} transition={{ duration: paused ? 0 : walkTime / 1000, ease: sceneEase }} />}
      </svg>
      {route.points.map(point => <span key={point.id}
        className={'district-point' + (route.path.includes(point.id) ? ' visited' : '')}
        style={{ left: point.x + '%', top: point.y + '%' }}>
        {(point.id === 'home' || point.id === 'school') && <span className="district-label">{point.label}</span>}
      </span>)}
      <span className={'district-player' + (movingTo ? ' walking' : '')} key={paused ? route.current : 'player'}
        style={{ left: marker.x + '%', top: marker.y + '%' }}><i />
        {!paused && !movingTo && <m.span key={route.current} className="district-arrival" initial={{ scale: .55, opacity: .9 }}
          animate={{ scale: 2.15, opacity: 0 }} transition={{ duration: .56, ease: sceneEase }} />}
      </span>
    </div>
    <p className="route-trail">Путь {route.path.map(id => points.get(id)?.label).join(' → ')}</p>
  </details>
}

export function SafeRoutePage() {
  const { data, error, retry } = useResource<RouteResponse>()
  const [params] = useSearchParams()
  return <>
    <PortalHeading title="Безопасный маршрут">Дойди от дома до школы. На каждом участке выбери, как поступить.</PortalHeading>
    {error ? <LoadError error={error} retry={retry} /> : data ? <RouteGame initial={data} requestedLevel={params.get('level')} /> : <Loading />}
  </>
}

function RouteGame({ initial, requestedLevel }: { initial: RouteResponse; requestedLevel: string | null }) {
  const { user } = useSession()
  const { enabled } = useMotionSettings()
  const trailStyle = useSharedArt('/', 'route-trail')
  const celebrate = useCelebrate()
  const [data, setData] = useState(initial)
  const [level, setLevel] = useState(
    initial.levels.find(option => option.id === requestedLevel)?.id ?? initial.route?.level ?? initial.levels[0].id,
  )
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>()
  const [openingRule, setOpeningRule] = useState(false)
  const [movingTo, setMovingTo] = useState<string | null>(null)
  const [scenePaused, setScenePaused] = useState(false)
  const [hint, setHint] = useState(false)
  const [hintRequest, setHintRequest] = useState(0)
  const board = useRef<HTMLDivElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const review = useRef<HTMLButtonElement>(null)
  const answers = useRef<HTMLDivElement>(null)
  const nextFocus = useRef<'heading' | 'review' | 'answer' | null>(null)
  const movement = useRef<number | undefined>(undefined)
  const route = data.route
  const paused = scenePaused || !enabled

  useEffect(() => () => window.clearTimeout(movement.current), [])

  useEffect(() => {
    if (nextFocus.current === 'heading') heading.current?.focus()
    if (nextFocus.current === 'review') review.current?.focus()
    if (nextFocus.current === 'answer') answers.current?.querySelector('button')?.focus({ preventScroll: true })
    nextFocus.current = null
  }, [route?.id, route?.current, route?.required_rule, route?.revision])

  useEffect(() => {
    if (!openingRule || !route?.required_rule) return
    const controller = new AbortController()
    let timer = 0
    let checks = 0
    const attempt = route.id
    const revision = route.revision
    async function refreshRule() {
      try {
        const latest = await api<RouteResponse>('safe-route/', { signal: controller.signal })
        if (latest.route?.id !== attempt || latest.route.revision !== revision || !latest.route.required_rule) {
          nextFocus.current = 'answer'
          setData(latest)
          setOpeningRule(false)
          return
        }
        checks += 1
        if (checks < 10) {
          timer = window.setTimeout(refreshRule, 500)
          return
        }
        setError('Переход по ссылке пока не подтверждён. Открой пункт ещё раз.')
      } catch {
        if (controller.signal.aborted) return
        setError('Не удалось обновить маршрут. Попробуй открыть пункт снова.')
      }
      setOpeningRule(false)
    }
    timer = window.setTimeout(refreshRule, 300)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [openingRule, route?.id, route?.required_rule, route?.revision])

  async function play(action: Record<string, string | number>) {
    setError(undefined)
    setPending(true)
    try {
      const updated = await api<RouteResponse>('safe-route/', { method: 'POST', data: action })
      const next = updated.route
      if (action.action === 'move' && next && next.current !== route?.current && !paused) {
        if (board.current && board.current.getBoundingClientRect().bottom < 120) {
          board.current.scrollIntoView({ block: 'start' })
        }
        setMovingTo(next.current)
        await new Promise<void>(resolve => { movement.current = window.setTimeout(resolve, walkTime) })
        setMovingTo(null)
      }
      if (next?.required_rule && next.revision !== route?.revision) nextFocus.current = 'review'
      else if (next?.id !== route?.id || next?.current !== route?.current) nextFocus.current = 'heading'
      if (next?.current !== route?.current || next?.id !== route?.id) setHint(false)
      setData(updated)
      if (next) setLevel(next.level)
      if (next?.completed && !route?.completed) void celebrate(heading.current)
    } catch (error) {
      setError(error)
      if (error instanceof ApiError && [403, 404, 409].includes(error.status)) {
        try { setData(await api<RouteResponse>('safe-route/')) } catch { /* The current game can still be retried. */ }
      }
    } finally {
      setPending(false)
    }
  }

  return <div className="safe-route">
    <div className="route-controls">
      <form onSubmit={event => { event.preventDefault(); void play({ action: 'start', level }) }}>
        <SelectField label="Уровень" value={level} onChange={setLevel} disabled={pending}
          options={data.levels.map(option => ({ value: option.id, label: option.title }))} />
        <button type="submit" className="button" disabled={pending}>
          {route ? 'Начать новый маршрут' : 'Начать маршрут'} <span aria-hidden="true">↻</span>
        </button>
        {user && <Link className="text-link route-rating" to="/rating/">Таблица рейтинга →</Link>}
      </form>
      <p>{data.levels.find(option => option.id === level)?.description}</p>
      {data.older_version && <p role="status">Сохранённый район относится к старой версии игры. Создай новый маршрут.</p>}
      {data.guest_route && <button type="button" className="button button-light" disabled={pending}
        onClick={() => void play({ action: 'attach', id: data.guest_route!.id })}>
        {route ? 'Заменить текущий маршрут гостевым' : 'Сохранить гостевой маршрут в кабинете'}
      </button>}
      <div className="route-links">
        {!user && route && <p><Link className="text-link" to="/login/" state={{ next: '/safe-route/' }}>Войди</Link>, чтобы сохранить маршрут в кабинете.</p>}
      </div>
    </div>
    {typeof error === 'string' ? <p className="feedback" role="alert">{error}</p> : <Feedback error={error} />}
    {!route && <JourneyTrail />}
    {route && <div className="route-game">
      <div className="panel route-board" ref={board}>
        <div className="route-board-title">
          <strong>Улица</strong>
          <button className="button button-light" type="button" disabled={pending || !enabled}
            onClick={() => setScenePaused(value => !value)}>{paused ? 'Движение выключено' : 'Пауза'} <span aria-hidden="true">{paused ? '▷' : 'Ⅱ'}</span></button>
        </div>
        <RouteStreet scene={route.scene} destination={movingTo} paused={paused} />
        <div className="route-guide">
          <Mascot mood={route.completed ? 'success' : route.required_rule ? 'retry' : hint ? 'hint' : 'idle'}
            reaction={route.revision + hintRequest} />
          <div>
            <strong>Штрих</strong>
            <p>{route.completed ? 'Ура, мы дошли до школы!' : route.required_rule ? 'Давай посмотрим правило и попробуем снова.'
              : 'Осмотрись. Я рядом, если нужна подсказка.'}</p>
            {!route.completed && !route.required_rule && <button className="text-link" type="button" aria-expanded={hint}
              onClick={() => { setHint(value => !value); setHintRequest(value => value + 1) }}>
              {hint ? 'Скрыть подсказку' : 'Попросить подсказку'}
            </button>}
            {hint && !route.required_rule && !route.completed && <m.p className="route-hint" role="status"
              initial={enabled ? { x: -19, scale: .92, opacity: .15 } : false}
              animate={{ x: 0, scale: 1, opacity: 1 }} transition={enabled ? livelySpring : { duration: 0 }}>
              Сначала осмотри улицу. Проверь сигналы, разметку и то, что может закрывать обзор.
            </m.p>}
          </div>
        </div>
      </div>
      <section className="panel route-stage" aria-labelledby="route-stage-heading">
        <div className="route-totals" aria-live="polite">
          <span className="tag">{data.levels.find(option => option.id === route.level)?.title}</span>
          <strong className={route.score < 0 ? 'negative' : ''}>{route.score} из {route.total} баллов</strong>
        </div>
        <div className="route-progress">
          <p>{route.completed ? 'Все ситуации пройдены' : `Ситуация ${Math.min(route.solved + 1, route.total)} из ${route.total}`}</p>
          <div className="route-progress-steps" aria-hidden="true">
            {Array.from({ length: route.total }, (_, index) => <m.span key={index} data-solved={index < route.solved} initial={false}
              animate={enabled && index === route.solved - 1 ? { scale: [1, 1.27, 1] } : { scale: 1 }}
              transition={{ duration: enabled ? .52 : 0 }} />)}
          </div>
        </div>
        <h2 id="route-stage-heading" ref={heading} tabIndex={-1}>{route.scene.label}</h2>
        <p>{route.scene.text}</p>
        {route.required_rule ? <FeedbackMotion className="route-review" success={false} attempt={route.revision}>
          <p role="status"><strong>−1 балл.</strong> {route.feedback?.text}</p>
          <p>Открой пункт ПДД в новой вкладке. Затем вернись и исправь ответ.</p>
          <form method="post" action="/api/safe-route/" target="_blank" rel="noopener"
            onSubmit={() => { setError(undefined); setOpeningRule(true) }}>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
            <input type="hidden" name="action" value="open-rule" />
            <input type="hidden" name="id" value={route.id} />
            <input type="hidden" name="revision" value={route.revision} />
            <button ref={review} className="button" type="submit" aria-describedby="review-required">{route.required_rule} ↗</button>
            <small id="review-required">{openingRule ? 'Проверяем переход…' : 'До открытия правила ответы закрыты.'}</small>
          </form>
        </FeedbackMotion> : route.feedback && <p className={route.feedback.accepted ? 'route-correct' : 'route-review'} role="status">
          <strong>{route.feedback.accepted ? 'Верно. ' : 'Пункт открыт. Выбери безопасный вариант. '}</strong>
          {route.feedback.text}{route.feedback.url && <> <a href={route.feedback.url} target="_blank" rel="noreferrer">{route.feedback.rule} ↗</a></>}
        </p>}
        {route.completed ? <>
          <p>Ошибок: {route.mistakes}. Открыто правил: {route.rules_opened}.</p>
          {!route.ranked_version && <p>Это результат предыдущей версии. Для рейтинга пройди новый маршрут.</p>}
          <a className="button" href={'/api/safe-route/' + route.id + '/memento/'}>Скачать памятку PDF</a>
        </> : <div className="route-options" ref={answers}>
          {route.choices.map(choice => <m.button key={choice.id} type="button" className="button button-light" disabled={pending}
            whileTap={enabled && !pending ? { scale: .985 } : undefined} transition={spring}
            onClick={() => void play({ action: 'move', id: route.id, revision: route.revision, choice: choice.id })}>
            {choice.label}<span aria-hidden="true">→</span>
          </m.button>)}
        </div>}
      </section>
      <div className="panel route-overview shared-art" style={trailStyle}>
        <RouteMap key={route.id} route={route} movingTo={movingTo} paused={paused} />
      </div>
    </div>}
  </div>
}
