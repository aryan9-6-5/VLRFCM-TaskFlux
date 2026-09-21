import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { ArrowRight, Trash, WarningOctagon } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Illustration, ramp, ease } from '../components/kit.jsx'
import Car from '../art/Car.jsx'
import { C } from '../tokens.js'
import './chapters.css'

const NAMES = ['chassis', 'wheels', 'motor', 'seats', 'doors', 'paint', 'roof']

/** "Start over": every finished part is thrown away, one after another. */
function useScrap(p, a, b) {
  const out = {}
  NAMES.forEach((n, i) => {
    const s = a + (i * (b - a) * 0.5) / NAMES.length
    const e = s + (b - a) * 0.5
    out[n] = { o: useTransform(p, (v) => 1 - ramp(s + (e - s) * 0.5, e)(v)), y: useTransform(p, (v) => 70 * ease(ramp(s, e)(v))) }
  })
  return out
}

export default function C04Answers() {
  return (
    <div id="answers" className="chapter c04">
      <Pinned height={340}>
        {(p) => {
          const scrap = useScrap(p, 0.08, 0.4)
          const bin = useTransform(p, ramp(0.06, 0.14))
          const roofDrop = useTransform(p, (v) => -70 * (1 - ease(ramp(0.5, 0.7)(v))))
          const roofO = useTransform(p, ramp(0.5, 0.56))
          const hit = useTransform(p, ramp(0.7, 0.78))
          const hitStroke = useTransform(p, (v) => (ramp(0.7, 0.76)(v) > 0.5 ? C.undo : C.text))
          const capL = useTransform(p, (v) => 0.4 + 0.6 * ramp(0.06, 0.14)(v))
          const capR = useTransform(p, (v) => 0.4 + 0.6 * ramp(0.46, 0.54)(v))
          return (
            <div className="stage stage-wide">
              <div className="copy">
                <Block p={p} a={0} b={0.34} first>
                  <h2 className="display d-lg">Start over, or carry on. <em>Both go wrong.</em></h2>
                </Block>
                <Block p={p} a={0.34} b={0.66}>
                  <h2 className="display d-lg">Start over: good work <em>is scrapped.</em></h2>
                  <p className="lede">Every finished part goes in the bin.</p>
                </Block>
                <Block p={p} a={0.66} b={1} last>
                  <h2 className="display d-lg">Carry on: the new roof <em>hits the old one.</em></h2>
                  <p className="lede">The plan forgot what was already built.</p>
                </Block>
              </div>
              <div className="vis">
                <div className="duo">
                  <div className="duo-col">
                    <motion.span className="lg lg-undo" style={{ opacity: capL }}><Trash size={20} weight="bold" aria-hidden="true" />Start over</motion.span>
                    <div className="carstage-art">
                      <Car label="A car whose finished parts are being scrapped one by one" parts={scrap} />
                      <motion.div className="bin" style={{ opacity: bin }} aria-label="scrap bin"><Trash size={34} weight="bold" aria-hidden="true" /></motion.div>
                    </div>
                  </div>
                  <div className="duo-col">
                    <motion.span className="lg" style={{ opacity: capR }}><ArrowRight size={20} weight="bold" aria-hidden="true" />Carry on</motion.span>
                    <div className="carstage-art">
                      <Car label="A new roof lowered onto a car that already has a roof" parts={{ roof: { stroke: hitStroke }, newRoof: { o: roofO, y: roofDrop, stroke: hitStroke } }} />
                      <motion.div className="boom" style={{ opacity: hit }} aria-label="collision"><WarningOctagon size={38} weight="fill" aria-hidden="true" /></motion.div>
                    </div>
                  </div>
                  <div className="duo-tag"><Illustration /></div>
                </div>
              </div>
            </div>
          )
        }}
      </Pinned>
    </div>
  )
}
