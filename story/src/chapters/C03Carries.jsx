import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { ArrowLineUp, Armchair, Lock } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Illustration, ramp, ease } from '../components/kit.jsx'
import Car from '../art/Car.jsx'
import { C } from '../tokens.js'
import './chapters.css'

const NAMES = ['chassis', 'wheels', 'motor', 'seats', 'doors', 'paint', 'roof']

/** Each finished part lights up in turn: a part is a decision somebody made. */
function useScan(p, a, b) {
  const out = {}
  NAMES.forEach((n, i) => {
    const s = a + (i * (b - a)) / NAMES.length
    const e = s + (b - a) / NAMES.length
    out[n] = { stroke: useTransform(p, (v) => { const w = Math.sin(Math.PI * ramp(s, e)(v)); return w > 0.05 ? C.accent : C.text }) }
  })
  return out
}

function Scene({ p }) {
  const scan = useScan(p, 0.02, 0.3)
  const lift = useTransform(p, (v) => 46 * ease(ramp(0.36, 0.5)(v)) * (1 - ease(ramp(0.7, 0.78)(v))))
  const rails = useTransform(p, (v) => ramp(0.36, 0.44)(v) * (1 - ramp(0.72, 0.8)(v)))
  const seatStroke = useTransform(p, (v) => (ramp(0.44, 0.5)(v) > 0.5 && ramp(0.68, 0.72)(v) < 0.5 ? C.keep : C.text))
  const paintStroke = useTransform(p, (v) => (ramp(0.76, 0.82)(v) > 0.5 ? C.limit : C.text))
  const paintFill = useTransform(p, (v) => 1)
  const lock = useTransform(p, ramp(0.78, 0.86))
  const lockY = useTransform(lock, (v) => 10 * (1 - v))
  const chip1 = useTransform(p, (v) => 0.35 + 0.65 * (ramp(0.34, 0.42)(v) * (1 - ramp(0.66, 0.72)(v))))
  const chip2 = useTransform(p, (v) => 0.35 + 0.65 * (ramp(0.44, 0.5)(v) * (1 - ramp(0.66, 0.72)(v))))
  const chip3 = useTransform(p, (v) => 0.35 + 0.65 * ramp(0.76, 0.84)(v))
  return (
    <div className="carstage">
      <div className="carstage-art">
        <Car label="A finished car: chassis, wheels, motor, seats, doors, paint and roof" parts={{
          chassis: scan.chassis, wheels: scan.wheels, motor: scan.motor, seats: { stroke: seatStroke }, doors: scan.doors,
          paint: { stroke: paintStroke, o: paintFill }, roof: { y: useTransform(lift, (v) => -v) }, rails: { o: rails },
        }} />
        <motion.div className="lockbadge" style={{ opacity: lock, y: lockY }} aria-label="cured paint cannot come off"><Lock size={26} weight="bold" aria-hidden="true" /></motion.div>
      </div>
      <div className="legend">
        <motion.span className="lg" style={{ opacity: chip1 }}><ArrowLineUp size={20} weight="bold" aria-hidden="true" />Roof</motion.span>
        <motion.span className="lg" style={{ opacity: chip2 }}><Armchair size={20} weight="bold" aria-hidden="true" />Seats</motion.span>
        <motion.span className="lg lg-limit" style={{ opacity: chip3 }}><Lock size={20} weight="bold" aria-hidden="true" />Paint</motion.span>
      </div>
      <Illustration />
    </div>
  )
}

export default function C03Carries() {
  return (
    <div id="carries" className="chapter c03">
      <Pinned height={360}>
        {(p) => (
          <div className="stage">
            <div className="copy">
              <Block p={p} a={0} b={0.34} first>
                <h2 className="display d-lg">Every finished part is <em>a decision.</em></h2>
                <p className="lede">Some are still right. Some are not.</p>
              </Block>
              <Block p={p} a={0.34} b={0.68}>
                <h2 className="display d-lg">Some parts sit <em>on top</em> of others.</h2>
                <p className="lede">The roof covers the seats.</p>
              </Block>
              <Block p={p} a={0.68} b={1} last>
                <h2 className="display d-lg">Some cannot come off <em>at all.</em></h2>
                <p className="lede">Cured paint stays cured.</p>
              </Block>
            </div>
            <div className="vis"><Scene p={p} /></div>
          </div>
        )}
      </Pinned>
    </div>
  )
}
