import React, { useEffect, useState } from 'react'
import { motion, useScroll, useSpring } from 'framer-motion'
import { CHAPTERS, GROUPS } from '../data/chapters.js'
import './nav.css'

const label = (g) => g.charAt(0) + g.slice(1).toLowerCase()

/** Minimal floating rail: five acts and a progress line. No chapter numbers, no counters. */
export default function Nav() {
  const [active, setActive] = useState(0)
  const { scrollYProgress } = useScroll()
  const fill = useSpring(scrollYProgress, { stiffness: 180, damping: 32, mass: 0.3 })

  useEffect(() => {
    let raf = 0
    const measure = () => {
      raf = 0
      const mid = window.innerHeight * 0.5
      let idx = 0
      CHAPTERS.forEach((c, i) => {
        const el = document.getElementById(c.id)
        if (el && el.getBoundingClientRect().top <= mid) idx = i
      })
      setActive(idx)
    }
    const on = () => { if (!raf) raf = requestAnimationFrame(measure) }
    measure()
    window.addEventListener('scroll', on, { passive: true })
    window.addEventListener('resize', on)
    return () => { window.removeEventListener('scroll', on); window.removeEventListener('resize', on); cancelAnimationFrame(raf) }
  }, [])

  const chapter = CHAPTERS[active]
  const go = (group) => {
    const target = CHAPTERS.find((c) => c.group === group)
    document.getElementById(target.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <>
      <motion.div className="progress-line" style={{ scaleX: fill }} aria-hidden="true" />
      <a className="wordmark" href="#start" aria-label="TaskFlux, back to start">TaskFlux</a>
      <nav className="rail" aria-label="Story progress">
        {GROUPS.map((g) => {
          const on = chapter.group === g
          return (
            <button key={g} className={`rail-item ${on ? 'on' : ''}`} onClick={() => go(g)} aria-current={on ? 'step' : undefined}>
              <span className="rail-label">{label(g)}</span>
              <span className="rail-dot" />
            </button>
          )
        })}
      </nav>
    </>
  )
}
