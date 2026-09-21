import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { ArrowLineUp, ChatCircleDots, Check, Lock } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Illustration, Tag, ramp, ease } from '../components/kit.jsx'
import Car from '../art/Car.jsx'
import { C } from '../tokens.js'
import './chapters.css'

const STAYS = ['chassis', 'wheels', 'motor', 'seats', 'doors']
// Four questions, one after another: what can stay, what comes off first, what can never come off, when to ask.
const Q = [[0.0, 0.2], [0.2, 0.4], [0.4, 0.6], [0.6, 0.8]]
const on = (v, [a, b], slack = 0.03) => ramp(a, a + slack)(v) * (1 - ramp(b - slack, b)(v))

function Scene({ p }) {
  const keep = useTransform(p, (v) => (v < 0.6 ? (ramp(0.02, 0.08)(v) > 0.5 ? C.keep : C.text) : C.text))
  const roofStroke = useTransform(p, (v) => (ramp(0.06, 0.1)(v) > 0.5 && v < 0.6 ? C.undo : C.text))
  const lift = useTransform(p, (v) => -46 * ease(ramp(0.22, 0.34)(v)) * (1 - ease(ramp(0.58, 0.62)(v))))
  const rails = useTransform(p, (v) => ramp(0.2, 0.26)(v) * (1 - ramp(0.56, 0.62)(v)))
  const paintStroke = useTransform(p, (v) => (v > 0.42 && v < 0.6 ? C.limit : C.text))
  const lock = useTransform(p, (v) => on(v, Q[2]) )
  const ask = useTransform(p, (v) => on(v, Q[3]))
  const allLit = useTransform(p, ramp(0.8, 0.86))
  const s = {}
  STAYS.forEach((n) => { s[n] = { stroke: keep } })
  const chips = Q.map((q, i) => useTransform(p, (v) => 0.3 + 0.7 * Math.max(on(v, q), ramp(0.8, 0.86)(v))))
  return (
    <div className="carstage">
      <div className="carstage-art">
        <Car label="A car with its parts marked by what should happen to them" parts={{
          ...s, roof: { stroke: roofStroke, y: lift }, rails: { o: rails }, paint: { stroke: paintStroke },
        }} />
        <motion.div className="lockbadge" style={{ opacity: lock }} aria-label="cured paint cannot come off"><Lock size={26} weight="bold" aria-hidden="true" /></motion.div>
        <motion.div className="askbadge" style={{ opacity: ask }} aria-label="a question for the operator"><ChatCircleDots size={34} weight="fill" aria-hidden="true" /></motion.div>
      </div>
      <div className="legend">
        <motion.span className="lg lg-keep" style={{ opacity: chips[0] }}><Check size={20} weight="bold" aria-hidden="true" />What can stay</motion.span>
        <motion.span className="lg lg-undo" style={{ opacity: chips[1] }}><ArrowLineUp size={20} weight="bold" aria-hidden="true" />What comes off first</motion.span>
        <motion.span className="lg lg-limit" style={{ opacity: chips[2] }}><Lock size={20} weight="bold" aria-hidden="true" />What cannot come off</motion.span>
        <motion.span className="lg" style={{ opacity: chips[3] }}><ChatCircleDots size={20} weight="bold" aria-hidden="true" />When to ask</motion.span>
      </div>
      <Illustration />
    </div>
  )
}

export default function C05Gap() {
  return (
    <div id="gap" className="chapter c05">
      <Pinned height={380}>
        {(p) => {
          return (
          <div className="stage">
            <div className="copy">
              <Block p={p} a={0} b={0.2} first>
                <h2 className="display d-lg">What can <em>stay?</em></h2>
                <p className="lede">The chassis, wheels, motor, seats and doors still fit.</p>
              </Block>
              <Block p={p} a={0.2} b={0.4}>
                <h2 className="display d-lg">What comes off <em>first?</em></h2>
                <p className="lede">The roof covers the seats, so it goes before them.</p>
              </Block>
              <Block p={p} a={0.4} b={0.6}>
                <h2 className="display d-lg">What can <em>never</em> come off?</h2>
                <p className="lede">Cured paint. The plan has to work around it.</p>
              </Block>
              <Block p={p} a={0.6} b={0.8}>
                <h2 className="display d-lg">When should it <em>ask?</em></h2>
                <p className="lede">A wrong guess can cost more than a question.</p>
              </Block>
              <Block p={p} a={0.8} b={1} last>
                <h2 className="display d-lg">No usual answer settles <em>all four.</em></h2>
                <p className="lede">The three we just saw each miss most of them.</p>
              </Block>
            </div>
            <div className="vis"><Scene p={p} /></div>
          </div>
          )
        }}
      </Pinned>
    </div>
  )
}
