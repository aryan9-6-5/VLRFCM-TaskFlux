import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { ArrowUUpLeft, Check, Flask, Lock } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { MVNumber } from '../components/Counter.jsx'
import { Block, Rise, Tag, ramp } from '../components/kit.jsx'
import { COUNTS, F, ORDER } from '../data/evidence.js'
import './chapters.css'

const S = Object.fromEntries(COUNTS.situations)
const TOTAL = COUNTS.gearbox_runs_per_system
const STATS = [
  { to: TOTAL, label: 'runs for each answer', a: 0.12 },
  { to: COUNTS.answers_compared, label: 'answers compared', a: 0.24 },
  { to: F.tests.value, label: 'automated tests', a: 0.36 },
]
const SITUATIONS = [
  { key: 'truncation', Icon: Check, label: 'Nothing has to come off', tone: 'keep' },
  { key: 'undo', Icon: ArrowUUpLeft, label: 'Parts have to come off', tone: 'undo' },
  { key: 'irreversible', Icon: Lock, label: 'Something cannot come off', tone: 'limit' },
]

function Stat({ p, to, label, a }) {
  const mv = useTransform(p, (v) => to * ramp(a, a + 0.14)(v))
  return (
    <Rise p={p} a={a} className="stat">
      <b className="tnum"><MVNumber mv={mv} /></b>
      <span>{label}</span>
    </Rise>
  )
}

function Seg({ p, k, tone, i }) {
  const a = 0.5 + i * 0.1
  const w = useTransform(p, (v) => `${ramp(a, a + 0.14)(v) * (S[k] / TOTAL) * 100}%`)
  return <motion.span className={`seg f-${tone}`} style={{ width: w }} />
}

export default function C08Tested() {
  return (
    <div id="tested" className="chapter c08">
      <Pinned height={340}>
        {(p) => (
          <div className="stage">
            <div className="copy">
              <Block p={p} a={0} b={1} first last>
                <h2 className="display d-lg">We tested it in <em>a simulator.</em></h2>
                <p className="lede">A gearbox with {ORDER.length} steps. Not a robot yet.</p>
              </Block>
            </div>
            <div className="vis">
              <div className="tested">
                <div className="stats">{STATS.map((s) => <Stat key={s.label} p={p} {...s} />)}</div>
                <div className="segbar" role="img" aria-label="How the runs split across three situations">
                  {SITUATIONS.map((s, i) => <Seg key={s.key} p={p} i={i} k={s.key} tone={s.tone} />)}
                </div>
                <div className="segrows">
                  {SITUATIONS.map(({ key, Icon, label, tone }, i) => (
                    <Rise key={key} p={p} a={0.54 + i * 0.1} className={`sit sit-${tone}`}>
                      <Icon size={22} weight="bold" aria-hidden="true" /><span>{label}</span><b className="tnum">{S[key].toLocaleString()} runs</b>
                    </Rise>
                  ))}
                </div>
                <Rise p={p} a={0.86}><Tag Icon={Flask}>Simulation with assumed rates</Tag></Rise>
              </div>
            </div>
          </div>
        )}
      </Pinned>
    </div>
  )
}
