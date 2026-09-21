import React, { useRef } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'

/**
 * Headline that rises word by word out of a mask when it enters the viewport.
 * Visibility is measured on the whole heading, never on a word: each word starts clipped inside
 * its own mask, so it can never count as "in view" by itself.
 */
export default function Words({ children, as: Tag = 'span', delay = 0, stagger = 0.055, className = '', style }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, amount: 0.2 })
  const reduce = useReducedMotion()
  const text = typeof children === 'string' ? children : null
  const parts = text ? text.split(' ') : React.Children.toArray(children)
  const shown = inView || reduce
  return (
    <Tag ref={ref} className={className} style={style}>
      {parts.map((w, i) => (
        <React.Fragment key={i}>
          <span className="w-mask">
            <motion.span
              initial={false}
              animate={{ y: shown ? '0%' : '112%' }}
              transition={{ duration: 0.85, delay: delay + i * stagger, ease: [0.22, 1, 0.36, 1] }}
            >
              {w}
            </motion.span>
          </span>{' '}
        </React.Fragment>
      ))}
    </Tag>
  )
}
