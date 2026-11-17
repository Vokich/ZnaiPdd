import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode, RefObject } from 'react'
import { useSpring, useTransform } from 'motion/react'
import * as m from 'motion/react-m'
import { useMotionSettings } from './motion-settings'

export const spring = { type: 'spring', stiffness: 360, damping: 28 } as const
export const sceneEase = [0.22, 0.82, 0.24, 1] as const
export const livelySpring = { type: 'spring', duration: .69, bounce: .34 } as const

const revealOffsets = {
  quiet: { opacity: .48, x: 0, y: 18, rotate: 0, scale: 1 },
  left: { opacity: 0, x: -76, y: 24, rotate: -9, scale: .88 },
  right: { opacity: 0, x: 76, y: 24, rotate: 9, scale: .88 },
  up: { opacity: 0, x: 0, y: 84, rotate: 0, scale: .82 },
}
const revealed = { opacity: 1, x: 0, y: 0, rotate: 0, scale: 1 }

export function useScrollEntrance(anchor: RefObject<HTMLElement | null>, enabled: boolean) {
  const canObserve = typeof IntersectionObserver !== 'undefined'
  const [entered, setEntered] = useState(false)
  useEffect(() => {
    const element = anchor.current
    if (!element || !enabled || !canObserve) return
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) {
          setEntered(false)
        } else if (entry.intersectionRatio >= .15) {
          setEntered(true)
        }
      }
    }, { threshold: [0, .15] })
    observer.observe(element)
    return () => observer.disconnect()
  }, [anchor, canObserve, enabled])
  return !enabled || !canObserve || entered
}

export function MotionNumber({ value }: { value: number }) {
  const { enabled } = useMotionSettings()
  const count = useSpring(enabled ? 0 : value, { stiffness: 125, damping: 25 })
  const display = useTransform(count, Math.round)
  useEffect(() => {
    if (enabled) count.set(value)
    else count.jump(value)
  }, [count, enabled, value])
  return <m.span className="motion-number" role="img" aria-label={String(value)}>{enabled ? display : value}</m.span>
}

export function Reveal({ children, className, delay = 0, from = 'quiet' }: {
  children: ReactNode; className?: string; delay?: number; from?: keyof typeof revealOffsets
}) {
  const anchor = useRef<HTMLDivElement>(null)
  const { enabled } = useMotionSettings()
  const visible = useScrollEntrance(anchor, enabled)
  return <div ref={anchor} className={className} data-entered={enabled && visible || undefined}>
    <m.div className="reveal-content" initial={false}
      animate={visible ? revealed : revealOffsets[from]}
      transition={enabled && visible ? from === 'quiet'
        ? { duration: .42, ease: sceneEase, delay }
        : { ...livelySpring, delay, opacity: { duration: .33, delay } }
        : { duration: 0 }}>
      {children}
    </m.div>
  </div>
}

export function FeedbackMotion({ children, success, attempt, className }: {
  children: ReactNode; success: boolean; attempt: number; className?: string
}) {
  const { enabled } = useMotionSettings()
  return <m.div key={attempt} className={className}
    initial={enabled ? { opacity: .28, y: 18, scale: .94 } : false}
    animate={!enabled ? { opacity: 1, y: 0, x: 0, scale: 1 } : success
      ? { opacity: 1, y: 0, scale: 1 }
      : { opacity: 1, y: 0, scale: 1, x: [0, -12, 9, -5, 2, 0] }}
    transition={enabled && success ? livelySpring : { duration: enabled ? .45 : 0 }}>
    {children}
  </m.div>
}

export function useCelebrate() {
  const { enabled } = useMotionSettings()
  const active = useRef(false)
  useEffect(() => {
    active.current = enabled
    return () => { active.current = false }
  }, [enabled])
  return useCallback(async (anchor?: HTMLElement | null) => {
    if (!active.current) return
    try {
      const { default: confetti } = await import('canvas-confetti')
      if (!active.current) return
      const rect = anchor?.getBoundingClientRect()
      const x = rect ? (rect.left + rect.width / 2) / innerWidth : .5
      const y = rect ? rect.top / innerHeight : .55
      void confetti({
        particleCount: 66, spread: 92, ticks: 146, startVelocity: 36, scalar: 1.08, disableForReducedMotion: true,
        origin: { x: Math.max(.12, Math.min(.88, x)), y: Math.max(.28, Math.min(.83, y)) },
        colors: ['#2e5aa7', '#ffb18e', '#d8c8fa', '#cce7ae', '#86c5ff'],
      })
    } catch {
      // A failed animation download must not affect the completed attempt.
    }
  }, [])
}
