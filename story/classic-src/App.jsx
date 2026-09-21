import { useEffect, useState } from "react";
import { MotionConfig, motion, useScroll, useSpring } from "framer-motion";
import data from "./data.json";
import Workpiece from "./Workpiece";
import { Broke, Missing, Perception, Problem, Reconcile, Refusal, Results, Search, Triage } from "./chapters";

const NAV = [
  ["problem", "The half-built part"], ["search", "Was it already solved?"], ["reconcile", "What has to come off"],
  ["refusal", "What cannot come off"], ["triage", "Knowing when to act"], ["broke", "What broke along the way"],
  ["perception", "When the robot's eyes are wrong"], ["results", "What it buys"], ["missing", "What is still missing"],
];

function Hero() {
  const roles = {};
  data.steps.forEach((s) => { roles[s.id] = s.group === "shared" ? "keep" : (s.group === "A" ? "leave" : "build"); });
  return (
    <header className="hero">
      <div className="hero-text">
        <motion.h1 initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: "easeOut" }}>How we built TaskFlux</motion.h1>
        <motion.p className="lead" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.25, ease: "easeOut" }}>
          A robot is halfway through building one product when someone asks for another. This is the story of building the part that decides what to do with the half-built one.
        </motion.p>
        <motion.p className="note" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.9 }}>
          Simulated planning layer. No robot and no OpenVLA model. Every number on this page is computed by the project's code.
        </motion.p>
      </div>
      <div className="hero-art"><Workpiece roles={roles} stagger showCovers label="Two gearbox variants sharing most of their steps" /></div>
      <motion.div className="cue" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.6 }} aria-hidden="true">
        <motion.span animate={{ y: [0, 8, 0] }} transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}>Scroll</motion.span>
      </motion.div>
    </header>
  );
}

function Nav() {
  const [active, setActive] = useState("");
  useEffect(() => {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) setActive(e.target.id); }), { rootMargin: "-45% 0px -45% 0px" });
    NAV.forEach(([id]) => { const el = document.getElementById(id); if (el) io.observe(el); });
    return () => io.disconnect();
  }, []);
  return (
    <nav className="nav" aria-label="Chapters">
      {NAV.map(([id, name]) => (
        <a key={id} href={`#${id}`} className={active === id ? "on" : ""} aria-label={name} aria-current={active === id ? "true" : undefined}>
          <span className="tip">{name}</span>
        </a>
      ))}
    </nav>
  );
}

function Outro() {
  return (
    <footer className="outro">
      <h2>Run it yourself</h2>
      <p>Everything on this page comes from code in the repository. One command reruns the tests and every experiment and gets identical results.</p>
      <pre><code>python -m experiments.reproduce{"\n"}python -m demo.build_demo{"\n"}python story/export_data.py</code></pre>
      <p className="fine">Success rates, timings and damage risks come from a simulator with assumed parameters, so they describe the planning layer, not a robot. Full tables and every error we found are in <b>docs/06-implementation-and-results.md</b>.</p>
    </footer>
  );
}

export default function App() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 120, damping: 24, restDelta: 0.001 });
  return (
    <MotionConfig reducedMotion="user">
      <motion.div className="progress" style={{ scaleX }} aria-hidden="true" />
      <Nav />
      <Hero />
      <main>
        <Problem />
        <Search />
        <Reconcile />
        <Refusal />
        <Triage />
        <Broke />
        <Perception />
        <Results />
        <Missing />
      </main>
      <Outro />
    </MotionConfig>
  );
}
