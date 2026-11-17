import { useRef } from 'react'
import { useInView } from 'motion/react'
import * as m from 'motion/react-m'
import { useMotionSettings } from './motion-settings'

export type MascotMood = 'idle' | 'wave' | 'sign' | 'hint' | 'success' | 'retry' | 'high-five'
const still = { x: '0%', y: '0%', scaleX: 1, scaleY: 1, rotate: 0 }
const reactions = {
  idle: still,
  wave: { ...still, x: ['0%', '2%', '0%', '-3%', '1%', '0%'], rotate: [0, -4, 5, -4, 2, 0] },
  sign: { ...still, x: ['0%', '-5%', '2%', '1%', '0%'], rotate: [0, -6, 8, 4, 0] },
  hint: { ...still, x: ['0%', '-3%', '-3%', '0%'], rotate: [0, -6, -6, 0] },
  success: {
    ...still, y: ['0%', '3%', '-22%', '1%', '-12%', '0%'],
    scaleX: [1, 1.12, .95, 1.08, .98, 1], scaleY: [1, .86, 1.12, .91, 1.05, 1],
    rotate: [0, -4, 9, -5, 5, 0],
  },
  retry: { ...still, rotate: [0, -12, 8, -5, 0], y: ['0%', '5%', '2%', '1%', '0%'], scaleY: [1, .9, .96, 1, 1] },
  'high-five': {
    ...still, x: ['0%', '6%', '-11%', '-8%', '0%'],
    y: ['0%', '3%', '-12%', '-7%', '0%'], rotate: [0, -9, 13, 6, 0], scaleY: [1, .88, 1.16, 1.06, 1],
  },
}
const durations = { idle: 0, wave: 1.06, sign: 1.05, hint: 1, success: 1.15, retry: .74, 'high-five': 1.08 }
const eyeSize = { idle: 1, wave: 1, sign: .94, hint: .64, success: .32, retry: .72, 'high-five': .34 }
const waveArm = [0, 13, -28, 17, -21, 11, 0]
const stillLimb = { x: '0%', y: '0%', rotate: 0, scale: 1 }
const highFiveArm = { ...stillLimb, rotate: [0, 15, -22, -8, 0], scale: [1, .99, 1.33, 1.15, 1] }
const highFiveTiming = { duration: 1.02, times: [0, .2, .46, .64, 1] }

export function Mascot({ mood = 'idle', reaction = 0, className = '', priority = false, active = true }: {
  mood?: MascotMood; reaction?: number; className?: string; priority?: boolean; active?: boolean
}) {
  const anchor = useRef<HTMLSpanElement>(null)
  const visible = useInView(anchor)
  const { enabled } = useMotionSettings()
  const moving = enabled && visible && active
  const blinking = moving && (mood === 'idle' || mood === 'wave')
  const wave = moving && mood === 'wave'
  const highFive = moving && mood === 'high-five'
  const sign = moving && mood === 'sign'
  const loading = priority ? 'eager' : 'lazy'
  return <span ref={anchor} className={`mascot ${className}`} aria-hidden="true" data-mood={mood}>
    <m.span className="mascot-shadow" key={'shadow-' + reaction} initial={false}
      animate={{ scale: moving && (mood === 'success' || highFive) ? [1, 1.13, .52, 1.1, .76, 1] : 1 }}
      transition={{ duration: moving ? durations[mood] : 0 }} />
    <m.span className="mascot-figure" key={reaction} initial={false}
      animate={moving ? reactions[mood] : still}
      transition={{ duration: moving ? durations[mood] : 0 }}>
      <m.img className="mascot-limb mascot-wave" src="/art/shtrikh-wave.webp" alt="" draggable={false}
        loading={loading} animate={wave ? { ...stillLimb, rotate: waveArm } : highFive
          ? { ...highFiveArm, opacity: [1, 1, 0, 0, 1] } : { ...stillLimb, opacity: 1 }}
        transition={highFive ? highFiveTiming : { duration: moving ? durations[mood] : 0 }} />
      {highFive && <m.img className="mascot-limb mascot-wave mascot-sleeve" src="/art/shtrikh-wave.webp" alt=""
        initial={{ opacity: 0 }} animate={{ ...highFiveArm, opacity: [0, 0, 1, 1, 0] }} transition={highFiveTiming} />}
      <m.img className="mascot-limb mascot-sign" src="/art/shtrikh-sign.webp" alt="" draggable={false}
        loading={loading} animate={sign ? {
          x: ['0%', '0%', '5%', '3%', '0%'], y: ['0%', '2%', '-9%', '-4%', '0%'],
          rotate: [0, 8, -24, -17, 0], scale: [1, .96, 1.34, 1.22, 1],
        } : stillLimb} transition={{ duration: moving ? durations[mood] : 0 }} />
      <img className="mascot-body" src="/art/shtrikh.webp" alt="" draggable={false}
        loading={loading} width="230" height="263" />
      <m.span className="mascot-head" initial={false} animate={{
        rotate: moving && mood === 'hint' ? [0, -17, -14, 0] : sign ? [0, 5, 13, 6, 0] : 0,
        y: moving && mood === 'hint' ? ['0%', '2%', '2%', '0%'] : '0%',
      }} transition={{ duration: moving ? durations[mood] : 0 }}>
        <img src="/art/shtrikh-head.webp" alt="" draggable={false} loading={loading} width="230" height="263" />
        {['left', 'right'].map(eye => <m.i key={eye} className={`mascot-eye eye-${eye}`}
          animate={{ scaleY: blinking ? [1, 1, .1, 1, 1] : eyeSize[mood] }}
          transition={blinking ? { duration: 4.8, times: [0, .74, .76, .79, 1], repeat: Infinity } : { duration: moving ? .16 : 0 }} />)}
        <span className="mascot-mouth" />
      </m.span>
    </m.span>
    {highFive && <m.img className="mascot-glove" key={'glove-' + reaction} src="/art/shtrikh-glove.webp" alt=""
      initial={{ opacity: 0, scale: .65, x: '30%', y: '35%', rotate: -25 }}
      animate={{ opacity: [0, 0, 1, 1, 0], scale: [.65, .8, 2.35, 1.7, .74],
        x: ['30%', '20%', '-172%', '-119%', '30%'], y: ['35%', '20%', '-38%', '-22%', '35%'], rotate: [-25, -10, 19, 14, -25] }}
      transition={highFiveTiming} />}
    {(mood === 'success' || highFive) && <m.span className="mascot-sparkles" key={'stars-' + reaction}
      initial={moving ? { scale: .48, opacity: 0 } : false}
      animate={moving ? { scale: [.48, 1.5, 1.15, 1.64], opacity: [0, 1, .9, 0] } : { scale: 1, opacity: 1 }}
      transition={{ duration: moving ? 1.02 : 0, delay: moving ? .16 : 0 }}>✦<span>✧</span><span>✦</span></m.span>}
  </span>
}
