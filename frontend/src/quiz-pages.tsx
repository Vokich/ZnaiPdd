import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from './navigation'
import { useLocation } from 'react-router-dom'
import { api, ApiError } from './api'
import type { Quiz, QuizResult, QuizType } from './api'
import { useResource } from './state'
import { ButtonLink, Feedback, FieldErrors, Loading, LoadError, PortalHeading } from './ui'
import { quizInfo } from './quiz-info'
import { Mascot } from './mascot'
import { FeedbackMotion, MotionNumber, useCelebrate } from './motion-ui'

export function QuizzesPage() {
  return <>
    <PortalHeading title="Тесты по ПДД">Выбери свою возрастную группу и проверь знания.</PortalHeading>
    <div className="portal-grid">
      {Object.values(quizInfo).map(quiz => <Link className="panel route-card quiz-link" data-scroll-reveal="card" to={quiz.path} key={quiz.path}>
        <span className="tag">{quiz.label}</span><h2>{quiz.ages}</h2><span aria-hidden="true">→</span>
      </Link>)}
    </div>
  </>
}

export function QuizPage({ type }: { type: QuizType }) {
  const { data, error, retry } = useResource<Quiz>()
  if (error) return <LoadError error={error} retry={retry} />
  return data ? <QuizForm type={type} quiz={data} /> : <Loading />
}

function QuizForm({ type, quiz }: { type: QuizType; quiz: Quiz }) {
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [error, setError] = useState<unknown>()
  const [pending, setPending] = useState(false)
  const navigate = useNavigate()
  const count = Object.keys(answers).length
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(undefined)
    try {
      const result = await api<QuizResult>(`tests/${type}/results/`, { method: 'POST', data: { answers } })
      navigate(quizInfo[type].result + '?id=' + result.id, { state: { justCompleted: true } })
    } catch (error) { setError(error) }
    finally { setPending(false) }
  }
  return <>
    <Link className="text-link" to="/age/">← К списку тестов</Link>
    <PortalHeading title={`Тест по ПДД · ${quizInfo[type].ages}`}>Выбери один ответ на каждый вопрос. Для зачёта нужно набрать {quiz.passing_score} баллов.</PortalHeading>
    <form className="quiz-form" onSubmit={submit}>
      <div className="quiz-progress panel">
        <label htmlFor="quiz-progress">Ответы <strong>{count} / {quiz.questions.length}</strong></label>
        <progress id="quiz-progress" value={count} max={quiz.questions.length} />
      </div>
      {quiz.questions.map((question, index) => <div key={question.id} className="panel question-panel" data-scroll-reveal="quiet">
        <fieldset className="question">
          <legend><span className="question-number">{index + 1}</span> {question.text}</legend>
          {question.options.map((option, optionIndex) => <label className="answer" key={optionIndex}>
            <input type="radio" name={`question_${question.id}`} required value={optionIndex + 1}
              checked={answers[question.id] === optionIndex + 1}
              onChange={() => setAnswers(previous => ({ ...previous, [question.id]: optionIndex + 1 }))} />
            <span>{option}</span>
          </label>)}
          <FieldErrors error={error} name={`question_${question.id}`} />
        </fieldset>
      </div>)}
      <Feedback error={error} />
      <button className="button" data-scroll-reveal="quiet" disabled={pending}>{pending ? 'Проверяем…' : 'Завершить тест →'}</button>
    </form>
  </>
}

export function ResultPage({ type }: { type: QuizType }) {
  const { data: result, error, retry } = useResource<QuizResult>()
  const { state } = useLocation()
  const score = useRef<HTMLElement>(null)
  const celebrated = useRef<number | null>(null)
  const celebrate = useCelebrate()
  useEffect(() => {
    if (!result?.passed || !state?.justCompleted || celebrated.current === result.id) return
    celebrated.current = result.id
    void celebrate(score.current)
  }, [celebrate, result, state])
  if (error instanceof ApiError && error.status === 404) return <div className="panel status-panel"><Feedback error={error} /><ButtonLink to={quizInfo[type].path}>Пройти тест →</ButtonLink></div>
  if (error) return <LoadError error={error} retry={retry} />
  if (!result) return <Loading />
  return <>
    <PortalHeading title={result.passed ? 'Тест пройден!' : 'Попробуй ещё раз'}>Тест по ПДД · {quizInfo[type].ages}</PortalHeading>
    <section className="panel result-panel" ref={score}>
      <div className="quiz-result-summary">
        <FeedbackMotion success={result.passed} attempt={result.id}>
          <span className="tag">{result.passed ? 'Зачёт' : 'Новая попытка'}</span>
          <p className="score"><strong><MotionNumber value={result.score} /></strong> / {result.total}</p>
          <p>Проходной балл — {result.passing_score}.</p>
        </FeedbackMotion>
        <Mascot mood={result.passed ? 'success' : 'retry'} reaction={result.id} />
      </div>
      <div className="actions">
        {result.passed && <a className="button" href={`/api/tests/${type}/certificate/?id=${result.id}`}>Скачать {result.score >= 24 ? 'диплом' : 'сертификат'} ↓</a>}
        <ButtonLink to={result.passed ? '/profile/' : quizInfo[type].path} light={result.passed}>{result.passed ? 'Мой кабинет →' : 'Пройти заново →'}</ButtonLink>
      </div>
    </section>
  </>
}
