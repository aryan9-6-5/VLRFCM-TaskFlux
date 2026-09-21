import React from 'react'
import { motion } from 'framer-motion'

/**
 * A flat side-view car drawn as separate groups (chassis, wheels, motor, seats, doors, paint, old roof, new roof, rails)
 * so each part can slide on and off. One stroke width, rounded joints, fills from the tokens in styles.css.
 * `parts` maps a part name to { o, x, y, stroke }, each a number or a MotionValue. Anything left out is fully drawn.
 * There is no text in the drawing; the parent labels things in HTML.
 */
const D = { o: 1, x: 0, y: 0 }
const part = (parts, k, def = {}) => ({ ...D, ...def, ...(parts[k] || {}) })

function G({ name, s, children }) {
  const st = { opacity: s.o, x: s.x, y: s.y }
  if (s.stroke) st.stroke = s.stroke
  return <motion.g role="img" aria-label={name} style={st}>{children}</motion.g>
}

export default function Car({ parts = {}, label = 'A car', className = '', width = '100%', style, x, y }) {
  const p = (k, def) => part(parts, k, def)
  return (
    <svg x={x} y={y} viewBox="0 0 260 120" width={width} height={typeof width === 'number' ? (width * 120) / 260 : undefined} className={className} style={{ overflow: 'visible', ...style }} role="img" aria-label={label}>
      <g strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" stroke="var(--carline)">
        <G name="chassis" s={p('chassis')}>
          <rect x="24" y="82" width="212" height="12" rx="6" fill="var(--carline)" />
        </G>
        <G name="paint and body panels" s={p('paint')}>
          <path d="M22 82 V64 Q22 54 34 52 L70 47 H188 L226 53 Q238 55 238 66 V82 Z" fill="var(--car)" />
        </G>
        <G name="motor" s={p('motor')}>
          <rect x="196" y="55" width="34" height="23" rx="6" fill="var(--old)" />
          <circle cx="213" cy="66.5" r="5" fill="var(--glass)" />
        </G>
        <G name="doors and windows" s={p('doors')}>
          <path d="M76 47 Q86 27 112 25 H168 Q190 28 200 47 Z" fill="var(--glass)" />
          <path d="M108 49 V80 H166 V49" fill="none" />
          <path d="M148 60 H158" fill="none" />
        </G>
        <G name="seats" s={p('seats')}>
          <path d="M90 50 V23 Q90 17 96 17 H104 Q110 17 110 23 V50 Z" fill="var(--carline)" />
          <path d="M134 50 V23 Q134 17 140 17 H148 Q154 17 154 23 V50 Z" fill="var(--carline)" />
        </G>
        <G name="wheels" s={p('wheels')}>
          <circle cx="66" cy="94" r="16" fill="var(--carline)" stroke="var(--bg)" />
          <circle cx="66" cy="94" r="5" fill="var(--glass)" stroke="none" />
          <circle cx="196" cy="94" r="16" fill="var(--carline)" stroke="var(--bg)" />
          <circle cx="196" cy="94" r="5" fill="var(--glass)" stroke="none" />
        </G>
        <G name="rails for the roof" s={p('rails', { o: 0 })}>
          <g stroke="var(--dim)"><path d="M84 -46 V14 M196 -46 V14" fill="none" /></g>
        </G>
        <G name="old roof" s={p('roof')}>
          <path d="M80 30 Q90 8 118 6 H156 Q184 8 196 30 Z" fill="var(--car)" />
        </G>
        <G name="planned old roof" s={p('oldGhost', { o: 0 })}>
          <path d="M80 30 Q90 8 118 6 H156 Q184 8 196 30 Z" fill="none" stroke="var(--dim)" strokeDasharray="6 6" />
        </G>
        <G name="planned new roof" s={p('newGhost', { o: 0 })}>
          <path d="M70 34 Q100 10 140 8 Q176 8 204 34 Z" fill="none" stroke="var(--accent)" strokeDasharray="6 6" />
        </G>
        <G name="new roof" s={p('newRoof', { o: 0, y: -70 })}>
          <path d="M70 34 Q100 10 140 8 Q176 8 204 34 Z" fill="var(--accent)" />
        </G>
      </g>
    </svg>
  )
}
