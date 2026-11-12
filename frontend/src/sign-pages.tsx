import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useParams, useSearchParams } from 'react-router-dom'
import { Link, useNavigate } from './navigation'
import { api } from './api'
import type { Sign, SignCatalog, SignTest } from './api'
import { useResource } from './state'
import { ButtonLink, Feedback, FieldErrors, Loading, LoadError, PortalHeading } from './ui'

export function SignsHomePage() {
  const { data, error, retry } = useResource<SignCatalog>()
  return <>
    <PortalHeading title="Знаки ПДД">Научись узнавать дорожные знаки и собери свою коллекцию.</PortalHeading>
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <section className="panel sign-overview">
      <div className="welcome-badge" aria-hidden="true"><div><span /></div></div>
      <div><h2>Моя коллекция</h2><p>Открыто {data.unlocked_count} из {data.total}</p>
        <progress aria-label="Прогресс коллекции" value={data.unlocked_count} max={data.total || 1} />
        <ButtonLink to="/signs/all/">Посмотреть все знаки →</ButtonLink>
      </div>
    </section>}
  </>
}

export function SignsListPage() {
  const [search] = useSearchParams()
  const category = search.get('category') ?? ''
  const { data, error, retry } = useResource<SignCatalog>()
  return <>
    <Link className="text-link" to="/signs/">← К коллекции</Link>
    <PortalHeading title="Все знаки ПДД" />
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <>
      <nav className="filters" aria-label="Категории знаков">
        {[{ value: '', label: 'Все' }, ...data.categories].map(({ value, label }) => <Link key={value}
          to={value ? '?category=' + encodeURIComponent(value) : '/signs/all/'}
          viewTransition={false} preventScrollReset
          aria-current={value === category ? 'true' : undefined}>{label}</Link>)}
      </nav>
      {data.signs.length ? <div className="sign-grid catalog-results" key={category}>
        {data.signs.map(sign => <Link to={`/signs/${sign.slug}/`} key={sign.slug} className="panel sign-card" data-scroll-reveal="card">
          <SignImage sign={sign} /><small>{sign.category_label}</small>
          <h2>{sign.name ?? 'Неизвестный знак'}</h2><span className={sign.unlocked ? 'tag' : 'tag tag-muted'}>{sign.unlocked ? 'Открыт' : 'Закрыт'}</span>
        </Link>)}
      </div> : <div className="panel status-panel" key={category}>В этой категории пока нет знаков.</div>}
    </>}
  </>
}

function SignImage({ sign }: { sign: Sign }) {
  return <div className="sign-image">
    {sign.image ? <img src={sign.image} alt={sign.name ?? ''} /> : <span aria-hidden="true">?</span>}
  </div>
}

export function SignDetailPage() {
  const { data: sign, error, retry } = useResource<Sign>()
  if (error) return <LoadError error={error} retry={retry} />
  if (!sign) return <Loading />
  return <>
    <Link className="text-link" to="/signs/all/">← Ко всем знакам</Link>
    <PortalHeading title={sign.name ?? 'Неизвестный знак'}>{sign.category_label}</PortalHeading>
    <article className="panel sign-overview">
      <SignImage sign={sign} />
      {sign.unlocked ? <div>
        <h2>Описание</h2><p>{sign.description || 'Описание пока добавляется.'}</p>
        {sign.fun_fact && <><h2 data-scroll-reveal="quiet">Интересный факт</h2><p data-scroll-reveal="quiet">{sign.fun_fact}</p></>}
      </div> : <div><h2>Открой этот знак</h2><p>Ответь на вопрос, чтобы узнать его название и значение.</p><ButtonLink to={`/signs/${sign.slug}/test/`}>Пройти мини-тест →</ButtonLink></div>}
    </article>
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
    } catch (error) { setError(error) }
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
        <div role="alert"><FieldErrors error={error} name="answer" /></div>
        <Feedback error={error} />
        <div className="actions" data-scroll-reveal="quiet"><button className="button" disabled={pending}>Проверить ответ →</button></div>
      </> : <p>Вопрос для этого знака пока не добавлен.</p>}
    </form>
  </>
}
