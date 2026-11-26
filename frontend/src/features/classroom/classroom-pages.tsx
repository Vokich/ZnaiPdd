import { useState } from 'react'
import * as m from 'motion/react-m'
import { useLocation } from 'react-router-dom'
import { api } from '../../shared/api'
import { Link, useNavigate } from '../../shared/navigation'
import { useResource } from '../../shared/state'
import { ButtonLink, Feedback, Loading, LoadError, PortalHeading } from '../../shared/ui'
import { ReportForm } from './reports'
import { ClassNav, runPath, runStates, TimeLeft, useAction, useLive } from './classroom-ui'
import type { Run, RunDetail, Step } from './classroom-ui'
import { OrderCard } from '../practice/practice-pages'
import { RouteStreet } from '../routes/route-street'
import '../../styles/learning.css'

type Lesson = { id: string; title: string; audience: string; minutes: number; plan: string[] }
type Library = { lessons: Lesson[]; history: Run[]; page: number; pages: number }

export function ClassroomPage() {
  const { data, error, retry } = useResource<Library>()
  const history = useLocation().pathname.includes('/history')
  const navigate = useNavigate()
  const action = useAction()
  async function start(lesson: string) {
    const run = await api<Run>('classroom/', { method: 'POST', data: { lesson } })
    await navigate(runPath(run.id))
  }
  return <><PortalHeading title={history ? 'История запусков' : 'Провести урок'} />
    <ClassNav />
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : history ?
      <section className="panel"><ul className="data-list">{data.history.map(run => <li key={run.id}><Link to={runPath(run.id)}>
        <span><strong>{run.title}</strong><small>{new Date(run.opened_at).toLocaleString('ru-RU')} · {runStates[run.state]}
        {run.version && ' · версия ' + run.version}</small></span><span aria-hidden="true">→</span></Link></li>)}</ul>
        {!data.history.length && <p>Здесь появятся проведённые занятия и запуски тестов.</p>}
        <nav className="actions" aria-label="Страницы истории">
          {data.page > 1 && <Link to={'?page=' + (data.page - 1)}>Назад</Link>}
          {data.page < data.pages && <Link to={'?page=' + (data.page + 1)}>Дальше</Link>}
        </nav></section> :
      <div className="class-list">{data.lessons.map(lesson => <article className="panel class-panel" key={lesson.id}>
        <small>{lesson.audience} · {lesson.minutes} минут</small><h2>{lesson.title}</h2>
        <ol>{lesson.plan.map(item => <li key={item}>{item}</li>)}</ol>
        <button className="button" disabled={action.pending} onClick={() => action.act(() => start(lesson.id))}>Начать показ</button>
      </article>)}</div>}
    <Feedback error={action.error} />
  </>
}

export function ClassroomRunPage() {
  const { data, error, retry } = useResource<RunDetail>()
  const report = useLocation().pathname.endsWith('/report/')
  const navigate = useNavigate()
  if (error) return <LoadError error={error} retry={retry} />
  if (!data) return <Loading />
  if (report) return <><PortalHeading title="Сохранить итог занятия" /><ClassNav />
    {data.report_id ? <ButtonLink to={'/pdd-teacher/' + data.report_id + '/'}>Открыть сохранённый отчёт</ButtonLink> :
      data.lesson || data.state === 'closed' ? <ReportForm options={{ routes: [], practice: [] }}
        classroom={{ ...data, submitted: data.counts?.submitted ?? null }}
        onSave={saved => navigate('/pdd-teacher/' + saved.id + '/')} /> :
        <ButtonLink to={runPath(data.id)}>Вернуться к тесту</ButtonLink>}
  </>
  return data.lesson ? <LessonShow run={data} /> : <TeacherMonitor initial={data} />
}

function ReportLink({ run }: { run: Run }) {
  return <ButtonLink to={run.report_id ? '/pdd-teacher/' + run.report_id + '/' : runPath(run.id) + 'report/'}>
    {run.report_id ? 'Открыть отчёт' : 'Сохранить итог'}</ButtonLink>
}

function LessonShow({ run }: { run: RunDetail }) {
  const [step, setStep] = useState(0)
  const steps = run.steps!
  return <><PortalHeading title={run.title}>Разобрали вместе · шаг {step + 1} из {steps.length}</PortalHeading>
    <LessonStep key={step} run={run} step={steps[step]} index={step} />
    <div className="class-actions">
      <button className="button button-light" disabled={step === 0} onClick={() => setStep(step - 1)}>Назад</button>
      {step + 1 < steps.length ? <button className="button" onClick={() => setStep(step + 1)}>Дальше</button> : <ReportLink run={run} />}
    </div><Link className="text-link" to="/classroom/">К готовым урокам</Link></>
}

function LessonStep({ run, step, index }: { run: Run; step: Step; index: number }) {
  const [cards, setCards] = useState(step.cards || [])
  const [choice, setChoice] = useState<string | null>(null)
  const [review, setReview] = useState<{ correct: boolean | null; explanation: string; source: string }>()
  const action = useAction()
  function move(from: number, to: number) {
    const next = cards.slice()
    next.splice(to, 0, next.splice(from, 1)[0])
    setCards(next)
    setReview(undefined)
  }
  return <section className="panel class-panel class-stage">
    <h2>{step.title}</h2><p>{step.prompt}</p>
    {step.image && <img className="class-sign" src={step.image} alt={step.title} />}
    {step.cards && <m.Reorder.Group as="ol" values={cards} onReorder={next => { setCards(next); setReview(undefined) }} className="order-cards">
      {cards.map((card, i) => <OrderCard key={card.id} card={card} index={i} total={cards.length} pending={action.pending}
        onMove={move} onDrop={() => setReview(undefined)} />)}
    </m.Reorder.Group>}
    {step.choices && <>
      <RouteStreet scene={{ label: step.title, text: step.prompt, kind: run.lesson === 'bike-crossing' ? 'dismount' : 'visibility',
        travel: run.lesson === 'bike-crossing' ? 'ride' : 'walk' }} destination={null} paused />
      <fieldset className="class-question"><legend>Как поступить?</legend>{step.choices.map(item => <label className="answer" key={item.id}>
        <input type="radio" name="scene" checked={choice === item.id} disabled={action.pending}
          onChange={() => { setChoice(item.id); setReview(undefined) }} />{item.text}</label>)}</fieldset></>}
    <div className="class-actions"><button className="button" disabled={action.pending} onClick={() => action.act(async () =>
      setReview(await api('classroom/runs/' + run.id + '/', { method: 'POST', data: {
        step: index, answer: step.cards ? cards.map(card => card.id) : choice,
      } })))}>Показать объяснение</button></div>
    {review && <div role="status"><strong>{review.correct === null ? 'Разбор' : review.correct ? 'Верно' : 'Обсудите ещё раз'}</strong>
      <p>{review.explanation}</p><a className="text-link" href={review.source} target="_blank" rel="noreferrer">Открыть правило ↗</a></div>}
    <Feedback error={action.error} />
  </section>
}

function TeacherMonitor({ initial }: { initial: RunDetail }) {
  const path = 'classroom/runs/' + initial.id + '/'
  const live = useLive(path, initial, run => run.state !== 'closed')
  const run = live.data
  const action = useAction()
  const [show, setShow] = useState(false)
  const [copied, setCopied] = useState(false)
  const [confirmClose, setConfirmClose] = useState(false)
  const join = new URL('/join/' + run.code + '/', window.location.origin).href
  const counts = run.counts!
  const summary = run.summary
  function send(command: string) { void action.act(async () => { await live.send({ action: command }) }) }
  return <><PortalHeading title={run.title}>Версия {run.version} · {runStates[run.state]}</PortalHeading>
    <section className="panel class-panel">
      {run.state !== 'closed' && <TimeLeft deadline={run.deadline} />}
      {run.accepting && <>
        <img className="class-qr" src={'/api/' + path + 'qr/'} alt="QR-код подключения к тесту" />
        <p>Код для входа на странице «Присоединиться»</p><strong className="class-code">{run.code}</strong>
        <div className="class-actions"><a className="text-link" href={join} target="_blank" rel="noreferrer">{join}</a>
          <button className="button button-light" onClick={() => action.act(async () => {
            await navigator.clipboard.writeText(join); setCopied(true)
          })}>{copied ? 'Ссылка скопирована' : 'Скопировать ссылку'}</button></div>
      </>}
      {!run.accepting && run.state !== 'closed' && <p>Вход для новых участников закрыт.</p>}
      <dl className="class-stats">{([['Подключились', counts.connected], ['Начали', counts.started], ['Отправили', counts.submitted]] as const)
        .map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
      <div className="class-actions">
        {run.state === 'waiting' && <button className="button" disabled={action.pending} onClick={() => send('start')}>Начать тест</button>}
        {run.accepting && <button className="button button-light" disabled={action.pending} onClick={() => send('lock')}>Закрыть вход</button>}
        {run.state !== 'closed' && <button className="button button-light" disabled={action.pending}
          onClick={() => confirmClose ? send('close') : setConfirmClose(true)}>{confirmClose ? 'Подтвердить завершение' : 'Завершить тест'}</button>}
        {confirmClose && run.state !== 'closed' && <button className="button button-light" onClick={() => setConfirmClose(false)}>Отмена</button>}
        {summary && <><button className="button button-light" aria-expanded={show} onClick={() => setShow(!show)}>
          {show ? 'Скрыть сводку' : 'Показать сводку'}</button><ReportLink run={run} /></>}
      </div>
      {show && summary && (summary.submitted ? <>
        <h2>Разбор с классом</h2><p>Средний балл — {summary.average?.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} из {summary.questions.length}.</p>
        <ol>{summary.questions.map((question, i) => <li key={i}>{question} — верно {Math.round(100 * summary.correct[i] / summary.submitted)} %
          {summary.correct[i] < summary.submitted && ' · повторить с классом'}</li>)}</ol></> : <p>Никто не сдал тест. Баллов для сводки пока нет.</p>)}
      <Feedback error={action.error || live.error} />
    </section><ButtonLink light to="/classroom/history/">История запусков</ButtonLink>
  </>
}
