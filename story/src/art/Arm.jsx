import React from 'react'
import { motion, useTransform } from 'framer-motion'

/**
 * A two-joint robot arm. `tx`/`ty` are MotionValues (the point the hand reaches for, in SVG units); the elbow is
 * solved from them, so the arm rotates on its pivots as the target moves. `bend` picks which way the elbow points.
 */
export default function Arm({ bx, by, tx, ty, l1 = 46, l2 = 46, color = 'var(--car)', w = 9, bend = -1, label = 'robot arm' }) {
  const pts = useTransform([tx, ty], ([x, y]) => {
    const dx = x - bx, dy = y - by
    const d = Math.min(Math.max(Math.hypot(dx, dy), Math.abs(l1 - l2) + 0.5), l1 + l2 - 0.5)
    const a = Math.atan2(dy, dx)
    const b = Math.acos(Math.max(-1, Math.min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    const e = [bx + l1 * Math.cos(a + bend * b), by + l1 * Math.sin(a + bend * b)]
    return { e, h: [bx + d * Math.cos(a), by + d * Math.sin(a)] }
  })
  const d = useTransform(pts, (q) => `M${bx} ${by} L${q.e[0].toFixed(1)} ${q.e[1].toFixed(1)} L${q.h[0].toFixed(1)} ${q.h[1].toFixed(1)}`)
  const ex = useTransform(pts, (q) => q.e[0]); const ey = useTransform(pts, (q) => q.e[1])
  const hx = useTransform(pts, (q) => q.h[0]); const hy = useTransform(pts, (q) => q.h[1])
  return (
    <g role="img" aria-label={label}>
      <rect x={bx - 15} y={by + 2} width="30" height="9" rx="4.5" fill={color} />
      <motion.path d={d} fill="none" stroke={color} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={bx} cy={by} r={w * 1.15} fill={color} />
      <motion.circle cx={ex} cy={ey} r={w * 0.72} fill="var(--surface)" stroke={color} strokeWidth="3" />
      <motion.circle cx={hx} cy={hy} r={w * 0.62} fill="var(--surface)" stroke={color} strokeWidth="3" />
    </g>
  )
}
