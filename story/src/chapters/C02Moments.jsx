import React from 'react'
import { ArrowsClockwise, Car, DeviceMobile, Armchair, PencilSimple } from '@phosphor-icons/react'
import Pinned from '../components/Pinned.jsx'
import { Block, Rise, Tag } from '../components/kit.jsx'
import './chapters.css'

const MOMENTS = [
  { Icon: Car, name: 'A car line', change: 'A new roofline', a: 0.18 },
  { Icon: DeviceMobile, name: 'A phone line', change: 'A different camera', a: 0.36 },
  { Icon: Armchair, name: 'A furniture line', change: 'Another armrest', a: 0.54 },
]

/** A ring that is half full: the product is half built when the change lands. */
function Half() {
  return (
    <svg viewBox="0 0 44 44" width="44" height="44" aria-hidden="true">
      <circle cx="22" cy="22" r="17" fill="none" stroke="var(--line-strong)" strokeWidth="5" />
      <circle cx="22" cy="22" r="17" fill="none" stroke="var(--keep)" strokeWidth="5" strokeLinecap="round" strokeDasharray="53.4 106.8" transform="rotate(-90 22 22)" />
    </svg>
  )
}

export default function C02Moments() {
  return (
    <div id="moments" className="chapter c02">
      <Pinned height={300}>
        {(p) => (
          <div className="stage stage-wide">
            <div className="copy">
              <Block p={p} a={0} b={1} first last>
                <h2 className="display d-lg">It happens <em>all the time.</em></h2>
                <p className="lede">On a line that builds many variants, the plan changes mid-build.</p>
              </Block>
            </div>
            <div className="vis">
              <div className="moments">
                {MOMENTS.map(({ Icon, name, change, a }) => (
                  <Rise key={name} p={p} a={a} className="mcard">
                    <div className="mcard-top"><Icon size={64} weight="duotone" aria-hidden="true" /><Half /></div>
                    <b>{name}</b>
                    <span className="mcard-change"><ArrowsClockwise size={18} weight="bold" aria-hidden="true" />{change}</span>
                  </Rise>
                ))}
                <Rise p={p} a={0.7} className="moments-tag"><Tag Icon={PencilSimple}>Conceptual scenes, not data</Tag></Rise>
              </div>
            </div>
          </div>
        )}
      </Pinned>
    </div>
  )
}
