import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { Bug, HandPalm, MagnifyingGlass, X } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { MVNumber } from '../components/Counter.jsx'
import { Block, Rise, Tag, ramp } from '../components/kit.jsx'
import { F, P, R, pct1 } from '../data/evidence.js'
import './chapters.css'

const [OLD_TF, OLD_RESTART] = F.withdrawn_gap.value
const NOW_TF = (R.undo.TF.success * 100).toFixed(1)
const NOW_RESTART = (R.undo.B2.success * 100).toFixed(1)
const WASTE = R.undo.B2.unneeded.toFixed(1)

function Strike({ p, a, b }) {
  const w = useTransform(p, ramp(a, b))
  return <motion.i className="strike" style={{ scaleX: w }} />
}

function Num({ p, to, a, decimals = 0, suffix = '' }) {
  const mv = useTransform(p, (v) => to * ramp(a, a + 0.1)(v))
  return <span className="tnum"><MVNumber mv={mv} decimals={decimals} />{suffix}</span>
}

export default function C10Wrong() {
  return (
    <div id="wrong" className="chapter c10">
      <Pinned height={520}>
        {(p) => {
          const dim = useTransform(p, ramp(0.8, 0.86))
          const lesson = useTransform(p, ramp(0.86, 0.92))
          return (
            <div className="stage">
              <div className="copy">
                <Block p={p} a={0} b={0.2} first>
                  <h2 className="display d-lg">Our first claim was <em>too strong.</em></h2>
                  <p className="lede">It said nobody had tackled this.</p>
                </Block>
                <Block p={p} a={0.2} b={0.4}>
                  <h2 className="display d-lg">Our headline gap was <em>inflated.</em></h2>
                  <p className="lede">Two simulator rules disagreed.</p>
                </Block>
                <Block p={p} a={0.4} b={0.6}>
                  <h2 className="display d-lg">One idea <em>changed nothing.</em></h2>
                  <p className="lede">We expected looking before an undo to help.</p>
                </Block>
                <Block p={p} a={0.6} b={0.8} last>
                  <h2 className="display d-lg">Tests caught <em>the rest.</em></h2>
                  <p className="lede">Errors that no run would have shown us.</p>
                </Block>
              </div>
              <div className="vis">
                <div className="scenes">
                  <Rise p={p} a={0.02} b={0.2} className="scene wrongcard">
                    <p className="claim"><span>“No paper addresses a goal replaced in the middle of a build.”</span><Strike p={p} a={0.08} b={0.14} /></p>
                    <Tag kind="idea">Removed. Neighbouring work exists.</Tag>
                  </Rise>
                  <Rise p={p} a={0.22} b={0.4} className="scene wrongcard">
                    <div className="gapnums"><div className="gaplabel"><s>{OLD_TF}%</s><small>TaskFlux, first claim</small></div><div className="gaplabel"><s>{OLD_RESTART}%</s><small>Start over, first claim</small></div></div>
                    <Rise p={p} a={0.3} className="gapnums gapnums-now"><div className="gaplabel"><b>{NOW_TF}%</b><small>TaskFlux, measured</small></div><div className="gaplabel"><b>{NOW_RESTART}%</b><small>Start over, measured</small></div></Rise>
                    <p className="cap">Runs that end with the right product. TaskFlux, then start over.</p>
                    <Tag kind="real">The honest gap is small: both nearly always finish.</Tag>
                  </Rise>
                  <Rise p={p} a={0.42} b={0.6} className="scene wrongcard">
                    <div className="gapnums"><div className="gaplabel"><b>{pct1(P.consistency.success)}</b><small>Free check alone</small></div><div className="gaplabel"><b>{pct1(P.inspect_undo.success)}</b><small>Plus a look before each undo</small></div></div>
                    <p className="cap">Runs done right when 5 in 100 steps are misread.</p>
                    <Tag Icon={MagnifyingGlass}>No gain</Tag>
                  </Rise>
                  <Rise p={p} a={0.62} b={0.8} className="scene wrongcard">
                    <div className="gapnums"><div className="gaplabel"><b><Num p={p} to={F.errors_fixed.value} a={0.64} /></b><small>Modelling errors fixed</small></div><div className="gaplabel"><b><Num p={p} to={F.stop_missed_pct.value} a={0.68} decimals={1} suffix="%" /></b><small>Stop requests missed</small></div></div>
                    <p className="cap">Both found by tests, before any result depended on them.</p>
                    <Tag Icon={Bug}>Found by tests, not by results</Tag>
                  </Rise>
                </div>
              </div>
              <motion.div className="lesson-dim" style={{ opacity: dim }} />
              <motion.div className="lesson" style={{ opacity: lesson }}>
                <h2 className="display d-xl">The saving is in the work <em>you do not undo.</em></h2>
                <p className="lede">Parts taken off that did not need to be: {R.undo.TF.unneeded} per run, against {WASTE}.</p>
              </motion.div>
            </div>
          )
        }}
      </Pinned>
    </div>
  )
}
