import { useEffect, useRef, useState } from 'react'
import { api } from '../../shared/api'
import type { Organization } from '../../shared/api'
import { Link } from '../../shared/navigation'
import './classroom.css'

export type Question = { text: string; options: string[]; image?: string; alt?: string; correct?: number | null; explanation?: string; sign?: string }
export type Answers = (number | null)[]
export type QuizCard = { id: number; title: string; ready: boolean; archived: boolean; builtin: boolean; revision: number; updated_at: string; last_version: number | null }
export type Run = {
  id: string; title: string; lesson: string; code: string | null; state: 'waiting' | 'running' | 'closed'
  opened_at: string; version: number | null; report_id: number | null; accepting: boolean; deadline: string | null
}
export type Step = { title: string; prompt: string; image?: string; cards?: { id: number; text: string }[]; choices?: { id: string; text: string }[] }
export type RunDetail = Run & {
  date: string; organization: Organization | null; steps?: Step[]
  counts?: { connected: number; started: number; submitted: number }
  summary?: { submitted: number; correct: number[]; average: number | null; questions: string[] }
}

export const runStates = { waiting: 'Подключение', running: 'Идёт занятие', closed: 'Завершено' }
export const runPath = (id: string) => '/classroom/runs/' + id + '/'
export const testPath = (id: number) => '/classroom/tests/' + id + '/'

export function ClassNav() {
  return <nav className="filters class-nav" aria-label="Кабинет педагога">
    <Link to="/classroom/">Готовые уроки</Link><Link to="/classroom/tests/">Мои тесты</Link>
    <Link to="/classroom/history/">История запусков</Link><Link to="/pdd-teacher/">Отчёты</Link>
  </nav>
}

export function useAction() {
  const busy = useRef(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>()
  async function act(work: () => Promise<void>) {
    if (busy.current) return
    busy.current = true
    setPending(true)
    setError(undefined)
    try { await work() } catch (e) { setError(e) }
    finally { busy.current = false; setPending(false) }
  }
  return { act, pending, error }
}

export function useLive<T>(path: string, initial: T, poll: (data: T) => boolean) {
  const [data, setData] = useState(initial)
  const [error, setError] = useState<unknown>()
  const sequence = useRef(0)
  const active = poll(data)
  useEffect(() => {
    if (!active) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    async function read() {
      const token = sequence.current
      try {
        const next = await api<T>(path, { signal: controller.signal })
        if (token === sequence.current && !controller.signal.aborted) { setData(next); setError(undefined) }
      } catch (e) { if (!controller.signal.aborted && token === sequence.current) setError(e) }
      if (!controller.signal.aborted) timer = setTimeout(read, 3000)
    }
    timer = setTimeout(read, 3000)
    return () => { clearTimeout(timer); controller.abort() }
  }, [path, active])
  async function send(body: unknown) {
    sequence.current++
    const next = await api<T>(path, { method: 'POST', data: body })
    sequence.current++
    setData(next)
    setError(undefined)
    return next
  }
  return { data, send, error }
}

export function TimeLeft({ deadline }: { deadline: string | null }) {
  const [now, setNow] = useState(Date.now)
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  const seconds = Math.max(0, Math.ceil((Date.parse(deadline || '') - now) / 1000))
  return <span className="tag" role="timer">Осталось {Math.floor(seconds / 60)} мин {seconds % 60} с</span>
}

export function QuestionList({ questions, answers, change, disabled = false, review = false }: {
  questions: Question[]; answers: Answers; change?: (index: number, answer: number) => void; disabled?: boolean; review?: boolean
}) {
  return <div className="class-questions">{questions.map((q, i) =>
    <fieldset className="panel class-question" key={i} disabled={disabled || review}>
      <legend>{i + 1}. {q.text || 'Вопрос без текста'}</legend>
      {q.image && <img className="class-sign" src={q.image} alt={q.alt || 'Дорожный знак'} />}
      {q.options.map((option, j) => <label className="answer" key={j}>
        <input type="radio" name={'question-' + i} checked={answers[i] === j} onChange={() => change?.(i, j)} />
        <span>{option || 'Вариант ответа'}</span>
      </label>)}
      {review && <p><strong>{answers[i] === q.correct ? 'Верно' : 'Верный ответ — ' + q.options[q.correct!]}</strong>
        {q.explanation && <>. {q.explanation}</>}</p>}
    </fieldset>)}</div>
}
