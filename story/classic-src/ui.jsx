import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useMotionValueEvent, useReducedMotion, useScroll } from "framer-motion";

/**
 * A scroll-pinned chapter. The section is tall; inside it a 100vh stage stays put while the scroll
 * position walks through `steps`. The text column swaps per step, and the visual receives the current
 * step plus the raw scroll progress (a MotionValue) so it can animate both discretely and continuously.
 */
export function Chapter({ id, title, steps, children }) {
  const ref = useRef(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const [step, setStep] = useState(0);
  useMotionValueEvent(scrollYProgress, "change", (v) => {
    const s = Math.max(0, Math.min(steps.length - 1, Math.floor(v * steps.length)));
    setStep((p) => (p === s ? p : s));
  });
  return (
    <section ref={ref} id={id} className="chapter" style={{ height: `${steps.length * 90 + 30}vh` }} aria-labelledby={`${id}-t`}>
      <div className="pin">
        <div className="col text">
          <h2 id={`${id}-t`} className="ch-title">{title}</h2>
          <div className="step" aria-live="polite">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={step}
                initial={{ opacity: 0, y: reduce ? 0 : 18 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: reduce ? 0 : -12 }}
                transition={{ duration: 0.26, ease: "easeOut" }}
              >
                <h3>{steps[step].title}</h3>
                <p>{steps[step].body}</p>
              </motion.div>
            </AnimatePresence>
          </div>
          <ol className="dots" aria-hidden="true">
            {steps.map((_, i) => (
              <motion.li key={i} initial={false} animate={{ scaleX: i <= step ? 1 : 0.35, opacity: i <= step ? 1 : 0.45 }} />
            ))}
          </ol>
        </div>
        <div className="col visual">{children({ step, progress: scrollYProgress })}</div>
      </div>
    </section>
  );
}

/** Types text out once `run` becomes true. Shows it all at once for reduced-motion users. */
export function Typewriter({ text, run, speed = 2 }) {
  const reduce = useReducedMotion();
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!run) { setN(0); return undefined; }
    if (reduce) { setN(text.length); return undefined; }
    let i = 0;
    const t = setInterval(() => {
      i += speed;
      setN(Math.min(i, text.length));
      if (i >= text.length) clearInterval(t);
    }, 22);
    return () => clearInterval(t);
  }, [run, text, reduce, speed]);
  return (
    <span>
      {text.slice(0, n)}
      {run && n < text.length ? <span className="caret" aria-hidden="true" /> : null}
    </span>
  );
}

/** Horizontal bars whose widths animate. Rows with show=false collapse and fade. */
export function Bars({ rows, max }) {
  return (
    <div className="bars">
      {rows.map((r) => {
        const on = r.show !== false;
        return (
          <motion.div
            key={r.key}
            className={`bar-row${r.strong ? " strong" : ""}`}
            initial={false}
            animate={{ opacity: on ? 1 : 0, y: on ? 0 : 10 }}
            transition={{ duration: 0.35 }}
          >
            <div className="bar-name">{r.label}</div>
            <div className="bar-track">
              <motion.div
                className="bar-fill"
                style={{ background: r.color }}
                initial={false}
                animate={{ width: on ? `${Math.max(1.2, (r.value / max) * 100)}%` : "0%" }}
                transition={{ duration: 0.8, ease: [0.2, 0.7, 0.2, 1], delay: on ? (r.delay || 0) : 0 }}
              />
            </div>
            <div className="bar-val">{r.display}</div>
            {r.note ? <div className="bar-note">{r.note}</div> : null}
          </motion.div>
        );
      })}
    </div>
  );
}
