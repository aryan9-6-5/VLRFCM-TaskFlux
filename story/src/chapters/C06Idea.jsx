import React from 'react'
import { motion, useTransform } from 'framer-motion'
import { ChatCircleDots, Hammer, ListChecks, Prohibit, Robot } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Rise, ramp } from '../components/kit.jsx'
import './chapters.css'

// From the bottom up: the robot's own skills, then four questions TaskFlux answers before the robot moves.
const LAYERS = [
  { Icon: ChatCircleDots, title: 'Understand the request', line: 'A change, a clarification, or a stop?', a: 0.42 },
  { Icon: ListChecks, title: 'Decide what to keep', line: 'Keep, take off in order, or leave alone.', a: 0.54 },
  { Icon: Prohibit, title: 'Refuse, and say why', line: 'Name the step that cannot come off.', a: 0.66 },
  { Icon: Hammer, title: 'Keep busy while it waits', line: 'Only work both designs need.', a: 0.78 },
]

export default function C06Idea() {
  return (
    <div id="idea" className="chapter c06">
      <Pinned height={340}>
        {(p) => {
          const frame = useTransform(p, ramp(0.36, 0.44))
          return (
            <div className="stage">
              <div className="copy">
                <Block p={p} a={0} b={0.36} first>
                  <h2 className="display d-lg">A robot already has <em>skills.</em></h2>
                  <p className="lede">Picking, placing, fastening. Those stay as they are.</p>
                </Block>
                <Block p={p} a={0.36} b={1} last>
                  <h2 className="display d-lg">TaskFlux adds <em>a thinking layer</em> above them.</h2>
                  <p className="lede">It decides before the robot moves.</p>
                </Block>
              </div>
              <div className="vis">
                <div className="layers">
                  <motion.div className="layers-top" style={{ opacity: frame }}>
                    {LAYERS.slice().reverse().map(({ Icon, title, line, a }) => (
                      <Rise key={title} p={p} a={a} className="slab slab-flux">
                        <Icon size={34} weight="bold" aria-hidden="true" />
                        <span><b>{title}</b><small>{line}</small></span>
                      </Rise>
                    ))}
                  </motion.div>
                  <Rise p={p} a={0.04} className="slab slab-base">
                    <Robot size={34} weight="bold" aria-hidden="true" />
                    <span><b>The robot's own skills</b><small>Unchanged</small></span>
                  </Rise>
                </div>
              </div>
            </div>
          )
        }}
      </Pinned>
    </div>
  )
}
