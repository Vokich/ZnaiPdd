import { useState } from 'react'
import type { FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { Link, useNavigate } from '../../shared/navigation'
import { useResource } from '../../shared/state'
import { Feedback, Loading, LoadError, PortalHeading } from '../../shared/ui'
import { QuestionList, TimeLeft, useAction, useLive } from './classroom-ui'
import type { Answers, Question, Run } from './classroom-ui'

type Attempt = Pick<Run, 'title' | 'state' | 'accepting' | 'deadline'> & {
  platform: boolean; joined: boolean; started: boolean; submitted: boolean; revision?: number; answers?: Answers
  questions?: Question[]; instruction?: string; score?: number; review_until: string | null
}

export function JoinPage() {
  const navigate = useNavigate()
  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const code = new FormData(e.currentTarget).get('code') as string
    void navigate('/join/' + code + '/')
  }
  return <><PortalHeading title="Присоединиться к тесту">Введите код с экрана педагога.</PortalHeading>
    <form className="panel class-editor class-join" onSubmit={submit}>
      <label>Код занятия<input name="code" inputMode="numeric" pattern="[0-9]{8}" minLength={8} maxLength={8} required autoComplete="off" /></label>
      <button className="button">Найти занятие</button>
    </form></>
}

export function JoinSessionPage() {
  const { code } = useParams()
  const { data, error, retry } = useResource<Attempt>()
  if (error) return <><LoadError error={error} retry={retry} /><Link to="/join/">Ввести другой код</Link></>
  return data && code ? <StudentTest initial={data} code={code} /> : <Loading />
}

function StudentTest({ initial, code }: { initial: Attempt; code: string }) {
  const live = useLive('classroom/join/' + code + '/', initial, data => data.state !== 'closed' || data.score !== undefined)
  const data = live.data
  const [unsaved, setUnsaved] = useState<{ answers: Answers; revision: number }>()
  const action = useAction()
  const [conflict, setConflict] = useState(false)
  const answers = unsaved?.answers || data.answers || []
  const changed = unsaved?.answers.flatMap((value, i) => value === data.answers?.[i] ? [] : [i + 1]) || []
  function command(name: string) { void action.act(async () => { await live.send({ action: name }) }) }
  async function persist(next: Answers, revision: number, submit = false) {
    try {
      await live.send({ action: submit ? 'submit' : 'save', revision, answers: next })
      setUnsaved(undefined); setConflict(false)
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setConflict(true)
      throw e
    }
  }
  function select(index: number, answer: number) {
    const next = answers.slice()
    next[index] = answer
    const revision = unsaved?.revision ?? data.revision!
    setUnsaved({ answers: next, revision })
    void action.act(() => persist(next, revision))
  }
  return <><PortalHeading title={data.title} />
    <section className="panel class-panel">
      {data.platform && !data.joined && <p>Это тест платформы. Если вы вошли в аккаунт, лучший результат учитывается в рейтинге.
        Ответы доступны администраторам. При гостевом прохождении имя не записывается.</p>}
      {data.state !== 'closed' && <TimeLeft deadline={data.deadline} />}
      {data.state === 'closed' ? (data.score !== undefined ? <>
        <h2>Твой результат — {data.score} из {data.questions?.length}</h2>
        <p>Личный разбор доступен до {new Date(data.review_until!).toLocaleString('ru-RU')}.</p>
      </> : <p>Занятие завершено. На этом устройстве доступного разбора нет.</p>) :
        !data.joined ? <>{data.accepting ? <><p>Подключись с устройства, на котором будешь отвечать.</p>
          <button className="button" disabled={action.pending} onClick={() => command('join')}>Присоединиться</button></> : <p>Вход для новых участников закрыт.</p>}</> :
        data.submitted ? <p role="status">Работа сдана. Когда занятие завершится, здесь появятся балл и разбор.</p> :
        data.state === 'waiting' ? <p role="status">Вы подключились. Ждём, когда педагог начнёт тест.</p> :
        !data.started ? <button className="button" disabled={action.pending} onClick={() => command('begin')}>Открыть вопросы</button> :
        <><p>{data.instruction || 'Выбери один ответ в каждом вопросе.'}</p>
          <p role="status">{action.pending ? 'Сохраняем…' : unsaved ? 'Ожидают подтверждения ответы на вопросы ' + (changed.join(', ') || 'текущего черновика') + '.' :
            data.revision ? 'Черновик сохранён.' : 'Ответы будут сохраняться автоматически.'}</p></>}
      <Feedback error={action.error || live.error} />
      {unsaved && !conflict && data.state === 'running' && !action.pending &&
        <button className="button button-light" onClick={() => action.act(() => persist(unsaved.answers, unsaved.revision))}>Повторить сохранение</button>}
      {conflict && <button className="button button-light" onClick={() => window.location.reload()}>Загрузить сохранённые ответы</button>}
    </section>
    {data.questions && <QuestionList questions={data.questions} answers={data.state === 'closed' ? data.answers || [] : answers} review={data.state === 'closed'}
      disabled={action.pending || conflict} change={select} />}
    {data.started && !data.submitted && data.state === 'running' && <div className="class-actions">
      <button className="button" disabled={action.pending || conflict || !!unsaved || answers.includes(null)}
        onClick={() => action.act(() => persist(answers, data.revision!, true))}>Сдать</button></div>}
  </>
}
