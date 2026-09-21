import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { PencilSimple } from '@phosphor-icons/react'
import { clamp01 } from '../hooks/index.js'

export const ramp = (a, b) => (v) => clamp01((v - a) / (b - a))
export const ease = (t) => 1 - Math.pow(1 - t, 3)

/** A block of copy that cross-fades inside its own slice [a, b] of the chapter's progress. */
export function Block({ p, a, b, first, last, className = '', children }) {
  const o = useTransform(p, (v) => Math.min(first ? 1 : ramp(a, a + 0.05)(v), last ? 1 : 1 - ramp(b - 0.05, b)(v)))
  const y = useTransform(p, (v) => (first ? 0 : 22 * (1 - ramp(a, a + 0.07)(v))))
  return <motion.div className={`block ${className}`} style={{ opacity: o, y }}>{children}</motion.div>
}

/** Appears at `a` (fades and rises), and optionally leaves at `b`. */
export function Rise({ p, a, b, rise = 16, as = 'div', className = '', style, children, ...rest }) {
  const o = useTransform(p, (v) => ramp(a, a + 0.05)(v) * (b == null ? 1 : 1 - ramp(b - 0.05, b)(v)))
  const y = useTransform(p, (v) => rise * (1 - ramp(a, a + 0.07)(v)))
  const Tag = motion[as]
  return <Tag className={className} style={{ opacity: o, y, ...style }} {...rest}>{children}</Tag>
}

/** Says whether a picture is real data or an idea, in the existing tag style. */
export function Tag({ kind = 'plain', Icon, children }) {
  return <span className={`tag ${kind}`}>{Icon ? <Icon size={17} weight="bold" aria-hidden="true" /> : null}{children}</span>
}

/** MotionValue for a number that ramps over [a, b]. */
export function useRamp(p, a, b, from = 0, to = 1) {
  return useTransform(p, (v) => from + (to - from) * ramp(a, b)(v))
}

/** One bar. It appears at `a` and grows with scroll; `dnf` rows show that the run never finished instead of a bar. */
function BarRow({ p, a, label, value, display, tone = 'old', note, Icon, max, dnf }) {
  const o = useTransform(p, ramp(a, a + 0.04))
  const y = useTransform(o, (v) => 12 * (1 - v))
  const w = useTransform(p, (v) => `${Math.max(0.8, ramp(a + 0.015, a + 0.06)(v) * (value / max) * 100)}%`)
  return (
    <motion.div className="bar" style={{ opacity: o, y }}>
      <div className="bar-head">
        <span className="bar-name">{Icon ? <Icon size={22} weight="bold" aria-hidden="true" /> : null}{label}</span>
        <b className="bar-val tnum">{display}</b>
      </div>
      <div className="bar-track">{dnf ? null : <motion.span className={`bar-fill f-${tone}`} style={{ width: w }} />}</div>
      {note ? <small className="bar-note">{note}</small> : null}
    </motion.div>
  )
}

export function BarRows({ p, a, rows, max, className = '' }) {
  return <div className={`bars ${className}`}>{rows.map((r, i) => <BarRow key={r.label} p={p} a={a + i * 0.02} max={max} {...r} />)}</div>
}

/** Every car drawing carries this: the cars explain the idea; the measured numbers come from a simulated gearbox. */
export function Illustration() {
  return <Tag Icon={PencilSimple}>Illustration: a car, drawn to explain the idea</Tag>
}
