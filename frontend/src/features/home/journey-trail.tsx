import type { MotionValue } from 'motion/react'
import * as m from 'motion/react-m'
import { useSharedArt } from '../../shared/navigation'

export function JourneyTrail({ landing = false, progress }: { landing?: boolean; progress?: MotionValue<number> }) {
  const style = useSharedArt(landing ? '/safe-route/' : '/', 'route-trail')
  return <div className={`journey-trail shared-art${landing ? ' home-trail' : ''}`} style={style}>
    <svg viewBox="0 0 720 48" preserveAspectRatio="none" aria-hidden="true">
      <path className="journey-track" d="M8 33H182C224 33 228 12 271 12h178c43 0 47 21 89 21h174" />
      <m.path className="journey-path" d="M8 33H182C224 33 228 12 271 12h178c43 0 47 21 89 21h174"
        style={progress ? { pathLength: progress } : undefined} />
    </svg>
    <ol className="journey-stops" aria-label="Путь от дома до школы"><li>Дом</li><li>Пешеходный переход</li><li>Школа</li></ol>
  </div>
}
