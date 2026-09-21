import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { ArrowsClockwise, Check, Minus, Scales, Target, Trash, X } from '@phosphor-icons/react'
import { PROBLEM, R, pct1 } from '../data/evidence.js'
import { Tag, ramp } from './kit.jsx'

// The four answers side by side on the four questions. Every figure is from the simulator run on the gearbox.
const COLS = [
  { name: 'Start over', Icon: Trash },
  { name: 'Compare build orders', Icon: Scales },
  { name: 'Carry on', Icon: ArrowsClockwise },
  { name: 'TaskFlux', Icon: Target, us: true },
]
const S = PROBLEM.strategies
const N = PROBLEM.done.length
const off = (k) => `${S[k].undone.length} of ${N}`
const fin = (k) => `${Math.round(R.undo[k].success * R.undo[k].n).toLocaleString()} of ${R.undo[k].n.toLocaleString()}`
const ROWS = [
  { q: 'Takes off only what must', cells: [['no', `${off('B2')} taken off`], ['no', `${off('B3b')} taken off`], ['no', 'Takes off none'], ['ok', `${off('TF')} taken off`]] },
  { q: 'Finishes the build', cells: [['ok', pct1(R.undo.B2.success)], ['ok', pct1(R.undo.B3b.success)], ['no', `${fin('B3a')} finish`], ['ok', pct1(R.undo.TF.success)]] },
  { q: 'A step that cannot come off', cells: [['part', 'Scraps it all'], ['no', 'Destroys the part'], ['no', 'Cannot finish'], ['ok', 'Says why, asks first']] },
  { q: 'Asks when unsure', cells: [['no', 'Never asks'], ['no', 'Never asks'], ['no', 'Never asks'], ['ok', 'Asks first']] },
]
const GLYPH = { ok: Check, no: X, part: Minus }
const WORD = { ok: 'yes', no: 'no', part: 'partly' }

function MxRow({ p, a, row }) {
  const o = useTransform(p, ramp(a, a + 0.04))
  const y = useTransform(o, (v) => 10 * (1 - v))
  return (
    <motion.div className="mx-row" style={{ opacity: o, y }}>
      <p className="mx-q">{row.q}</p>
      <div className="mx-cells">
        {row.cells.map(([k, note], j) => {
          const Glyph = GLYPH[k]
          return (
            <div key={j} className={`mx-cell ${k}${j === 3 ? ' us' : ''}`} role="img" aria-label={`${COLS[j].name}: ${WORD[k]}, ${note}`}>
              <Glyph size={22} weight="bold" aria-hidden="true" /><small>{note}</small>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}

/** Rows fade in one after another, starting at progress `a`. */
export default function Matrix({ p, a = 0 }) {
  return (
    <div className="matrix">
      <div className="mx-head">
        {COLS.map(({ name, Icon, us }) => <div key={name} className={`mx-col${us ? ' us' : ''}`}><Icon size={26} weight="bold" aria-hidden="true" /><b>{name}</b></div>)}
      </div>
      {ROWS.map((r, i) => <MxRow key={r.q} p={p} a={a + i * 0.04} row={r} />)}
      <Tag kind="real">Simulated. The three others are simple answers we built to compare.</Tag>
    </div>
  )
}

