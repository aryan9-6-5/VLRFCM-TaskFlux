import React from 'react'
import { ArrowRight, ArrowSquareOut, Code, FileText, GithubLogo, MonitorPlay, Question } from '@phosphor-icons/react'
import './chapters.css'

const SOURCES = [
  ['experiments/results/results.md', 'Every timing and success figure (E1, E8)'],
  ['story/scripts/build_data.py', 'Builds each number on this page'],
  ['docs/06-implementation-and-results.md', 'Errors found and claims withdrawn'],
]

export default function Outro() {
  return (
    <footer className="outro">
      <p className="outro-scope">One simulated gearbox, one robot, assumed rates. Recorded runs, not a live cell. Nothing here has run on a real robot.</p>
      <h2 className="display d-md">Go deeper</h2>
      <div className="links">
        <a href="./demo/index.html"><MonitorPlay size={34} weight="duotone" aria-hidden="true" /><b>Try the demo</b><span>Drag a slider, change the order</span><ArrowRight className="go" size={20} weight="bold" aria-hidden="true" /></a>
        <a href="./classic/index.html"><Code size={34} weight="duotone" aria-hidden="true" /><b>Technical story</b><span>The earlier, detailed version</span><ArrowRight className="go" size={20} weight="bold" aria-hidden="true" /></a>
        <a href="https://github.com/aryan9-6-5/VLRFCM-TaskFlux"><GithubLogo size={34} weight="duotone" aria-hidden="true" /><b>Source code</b><span>Code, tests and docs</span><ArrowSquareOut className="go" size={20} weight="bold" aria-hidden="true" /></a>
      </div>
      <h3>Where the numbers come from</h3>
      <ul className="sources">
        {SOURCES.map(([f, d]) => <li key={f}><FileText size={22} weight="duotone" aria-hidden="true" /><code>{f}</code><span>{d}</span></li>)}
      </ul>
      <p className="fine"><Question size={18} weight="bold" aria-hidden="true" /> Drawings of a car are illustrations. The measured numbers come from a simulated gearbox.</p>
    </footer>
  )
}
