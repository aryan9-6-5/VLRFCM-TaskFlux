import React from 'react'
import { motion, useMotionValue, useTransform } from 'framer-motion'
import { ArrowRight, ChatCircleDots, HandPalm, Lock, Play, Question } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Illustration, Rise, Tag, ramp, ease } from '../components/kit.jsx'
import Car from '../art/Car.jsx'
import Arm from '../art/Arm.jsx'
import { C } from '../tokens.js'
import { TRIAGE } from '../data/evidence.js'
import './chapters.css'

const STAYS = ['chassis', 'wheels', 'motor', 'seats', 'doors']
const K = 360 / 260 // the car is drawn at 1.385x, origin (140, 170)

function Reconcile({ p }) {
  const keep = useTransform(p, (v) => (ramp(0.22, 0.26)(v) > 0.5 ? C.keep : C.text))
  const oldStroke = useTransform(p, (v) => (ramp(0.42, 0.46)(v) > 0.5 ? C.undo : C.text))
  const lift = useTransform(p, (v) => -46 * ease(ramp(0.46, 0.6)(v)))
  const oldO = useTransform(p, (v) => 1 - ramp(0.78, 0.84)(v))
  const rails = useTransform(p, (v) => ramp(0.44, 0.5)(v))
  const paintStroke = useTransform(p, (v) => (ramp(0.62, 0.66)(v) > 0.5 && v < 0.8 ? C.limit : C.text))
  const lock = useTransform(p, (v) => ramp(0.64, 0.72)(v) * (1 - ramp(0.84, 0.9)(v)))
  const ghost = useTransform(p, (v) => ramp(0.04, 0.1)(v) * (1 - ramp(0.8, 0.84)(v)))
  const newY = useTransform(p, (v) => -70 * (1 - ease(ramp(0.82, 0.96)(v))))
  const newO = useTransform(p, ramp(0.8, 0.85))
  // The arm holds whichever roof is moving.
  const hx = useMotionValue(140 + 138 * K)
  const hy = useTransform(p, (v) => {
    const old = 170 + 4 * K + 46 * K * 0 + (-46 * ease(ramp(0.46, 0.6)(v))) * K
    const nw = 170 + 4 * K + (-70 * (1 - ease(ramp(0.82, 0.96)(v)))) * K
    if (v < 0.44) return 100
    if (v < 0.62) return old
    if (v < 0.8) return 100 + (old - 100) * (1 - ramp(0.66, 0.78)(v))
    return nw
  })
  const s = {}
  STAYS.forEach((n) => { s[n] = { stroke: keep } })
  return (
    <svg viewBox="90 6 450 350" className="art" role="img" aria-label="One robot fits a new design to a half-built car: keep what fits, lift the old roof off first, leave the cured paint, then lower the new roof.">
      <rect x="30" y="322" width="580" height="22" rx="11" fill="var(--bg-2)" stroke="var(--carline)" strokeWidth="3" />
      <rect x="316" y="18" width="8" height="26" rx="4" fill="var(--old)" />
      <rect x="140" y="40" width="360" height="8" rx="4" fill="var(--old)" />
      <Car x={140} y={170} width={360} label="The car" parts={{
        ...s, paint: { stroke: paintStroke }, roof: { o: oldO, y: lift, stroke: oldStroke }, rails: { o: rails },
        newGhost: { o: ghost }, newRoof: { o: newO, y: newY },
      }} />
      <Arm bx={320} by={48} tx={hx} ty={hy} l1={90} l2={90} bend={1} label="robot arm on the ceiling rail" />
      <motion.g style={{ opacity: lock }} role="img" aria-label="cured paint cannot come off">
        <circle cx="240" cy="268" r="22" fill="var(--limit-bg)" stroke="var(--limit)" strokeWidth="3" />
        <Lock x="228" y="256" size={24} weight="bold" color={C.limit} />
      </motion.g>
    </svg>
  )
}

const ACTION = { act: [Play, 'Acts'], ask: [Question, 'Asks'], continue: [ArrowRight, 'Carries on'], halt: [HandPalm, 'Stops'] }
const NOTE = (t) => (t.action === 'act' ? `Asking would add ${t.ca} s.` : t.action === 'ask' ? `Asking costs ${t.ca} s. A wrong guess costs ${Math.min(t.ra, t.rc)} s or more.` : t.action === 'continue' ? 'Not a change, so the build carries on.' : 'A stop always wins.')

function Triage({ p }) {
  return (
    <div className="triage">
      {TRIAGE.map((t, i) => {
        const [Icon, word] = ACTION[t.action]
        const a = 0.16 + i * 0.18
        return (
          <Rise key={t.text} p={p} a={a} className="trow">
            <div className="quote"><ChatCircleDots size={24} weight="bold" aria-hidden="true" /><span>“{t.text}”</span></div>
            <div className="trow-out"><span className={`act act-${t.action}`}><Icon size={20} weight="bold" aria-hidden="true" />{word}</span><small>{NOTE(t)}</small></div>
          </Rise>
        )
      })}
      <Rise p={p} a={0.88} className="triage-tag"><Tag kind="real">The planner's own decisions on four sentences</Tag></Rise>
    </div>
  )
}

export default function C07How() {
  return (
    <div id="how" className="chapter c07">
      <Pinned height={400}>
        {(p) => (
          <div className="stage">
            <div className="copy">
              <Block p={p} a={0} b={0.2} first>
                <h2 className="display d-lg">The new design <em>arrives.</em></h2>
                <p className="lede">Only the roof changes.</p>
              </Block>
              <Block p={p} a={0.2} b={0.4}>
                <h2 className="display d-lg">Keep what <em>still fits.</em></h2>
                <p className="lede">Those parts are never touched.</p>
              </Block>
              <Block p={p} a={0.4} b={0.62}>
                <h2 className="display d-lg">Take off what sits <em>on top first.</em></h2>
                <p className="lede">One robot lifts the old roof away.</p>
              </Block>
              <Block p={p} a={0.62} b={0.8}>
                <h2 className="display d-lg">Leave the paint. <em>Work around it.</em></h2>
                <p className="lede">It cannot come off, so the plan avoids it.</p>
              </Block>
              <Block p={p} a={0.8} b={1} last>
                <h2 className="display d-lg">Then build the <em>new roof.</em></h2>
                <p className="lede">In the order the design needs.</p>
              </Block>
            </div>
            <div className="vis"><div className="stackcol"><Reconcile p={p} /><Illustration /></div></div>
          </div>
        )}
      </Pinned>
      <Pinned height={300}>
        {(p) => (
          <div className="stage">
            <div className="copy">
              <Block p={p} a={0} b={1} first last>
                <h2 className="display d-lg">It also decides when <em>to ask.</em></h2>
                <p className="lede">Four sentences, four decisions.</p>
              </Block>
            </div>
            <div className="vis"><Triage p={p} /></div>
          </div>
        )}
      </Pinned>
    </div>
  )
}
