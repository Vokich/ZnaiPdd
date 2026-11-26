import { createContext, useContext, useState, useSyncExternalStore } from 'react'
import type { ReactNode } from 'react'
import { LazyMotion, MotionConfig } from 'motion/react'

const preferenceKey = 'znai-pdd-motion'
const loadFeatures = () => import('./motion-features').then(module => module.default)
const MotionSettings = createContext({ enabled: true, reduced: false, toggle: () => {} })
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

function subscribeToReducedMotion(onChange: () => void) {
  reducedMotion.addEventListener('change', onChange)
  return () => reducedMotion.removeEventListener('change', onChange)
}

export function MotionProvider({ children }: { children: ReactNode }) {
  const reduced = useSyncExternalStore(subscribeToReducedMotion, () => reducedMotion.matches)
  const [paused, setPaused] = useState(() => {
    try { return localStorage.getItem(preferenceKey) === 'off' } catch { return false }
  })
  function toggle() {
    if (reduced) return
    try { localStorage.setItem(preferenceKey, paused ? 'on' : 'off') } catch { /* Storage can be unavailable. */ }
    setPaused(!paused)
  }
  return <MotionSettings.Provider value={{ enabled: !paused && !reduced, reduced, toggle }}>
    <MotionConfig reducedMotion={paused || reduced ? 'always' : 'never'}>
      <LazyMotion features={loadFeatures} strict>{children}</LazyMotion>
    </MotionConfig>
  </MotionSettings.Provider>
}

export function useMotionSettings() {
  return useContext(MotionSettings)
}
