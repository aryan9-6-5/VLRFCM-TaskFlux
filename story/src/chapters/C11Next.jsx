import React, { useState } from 'react'
import { useMotionValueEvent } from 'framer-motion'
import { Hourglass } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Tag } from '../components/kit.jsx'
import Concept from '../art/Concept.jsx'
import './chapters.css'

// The next question, drawn as a car line. It is an idea: the planner handles one process at a time.
const BEATS = [
  ['The design changes mid-build.', 'What if many robots share the same car?'],
  ['Every robot gets the same snapshot.', 'The problem splits into four parallel lanes.'],
  ['Four small problems, four lanes.', 'Each robot takes one, side by side.'],
  ['A lock stops one lane.', 'Cured paint stays. Order settles a clash.'],
  ['One line, new roofline.', 'The untouched dots did not change.'],
]
// The drawing has nine states; each beat shows the last state it explains.
const STEP_OF = [0, 2, 4, 6, 8]
const N = BEATS.length

function Stage({ p }) {
  const [step, setStep] = useState(0)
  useMotionValueEvent(p, 'change', (v) => setStep(STEP_OF[Math.max(0, Math.min(N - 1, Math.floor(v * N)))]))
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
