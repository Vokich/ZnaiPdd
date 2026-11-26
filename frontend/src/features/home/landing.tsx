import { useEffect, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import { useScroll, useSpring, useTransform } from 'motion/react'
import type { MotionValue } from 'motion/react'
import * as m from 'motion/react-m'
import { api } from '../../shared/api'
import { JourneyTrail } from './journey-trail'
import { Mascot } from '../../shared/mascot'
import type { MascotMood } from '../../shared/mascot'
import { useMotionSettings } from '../../shared/motion/motion-settings'
import { livelySpring, Reveal, sceneEase, spring, useScrollEntrance } from '../../shared/motion/motion-ui'
import { Link } from '../../shared/navigation'
import { articleDate } from '../news/news-data'
import type { ArticleCard } from '../news/news-data'
import { ButtonLink, Character } from '../../shared/ui'
import './home.css'

const features = [
  { to: '/signs/', icon: 'crossing', title: 'Знаки', text: 'Узнай знаки, которые встречаются по пути в школу.', from: 'left' },
  { to: '/practice/', icon: 'practice', title: 'Практика', text: 'Собери действия по порядку и проверь свой ответ.', from: 'up' },
  { to: '/safe-route/', icon: 'map', title: 'Маршрут', text: 'Пройди от дома до школы и выбери безопасный путь.', from: 'right' },
] as const

const audiences = [
  {
    role: 'student', title: 'Детям и подросткам',
    text: 'Попробуй пройти свой первый маршрут. На каждой остановке можно осмотреться и выбрать ответ.',
    to: '/safe-route/', action: 'Начать маршрут', from: 'left',
  },
  {
    role: 'teacher', title: 'Педагогам',
    text: 'Откройте на уроке одну ситуацию. Поставьте сцену на паузу и обсудите с классом каждое действие.',
    to: '/practice/', action: 'Выбрать задание', from: 'right',
  },
] as const

const greeting = 'Привет! Я Штрих. Пройдём от дома до школы вместе?'
const mascotActions = [
  { mood: 'wave', label: 'Помахать', line: greeting },
  { mood: 'sign', label: 'Посмотреть знак', line: 'Это знак пешеходного перехода. Он подсказывает, где можно перейти дорогу.' },
  { mood: 'high-five', label: 'Дать пять', line: 'Дай пять! Увидимся на маршруте.' },
] as const

function CityScene({ progress, enabled }: { progress: MotionValue<number>; enabled: boolean }) {
  const scene = useRef<HTMLDivElement>(null)
  const visible = useScrollEntrance(scene, enabled)
  const rotateX = useSpring(0, spring)
  const rotateY = useSpring(0, spring)
  const cameraZoom = useTransform(progress, [0, 1], [1, 1.18])
  const sky = useTransform(progress, [0, 1], ['scale(1)', 'scale(1.07)'])
  const buildings = useTransform(progress, [0, 1], ['translateY(0%) scale(1)', 'translateY(2%) scale(1.12)'])
  const road = useTransform(progress, [0, 1], ['scale(1)', 'scale(1.25)'])
  const actor = useTransform(progress, [0, 1], ['translateX(0%) scale(1)', 'translateX(-8%) scale(1.32)'])
  const greetingOpacity = useTransform(progress, [.3, .85], [1, 0])

  function tilt(event: PointerEvent<HTMLDivElement>) {
    if (!enabled || event.pointerType !== 'mouse') return
    const bounds = event.currentTarget.getBoundingClientRect()
    rotateX.set((.5 - (event.clientY - bounds.top) / bounds.height) * 7)
    rotateY.set(((event.clientX - bounds.left) / bounds.width - .5) * 10)
  }

  return <div ref={scene} className="home-scene" data-entered={enabled && visible || undefined}
    onPointerMove={tilt} onPointerLeave={() => { rotateX.set(0); rotateY.set(0) }}>
    <m.div className="home-scene-plane" style={enabled ? { rotateX, rotateY, scale: cameraZoom } : undefined}>
      <m.img className="home-city" src={enabled ? '/art/city-sky.webp' : '/art/city.webp'}
        fetchPriority="high" alt="" width="638" height="474" style={enabled ? { transform: sky } : undefined} />
      {enabled && <>
        <m.img className="home-buildings" src="/art/city-buildings.webp" alt="" width="638" height="474" style={{ transform: buildings }} />
        <m.img className="home-road" src="/art/city-road.webp" alt="" width="638" height="474" style={{ transform: road }} />
      </>}
      <m.div className="home-scene-actor" style={enabled ? { transform: actor } : undefined}>
        <div className="hero-actor-entry"><Mascot mood="wave" priority /></div>
      </m.div>
      <m.p className="home-greeting" style={enabled ? { opacity: greetingOpacity } : undefined}>Привет! Я Штрих.</m.p>
    </m.div>
  </div>
}

function HomeHero() {
  const hero = useRef<HTMLElement>(null)
  const { enabled } = useMotionSettings()
  const copy = useRef<HTMLDivElement>(null)
  const visible = useScrollEntrance(copy, enabled)
  const { scrollYProgress } = useScroll({ target: hero, offset: ['start start', 'end start'] })
  const trail = useTransform(scrollYProgress, [0, .85], [.35, 1])
  const titleOpacity = useTransform(scrollYProgress, [.35, .85], [1, .3])
  return <section ref={hero} className="home-hero" aria-labelledby="hero-title">
    <div className="content-width">
      <div className="home-hero-grid">
        <div ref={copy} className="home-hero-copy" data-entered={enabled && visible || undefined}>
          <m.h1 id="hero-title" style={enabled ? { opacity: titleOpacity } : undefined}>
            <span className="hero-title-line"><span>Скажи «да»</span></span>{' '}
            <span className="hero-title-line"><span>безопасным</span></span>{' '}
            <span className="hero-title-line"><span>дорогам</span></span>
          </m.h1>
          <p>Штрих покажет дорогу от дома до школы. Узнавай знаки, выбирай, как поступить на улице, и смотри, куда ведёт твой выбор.</p>
          <div className="actions"><ButtonLink to="/safe-route/" viewTransition>Пройти маршрут <span aria-hidden="true">→</span></ButtonLink>
            <ButtonLink to="/practice/" light>В практику</ButtonLink></div>
        </div>
        <CityScene progress={scrollYProgress} enabled={enabled} />
      </div>
      <JourneyTrail landing progress={enabled ? trail : undefined} />
      <Link className="hero-scroll-link" to="#project">
        Дальше по дороге <span aria-hidden="true">↓</span>
      </Link>
    </div>
  </section>
}

function FeatureArt({ icon }: { icon: (typeof features)[number]['icon'] }) {
  if (icon === 'practice') return <span className="feature-art" aria-hidden="true">
    <m.img src="/art/practice-back.webp" alt="" variants={{ rest: { x: 0, rotate: 0 }, hover: { x: -13, y: -5, rotate: -14 } }} transition={livelySpring} />
    <m.img src="/art/practice-front.webp" alt="" variants={{ rest: { x: 0, y: 0, rotate: 0 }, hover: { x: 12, y: 5, rotate: 12 } }} transition={livelySpring} />
  </span>
  if (icon === 'map') return <span className="feature-art" aria-hidden="true">
    <m.img src="/art/map.webp" alt="" variants={{ rest: { rotate: 0 }, hover: { rotate: -5 } }} transition={livelySpring} />
    <m.svg viewBox="0 0 114 77" aria-hidden="true" variants={{ rest: { rotate: 0 }, hover: { rotate: -5 } }} transition={livelySpring}>
      <m.path d="M22 58 40 42 70 50 87 25" fill="none" stroke="#fff" strokeWidth="3.5" strokeLinecap="round"
        variants={{ rest: { pathLength: 0, opacity: 0 }, hover: { pathLength: 1, opacity: 1 } }} transition={{ duration: .56, ease: sceneEase }} />
    </m.svg>
  </span>
  return <span className="feature-art" aria-hidden="true"><m.img src="/art/crossing.webp" alt=""
    variants={{ rest: { rotate: 0, scale: 1 }, hover: { rotate: -17, scale: 1.18 } }} transition={livelySpring} /></span>
}

function MeetMascot() {
  const stage = useRef<HTMLElement>(null)
  const portrait = useRef<HTMLDivElement>(null)
  const { enabled } = useMotionSettings()
  const visible = useScrollEntrance(stage, enabled)
  const portraitVisible = useScrollEntrance(portrait, enabled)
  const [mood, setMood] = useState<MascotMood>('wave')
  const [reaction, setReaction] = useState(0)
  const [line, setLine] = useState<string>(greeting)
  return <section id="shtrikh" ref={stage} className="home-mascot" tabIndex={-1} aria-labelledby="mascot-title">
    <m.div className="mascot-curtain" aria-hidden="true" initial={false}
      animate={{ clipPath: visible ? 'inset(0% 0% 0% 0% round 0px)' : 'inset(44% 83% 44% 8% round 50px)' }}
      transition={enabled && visible ? { duration: .72, ease: sceneEase } : { duration: 0 }} />
    <div className="content-width home-mascot-grid">
      <div ref={portrait} className="mascot-portrait">
        <m.svg viewBox="0 0 480 340" preserveAspectRatio="none" aria-hidden="true" className="mascot-frame">
          <m.rect x="5" y="5" rx="65" ry="55" width="470" height="330" initial={false}
            animate={{ pathLength: portraitVisible ? 1 : 0, opacity: portraitVisible ? 1 : 0 }}
            transition={enabled && portraitVisible ? { duration: 1, ease: sceneEase } : { duration: 0 }} />
        </m.svg>
        <m.div className="mascot-walk-in" initial={false}
          animate={portraitVisible ? { x: '0%', y: '0%', rotate: 0, scale: 1, opacity: 1 }
            : { x: '-85%', y: '28%', rotate: -25, scale: .58, opacity: 0 }}
          transition={enabled && portraitVisible ? { type: 'spring', duration: .85, bounce: .42, opacity: { duration: .23 } } : { duration: 0 }}>
          <Mascot mood={mood} reaction={reaction} active={portraitVisible} />
        </m.div>
      </div>
      <Reveal from="right" className="home-mascot-copy">
        <p className="eyebrow">Твой проводник</p>
        <h2 id="mascot-title">Знакомься, Штрих.</h2>
        <p>У этой зебры есть фуражка, свой знак и время на любой вопрос. В заданиях Штрих поможет заметить то, что легко пропустить.</p>
        <div className="mascot-message" role="status">
          <m.p key={reaction} initial={enabled ? { opacity: .25, y: 10, scale: .96 } : false}
            animate={{ opacity: 1, y: 0, scale: 1 }} transition={enabled ? livelySpring : { duration: 0 }}>{line}</m.p>
        </div>
        <div className="actions mascot-actions">
          {mascotActions.map(action => <m.button key={action.mood} className="button button-light" type="button"
            whileTap={enabled ? { scale: .9 } : undefined} transition={spring}
            aria-pressed={mood === action.mood} onClick={() => {
              setMood(action.mood)
              setLine(action.line)
              setReaction(value => value + 1)
            }}>{action.label}</m.button>)}
        </div>
      </Reveal>
    </div>
  </section>
}

function Audience() {
  const anchor = useRef<HTMLElement>(null)
  const { enabled } = useMotionSettings()
  const visible = useScrollEntrance(anchor, enabled)
  return <section ref={anchor} className="content-width home-audience" id="audience" tabIndex={-1} aria-labelledby="audience-title">
    <Reveal from="up"><h2 id="audience-title">Для кого этот сайт?</h2></Reveal>
    <div className="audience-grid">
      {audiences.map(({ title, text, role, to, action, from }) => <Reveal key={role} from={from} className={`audience-${role}`}>
        <article className="home-audience-card">
          <div><h3>{title}</h3><p>{text}</p><Link className="text-link" to={to}>{action} →</Link></div>
          <Character role={role} />
        </article>
      </Reveal>)}
    </div>
    <svg className="audience-trail" viewBox="0 0 560 56" preserveAspectRatio="none" aria-hidden="true">
      <path d="M5 15h163c42 0 43 24 84 24h53c41 0 44-24 86-24h164" className="journey-track" />
      <m.path d="M5 15h163c42 0 43 24 84 24h53c41 0 44-24 86-24h164" className="journey-path" initial={false}
        animate={{ pathLength: visible || !enabled ? 1 : 0 }}
        transition={enabled && visible ? { delay: .18, duration: 1, ease: sceneEase } : { duration: 0 }} />
    </svg>
  </section>
}

export function HomePage() {
  const { enabled } = useMotionSettings()
  return <div className="landing">
    <HomeHero />
    <section className="content-width home-features" id="project" tabIndex={-1} aria-labelledby="project-title">
      <Reveal className="home-feature-heading" from="up">
        <p className="eyebrow">О проекте</p>
        <h2 id="project-title">Дорога знакомая.<br />А ситуации разные.</h2>
        <p>На «Знай ПДД» можно остановить движение, рассмотреть знак и попробовать снова.</p>
      </Reveal>
      <div className="home-feature-grid">{features.map((feature, index) => <Reveal key={feature.to} from={feature.from} delay={index * .11}>
        <m.div className={`home-feature home-feature-${feature.icon}`} initial={false} animate="rest"
          whileHover={enabled ? 'hover' : undefined} whileTap={enabled ? { scale: .96 } : undefined}
          variants={{ rest: { y: 0 }, hover: { y: -10 } }} transition={spring}>
          <Link to={feature.to}>
            <FeatureArt icon={feature.icon} />
            <span className="feature-arrow" aria-hidden="true">↗</span>
            <h3>{feature.title}</h3><p>{feature.text}</p>
          </Link>
        </m.div>
      </Reveal>)}</div>
    </section>
    <MeetMascot />
    <Audience />
    <NextEvent />
  </div>
}

function NextEvent() {
  const anchor = useRef<HTMLDivElement>(null)
  const [event, setEvent] = useState<ArticleCard | null>(null)
  const [contacts, setContacts] = useState<{ label: string; url: string; direct: boolean }[]>([])
  const [failed, setFailed] = useState(false)
  const [revision, retry] = useState(0)
  useEffect(() => {
    const request = new AbortController()
    function load() {
      setFailed(false)
      api<{ event: ArticleCard | null; contacts: typeof contacts }>('news/next/', { signal: request.signal })
        .then(result => { setEvent(result.event); setContacts(result.contacts) })
        .catch(() => { if (!request.signal.aborted) setFailed(true) })
    }
    const observer = typeof IntersectionObserver === 'undefined' ? null : new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { observer?.disconnect(); load() }
    }, { rootMargin: '450px' })
    if (observer && anchor.current) observer.observe(anchor.current)
    else load()
    return () => { observer?.disconnect(); request.abort() }
  }, [revision])
  return <div ref={anchor} className="content-width home-contact">
    <section className="panel" id="teacher-contact" aria-labelledby="teacher-contact-title">
      <h2 id="teacher-contact-title">Как стать преподавателем</h2>
      <p>Создайте аккаунт и напишите администратору в личные сообщения. Укажите свой логин и название организации.</p>
      <div className="teacher-direct">{contacts.filter(c => c.direct).map(c =>
        <a className="button" key={c.url} href={c.url} target="_blank" rel="noreferrer">{c.label} ↗</a>)}</div>
      <nav className="actions" aria-label="Сообщества проекта">{contacts.filter(c => !c.direct).map(c =>
        <a className="text-link" key={c.url} href={c.url} target="_blank" rel="noreferrer">{c.label} ↗</a>)}</nav>
      {failed && <button className="button button-light" onClick={() => retry(value => value + 1)}>Загрузить контакты ещё раз</button>}
    </section>
    {event && <section className="panel next-event">
      <div><p className="tag">Ближайшее мероприятие</p><h2>{event.title}</h2>
        <p>{articleDate(event)} · {event.event?.venue}</p></div>
      <ButtonLink to={'/news/' + event.slug + '/'}>Об анонсе →</ButtonLink>
    </section>}
  </div>
}
