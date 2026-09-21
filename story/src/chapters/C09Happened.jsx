import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { Eye, Eyes, ListChecks, MagnifyingGlass, Question, Target } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, BarRows, Rise, Tag, ramp } from '../components/kit.jsx'
import { P, R, pct, pct1 } from '../data/evidence.js'
import './chapters.css'

const U = R.undo
const finished = (k) => Math.round(U[k].success * U[k].n)
const DNF = `${finished('B3a')} of ${U.B3a.n.toLocaleString()} finished`

// Fixed order in every chart. TaskFlux is drawn in the accent, the rest in neutral grey.
const timeRows = [
  { label: 'Start over', value: U.B2.time, display: `${U.B2.time} s` },
  { label: 'Compare build orders', value: U.B3b.time, display: `${U.B3b.time} s` },
  { label: 'Replan on top of the old parts', value: 0, display: DNF, dnf: true, note: 'It ran into the parts already built.' },
  { label: 'TaskFlux', value: U.TF.time, display: `${U.TF.time} s`, tone: 'accent' },
]
const lostRows = [
  { label: 'Start over', value: U.B2.lost, display: pct(U.B2.lost) },
  { label: 'Compare build orders', value: U.B3b.lost, display: pct(U.B3b.lost) },
  { label: 'Replan on top of the old parts', value: 0, display: 'Did not finish', dnf: true },
  { label: 'TaskFlux', value: U.TF.lost, display: pct(U.TF.lost), tone: 'accent' },
]
const T = R.truncation
const I = R.irreversible
const nothing = [
  { label: 'Plain replan', value: T.B3a.time, display: `${T.B3a.time} s` },
  { label: 'TaskFlux', value: T.TF.time, display: `${T.TF.time} s`, tone: 'accent' },
  { label: 'Start over', value: T.B2.time, display: `${T.B2.time} s` },
]
const cannot = [
  { label: 'Start over', value: I.B2.time, display: `${I.B2.time} s` },
  { label: 'TaskFlux', value: I.TF.time, display: `${I.TF.time} s`, tone: 'accent' },
  { label: 'Compare build orders', value: I.B3b.time, display: `${I.B3b.time} s`, note: `Destroys the part in ${pct(I.B3b.lost)} of runs.` },
]
const eyes = [
  { label: 'Trust the readings', value: P.trust.success, display: pct1(P.trust.success), Icon: Eye, note: 'No extra looks.' },
  { label: 'Free consistency check', value: P.consistency.success, display: pct1(P.consistency.success), Icon: ListChecks, note: `${P.consistency.inspections} looks per changeover.` },
  { label: 'Look before each undo', value: P.inspect_undo.success, display: pct1(P.inspect_undo.success), Icon: MagnifyingGlass, note: `${P.inspect_undo.inspections} looks. No gain.` },
  { label: 'Look only at what could change the plan', value: P.inspect_critical.success, display: pct1(P.inspect_critical.success), Icon: Target, tone: 'accent', note: `${P.inspect_critical.inspections} looks per changeover.` },
  { label: 'Look at everything', value: P.inspect_all.success, display: pct1(P.inspect_all.success), Icon: Eyes, note: `${P.inspect_all.inspections} looks per changeover.` },
]

const at = (p, a, b, children, cls = '') => <Rise p={p} a={a} b={b} rise={14} className={`scene ${cls}`}>{children}</Rise>

export default function C09Happened() {
  return (
    <div id="happened" className="chapter c09">
      <Pinned height={560}>
        {(p) => {
          const q = useTransform(p, (v) => ramp(0.02, 0.07)(v) * (1 - ramp(0.11, 0.15)(v)))
          return (
            <div className="stage">
              <div className="copy">
                <Block p={p} a={0} b={0.15} first>
                  <h2 className="display d-xl">So, does it <em>help?</em></h2>
                </Block>
                <Block p={p} a={0.15} b={0.4}>
                  <h2 className="display d-lg">About twice as fast when parts <em>must come off.</em></h2>
                  <p className="lede">{U.TF.time} seconds, against {U.B3b.time} and {U.B2.time}.</p>
                </Block>
                <Block p={p} a={0.4} b={0.58}>
                  <h2 className="display d-lg">And no parts <em>destroyed.</em></h2>
                  <p className="lede">{pct(U.TF.lost)} of runs, against {pct(U.B2.lost)} and {pct(U.B3b.lost)}.</p>
                </Block>
                <Block p={p} a={0.58} b={0.8}>
                  <h2 className="display d-lg">Where it <em>does not help.</em></h2>
                  <p className="lede">Nothing to undo, or something that cannot be: no gain.</p>
                </Block>
                <Block p={p} a={0.8} b={1} last>
                  <h2 className="display d-lg">When the robot's eyes <em>are wrong.</em></h2>
                  <p className="lede">Checking only what could change the plan is enough.</p>
                </Block>
              </div>
              <div className="vis">
                <div className="scenes">
                  <motion.div className="scene scene-q" style={{ opacity: q }} aria-hidden="true"><Question size={120} weight="bold" /></motion.div>
                  {at(p, 0.15, 0.4, <><p className="cap">Seconds from the request to a finished product</p><BarRows p={p} a={0.17} rows={timeRows} max={340} /><Tag kind="real">Simulated: {U.TF.n.toLocaleString()} runs each</Tag></>)}
                  {at(p, 0.4, 0.58, <><p className="cap">Share of runs in which a part was destroyed</p><BarRows p={p} a={0.42} rows={lostRows} max={0.2} /><Tag kind="real">Simulated: {U.TF.n.toLocaleString()} runs each</Tag></>)}
                  {at(p, 0.58, 0.8, (
                    <div className="two">
                      <div><p className="cap">Nothing has to come off</p><BarRows p={p} a={0.6} rows={nothing} max={260} /></div>
                      <div><p className="cap">Something cannot come off</p><BarRows p={p} a={0.66} rows={cannot} max={400} /></div>
                      <Tag kind="real">Simulated: {T.TF.n.toLocaleString()} and {I.TF.n.toLocaleString()} runs each</Tag>
                    </div>
                  ))}
                  {at(p, 0.8, undefined, <><p className="cap">Changeovers done right when 5 in 100 steps are misread</p><BarRows p={p} a={0.82} rows={eyes} max={1} /><Tag kind="real">Simulated: {P.n.toLocaleString()} runs</Tag></>)}
                </div>
              </div>
            </div>
          )
        }}
      </Pinned>
    </div>
  )
}
