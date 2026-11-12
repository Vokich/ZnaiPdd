import { useLayoutEffect, useRef } from 'react'
import { Link } from './navigation'
import './road-circuit.css'

const signs = [
  { name: 'Пешеходный переход', icon: 'crossing', tone: 'sky' },
  { name: 'Светофор', icon: 'light', tone: 'blue' },
  { name: 'Повороты', icon: 'turn', tone: 'cream' },
  { name: 'Велосипед', icon: 'bike', tone: 'lavender' },
  { name: 'Остановка', icon: 'bus', tone: 'mint' },
  { name: 'Приоритет', icon: 'priority', tone: 'ice' },
] as const

function RoadGlyph({ icon }: { icon: typeof signs[number]['icon'] }) {
  return <svg viewBox="0 0 96 96" fill="none" aria-hidden="true" stroke="currentColor" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round">
    {icon === 'crossing' && <><path d="M23 31 12 69m24-38-6 38m18-38v38m12-38 6 38m7-38 11 38" strokeWidth="8" /></>}
    {icon === 'light' && <><rect x="30" y="9" width="36" height="78" rx="14" /><circle cx="48" cy="27" r="5" fill="#ff9f98" stroke="none" /><circle cx="48" cy="48" r="5" fill="#ffe192" stroke="none" /><circle cx="48" cy="69" r="5" fill="#a6efd7" stroke="none" /></>}
    {icon === 'turn' && <><path d="M48 80V48c0-10 6-17 18-24l14-8m-22-1h23v24M48 64c0-12-5-19-17-27l-13-8m0 20V28h21" /></>}
    {icon === 'bike' && <><circle cx="24" cy="64" r="15" /><circle cx="72" cy="64" r="15" /><path d="m24 64 17-29 13 29H24m30 0 11-37h10M33 35h13" /></>}
    {icon === 'bus' && <><rect x="23" y="15" width="50" height="62" rx="12" /><path d="M23 46h50M33 77v7m30-7v7M41 25h14" /><circle cx="35" cy="62" r="3" fill="currentColor" stroke="none" /><circle cx="61" cy="62" r="3" fill="currentColor" stroke="none" /></>}
    {icon === 'priority' && <><path d="m48 9 39 39-39 39L9 48 48 9Z" /><path d="m48 24 24 24-24 24-24-24 24-24Z" fill="#ffd16e" stroke="none" /></>}
  </svg>
}

function useRoadLane() {
  const viewportRef = useRef<HTMLDivElement>(null)
  const trackRef = useRef<HTMLDivElement>(null)
  const runRef = useRef<HTMLUListElement>(null)
  const stepRef = useRef<(direction: number) => void>(() => {})

  useLayoutEffect(() => {
    const viewport = viewportRef.current!
    const track = trackRef.current!
    const run = runRef.current!
    const landing = viewport.closest('.landing')!
    const preference = matchMedia('(prefers-reduced-motion: reduce)')
    const supported = typeof IntersectionObserver !== 'undefined' && typeof ResizeObserver !== 'undefined'
    const enabled = (media = preference) => supported && !media.matches
    let width = 0
    let offset = 0
    let impulse = 0
    let visible = false
    let hovered = false
    let frame = 0
    let last = 0
    let drag: { id: number; x: number; time: number; velocity: number; moved: boolean } | undefined

    function paint() {
      if (width > 0) offset = ((offset % width) + width) % width
      track.style.setProperty('--circuit-offset', `${-offset}px`)
    }

    const cruises = () => !hovered && !landing.hasAttribute('data-paused')

    function tick(time: number) {
      frame = 0
      const dt = last ? Math.min(40, time - last) : 0
      last = time
      if (!drag) {
        const delta = impulse * (1 - Math.exp(-dt / 118))
        offset += delta + (cruises() ? dt * .047 : 0)
        impulse = Math.abs(impulse - delta) > .3 ? impulse - delta : 0
      }
      paint()
      schedule()
    }

    function schedule() {
      if (enabled() && visible && !document.hidden && (drag || cruises() || impulse)) {
        if (!frame) frame = requestAnimationFrame(tick)
      } else {
        if (frame) cancelAnimationFrame(frame)
        frame = last = 0
      }
    }

    function measure() {
      const next = run.getBoundingClientRect().width
      if (width && next) offset *= next / width
      width = next
      if (enabled()) paint()
    }

    function sync() {
      if (enabled()) {
        viewport.scrollLeft = 0
        viewport.dataset.drive = ''
      } else {
        delete viewport.dataset.drive
        track.style.removeProperty('--circuit-offset')
        drag = undefined
        impulse = 0
        delete viewport.dataset.dragging
      }
      measure()
      schedule()
    }

    stepRef.current = direction => {
      const cards = run.children
      const pitch = cards[1].getBoundingClientRect().left - cards[0].getBoundingClientRect().left
      if (!enabled(matchMedia(preference.media))) {
        const max = viewport.scrollWidth - viewport.clientWidth
        const next = viewport.scrollLeft + direction * pitch
        viewport.scrollLeft = direction > 0 && viewport.scrollLeft >= max - 1 ? 0 : direction < 0 && viewport.scrollLeft <= 1 ? max : next
        return
      }
      impulse += direction * pitch
      schedule()
    }

    function start(event: PointerEvent) {
      if (!enabled(matchMedia(preference.media)) || !event.isPrimary || event.button !== 0 || drag) return
      impulse = 0
      drag = { id: event.pointerId, x: event.clientX, time: event.timeStamp, velocity: 0, moved: false }
      viewport.setPointerCapture(event.pointerId)
      schedule()
    }

    function move(event: PointerEvent) {
      if (drag?.id !== event.pointerId) return
      const delta = drag.x - event.clientX
      if (!drag.moved && Math.abs(delta) < 4) return
      drag.moved = true
      viewport.dataset.dragging = ''
      const dt = Math.max(8, event.timeStamp - drag.time)
      drag.velocity = delta / dt * .7 + drag.velocity * .3
      drag.x = event.clientX
      drag.time = event.timeStamp
      offset += delta
      schedule()
    }

    function end(event: PointerEvent) {
      if (drag?.id !== event.pointerId) return
      if (event.type === 'pointerup' && drag.moved && event.timeStamp - drag.time < 110) impulse = Math.max(-220, Math.min(220, drag.velocity * 105))
      drag = undefined
      delete viewport.dataset.dragging
      if (viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId)
      if (enabled()) paint()
      schedule()
    }

    function enter(event: PointerEvent) { if (event.pointerType === 'mouse') { hovered = true; schedule() } }
    function leave(event: PointerEvent) { if (event.pointerType === 'mouse') { hovered = false; schedule() } }

    const intersection = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; schedule() }) : null
    const resize = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : null
    const pause = new MutationObserver(schedule)
    intersection?.observe(viewport)
    resize?.observe(run)
    pause.observe(landing, { attributes: true, attributeFilter: ['data-paused'] })
    viewport.addEventListener('pointerdown', start)
    viewport.addEventListener('pointermove', move)
    viewport.addEventListener('pointerup', end)
    viewport.addEventListener('pointercancel', end)
    viewport.addEventListener('lostpointercapture', end)
    viewport.addEventListener('pointerenter', enter)
    viewport.addEventListener('pointerleave', leave)
    document.addEventListener('visibilitychange', schedule)
    preference.addEventListener('change', sync)
    sync()

    return () => {
      cancelAnimationFrame(frame)
      intersection?.disconnect()
      resize?.disconnect()
      pause.disconnect()
      viewport.removeEventListener('pointerdown', start)
      viewport.removeEventListener('pointermove', move)
      viewport.removeEventListener('pointerup', end)
      viewport.removeEventListener('pointercancel', end)
      viewport.removeEventListener('lostpointercapture', end)
      viewport.removeEventListener('pointerenter', enter)
      viewport.removeEventListener('pointerleave', leave)
      document.removeEventListener('visibilitychange', schedule)
      preference.removeEventListener('change', sync)
    }
  }, [])

  return { viewportRef, trackRef, runRef, step: (direction: number) => stepRef.current(direction) }
}

const ticker = ['Смотри по сторонам', 'Знай ПДД', 'Двигайся уверенно']

export function RoadCircuit({ paused, toggle }: { paused: boolean; toggle: () => void }) {
  const { viewportRef, trackRef, runRef, step } = useRoadLane()
  return <section className="road-circuit" id="road-circuit" aria-labelledby="road-circuit-title">
    <div className="circuit-head">
      <div data-scroll-reveal="card">
        <p className="circuit-kicker">ЗНАЙ ПДД <span /> ДОРОЖНЫЙ МАРШРУТ</p>
        <h2 id="road-circuit-title">Дорога в<br /><em>движении.</em></h2>
      </div>
      <div className="circuit-intro" data-scroll-reveal="quiet">
        <p>Листай карточки, узнавай знакомые ситуации и открывай каталог дорожных знаков.</p>
        <Link className="circuit-link" to="/signs/all/">Смотреть все знаки <span aria-hidden="true">↗</span></Link>
      </div>
    </div>
    <div className="circuit-tools" data-scroll-reveal="quiet">
      <p>01—06 <span /> Дорожные ситуации</p>
      <div className="circuit-controls" aria-label="Управление лентами">
        <button type="button" className="circuit-control" aria-label="Прокрутить карточки влево" aria-controls="circuit-lane" onClick={() => step(-1)}>←</button>
        <button type="button" className="circuit-control" aria-label="Прокрутить карточки вправо" aria-controls="circuit-lane" onClick={() => step(1)}>→</button>
        <button type="button" className="circuit-control circuit-play" aria-label={paused ? 'Запустить дорожные ленты' : 'Остановить дорожные ленты'} onClick={toggle}><span aria-hidden="true" /></button>
      </div>
    </div>
    <div className="circuit-lane" id="circuit-lane" ref={viewportRef}>
      <div className="circuit-track" ref={trackRef}>
        {[0, 1].map(copy => <ul className="circuit-run" ref={copy ? undefined : runRef} key={copy} aria-hidden={copy ? true : undefined}>
          {signs.map(({ name, icon, tone }, index) => <li key={icon} className={`circuit-card circuit-${tone}`}>
            <span className="circuit-index" aria-hidden="true">0{index + 1}</span>
            <div className="circuit-glyph"><RoadGlyph icon={icon} /></div>
            <span className="circuit-card-title">{name}</span>
          </li>)}
        </ul>)}
      </div>
    </div>
    <div className="circuit-ticker" data-loop="" aria-hidden="true">
      <div className="circuit-ticker-track">
        {[0, 1].map(copy => <div key={copy} className="circuit-ticker-run">
          {[...ticker, ...ticker, ...ticker].map((word, index) => <span key={index}>{word}<b>✦</b></span>)}
        </div>)}
      </div>
    </div>
  </section>
}
