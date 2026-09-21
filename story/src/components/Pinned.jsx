import React, { useRef } from 'react'
import { useMotionValue, useReducedMotion, useScroll } from 'framer-motion'

/**
 * A tall scroll track with a sticky viewport-sized stage. Children receive a
 * MotionValue (0→1) describing how far the visitor has scrolled through the
 * track. With reduced motion the stage is not pinned and progress rests at 1,
 * so every scene shows its final, fully explained state.
 */
export default function Pinned({ height = 300, id, className = '', children, offset, paper, rest = 1 }) {
  const ref = useRef(null)
  const reduce = useReducedMotion()
  const resting = useMotionValue(rest)
  const { scrollYProgress } = useScroll({ target: ref, offset: offset || ['start start', 'end end'] })
  const progress = reduce ? resting : scrollYProgress
  return (
    <section ref={ref} id={id} data-paper={paper ? '' : undefined} className={`pin ${reduce ? 'is-static' : ''} ${className}`} style={reduce ? undefined : { height: `${height}vh` }}>
      <div className="pin-stick">{children(progress)}</div>
    </section>
  )
}
