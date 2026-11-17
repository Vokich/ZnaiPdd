import { useSearchParams } from 'react-router-dom'
import { Link, useSharedArt } from './navigation'
import { useResource } from './state'
import { Loading, LoadError, MediaGallery, PortalHeading } from './ui'
import { Reveal } from './motion-ui'
import './learning.css'

import { articleDate, formatEvent } from './news-data'
import type { Article, ArticleCard, Feed } from './news-data'

function PublicationCover({ post, detail = false }: { post: ArticleCard; detail?: boolean }) {
  const style = useSharedArt(detail ? '/news/' : '/news/' + post.slug + '/', 'story', post.slug)
  return <div className={`publication-cover shared-art${post.cover ? ' has-cover' : ''}`} style={style}>
    <img src={post.cover || '/art/news-ticket.webp'} alt="" loading={detail ? 'eager' : 'lazy'} />
  </div>
}

export function NewsPage() {
  const { data, error, retry } = useResource<Feed>()
  const [filters] = useSearchParams()
  const tab = filters.get('tab') ?? ''
  function href(section: string, page = 1) {
    const query = new URLSearchParams()
    if (section) query.set('tab', section)
    if (page > 1) query.set('page', String(page))
    return '/news/' + (query.size ? '?' + query.toString() : '')
  }
  return <>
    <PortalHeading title="Новости и мероприятия">Новые занятия и события «Знай ПДД».</PortalHeading>
    <nav className="filters" aria-label="Публикации">
      {[['', 'Все публикации'], ['upcoming', 'Предстоящие'], ['archive', 'Архив мероприятий']].map(([key, label]) =>
        <Link key={key} to={href(key)} aria-current={tab === key ? 'page' : undefined}>{label}</Link>)}
    </nav>
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <>
      {data.items.length ? <div className="news-grid">{data.items.map(post =>
        <Reveal key={post.slug}><Link to={'/news/' + post.slug + '/'} className="panel publication-card">
          <PublicationCover post={post} />
          <div className="publication-card-copy">
            <small>{post.kind_label} · {articleDate(post)}</small>
            <h2>{post.title}</h2>
            {post.event?.cancelled && <span className="tag tag-muted">Отменено</span>}
            {post.event?.past && !post.event.cancelled && <span className="tag tag-muted">Прошло</span>}
            <p>{post.summary}</p>
            <span className="text-link">Читать {post.event ? 'анонс' : 'новость'} →</span>
          </div>
        </Link></Reveal>)}</div> : <p className="panel">Здесь пока нет публикаций.</p>}
      {data.pages > 1 && <nav aria-label="Страницы" className="learning-links">
        {data.page > 1 && <Link to={href(tab, data.page - 1)}>← Назад</Link>}
        <span>Страница {data.page} из {data.pages}</span>
        {data.page < data.pages && <Link to={href(tab, data.page + 1)}>Вперёд →</Link>}
      </nav>}
    </>}
  </>
}

export function NewsPostPage() {
  const { data, error, retry } = useResource<Article>()
  return <>
    <Link className="text-link" to="/news/">← К новостям</Link>
    {error ? <LoadError error={error} retry={retry} /> : !data ? <Loading /> : <>
      <PortalHeading title={data.title}>{data.kind_label} · {articleDate(data)}</PortalHeading>
      <article className="panel publication">
        <figure className="publication-lead">
          <PublicationCover post={data} detail />
          {data.cover_credit && <figcaption>{data.cover_credit}</figcaption>}
        </figure>
        <p className="publication-summary">{data.summary}</p>
        {data.event && <section aria-label="О мероприятии">
          {data.event.cancelled && <p className="feedback">Мероприятие отменено.</p>}
          {data.event.past && !data.event.cancelled && <p className="tag tag-muted">Мероприятие прошло</p>}
          <dl className="event-details">
            <div><dt>Место</dt><dd>{data.event.venue}</dd></div>
            <div><dt>Для кого</dt><dd>{data.event.audience}</dd></div>
            <div><dt>Организатор</dt><dd>{data.event.organizer}</dd></div>
            {data.event.registration_deadline && <div><dt>Регистрация до</dt>
              <dd>{formatEvent(data.event.registration_deadline, data.event)} · {data.event.timezone_label}</dd></div>}
          </dl>
          {data.registration_url && <a className="button" href={data.registration_url} target="_blank" rel="noopener noreferrer">
            Регистрация на внешней площадке ↗
          </a>}
        </section>}
        <div className="publication-body">{data.body}</div>
        <MediaGallery images={data.images} />
        {(data.signs.length > 0 || data.exercises.length > 0) && <section>
          <h2>Связанные материалы</h2>
          <ul>
            {data.signs.map(sign => <li key={sign.slug}><Link className="text-link" to={'/signs/' + sign.slug + '/'}>{sign.number} · {sign.name}</Link></li>)}
            {data.exercises.map(item => <li key={item.slug}><Link className="text-link" to={'/practice/' + item.slug + '/'}>{item.title}</Link></li>)}
          </ul>
        </section>}
      </article>
    </>}
  </>
}
