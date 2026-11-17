import { useEffect, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import { useMotionValue, useScroll, useSpring, useTransform } from 'motion/react'
import type { MotionStyle, MotionValue } from 'motion/react'
import * as m from 'motion/react-m'
import { api } from './api'
import { JourneyTrail } from './journey-trail'
import { Mascot } from './mascot'
import type { MascotMood } from './mascot'
import { useMotionSettings } from './motion-settings'
import { livelySpring, Reveal, sceneEase, spring, useScrollEntrance } from './motion-ui'
import { Link } from './navigation'
import { articleDate } from './news-data'
import type { ArticleCard } from './news-data'
import { ButtonLink, Character } from './ui'
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

const cameraSpring = { stiffness: 170, damping: 24, mass: .65, restDelta: .0007, restSpeed: .005 }

function smoothRange(value: number, start: number, end: number) {
  const fraction = Math.max(0, Math.min(1, (value - start) / (end - start)))
  return fraction * fraction * (3 - 2 * fraction)
}

function CityScene({ progress, enabled }: { progress: MotionValue<number>; enabled: boolean }) {
  const approach = useTransform(progress, value => smoothRange(value, .24, 1))
  const depth = useTransform(progress, value => smoothRange(value, 0, .8))
  const skyScale = useTransform(depth, [0, 1], [1, 1.06])
  const buildingScale = useTransform(depth, [0, 1], [1, 1.12])
  const roadScale = useTransform(depth, [0, 1], [1, 1.19])
  const actorScale = useTransform(() => 1 + .09 * depth.get() - .28 * approach.get())
  const greetingOpacity = useTransform(progress, value => 1 - smoothRange(value, .21, .53))
  const pitch = useMotionValue(0)
  const yaw = useMotionValue(0)
  const tiltX = useSpring(pitch, spring)
  const tiltY = useSpring(yaw, spring)
  const rotateX = useTransform(() => tiltX.get() * (1 - smoothRange(progress.get(), 0, .31)))
  const rotateY = useTransform(() => tiltY.get() * (1 - smoothRange(progress.get(), 0, .31)))

  function tilt(event: PointerEvent<HTMLDivElement>) {
    if (!enabled || event.pointerType !== 'mouse' || progress.get() >= .31) return
    const bounds = event.currentTarget.getBoundingClientRect()
    pitch.set((.5 - (event.clientY - bounds.top) / bounds.height) * 7)
    yaw.set(((event.clientX - bounds.left) / bounds.width - .5) * 10)
  }

  return <div className="home-scene" onPointerMove={tilt} onPointerLeave={() => { pitch.set(0); yaw.set(0) }}>
    <m.div className="home-scene-camera" style={enabled ? { '--approach': approach } as MotionStyle : undefined}>
      <m.div className="home-scene-plane" style={enabled ? { rotateX, rotateY } : undefined}>
        <m.img className="home-city" src={enabled ? '/art/city-sky.webp' : '/art/city.webp'}
          fetchPriority="high" alt="" width="638" height="474" style={enabled ? { scale: skyScale } : undefined} />
        {enabled && <>
          <m.img className="home-buildings" src="/art/city-buildings.webp" alt="" width="638" height="474"
            style={{ scale: buildingScale }} />
          <m.img className="home-road" src="/art/city-road.webp" alt="" width="638" height="474"
            style={{ scale: roadScale }} />
        </>}
        <m.div className="home-scene-actor" style={enabled ? { scale: actorScale } : undefined}>
          <div className="hero-actor-entry"><Mascot mood="wave" priority /></div>
        </m.div>
        <m.p className="home-greeting" style={enabled ? { opacity: greetingOpacity } : undefined}>Привет! Я Штрих.</m.p>
      </m.div>
    </m.div>
  </div>
}

function HomeHero() {
  const travel = useRef<HTMLDivElement>(null)
  const { enabled } = useMotionSettings()
  const { scrollYProgress } = useScroll({ target: travel, offset: ['start start', 'end start'] })
  const cameraTarget = useTransform(scrollYProgress, value => enabled ? value : 0)
  const camera = useSpring(cameraTarget, cameraSpring)
  const trail = useTransform(camera, [0, 1], [.35, 1])
  const copyOpacity = useTransform(camera, value => 1 - smoothRange(value, .35, .77))
  const copyY = useTransform(camera, value => -27 * smoothRange(value, .42, 1))
  const copyPointer = useTransform(camera, value => value < .7 ? 'auto' : 'none')
  return <section className="home-hero" data-motion={enabled ? 'on' : 'off'} aria-labelledby="hero-title">
    <div ref={travel} className="hero-scroll-range" aria-hidden="true" />
    <div className="hero-sticky">
      <div className="content-width">
        <div className="home-hero-grid">
          <m.div className="home-hero-copy" style={enabled ? { opacity: copyOpacity, y: copyY, pointerEvents: copyPointer } : undefined}>
            <h1 id="hero-title">
              <span className="hero-title-line"><span>Скажи «да»</span></span>{' '}
              <span className="hero-title-line"><span>безопасным</span></span>{' '}
              <span className="hero-title-line"><span>дорогам</span></span>
            </h1>
            <p>Штрих покажет дорогу от дома до школы. Узнавай знаки, выбирай, как поступить на улице, и смотри, куда ведёт твой выбор.</p>
            <div className="actions"><ButtonLink to="/safe-route/">Пройти маршрут <span aria-hidden="true">→</span></ButtonLink>
              <ButtonLink to="/practice/" light>В практику</ButtonLink></div>
          </m.div>
          <CityScene progress={camera} enabled={enabled} />
        </div>
        <JourneyTrail landing progress={enabled ? trail : undefined} />
        <m.a className="hero-scroll-link" href="#project" style={enabled ? { opacity: copyOpacity, pointerEvents: copyPointer } : undefined}>
          Дальше по дороге <span aria-hidden="true">↓</span>
        </m.a>
      </div>
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
  const { enabled } = useMotionSettings()
  const visible = useScrollEntrance(stage, enabled, .26)
  const [mood, setMood] = useState<MascotMood>('wave')
  const [reaction, setReaction] = useState(0)
  const [line, setLine] = useState<string>(greeting)
  return <section id="shtrikh" ref={stage} className="home-mascot">
    <m.div className="mascot-curtain" aria-hidden="true" initial={false}
      animate={{ clipPath: visible ? 'inset(0% 0% 0% 0% round 0px)' : 'inset(44% 83% 44% 8% round 50px)' }}
      transition={enabled && visible ? { duration: .72, ease: sceneEase } : { duration: 0 }} />
    <div className="content-width home-mascot-grid">
      <div className="mascot-portrait">
        <m.svg viewBox="0 0 480 340" preserveAspectRatio="none" aria-hidden="true" className="mascot-frame">
          <m.rect x="5" y="5" rx="65" ry="55" width="470" height="330" initial={false}
            animate={{ pathLength: visible ? 1 : 0, opacity: visible ? 1 : 0 }}
            transition={enabled && visible ? { duration: 1, ease: sceneEase } : { duration: 0 }} />
        </m.svg>
        <m.div className="mascot-walk-in" initial={false}
          animate={visible ? { x: '0%', y: '0%', rotate: 0, scale: 1, opacity: 1 }
            : { x: '-57%', y: '20%', rotate: -19, scale: .72, opacity: 0 }}
          transition={enabled && visible ? { ...livelySpring, delay: .18, opacity: { duration: .27, delay: .18 } } : { duration: 0 }}>
          <Mascot mood={mood} reaction={reaction} active={visible} />
        </m.div>
      </div>
      <m.div className="home-mascot-copy" initial={false}
        animate={visible ? { x: 0, opacity: 1 } : { x: 52, opacity: 0 }}
        transition={enabled && visible ? { duration: .58, delay: .16, ease: sceneEase } : { duration: 0 }}>
        <p className="eyebrow">Твой проводник</p>
        <h2>Знакомься, Штрих.</h2>
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
      </m.div>
    </div>
  </section>
}

function Audience() {
  const anchor = useRef<HTMLElement>(null)
  const { enabled } = useMotionSettings()
  const visible = useScrollEntrance(anchor, enabled, .26)
  return <section ref={anchor} className="content-width home-audience" id="audience" aria-labelledby="audience-title">
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
    <section className="content-width home-features" id="project" aria-labelledby="project-title">
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
  const [event, setEvent] = useState<ArticleCard | null>(null)
  useEffect(() => {
    const request = new AbortController()
    api<{ event: ArticleCard | null }>('news/next/', { signal: request.signal })
      .then(result => setEvent(result.event), () => {})
    return () => request.abort()
  }, [])
  if (!event) return null
  return <section className="panel next-event">
    <div><p className="tag">Ближайшее мероприятие</p><h2>{event.title}</h2>
      <p>{articleDate(event)} · {event.event?.venue}</p></div>
    <ButtonLink to={'/news/' + event.slug + '/'}>Об анонсе →</ButtonLink>
  </section>
}
