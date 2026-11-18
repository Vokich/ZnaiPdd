import { useEffect, useState } from 'react'
import { api } from './api'
import type { SignCatalog } from './api'
import { useResource } from './state'
import { Link, useNavigate } from './navigation'
import { ButtonLink, Feedback, Loading, LoadError, PortalHeading } from './ui'
import { ClassNav, QuestionList, runPath, testPath, useAction } from './classroom-ui'
import type { Answers, Question, QuizCard, Run } from './classroom-ui'

type Draft = QuizCard & { instruction: string; questions: Question[]; deletable: boolean }
const emptyQuestion = (): Question => ({ text: '', options: ['', ''], correct: null, explanation: '' })

export function ClassroomTestsPage() {
  const { data, error, retry } = useResource<QuizCard[]>()
  const [archive, setArchive] = useState(false)
  const action = useAction()
  const navigate = useNavigate()
  async function start(quiz: number) {
    const run = await api<Run>('classroom/', { method: 'POST', data: { quiz } })
    await navigate(runPath(run.id))
  }
  function cards(items: QuizCard[]) {
    return <div className="class-list">{items.map(q => <article className="panel class-panel" key={q.id}>
      <small>{q.archived ? 'В архиве' : q.ready ? 'Готов' : 'Черновик'} · {new Date(q.updated_at).toLocaleDateString('ru-RU')}</small>
      <h2>{q.title || 'Без названия'}</h2>
      <div className="class-actions">
        <ButtonLink light to={testPath(q.id)}>Открыть</ButtonLink>
        {q.last_version && !q.archived && <button className="button" disabled={action.pending} onClick={() => action.act(() => start(q.id))}>
          {q.ready ? 'Запустить по QR' : 'Запустить версию ' + q.last_version + ' по QR'}</button>}
        <button className="button button-light" disabled={action.pending} onClick={() => action.act(async () => {
          const copy = await api<QuizCard>('classroom/tests/' + q.id + '/', { method: 'POST', data: { action: 'copy' } })
          await navigate(testPath(copy.id))
        })}>Копировать</button>
        {!q.builtin && <button className="button button-light" disabled={action.pending} onClick={() => action.act(async () => {
          await api('classroom/tests/' + q.id + '/', { method: 'POST', data: { action: q.archived ? 'restore' : 'archive', revision: q.revision } })
          retry()
        })}>{q.archived ? 'Вернуть из архива' : 'В архив'}</button>}
      </div>
    </article>)}</div>
  }
  const mine = data?.filter(q => !q.builtin && q.archived === archive) || []
  return <><PortalHeading title="Мои тесты" /><ClassNav />
    <div className="class-actions"><button className="button" disabled={action.pending} onClick={() => action.act(async () => {
      const draft = await api<QuizCard>('classroom/tests/', { method: 'POST', data: { title: '', questions: [emptyQuestion()] } })
      await navigate(testPath(draft.id))
    })}>Создать тест</button><button className="button button-light" aria-pressed={archive} onClick={() => setArchive(!archive)}>
      {archive ? 'Показать активные' : 'Открыть архив'}</button></div>
    <Feedback error={action.error} />
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <>
      <h2>{archive ? 'Архив' : 'Моя библиотека'}</h2>{mine.length ? cards(mine) : <p>Здесь пока нет тестов.</p>}
      {!archive && <><h2>Готовые тесты для класса</h2>{cards(data.filter(q => q.builtin))}</>}
    </>}
  </>
}

export function ClassroomTestPage() {
  const { data, error, retry } = useResource<Draft>()
  if (error) return <LoadError error={error} retry={retry} />
  return data ? <TestEditor initial={data} /> : <Loading />
}

function TestEditor({ initial }: { initial: Draft }) {
  const [draft, setDraft] = useState(initial)
  const [preview, setPreview] = useState(initial.builtin)
  const [answers, setAnswers] = useState<Answers>([])
  const [notice, setNotice] = useState('')
  const [dirty, setDirty] = useState(false)
  const [signs, setSigns] = useState<SignCatalog['signs']>([])
  const [remove, setRemove] = useState(false)
  const action = useAction()
  const navigate = useNavigate()
  const path = 'classroom/tests/' + initial.id + '/'
  const readonly = draft.archived || draft.builtin
  useEffect(() => {
    const controller = new AbortController()
    api<SignCatalog>('signs/', { signal: controller.signal }).then(catalog => setSigns(catalog.signs)).catch(() => {})
    return () => controller.abort()
  }, [])
  function edit(fields: Partial<Draft>) {
    setDraft({ ...draft, ...fields })
    setNotice(''); setDirty(true); setAnswers([])
  }
  function changeQuestion(index: number, fields: Partial<Question>) {
    edit({ questions: draft.questions.map((q, i) => i === index ? { ...q, ...fields } : q) })
  }
  function move(index: number, offset: number) {
    const rows = draft.questions.slice()
    rows.splice(index + offset, 0, rows.splice(index, 1)[0])
    edit({ questions: rows })
  }
  async function save(publish: boolean) {
    const saved = await api<QuizCard>(path, { method: 'POST', data: { title: draft.title, instruction: draft.instruction,
      questions: draft.questions, revision: draft.revision, action: publish ? 'publish' : 'save' } })
    setDraft({ ...draft, ...saved, deletable: draft.deletable && !publish })
    setNotice(publish ? 'Готовая версия сохранена.' : 'Черновик сохранён.'); setDirty(false)
  }
  const previewQuestions = draft.questions.map(q => {
    const sign = signs.find(item => item.slug === q.sign)
    return { ...q, image: sign?.image || undefined, alt: sign?.name }
  })
  return <><Link className="text-link" to="/classroom/tests/">← Мои тесты</Link>
    <PortalHeading title={preview ? draft.title || 'Предпросмотр теста' : 'Редактор теста'}>{preview ? 'Предпросмотр ученика' : 'Вопросы с выбором одного ответа'}</PortalHeading>
    <div className="class-actions">{!readonly && <button className="button button-light" onClick={() => setPreview(!preview)}>
      {preview ? 'К редактированию' : 'Предпросмотр'}</button>}
      {draft.ready && !draft.archived && !dirty && <button className="button" disabled={action.pending} onClick={() => action.act(async () => {
        const run = await api<Run>('classroom/', { method: 'POST', data: { quiz: draft.id } })
        await navigate(runPath(run.id))
      })}>Запустить по QR</button>}</div>
    {preview ? <><p>{draft.instruction}</p><QuestionList questions={previewQuestions} answers={answers} change={(i, value) => {
      const next = answers.slice(); next[i] = value; setAnswers(next)
    }} /></> : <fieldset className="panel class-editor" disabled={action.pending || readonly}>
      <legend>Содержание теста</legend>
      <p>Не добавляйте ФИО учеников и другие персональные данные класса.</p>
      <label>Название<input maxLength={160} value={draft.title} onChange={e => edit({ title: e.target.value })} /></label>
      <label>Тема или инструкция<textarea maxLength={2000} value={draft.instruction} onChange={e => edit({ instruction: e.target.value })} /></label>
      {draft.questions.map((q, i) => <fieldset className="class-editor class-question" key={i}><legend>Вопрос {i + 1}</legend>
        <label>Текст вопроса<textarea maxLength={1000} value={q.text} onChange={e => changeQuestion(i, { text: e.target.value })} /></label>
        <label>Изображение знака<select value={q.sign || ''} onChange={e => changeQuestion(i, { sign: e.target.value })}>
          <option value="">Без изображения</option>{signs.filter(s => s.image).map(s =>
            <option key={s.slug} value={s.slug}>{s.number} · {s.name}</option>)}</select></label>
        {q.options.map((option, j) => <div key={j} className="class-option">
          <input type="radio" name={'correct-' + i} aria-label={'Верный вариант ' + (j + 1)} checked={q.correct === j}
            onChange={() => changeQuestion(i, { correct: j })} />
          <input aria-label={'Вариант ' + (j + 1)} maxLength={500} value={option}
            onChange={e => changeQuestion(i, { options: q.options.map((o, k) => k === j ? e.target.value : o) })} />
          <button className="button button-light" aria-label={'Удалить вариант ' + (j + 1)} onClick={() =>
            changeQuestion(i, { options: q.options.filter((_, k) => k !== j),
              correct: q.correct == null || q.correct === j ? null : q.correct > j ? q.correct - 1 : q.correct })}>×</button>
        </div>)}
        <div><button className="button button-light" disabled={q.options.length >= 6}
          onClick={() => changeQuestion(i, { options: [...q.options, ''] })}>Добавить вариант</button></div>
        <label>Пояснение (необязательно)<textarea maxLength={1500} value={q.explanation || ''} onChange={e => changeQuestion(i, { explanation: e.target.value })} /></label>
        <div className="class-actions"><button className="button button-light" disabled={!i} onClick={() => move(i,-1)}>Выше</button>
          <button className="button button-light" disabled={i === draft.questions.length - 1} onClick={() => move(i,1)}>Ниже</button>
          <button className="button button-light" onClick={() => edit({ questions: draft.questions.filter((_, k) => k !== i) })}>Удалить вопрос</button></div>
      </fieldset>)}
      <div><button className="button" disabled={draft.questions.length >= 30} onClick={() => edit({ questions: [...draft.questions, emptyQuestion()] })}>Добавить вопрос</button></div>
    </fieldset>}
    {!readonly && <div className="class-actions">
      <button className="button button-light" disabled={action.pending} onClick={() => action.act(() => save(false))}>Сохранить черновик</button>
      <button className="button" disabled={action.pending} onClick={() => action.act(() => save(true))}>Сохранить готовую версию</button>
      {draft.deletable && <button className="button button-light" disabled={action.pending} onClick={() => {
        if (!remove) return setRemove(true)
        void action.act(async () => { await api(path, { method: 'DELETE', data: { revision: draft.revision } }); await navigate('/classroom/tests/') })
      }}>{remove ? 'Подтвердить удаление' : 'Удалить черновик'}</button>}
      {remove && <button className="button button-light" onClick={() => setRemove(false)}>Отмена</button>}
    </div>}
    <p role="status">{dirty ? 'Есть несохранённые изменения.' : notice}</p><Feedback error={action.error} />
  </>
}
