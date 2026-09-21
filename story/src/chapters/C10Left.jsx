import React from 'react'
import { Check, Cpu, Eye, Hourglass, Microphone, Prohibit, Robot, Ruler, TestTube, TreeStructure, UsersThree, ChatCircleDots } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Rise, Tag } from '../components/kit.jsx'
import { F } from '../data/evidence.js'
import './chapters.css'

// What is done and what is left, taken from docs/06 (status, threats to validity) and docs/07 (section 6, next steps).
// Each "left" item is quoted from docs/07 in evidence.json, and tests/test_story_data.py checks the quote is still there.
const DONE = [
  [TreeStructure, 'Takes off only what has to come off', `With a proof, checked on ${F.random_processes.value} random processes`],
  [ChatCircleDots, 'Decides to act, ask or wait', 'By what a wrong move would cost'],
  [Prohibit, 'Says no, and why', 'When a step cannot be undone'],
  [TestTube, `${F.tests.value} automated tests`, 'Every experiment gives the same result on every run'],
]
const NOT_YET = [
  [Robot, 'A real robot', 'Everything so far is a simulator'],
  [Cpu, 'The real robot brain', 'The 7B OpenVLA model does not fit our 4 GB GPU'],
  [Eye, 'A camera that checks each step', 'Its mistakes are assumed, not measured'],
  [UsersThree, 'Someone else checking what can be undone', 'We wrote both processes ourselves'],
  [Microphone, 'Real operator speech', 'We wrote every sentence ourselves'],
  [Ruler, 'Real robot geometry', 'A stub, not robot kinematics'],
]
const NEXT = [
  ['1', Robot, 'A real policy in the loop', 'On rented GPU time, so undo and rebuild success are measured, not assumed.'],
  ['2', Eye, 'A vision check of each step', 'With its own measured error rate.'],
  ['3', UsersThree, 'An independent check', 'Someone else marks what can be undone. About an hour of their time.'],
]

function Row({ p, a, Icon, title, line, mark: Mark, tone }) {
  return (
    <Rise p={p} a={a} rise={12} className={`todo-item ${tone}`}>
      <Icon size={30} weight="bold" aria-hidden="true" />
      <span><b>{title}</b><small>{line}</small></span>
      <Mark className="mark" size={20} weight="bold" aria-hidden="true" />
    </Rise>
  )
}

export default function C10Left() {
  return (
    <div id="left" className="chapter c10">
      <Pinned height={380}>
        {(p) => (
          <div className="stage">
            <div className="copy">
              <Block p={p} a={0} b={0.3} first>
                <h2 className="display d-lg">What works, <em>in simulation.</em></h2>
                <p className="lede">Four things, all tested.</p>
              </Block>
              <Block p={p} a={0.3} b={0.64}>
                <h2 className="display d-lg">What is <em>not done yet.</em></h2>
                <p className="lede">Every number so far comes from a simulator.</p>
              </Block>
              <Block p={p} a={0.64} b={1} last>
                <h2 className="display d-lg">What comes <em>next.</em></h2>
                <p className="lede">The first two turn a simulation into a system.</p>
              </Block>
            </div>
            <div className="vis">
              <div className="scenes">
                <Rise p={p} a={0.02} b={0.3} rise={14} className="scene">
                  <div className="todo done">{DONE.map(([Icon, t, l], i) => <Row key={t} p={p} a={0.04 + i * 0.04} Icon={Icon} title={t} line={l} mark={Check} tone="done" />)}</div>
                </Rise>
                <Rise p={p} a={0.32} b={0.64} rise={14} className="scene">
                  <div className="todo open">{NOT_YET.map(([Icon, t, l], i) => <Row key={t} p={p} a={0.34 + i * 0.03} Icon={Icon} title={t} line={l} mark={Hourglass} tone="open" />)}</div>
                </Rise>
                <Rise p={p} a={0.66} rise={14} className="scene">
                  <ol className="road">
                    {NEXT.map(([n, Icon, t, l], i) => (
                      <Rise key={t} p={p} a={0.68 + i * 0.05} rise={12} as="li" className="road-item">
                        <b className="road-n tnum">{n}</b>
                        <Icon size={30} weight="bold" aria-hidden="true" />
                        <span><b>{t}</b><small>{l}</small></span>
                      </Rise>
                    ))}
                  </ol>
                  <Tag kind="real">From the project record: docs/07, section 6, next steps.</Tag>
                </Rise>
              </div>
            </div>
          </div>
        )}
      </Pinned>
    </div>
  )
}
