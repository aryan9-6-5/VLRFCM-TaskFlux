import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { ArrowsClockwise } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Illustration, Rise, ramp, ease } from '../components/kit.jsx'
import Car from '../art/Car.jsx'
import Arm from '../art/Arm.jsx'
import './chapters.css'

const pulse = (v, a, b) => Math.pow(Math.sin(Math.PI * ramp(a, b)(v)), 0.6)

/** A part slides in along its own axis and fades up over [a, b]. */
function usePart(p, [a, b], dx = 0, dy = 0, min = 0) {
  const o = useTransform(p, (v) => min + (1 - min) * ramp(a, b)(v))
  const x = useTransform(p, (v) => dx * (1 - ease(ramp(a, b)(v))))
  const y = useTransform(p, (v) => dy * (1 - ease(ramp(a, b)(v))))
  return { o, x, y }
}

/** The hand of an arm rests, then reaches for the part it is fitting while that part arrives. */
function useReach(p, rest, jobs) {
  const at = (v, k) => {
    let best = null
    for (const [a, b, t] of jobs) { const w = pulse(v, a, b); if (w > 0.001 && (!best || w > best.w)) best = { w, t } }
    return best ? rest[k] + (best.t[k] - rest[k]) * best.w : rest[k]
  }
  return [useTransform(p, (v) => at(v, 0)), useTransform(p, (v) => at(v, 1))]
}

// Where each part sits in the scene (the car is drawn at 1.385x, origin 150,170).
const T = { chassis: [0.05, 0.1], wheels: [0.1, 0.15], motor: [0.15, 0.2], seats: [0.2, 0.25], doors: [0.25, 0.3] }

function Scene({ p }) {
  const chassis = usePart(p, T.chassis, 0, 34)
  const wheels = usePart(p, T.wheels, 0, 44)
  const motor = usePart(p, T.motor, 50, 0)
  const seats = usePart(p, T.seats, 0, -46)
  const doors = usePart(p, T.doors, -30, 0)
  const oldGhost = useTransform(p, (v) => ramp(0.3, 0.34)(v) * (1 - ramp(0.7, 0.76)(v)))
  const newGhost = useTransform(p, ramp(0.7, 0.78))
  const [lx, ly] = useReach(p, { 0: 175, 1: 250 }, [[T.chassis[0], T.chassis[1], { 0: 262, 1: 305 }], [T.wheels[0], T.wheels[1], { 0: 245, 1: 300 }]])
  const [rx, ry] = useReach(p, { 0: 490, 1: 250 }, [[T.motor[0], T.motor[1], { 0: 448, 1: 262 }], [T.doors[0], T.doors[1], { 0: 372, 1: 256 }]])
  const [tx, ty] = useReach(p, { 0: 340, 1: 150 }, [[T.seats[0], T.seats[1], { 0: 300, 1: 222 }]])
  const chip = useTransform(p, ramp(0.7, 0.78))
  const chipY = useTransform(chip, (v) => 14 * (1 - v))
  return (
    <div className="hero-art">
      <svg viewBox="40 16 570 340" className="art" role="img" aria-label="A robot line builds a car. Chassis, wheels, motor, seats and doors are done. Then the design changes: a new roofline is planned in place of the old one.">
        <rect x="30" y="322" width="580" height="22" rx="11" fill="var(--bg-2)" stroke="var(--carline)" strokeWidth="3" />
        {Array.from({ length: 14 }, (_, i) => <circle key={i} cx={62 + i * 40} cy="333" r="4" fill="var(--dim)" />)}
        <rect x="316" y="24" width="8" height="34" rx="4" fill="var(--old)" />
        <rect x="120" y="52" width="400" height="8" rx="4" fill="var(--old)" />
        <Car x={150} y={170} width={360} label="The car being built" parts={{
          chassis, wheels, motor, seats, doors, paint: { o: 0.2 }, roof: { o: 0 }, oldGhost: { o: oldGhost }, newGhost: { o: newGhost },
        }} />
        <Arm bx={110} by={334} tx={lx} ty={ly} l1={86} l2={86} bend={1} label="robot arm at the left station" />
        <Arm bx={560} by={334} tx={rx} ty={ry} l1={86} l2={86} bend={-1} label="robot arm at the right station" />
        <Arm bx={340} by={62} tx={tx} ty={ty} l1={86} l2={86} bend={1} label="robot arm on the ceiling rail" />
      </svg>
      <div className="ill-row"><Illustration /></div>
      <motion.div className="chip-float" style={{ opacity: chip, y: chipY }}>
        <ArrowsClockwise size={18} weight="bold" aria-hidden="true" /> New design
      </motion.div>
    </div>
  )
}

export default function C01Start() {
  return (
    <div id="start" className="chapter c01">
      <Pinned height={430}>
        {(p) => (
          <div className="stage">
            <div className="copy">
              <Block p={p} a={0} b={0.34} first>
                <h1 className="display d-lg">A robot line is building <em>a car.</em></h1>
                <p className="lede">One robot at each station.</p>
              </Block>
              <Block p={p} a={0.34} b={0.66}>
                <h1 className="display d-lg">It is <em>half built.</em></h1>
                <p className="lede">Chassis, wheels, motor, seats, doors.</p>
              </Block>
              <Block p={p} a={0.66} b={1} last>
                <h1 className="display d-lg">Then the design <em>changes.</em></h1>
                <p className="lede">What should the robots do with the half-built car?</p>
              </Block>
            </div>
            <div className="vis"><Scene p={p} /></div>
          </div>
        )}
      </Pinned>
    </div>
  )
}
