import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { ArrowRight, Scales, Trash, WarningOctagon } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Illustration, ramp, ease } from '../components/kit.jsx'
import Car from '../art/Car.jsx'
import { PROBLEM } from '../data/evidence.js'
import { C } from '../tokens.js'
import './chapters.css'

const NAMES = ['chassis', 'wheels', 'motor', 'seats', 'doors', 'paint', 'roof']
const N = PROBLEM.done.length
const OFF = (k) => PROBLEM.strategies[k].undone.length

/** A set of finished parts thrown away one after another, between progress a and b. */
function useScrap(p, a, b, names = NAMES) {
  const out = {}
  names.forEach((n, i) => {
    const s = a + (i * (b - a) * 0.5) / names.length
    const e = s + (b - a) * 0.5
    out[n] = { o: useTransform(p, (v) => 1 - ramp(s + (e - s) * 0.5, e)(v)), y: useTransform(p, (v) => 70 * ease(ramp(s, e)(v))) }
  })
  return out
}

// The three usual answers, one after another: start over (all of it comes off), compare build orders (nearly all of it),
// carry on (none of it, so the new roof lands on the old one).
export default function C04Answers() {
  return (
    <div id="answers" className="chapter c04">
      <Pinned height={420}>
        {(p) => {
          const scrapAll = useScrap(p, 0.22, 0.44)
          const scrapMost = useScrap(p, 0.46, 0.66, NAMES.filter((n) => n !== 'chassis'))
          const bin1 = useTransform(p, ramp(0.2, 0.26))
          const bin2 = useTransform(p, ramp(0.44, 0.5))
          const roofDrop = useTransform(p, (v) => -70 * (1 - ease(ramp(0.7, 0.86)(v))))
          const roofO = useTransform(p, ramp(0.7, 0.76))
          const hit = useTransform(p, ramp(0.86, 0.92))
          const hitStroke = useTransform(p, (v) => (ramp(0.86, 0.9)(v) > 0.5 ? C.undo : C.text))
          const cap1 = useTransform(p, (v) => 0.4 + 0.6 * ramp(0.2, 0.26)(v))
          const cap2 = useTransform(p, (v) => 0.4 + 0.6 * ramp(0.44, 0.5)(v))
          const cap3 = useTransform(p, (v) => 0.4 + 0.6 * ramp(0.68, 0.74)(v))
          return (
            <div className="stage stage-wide">
              <div className="copy">
                <Block p={p} a={0} b={0.22} first>
                  <h2 className="display d-lg">Three usual answers. <em>All go wrong.</em></h2>
                </Block>
                <Block p={p} a={0.22} b={0.46}>
                  <h2 className="display d-lg">Start over: good work <em>is scrapped.</em></h2>
                  <p className="lede">All {OFF('B2')} of {N} finished steps come off.</p>
                </Block>
                <Block p={p} a={0.46} b={0.68}>
                  <h2 className="display d-lg">Compare build orders: <em>too much comes off.</em></h2>
                  <p className="lede">It undoes every step that sits differently in the two plans: {OFF('B3b')} of {N}, to keep one.</p>
                </Block>
                <Block p={p} a={0.68} b={1} last>
                  <h2 className="display d-lg">Carry on: the new roof <em>hits the old one.</em></h2>
                  <p className="lede">The plan forgot what was already built.</p>
                </Block>
              </div>
              <div className="vis">
                <div className="duo">
                  <div className="duo-col">
                    <motion.span className="lg lg-undo" style={{ opacity: cap1 }}><Trash size={20} weight="bold" aria-hidden="true" />Start over</motion.span>
                    <div className="carstage-art">
                      <Car label="A car whose finished parts are all being scrapped" parts={scrapAll} />
                      <motion.div className="bin" style={{ opacity: bin1 }} aria-label="scrap bin"><Trash size={34} weight="bold" aria-hidden="true" /></motion.div>
                    </div>
                  </div>
                  <div className="duo-col">
                    <motion.span className="lg lg-undo" style={{ opacity: cap2 }}><Scales size={20} weight="bold" aria-hidden="true" />Compare build orders</motion.span>
                    <div className="carstage-art">
                      <Car label="A car whose finished parts are all scrapped except the chassis" parts={{ ...scrapMost, shell: scrapMost.paint, tailLight: scrapMost.paint }} />
                      <motion.div className="bin" style={{ opacity: bin2 }} aria-label="scrap bin"><Trash size={34} weight="bold" aria-hidden="true" /></motion.div>
                    </div>
                  </div>
                  <div className="duo-col">
                    <motion.span className="lg" style={{ opacity: cap3 }}><ArrowRight size={20} weight="bold" aria-hidden="true" />Carry on</motion.span>
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
