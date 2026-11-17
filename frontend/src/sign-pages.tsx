import { useState } from 'react'
import type { FormEvent } from 'react'
import { Form, Navigate, useParams, useSearchParams } from 'react-router-dom'
import { Link, useNavigate } from './navigation'
import { api } from './api'
import type { Sign, SignCatalog, SignTest } from './api'
import { useResource, useSession } from './state'
import { ButtonLink, Feedback, FieldErrors, Loading, LoadError, PortalHeading } from './ui'
import { Mascot } from './mascot'
import { FeedbackMotion } from './motion-ui'

export function SignsListPage() {
  const [search] = useSearchParams()
  const { user } = useSession()
  const { data, error, retry } = useResource<SignCatalog>()
  const category = search.get('category') || ''
  const query = search.get('q') || ''
  const collection = search.get('learned') === '1'
  const route = (nextCategory: string, learned: boolean, term = query) => {
    const filters = new URLSearchParams()
    if (nextCategory) filters.set('category', nextCategory)
    if (term) filters.set('q', term)
    if (learned) filters.set('learned', '1')
    return '/signs/all/' + (filters.size ? '?' + filters.toString() : '')
  }
  const signs = collection ? data?.signs.filter(sign => sign.unlocked) : data?.signs

  return <>
    <PortalHeading title="Знаки ПДД">Справочник дорожных знаков по номеру и названию.</PortalHeading>
    <Link className="text-link catalog-circuit" to="/road-circuit/">Дорожные карточки →</Link>
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <>
      {user && <nav className="filters sign-modes" aria-label="Справочник и коллекция">
        <Link to={route(category, false)} preventScrollReset aria-current={!collection ? 'page' : undefined}>Справочник</Link>
        <Link to={route(category, true)} preventScrollReset aria-current={collection ? 'page' : undefined}>
          Моя коллекция · {data.unlocked_count} из {data.total}
        </Link>
      </nav>}
      <Form className="sign-search" method="get" action="/signs/all/" preventScrollReset key={search.toString()}>
        <label className="field">Номер или название знака
          <input type="search" name="q" defaultValue={query} maxLength={120} placeholder="Например, 5.19.1" />
        </label>
        {category && <input type="hidden" name="category" value={category} />}
        {collection && <input type="hidden" name="learned" value="1" />}
        <button className="button" type="submit">Найти</button>
        {query && <Link className="text-link" to={route(category, collection, '')} preventScrollReset>Сбросить поиск</Link>}
      </Form>
      <nav className="filters" aria-label="Категории знаков">
        {[{ value: '', label: 'Все' }, ...data.categories].map(({ value, label }) => <Link key={value}
          to={route(value, collection)} viewTransition={false} preventScrollReset
          aria-current={value === category ? 'true' : undefined}>{label}</Link>)}
      </nav>
      {signs?.length ? <div className="sign-grid catalog-results">
        {signs.map(sign => <Link to={'/signs/' + sign.slug + '/'} key={sign.slug} className="panel sign-card">
          <SignImage sign={sign} />
          <small>{sign.number} · {sign.category_label}</small>
          <h2>{sign.name}</h2>
          {sign.unlocked && <span className="tag">Изучен</span>}
        </Link>)}
      </div> : <div className="panel status-panel">
        {collection && !user && <Link className="text-link" to="/login/" state={{ next: route(category, true) }}>Войти для просмотра коллекции</Link>}
        {collection && user && !query && !category && <p>После мини-теста знак появится в коллекции.</p>}
        {(!collection || Boolean(user && (query || category))) && <p>По этим условиям знаки не найдены.</p>}
      </div>}
    </>}
  </>
}

function SignImage({ sign }: { sign: Sign }) {
  const [missing, setMissing] = useState(!sign.image)
  return <div className="sign-image">
    {!missing && sign.image ? <img src={sign.image} alt={sign.name} onError={() => setMissing(true)} />
      : <p>Изображение недоступно</p>}
  </div>
}

export function SignDetailPage() {
  const { data: sign, error, retry } = useResource<Sign>()
  const { user } = useSession()
  if (error) return <LoadError error={error} retry={retry} />
  if (!sign) return <Loading />
  const testPath = '/signs/' + sign.slug + '/test/'
  return <>
    <Link className="text-link" to="/signs/all/">← К справочнику</Link>
    <PortalHeading title={sign.name}>{sign.number} · {sign.category_label}</PortalHeading>
    <article className="panel sign-overview">
      <div>
        <SignImage key={sign.slug} sign={sign} />
        {sign.image_credit && <small className="sign-credit">{sign.image_credit}</small>}
      </div>
      <div>
        <h2>Что означает знак</h2><p>{sign.description}</p>
        {sign.fun_fact && <><h2>Интересный факт</h2><p>{sign.fun_fact}</p></>}
        <p><a className="text-link" href={sign.source_url} target="_blank" rel="noreferrer">Открыть источник в ПДД ↗</a></p>
        {sign.unlocked && <div className="actions"><span className="tag">Изучен</span><Link className="text-link" to="/signs/all/?learned=1">Моя коллекция</Link></div>}
        {!sign.unlocked && sign.has_test && user && <ButtonLink to={testPath}>Пройти мини-тест</ButtonLink>}
        {!sign.unlocked && sign.has_test && user === null && <Link className="button button-light" to="/login/" state={{ next: testPath }}>Войти для мини-теста</Link>}
      </div>
    </article>
    {!!sign.exercises?.length && <section className="panel" style={{ marginTop: 16 }}>
      <h2>Задания по этому знаку</h2>
      <ul>{sign.exercises.map(exercise => <li key={exercise.slug}>
        <Link className="text-link" to={'/practice/' + exercise.slug + '/'}>{exercise.title} →</Link>
      </li>)}</ul>
    </section>}
  </>
}

export function SignTestPage() {
  const { slug } = useParams()
  const { data, error, retry } = useResource<SignTest>()
  if (error) return <LoadError error={error} retry={retry} />
  if (!data || !slug) return <Loading />
  if (data.unlocked) return <Navigate to={`/signs/${slug}/`} replace />
  return <SignTestForm test={data} slug={slug} />
}

function SignTestForm({ test, slug }: { test: SignTest; slug: string }) {
  const [error, setError] = useState<unknown>()
  const [attempt, setAttempt] = useState(0)
  const [pending, setPending] = useState(false)
  const navigate = useNavigate()
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const answer = Number(new FormData(event.currentTarget).get('answer'))
    setPending(true)
    setError(undefined)
    try {
      await api(`signs/${slug}/test/`, { method: 'POST', data: { answer } })
      navigate(`/signs/${slug}/`, { replace: true })
    } catch (error) { setError(error); setAttempt(value => value + 1) }
    finally { setPending(false) }
  }
  return <>
    <Link className="text-link" to={`/signs/${slug}/`}>← К знаку</Link>
    <PortalHeading title="Мини-тест" />
    <form className="panel editor" onSubmit={submit}>
      {test.options?.length ? <>
        <fieldset className="question"><legend>{test.question}</legend>
          {test.options.map(option => <label key={option.id} className="answer">
            <input type="radio" name="answer" value={option.id} required /><span>{option.text}</span>
          </label>)}
        </fieldset>
        <div className="sign-test-guide">
          <Mascot mood={error ? 'retry' : 'idle'} reaction={attempt} />
          {Boolean(error) && <FeedbackMotion success={false} attempt={attempt}>
            <div role="alert"><FieldErrors error={error} name="answer" /></div>
            <Feedback error={error} />
          </FeedbackMotion>}
        </div>
        <div className="actions" data-scroll-reveal="quiet"><button className="button" disabled={pending}>Проверить ответ →</button></div>
      </> : <p>Вопрос для этого знака пока не добавлен.</p>}
    </form>
  </>
}
