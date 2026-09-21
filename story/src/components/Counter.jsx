import React, { useEffect, useRef, useState } from 'react'
import { animate, useInView, useMotionValueEvent } from 'framer-motion'

const fmt = (v, decimals, sign) => {
  const s = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  return (v < 0 ? '−' : sign ? '+' : '') + s
}

function Slots({ text }) {
  return (
    <span className="digits">
      {[...text].map((c, i) => (/[0-9]/.test(c) ? <span key={i} className="dg">{c}</span> : <span key={i} className={c === ',' || c === '.' ? 'sep' : ''}>{c}</span>))}
    </span>
  )
}

/** Counts up from zero once visible. */
export function Counter({ to, decimals = 0, duration = 1.8, sign = false, delay = 0 }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, amount: 0.6 })
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (!inView) return
    const c = animate(0, to, { duration, delay, ease: [0.16, 1, 0.3, 1], onUpdate: setVal })
    return () => c.stop()
  }, [inView, to, duration, delay])
  return <span ref={ref}><Slots text={fmt(inView ? val : 0, decimals, sign)} /></span>
}

/** Displays a MotionValue as a fixed-width number (scroll-linked counting). */
export function MVNumber({ mv, decimals = 0, sign = false }) {
  const [val, setVal] = useState(mv.get())
  useMotionValueEvent(mv, 'change', setVal)
  return <Slots text={fmt(val, decimals, sign)} />
}
