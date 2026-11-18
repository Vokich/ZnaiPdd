import { useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Form, useParams, useSearchParams } from 'react-router-dom'
import * as Tabs from '@radix-ui/react-tabs'
import { AnimatePresence, useDragControls, useMotionValue, useSpring } from 'motion/react'
import * as m from 'motion/react-m'
import { api } from './api'
import type { GalleryImage } from './api'
import { Link, useSharedArt } from './navigation'
import { useResource, useSession } from './state'
import { ButtonLink, Feedback, formatDate, Loading, LoadError, MediaGallery, PortalHeading, PracticeIcon } from './ui'
import { FeedbackMotion, livelySpring, Reveal, spring, useCelebrate } from './motion-ui'
import { SelectField } from './motion-controls'
import { useMotionSettings } from './motion-settings'
import { Mascot } from './mascot'
import './learning.css'

export type ExerciseCard = { slug: string; title: string; topic: string; difficulty: string; kind: string; kind_id: string }
export type LinkedSign = { slug: string; name: string; number: string; image: string | null }
type Choice = { id: number; text: string }
type Option = { id: string; label: string }
type Catalog = { items: ExerciseCard[]; topics: Option[]; difficulties: Option[] }
type BaseExercise = {
  title: string; version: number; prompt: string; preview: boolean; completed: boolean; sign: LinkedSign | null; images?: GalleryImage[]
}
type Exercise = BaseExercise & (
  { kind: 'order'; cards: Choice[] } |
  { kind: 'plates'; meanings: Choice[]; conditions: Choice[]; plates: (LinkedSign | null)[] }
)
type Review = { correct: boolean; explanation: string; source_url: string; sign: LinkedSign | null }
type History = { id: number; title: string; slug: string | null; version: number; completed_at: string }[]

const featured = [
  { slug: 'cross-on-green', title: 'Переход на зелёный', text: 'Расставь четыре действия перед выходом на дорогу.' },
  { slug: 'stop-calendar', title: 'Остановка по дням недели', text: 'Посмотри, как табличка меняет действие знака.' },
]

export function PracticePage() {
  const { data, error, retry } = useResource<Catalog>()
  const [query] = useSearchParams()
  const { user } = useSession()
  return <>
    <PortalHeading title="Практика ПДД">Выбери ситуацию, которую хочешь разобрать.</PortalHeading>
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <>
      <div className="practice-tools">
        <details className="practice-filters" open={Boolean(query.get('topic') || query.get('difficulty')) || undefined}>
          <summary>Фильтры</summary>
          <Form key={query.toString()} className="learning-filters" method="get" preventScrollReset>
            {[{ name: 'topic', label: 'Тема', items: data.topics },
              { name: 'difficulty', label: 'Сложность', items: data.difficulties }].map(filter =>
              <SelectField key={filter.name} label={filter.label} name={filter.name} defaultValue={query.get(filter.name) ?? ''}
                options={[{ value: '', label: 'Все' }, ...filter.items.map(item => ({ value: item.id, label: item.label }))]} />)}
            <button className="button">Показать</button>
          </Form>
        </details>
        {user && <Link className="text-link" to="/practice/history/">Мои прохождения →</Link>}
      </div>
      {data.items.length ? <div className="practice-grid">
        {[...featured.flatMap(item => data.items.filter(card => card.slug === item.slug)),
          ...data.items.filter(item => !featured.some(card => card.slug === item.slug))].map(item =>
          <PracticeCatalogCard key={item.slug} item={item} />)}
      </div> : <p className="panel">По этим условиям пока нет заданий.</p>}
    </>}
  </>
}

function PracticeCatalogCard({ item }: { item: ExerciseCard }) {
  const path = '/practice/' + item.slug + '/'
  const shared = useSharedArt(path, 'exercise', item.slug)
  const { enabled } = useMotionSettings()
  return <Reveal>
    <m.article className={`panel practice-card shared-art practice-${item.kind_id}`} style={shared}
      initial={false} animate="rest" whileHover={enabled ? 'hover' : undefined}
      variants={{ rest: { y: 0 }, hover: { y: -6 } }} transition={spring}>
      <m.div variants={{ rest: { scale: 1, rotate: 0 }, hover: { scale: 1.19, rotate: -10 } }} transition={livelySpring}>
        <PracticeIcon kind={item.kind_id} />
      </m.div>
      <h2>{item.title}</h2>
      <p>{featured.find(card => card.slug === item.slug)?.text ?? `${item.topic} · ${item.difficulty}`}</p>
      <ButtonLink to={path} viewTransition>Начать задание <span aria-hidden="true">→</span></ButtonLink>
    </m.article>
  </Reveal>
}

export function PracticeExercisePage() {
  const { slug } = useParams()
  const { data, error, retry } = useResource<Exercise>()
  return <>
    <Link to="/practice/" className="text-link" viewTransition>← К практике</Link>
    {error ? <LoadError error={error} retry={retry} /> : !data || !slug ? <Loading /> : <>
      <PortalHeading title={data.title}>{data.preview ? 'Предпросмотр версии' : data.prompt}</PortalHeading>
      <ExerciseForm key={data.version} exercise={data} slug={slug} />
    </>}
  </>
}

function ExerciseForm({ exercise, slug }: { exercise: Exercise; slug: string }) {
  const [cards, setCards] = useState(exercise.kind === 'order' ? exercise.cards : [])
  const [variant, setVariant] = useState(() => exercise.kind === 'plates' ? Math.max(0, exercise.plates.findIndex(plate => plate?.number === '8.5.2')) : 0)
  const [plateDirection, setPlateDirection] = useState(0)
  const [choices, setChoices] = useState([0, 0, 0])
  const [result, setResult] = useState<Review>()
  const [error, setError] = useState<unknown>()
  const [pending, setPending] = useState(false)
  const [status, setStatus] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [hint, setHint] = useState(false)
  const [hintRequest, setHintRequest] = useState(0)
  const [showHintReaction, setShowHintReaction] = useState(false)
  const feedback = useRef<HTMLDivElement>(null)
  const celebrate = useCelebrate()
  const { enabled } = useMotionSettings()
  const shared = useSharedArt('/practice/', 'exercise', slug)

  function move(from: number, to: number) {
    if (pending || from < 0 || to < 0 || from >= cards.length || to >= cards.length || from === to) return
    const next = cards.slice()
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    setCards(next)
    setResult(undefined)
    setStatus(`«${moved.text}» теперь на позиции ${to + 1}.`)
  }

  function reorder(next: Choice[]) {
    setCards(next)
    setResult(undefined)
  }

  function select(index: number, value: string) {
    setChoices(current => current.map((choice, position) => position === index ? Number(value) : choice))
    setResult(undefined)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (pending || exercise.preview) return
    setPending(true)
    setError(undefined)
    try {
      const answer = exercise.kind === 'order' ? cards.map(card => card.id) : choices
      const review = await api<Review>('practice/' + slug + '/', { method: 'POST', data: { version: exercise.version, answer } })
      setResult(review)
      setShowHintReaction(false)
      setAttempt(value => value + 1)
      feedback.current?.focus()
      if (review.correct) void celebrate(feedback.current)
    } catch (error) {
      setError(error)
    } finally {
      setPending(false)
    }
  }

  const mood = hint && showHintReaction ? 'hint' : result ? result.correct ? 'success' : 'retry' : 'idle'
  const plateTabs = exercise.kind === 'plates' ? exercise.plates.map((plate, index) => ({ plate, index })) : []
  if (plateTabs[1]?.plate?.number === '8.5.2') plateTabs.reverse()
  function changePlate(value: string) {
    const next = Number(value)
    if (next === variant) return
    setPlateDirection(Math.sign(plateTabs.findIndex(item => item.index === next) - plateTabs.findIndex(item => item.index === variant)))
    setVariant(next)
  }

  return <Tabs.Root value={String(variant)} onValueChange={changePlate}>
    <div className="exercise-grid">
      <aside className="exercise-aside">
        <div className="panel exercise-scene shared-art" style={shared}>
          {exercise.kind === 'order' ? <>
            <p className="eyebrow">{slug === 'cross-on-green' ? 'Пешеходный переход' : 'Дорожная ситуация'}</p>
            <h2>{slug === 'cross-on-green' ? 'До выхода на дорогу' : exercise.title}</h2>
            <div className="exercise-illustration">
              {slug === 'cross-on-green' && <img src="/art/signal.webp" alt="Красный сигнал пешеходного светофора" />}
              <Mascot mood={mood} reaction={attempt + hintRequest} />
            </div>
          </> : <>
            <h2>{exercise.sign?.name ?? 'Знак с табличками'}</h2>
            <Tabs.List className="practice-tabs" aria-label="Варианты табличек">
              {plateTabs.map(({ plate, index }) => <Tabs.Trigger key={index} className="practice-tab" value={String(index)}>
                {plate?.number === '8.5.2' ? 'Рабочие дни' : plate?.number === '8.5.1' ? 'Выходные и праздники' : `Табличка ${index + 1}`}
                {variant === index && <m.span className="tab-highlight" layoutId="practice-tab"
                  transition={enabled ? spring : { duration: 0 }} />}
                {choices[index + 1] > 0 && <span aria-label="ответ выбран"> ✓</span>}
              </Tabs.Trigger>)}
            </Tabs.List>
            <div className="practice-combination">
              {exercise.sign?.image && <img className="main-practice-sign" src={exercise.sign.image} alt={exercise.sign.name} />}
              {exercise.plates.map((plate, index) => <Tabs.Content key={index} value={String(index)} className="plate-holder">
                {plate && <m.figure key={variant} className="moving-plate"
                  initial={enabled && plateDirection !== 0 ? { x: 62 * plateDirection, y: -13, scale: .66, rotate: 12 * plateDirection, opacity: .18 } : false}
                  animate={{ x: 0, y: 0, scale: 1, rotate: 0, opacity: 1 }}
                  transition={enabled ? livelySpring : { duration: 0 }}>
                  {plate.image && <img src={plate.image} alt={plate.name} />}
                  <figcaption>{plate.number} · {plate.name}</figcaption>
                </m.figure>}
              </Tabs.Content>)}
            </div>
          </>}
        </div>
        <MediaGallery images={exercise.images} />
        <div className="panel exercise-hint">
          {exercise.kind === 'plates' && <Mascot mood={mood} reaction={attempt + hintRequest} />}
          <div>
            <h3>Подсказка Штриха</h3>
            <p>Если запутаешься, я помогу с первым шагом.</p>
            <button className="text-link" type="button" aria-expanded={hint} onClick={() => {
              setHint(!hint)
              setShowHintReaction(!hint)
              setHintRequest(value => value + 1)
            }}>{hint ? 'Скрыть подсказку' : 'Попросить подсказку'}</button>
            <AnimatePresence initial={false}>{hint && <m.p className="hint-copy"
              initial={enabled ? { opacity: 0, y: 5 } : false} animate={{ opacity: 1, y: 0 }}
              exit={enabled ? { opacity: 0, transition: { duration: .12 } } : undefined}>
              {exercise.kind === 'order' ? 'Начни с действия, которое можно выполнить, оставаясь в безопасном месте.'
                : 'Сначала прочитай основной знак. Затем посмотри, когда или где действует правило с каждой табличкой.'}
            </m.p>}</AnimatePresence>
          </div>
        </div>
      </aside>
      <form className="panel exercise-form" onSubmit={submit}>
        {exercise.preview && <p>{exercise.prompt}</p>}
        {exercise.completed && <p><span className="tag">Уже выполнено</span></p>}
        {exercise.kind === 'order' ? <>
          <h2>Расставь действия по порядку</h2>
          <p>Перетащи карточки или передвинь их стрелками.</p>
          <m.Reorder.Group as="ol" axis="y" values={cards} onReorder={reorder} className="order-cards">
            {cards.map((card, index) => <OrderCard key={card.id} card={card} index={index} total={cards.length}
              pending={pending} onMove={move} onDrop={() => setStatus(`«${card.text}» теперь на позиции ${index + 1}.`)} />)}
          </m.Reorder.Group>
          <span className="learning-live" role="status">{status}</span>
        </> : <>
          <h2>Что меняет табличка?</h2>
          <p>Выбери смысл знака один раз. Затем укажи условия для каждой таблички.</p>
          <AnswerChoices label="Смысл знака" items={exercise.meanings} value={choices[0]} disabled={pending} onChange={value => select(0, value)} />
          <AnswerChoices label={'Условие для таблички ' + (exercise.plates[variant]?.number ?? variant + 1)}
            items={exercise.conditions} value={choices[variant + 1]} disabled={pending} onChange={value => select(variant + 1, value)} />
        </>}
        {!exercise.preview && <button className="button" disabled={pending || (exercise.kind === 'plates' && choices.includes(0))}>
          {pending ? 'Проверяем…' : 'Проверить ответ ✓'}
        </button>}
        <Feedback error={error} />
        <div ref={feedback} tabIndex={-1} aria-live="polite">
          {result && <FeedbackMotion success={result.correct} attempt={attempt} className={`exercise-result ${result.correct ? 'success' : 'feedback'}`}>
            <Mascot mood={result.correct ? 'success' : 'retry'} reaction={attempt} />
            <div>
              <strong>{result.correct ? 'Верно. Задание выполнено.' : 'Попробуй изменить ответ.'}</strong>
              <p>{result.explanation}</p>
              <div className="learning-links">
                <a href={result.source_url} target="_blank" rel="noreferrer" className="text-link">Посмотреть пункт ПДД ↗</a>
                {result.sign && <Link to={'/signs/' + result.sign.slug + '/'} className="text-link">Карточка знака →</Link>}
              </div>
            </div>
          </FeedbackMotion>}
        </div>
      </form>
    </div>
  </Tabs.Root>
}

export function OrderCard({ card, index, total, pending, onMove, onDrop }: {
  card: Choice; index: number; total: number; pending: boolean
  onMove: (from: number, to: number) => void; onDrop: () => void
}) {
  const drag = useDragControls()
  const { enabled } = useMotionSettings()
  const lean = useMotionValue(0)
  const rotate = useSpring(lean, { stiffness: 270, damping: 19 })
  const [landings, setLandings] = useState(0)
  return <m.Reorder.Item value={card} dragListener={false} dragControls={drag} dragMomentum={false}
    style={enabled ? { rotate } : undefined}
    whileHover={enabled && !pending ? { scale: 1.035 } : undefined}
    whileDrag={enabled ? { scale: 1.09, backgroundColor: '#f0e7fb', borderColor: '#8469bc', boxShadow: '0 14px 27px #322d4d45' } : undefined}
    onDrag={(_, info) => { if (enabled) lean.set(Math.max(-5, Math.min(5, info.velocity.y / 185))) }}
    transition={enabled ? { ...spring, layout: { type: 'spring', stiffness: 365, damping: 24 } } : { duration: 0 }}
    onDragEnd={() => { lean.set(0); setLandings(count => count + 1); onDrop() }}>
    {enabled && landings > 0 && <m.span key={landings} className="order-landing" aria-hidden="true"
      initial={{ scale: .96, opacity: 1 }} animate={{ scale: 1.12, opacity: 0 }} transition={{ duration: .42 }} />}
    <span className="order-grip" aria-hidden="true" onPointerDown={event => { if (!pending) drag.start(event) }}>{index + 1}</span>
    <span className="order-text"
      onPointerDown={event => { if (!pending && event.pointerType === 'mouse') drag.start(event) }}>{card.text}</span>
    <div className="order-controls">
      <button type="button" className="button button-light" aria-label={'Выше. ' + card.text}
        disabled={index === 0 || pending} onClick={() => onMove(index, index - 1)}>⌃</button>
      <button type="button" className="button button-light" aria-label={'Ниже. ' + card.text}
        disabled={index === total - 1 || pending} onClick={() => onMove(index, index + 1)}>⌄</button>
    </div>
  </m.Reorder.Item>
}

function AnswerChoices({ label, items, value, disabled, onChange }: {
  label: string; items: Choice[]; value: number; disabled: boolean; onChange: (value: string) => void
}) {
  const id = useId()
  return <fieldset className="practice-fragments" disabled={disabled}>
    <legend>{label}</legend>
    {items.map(item => <label className="answer" key={item.id}>
      <input type="radio" name={id} value={item.id} checked={item.id === value} onChange={event => onChange(event.target.value)} />
      <span>{item.text}</span>
    </label>)}
  </fieldset>
}

export function PracticeHistoryPage() {
  const { data, error, retry } = useResource<History>()
  return <>
    <PortalHeading title="Мои прохождения">Последние выполненные задания из практики.</PortalHeading>
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <section className="panel history">
      {data.length ? <ul className="data-list">{data.map(item => <li key={item.id}>
        {item.slug
          ? <Link to={'/practice/' + item.slug + '/'}><strong>{item.title}</strong><small>{formatDate(item.completed_at)}</small></Link>
          : <p>{item.title} · {formatDate(item.completed_at)}</p>}
      </li>)}</ul> : <p>После первого верного ответа результат появится здесь.</p>}
      <ButtonLink to="/practice/" light>К заданиям</ButtonLink>
    </section>}
  </>
}
