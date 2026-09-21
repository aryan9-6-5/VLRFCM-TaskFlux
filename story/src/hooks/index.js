import { useEffect, useState } from 'react'
import { useTransform } from 'framer-motion'

/** True below tablet width. Used to swap spatial layouts for vertical flows. */
export function useIsMobile(query = '(max-width: 1023px)') {
  const [match, setMatch] = useState(() => (typeof window === 'undefined' ? false : window.matchMedia(query).matches))
  useEffect(() => {
    const mq = window.matchMedia(query)
    const on = () => setMatch(mq.matches)
    on()
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [query])
  return match
}

/** Normalised 0→1 progress of `p` between a and b. */
export const useSeg = (p, a, b, ease) => useTransform(p, [a, b], [0, 1], { clamp: true, ease })

/** Map progress through keyframes. */
export const useKeys = (p, input, output, opts) => useTransform(p, input, output, { clamp: true, ...opts })

export const clamp01 = (v) => Math.min(1, Math.max(0, v))
export const lerp = (a, b, t) => a + (b - a) * t
export const seg = (v, a, b) => clamp01((v - a) / (b - a))
export const easeOut = (t) => 1 - Math.pow(1 - t, 3)
export const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

/** Deterministic PRNG so scenes look identical on every load. */
export function mulberry32(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
