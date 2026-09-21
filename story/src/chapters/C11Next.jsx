import React, { useState } from 'react'
import { useMotionValueEvent } from 'framer-motion'
import { Hourglass } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Tag } from '../components/kit.jsx'
import Concept from '../art/Concept.jsx'
import './chapters.css'

// The next question, drawn as a car line. It is an idea: the planner handles one process at a time.
const BEATS = [
  ['What if many robots share it?', 'Everyone starts from the same car.'],
  ['Then the design changes.', 'A new roofline arrives.'],
  ['Every robot gets the same snapshot.', 'Same finished parts, same starting point.'],
  ['Four small problems, four lanes.', 'Each robot takes one.'],
  ['Robots work side by side.', 'Their dots fill in.'],
  ['Cured paint cannot come off.', 'That lane stops at the lock.'],
  ['Two robots want one part.', 'The order settles it.'],
  ['Undo in reverse, then rebuild.', 'Roof off first. Then the new roof.'],
  ['One line, new roofline.', 'The untouched dots did not change.'],
]
const N = BEATS.length

function Stage({ p }) {
  const [step, setStep] = useState(0)
  useMotionValueEvent(p, 'change', (v) => setStep(Math.max(0, Math.min(N - 1, Math.floor(v * N)))))
  return (
    <div className="stage">
      <div className="copy">
        {BEATS.map(([h, l], i) => (
          <Block key={h} p={p} a={i / N} b={(i + 1) / N} first={i === 0} last={i === N - 1}>
            <h2 className="display d-md">{h}</h2>
            <p className="lede">{l}</p>
            {i === N - 1 ? <p className="lede next-tag"><Tag kind="idea" Icon={Hourglass}>Not built yet</Tag></p> : null}
          </Block>
        ))}
      </div>
      <div className="vis">
        <div className="concept">
          <Concept step={step} />
          <Tag kind="idea">An idea, drawn to explain. Not built or measured.</Tag>
        </div>
      </div>
    </div>
  )
}

export default function C11Next() {
  return (
    <div id="next" className="chapter c11">
      <Pinned height={N * 82}>{(p) => <Stage p={p} />}</Pinned>
    </div>
  )
}
