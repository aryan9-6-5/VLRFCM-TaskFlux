import { AnimatePresence, motion } from "framer-motion";
import data from "./data.json";
import { usePalette } from "./theme";
import Workpiece from "./Workpiece";
import { Bars, Chapter, Typewriter } from "./ui";

const S = Object.fromEntries(data.steps.map((s) => [s.id, s]));
const lab = (id) => S[id].label;
const MINUS = "−";
const pct = (x) => `${Math.round(x * 100)}%`;
const R = data.results;

/* ---------------------------------------------------------------- 1. the problem */
const SHORT = { base: "base", sticker_a: "label", bearing: "bearing", shaft: "shaft", connector: "connector", cover: "cover" };
const STRATS = [
  { key: "B2", name: "Start over", say: (u) => `Throws away all ${u.length} steps` },
  { key: "B3b", name: "Compare the two build orders", say: (u, n) => `Takes off ${u.length} of ${n}, keeps ${n - u.length}` },
  { key: "B3a", name: "Plan B on top of what is there", say: () => "Collides while seating the B housing" },
  { key: "TF", name: "TaskFlux", say: () => "Takes off one step: the cover plate" },
];

function Strategies({ step }) {
  const pal = usePalette();
  const P = data.problem;
  return (
    <div className="strats">
      {STRATS.map((s, r) => {
        const show = step >= 2 && (s.key !== "TF" || step >= 3);
        const undone = new Set(P.strategies[s.key].undone);
        return (
          <motion.div key={s.key} className={`strat${s.key === "TF" ? " tf" : ""}`} initial={false}
            animate={{ opacity: show ? 1 : 0, y: show ? 0 : 14 }} transition={{ duration: 0.4, delay: show ? r * 0.12 : 0 }}>
            <div className="strat-name">{s.name}</div>
            <div className="chips">
              {P.done.map((id, i) => {
                const off = show && undone.has(id);
                return (
                  <motion.span key={id} className="chip" initial={false}
                    animate={{ backgroundColor: off ? pal.undoBg : pal.keepBg, borderColor: off ? pal.undo : pal.keep }}
                    transition={{ duration: 0.35, delay: show ? 0.3 + i * 0.09 : 0 }}>
                    {SHORT[id] || id}
                  </motion.span>
                );
              })}
              {s.key === "B3a" ? (
                <motion.span className="chip crash" initial={false} animate={{ opacity: show ? 1 : 0, scale: show ? 1 : 0.6 }} transition={{ delay: 1.1, type: "spring" }}>
                  B housing {"✕"}
                </motion.span>
              ) : null}
            </div>
            <div className="strat-say">{s.say([...undone], P.done.length)}</div>
          </motion.div>
        );
      })}
    </div>
  );
}

export function Problem() {
  const P = data.problem;
  const done = new Set(P.done);
  const steps = [
    { title: "A robot is halfway through gearbox A.", body: "Six of its eleven steps are done: a bearing pressed in, a connector seated, a cover fitted. That is real work sitting on the bench." },
    { title: "The operator asks for B.", body: "“Switch to the B housing, skip the foam gasket.” The plan the robot was following no longer says what to build, and the bench is not empty." },
    { title: "Every option we could find is wasteful or unsafe.", body: "Start over and lose six steps. Plan B on top of the old parts and it collides. Compare build orders and it takes off five steps to keep one, needlessly." },
    { title: "Only the cover plate has to come off.", body: "The B housing goes in underneath the cover, so the cover comes off and goes back on later. Everything else stays. Working that out for any process, fast and provably, is what TaskFlux does." },
  ];
  return (
    <Chapter id="problem" title="The half-built part" steps={steps}>
      {({ step }) => {
        const roles = {};
        data.steps.forEach((s) => { roles[s.id] = done.has(s.id) ? "keep" : (step >= 1 && s.group === "B" ? "build" : "skip"); });
        return (
          <div className="v-problem">
            <div className="bubble-slot">
              <AnimatePresence>
                {step >= 1 ? (
                  <motion.blockquote key="b" className="bubble" initial={{ opacity: 0, y: 10, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0 }}>
                    {"“"}{P.utterance}{"”"}
                  </motion.blockquote>
                ) : null}
              </AnimatePresence>
            </div>
            <Workpiece roles={roles} showCovers={step >= 3} label="Gearbox A after six steps" />
            <Strategies step={step} />
          </div>
        );
      }}
    </Chapter>
  );
}

/* ---------------------------------------------------------------- 2. prior art */
const WORKS = [
  ["SwitchVLA", "Switches tasks inside the robot policy, using how far execution has got. Does not decide which finished steps to undo."],
  ["A vision-language replanner", "Replans forward from the execution history. No undo, and no idea that some steps cannot be undone."],
  ["“Do This Instead”", "Generates undo steps when an instruction is corrected, in a rule-based system with no optimality argument."],
  ["Plan repair", "Repairs a partly executed plan in classical planning. Nothing about parts covering each other, or about irreversibility."],
  ["Selective disassembly planning", "Orders removals to reach one part. It is not about a goal replaced in the middle of a build."],
];
const CLAIMS = [
  "The smallest set of steps to take off, proved, with an exact reason when it cannot be done",
  "A choice between acting, asking and carrying on that depends on how much is already built",
  "Work that is safe whichever answer the operator gives, done while it waits",
  "A way to measure all of it, since no benchmark did",
];

export function Search() {
  const steps = [
    { title: "We looked before we built.", body: "The first plan claimed nobody had tackled this. A literature search found five nearby lines of work, and each one stops just short of the half-built part." },
    { title: "So the headline claim was wrong.", body: "“No paper addresses a goal replaced mid-build” is false: recent work touches it. We struck it from the draft." },
    { title: "What is left is smaller, and defensible.", body: "Four contributions survive. Our own assessment is moderate novelty: enough for a workshop paper, not yet a full one." },
  ];
  return (
    <Chapter id="search" title="Was it already solved?" steps={steps}>
      {({ step }) => (
        <div className="v-search">
          <AnimatePresence mode="wait" initial={false}>
            {step === 0 ? (
              <motion.ul key="w" className="works" initial="h" animate="s" exit={{ opacity: 0 }} variants={{ s: { transition: { staggerChildren: 0.11 } } }}>
                {WORKS.map(([n, d]) => (
                  <motion.li key={n} variants={{ h: { opacity: 0, x: 24 }, s: { opacity: 1, x: 0 } }}>
                    <b>{n}</b><span>{d}</span>
                  </motion.li>
                ))}
              </motion.ul>
            ) : null}
            {step === 1 ? (
              <motion.div key="c" className="claim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <p className="claim-text">
                  {"“"}No paper addresses a goal that is withdrawn and replaced in the middle of a build.{"”"}
                  <motion.i className="strike" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.7, delay: 0.5, ease: "easeInOut" }} />
                </p>
                <motion.p className="stamp" initial={{ opacity: 0, rotate: -6, scale: 1.3 }} animate={{ opacity: 1, rotate: -3, scale: 1 }} transition={{ delay: 1.15, type: "spring", stiffness: 300, damping: 18 }}>
                  Too strong. Removed.
                </motion.p>
              </motion.div>
            ) : null}
            {step === 2 ? (
              <motion.ol key="k" className="claims" initial="h" animate="s" exit={{ opacity: 0 }} variants={{ s: { transition: { staggerChildren: 0.14 } } }}>
                {CLAIMS.map((c) => (
                  <motion.li key={c} variants={{ h: { opacity: 0, y: 16 }, s: { opacity: 1, y: 0 } }}>{c}</motion.li>
                ))}
              </motion.ol>
            ) : null}
          </AnimatePresence>
        </div>
      )}
    </Chapter>
  );
}

/* ---------------------------------------------------------------- 3. the reconciler */
export function Reconcile() {
  const plan = data.plans["9"];
  const done = new Set(plan.done);
  const undo = plan.undo;
  const forward = plan.forward;
  const discard = new Set(plan.discard);
  const roots = new Set(undo.filter((id) => S[id].group === "A" || id === "cover"));
  const steps = [
    { title: "Nine steps in, the operator asks for B.", body: "The robot knows which steps are done and what each one sits on. That is all it needs." },
    { title: "Some steps do not belong to B.", body: "The A housing, its screws and the foam gasket are not part of B. The cover plate is in the way of the B housing. None of these can stay." },
    { title: "Whatever is stacked on them comes off first.", body: "Screws before housing, housing before gasket. The order comes from what physically sits on what, so it is never a guess." },
    { title: "Then B is built, in order.", body: "The B housing goes in, the cover goes back on, and the rest of B follows. The kept steps are never touched." },
    { title: "That is the smallest possible set.", body: "Every valid plan has to take off at least these steps. We proved it, then checked it against every alternative on 40 random processes." },
  ];
  return (
    <Chapter id="reconcile" title="What has to come off" steps={steps}>
      {({ step }) => {
        const roles = {}; const badges = {}; let pulse = []; let hot = [];
        data.steps.forEach((s) => {
          const wasDone = done.has(s.id);
          let r = wasDone ? (discard.has(s.id) ? "leave" : "keep") : "skip";
          if (step >= 1 && step <= 3 && undo.includes(s.id) && (step >= 2 || roots.has(s.id))) r = "undo";
          if (step === 3 && forward.includes(s.id) && !wasDone) r = "build";
          if (step === 4) {
            if (forward.includes(s.id)) r = "built";
            else if (wasDone && undo.includes(s.id)) r = "removed";
          }
          roles[s.id] = r;
        });
        if (step === 1) { pulse = [...roots]; hot = ["cover>housing_b"]; }
        if (step >= 2 && step <= 3) undo.forEach((id, i) => { badges[id] = [{ kind: "undo", text: `${MINUS}${i + 1}`, delay: step === 2 ? i * 0.28 : 0 }]; });
        if (step === 3) forward.forEach((id, j) => { badges[id] = [...(badges[id] || []), { kind: "build", text: `+${j + 1}`, delay: 0.15 + j * 0.2 }]; });
        return <Workpiece roles={roles} badges={badges} pulse={pulse} hot={hot} showCovers label="The changeover plan at nine steps" />;
      }}
    </Chapter>
  );
}

/* ---------------------------------------------------------------- 4. the refusal */
export function Refusal() {
  const plan = data.plans["10"];
  const done = new Set(plan.done);
  const steps = [
    { title: "Ten steps in, the seam adhesive has cured.", body: "Some steps cannot be undone. Cured adhesive stays cured, and the robot is told which steps those are." },
    { title: "So it says no, and says why.", body: "Not an error code. The reason names the step that blocks the change, in words the operator can act on." },
    { title: "The part would be scrapped, so it asks first.", body: `Scrapping and rebuilding takes about ${plan.scrap_total} seconds. Restarting is the only option that works, and the robot will not throw away ten steps without a yes.` },
  ];
  return (
    <Chapter id="refusal" title="What cannot come off" steps={steps}>
      {({ step }) => {
        const roles = {}; const badges = {};
        data.steps.forEach((s) => {
          let r = done.has(s.id) ? "keep" : "skip";
          if (step >= 1 && s.id === "adhesive_a") r = "undo";
          if (step === 2) {
            if (done.has(s.id)) r = "lost";
            else if (plan.forward.includes(s.id)) r = "build";
          }
          roles[s.id] = r;
        });
        if (step === 2) plan.forward.forEach((id, j) => { badges[id] = [{ kind: "build", text: `+${j + 1}`, delay: 0.5 + j * 0.15 }]; });
        return (
          <div className="v-refusal">
            <Workpiece roles={roles} badges={badges} lit={["adhesive_a"]} pulse={step === 1 ? ["adhesive_a"] : []} showCovers={false} label="The workpiece after ten steps" />
            <div className="reply">
              <AnimatePresence>
                {step >= 1 ? (
                  <motion.div key="r" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    <p className="say"><Typewriter text={plan.explanation} run={step >= 1} /></p>
                    <motion.span className="tag ask" initial={{ opacity: 0 }} animate={{ opacity: step >= 2 ? 1 : 0 }} transition={{ delay: 0.3 }}>Asks first</motion.span>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
          </div>
        );
      }}
    </Chapter>
  );
}

/* ---------------------------------------------------------------- 5. triage */
const CLASSES = ["clarification", "parameter edit", "changeover", "stop"];
const TAGS = { act: "Acts now", ask: "Asks first", continue: "Carries on with A", halt: "Stops" };
const WHY = {
  act: "It is confident this is a changeover and the plan is safe to run, so it acts without asking.",
  ask: "It is not sure enough to move parts, and a wrong move costs more than a question. Everything left in plan A is specific to A, so there is nothing safe to build while it waits.",
  continue: "It reads this as a clarification, not a new product, so the build carries on.",
  halt: "A stop halts the arm before any cost is weighed. A keyword check guarantees it, because the classifier alone missed 11.5% of stop requests.",
};

export function Triage() {
  const pal = usePalette();
  const T = data.triage;
  const H = data.hedge;
  const steps = [
    { title: "A clear request: it acts.", body: `The classifier puts ${pct(T[0].probs[2])} on a changeover. With no doubt, asking would only cost ${T[0].ca} seconds of the operator’s attention, so the robot acts.` },
    { title: "A vague one: it asks.", body: `Acting on a change that was not one would cost about ${T[1].ra} seconds, and ignoring a real one about ${T[1].rc}. A question costs about ${T[1].ca}. So it asks.` },
    { title: "A clarification is not a change.", body: "“The other screw” is about which screw, not which product. The build carries on." },
    { title: "A stop always wins.", body: "Safety is not weighed against cost. Any stop word halts the arm before anything else is considered." },
    { title: "While it waits, it keeps working.", body: "Steps that both versions need are safe to build whichever answer comes. Here only the bearing and the connector qualify, and the robot builds those instead of standing idle." },
  ];
  return (
    <Chapter id="triage" title="Knowing when to act" steps={steps}>
      {({ step }) => {
        if (step === 4) {
          const roles = {};
          data.steps.forEach((s) => { roles[s.id] = H.done.includes(s.id) ? "keep" : (H.safe.includes(s.id) ? "build" : "skip"); });
          return (
            <div className="v-triage">
              <Workpiece roles={roles} pulse={H.safe} showCovers={false} label="Steps that are safe to build while waiting" />
              <p className="caption">Two steps in. The robot has asked and is waiting: the blue steps are needed by A and by B.</p>
            </div>
          );
        }
        const t = T[step];
        const top = t.probs.indexOf(Math.max(...t.probs));
        return (
          <div className="v-triage">
            <motion.blockquote key={step} className="bubble" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>{"“"}{t.text}{"”"}</motion.blockquote>
            <p className="caption">{t.kind}, said when {t.k} of 11 steps are done.</p>
            <Bars max={1} rows={t.probs.map((p, i) => ({ key: CLASSES[i], label: CLASSES[i], value: p, display: pct(p), color: i === top ? pal.ink : pal.build }))} />
            <div className="decision">
              <motion.span key={`${step}-tag`} className={`tag ${t.action}`} initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }} transition={{ type: "spring", stiffness: 300, damping: 20, delay: 0.5 }}>{TAGS[t.action]}</motion.span>
              <p>{WHY[t.action]}</p>
            </div>
          </div>
        );
      }}
    </Chapter>
  );
}

/* ---------------------------------------------------------------- 6. what broke */
const BROKE = [
  ["Hedging was not zero-regret.", "A step can be ready and still cover something the plan needs first. A property test failed the first definition."],
  ["“Carry on” looked free.", "With the product finished and nothing left to do, a certain changeover request was ignored. Running the demo showed it. No metric did."],
  ["The simulator ended runs at a damaged part.", "The cost model assumed damage meant scrap and rebuild. The mismatch made restart look 15 points worse than it is.", true],
  ["A state can be impossible with every prerequisite present.", "Found when the noise experiment crashed on six steps that each had to come off before another."],
  ["The classifier missed 11.5% of stop requests.", "A keyword check now halts the arm before the classifier is consulted."],
  ["Checking before an undo changed nothing.", "We expected it to help. The harmful mistakes were never on the undo list."],
];

export function Broke() {
  const pal = usePalette();
  const steps = [
    { title: "Tests and a demo caught what the numbers hid.", body: "Fifteen modelling errors were found and fixed. Each one looked fine in an average." },
    { title: "One of them inflated our headline.", body: "The gap we first reported between TaskFlux and restarting came from a simulator inconsistency, not from the planning. We withdrew it." },
    { title: "Two ideas did not survive contact.", body: "A safety rule and a hunch both failed a check. Reporting them keeps the next person from repeating the detour." },
  ];
  return (
    <Chapter id="broke" title="What broke along the way" steps={steps}>
      {({ step }) => (
        <div className="v-broke">
          {BROKE.map(([t, d, big], i) => {
            const on = i < (step + 1) * 2;
            return (
              <motion.div key={t} className={`broke${big ? " big" : ""}`} initial={false}
                animate={{ opacity: on ? 1 : 0, x: on ? 0 : 40 }} transition={{ duration: 0.45, delay: on ? (i % 2) * 0.18 : 0 }}>
                <h4>{t}</h4>
                <p>{d}</p>
                {big ? (
                  <div className="was">
                    <span className="old">99.9% against 84.7%</span>
                    <motion.i className="strike" initial={false} animate={{ scaleX: step >= 1 ? 1 : 0 }} transition={{ duration: 0.6, delay: 0.5 }} />
                    <motion.span className="now" initial={false} animate={{ opacity: step >= 1 ? 1 : 0 }} transition={{ delay: 1.1 }} style={{ color: pal.keep }}>about 99% against 99%</motion.span>
                  </div>
                ) : null}
              </motion.div>
            );
          })}
        </div>
      )}
    </Chapter>
  );
}

/* ---------------------------------------------------------------- 7. perception */
export function Perception() {
  const pal = usePalette();
  const P = data.perception;
  const steps = [
    { title: "The robot's eyes will be wrong sometimes.", body: `A vision model reports which steps are done. At a 5% error rate per step, more than half of all readings contain a mistake, and trusting them gets only ${pct(P.trust.success)} of changeovers right.` },
    { title: "Impossible readings give errors away.", body: `A step seen done without what it sits on cannot be. Nor can steps that would each have to come off before another. That free check notices ${pct(P.noticed)} of bad readings and lifts success to ${pct(P.consistency.success)}.` },
    { title: "Checking before an undo changed nothing.", body: "The harmful mistakes are steps wrongly believed done or wrongly missed, and neither is on the undo list. The extra inspections bought no accuracy." },
    { title: "Check what would change the plan.", body: `Inspecting only the steps whose status would change the plan reaches ${pct(P.inspect_critical.success)} with about ${Math.round(P.inspect_critical.inspections)} inspections, against ${Math.round(P.inspect_all.inspections)} for checking everything.` },
  ];
  return (
    <Chapter id="perception" title="When the robot's eyes are wrong" steps={steps}>
      {({ step }) => {
        const rows = [
          ["trust", "Trust the readings", pal.leave, 0],
          ["consistency", "Free consistency check", pal.build, 1],
          ["inspect_undo", "Also inspect before each undo", pal.leave, 2],
          ["inspect_critical", "Inspect what would change the plan", pal.keep, 3],
          ["inspect_all", "Inspect everything", pal.leave, 3],
        ].map(([k, label, color, from]) => ({
          key: k, label, color, value: P[k].success, show: step >= from,
          display: `${pct(P[k].success)}`, note: `${P[k].inspections} inspections${k === "inspect_undo" && step >= 2 ? ", no better than the free check" : ""}`,
          strong: k === "inspect_critical", delay: 0.1 + from * 0.05,
        }));
        return (
          <div className="v-bars">
            <p className="caption">Changeovers done correctly with 5% of steps misread. Generated processes.</p>
            <Bars rows={rows} max={1} />
          </div>
        );
      }}
    </Chapter>
  );
}

/* ---------------------------------------------------------------- 8. results */
export function Results() {
  const pal = usePalette();
  const U = R.undo;
  const steps = [
    { title: "When something has to come off, it is about twice as fast.", body: `On the gearbox, after a change that needs undoing: ${U.TF.time} seconds against ${U.B3b.time} and ${U.B2.time}. Planning B on top of the old parts fails every time.` },
    { title: "And it does not damage parts.", body: `Taking off only what has to come off means fewer risky removals: no parts lost, against ${pct(U.B2.lost)} and ${pct(U.B3b.lost)} for the alternatives.` },
    { title: "Where it does not help.", body: "If nothing has to come off, a plain replan does just as well. If something cannot come off, scrapping and restarting is the only option, and TaskFlux ties it. What it adds there is asking first, and saying why." },
  ];
  return (
    <Chapter id="results" title="What it buys" steps={steps}>
      {({ step }) => {
        if (step < 2) {
          const key = step === 0 ? "time" : "lost";
          const max = step === 0 ? 400 : 0.2;
          const fmt = (v) => (step === 0 ? `${v} s` : pct(v));
          const mk = (k, label, color, strong) => ({ key: k, label, color, strong, value: U[k][key] ?? 0, display: fmt(U[k][key] ?? 0), show: true });
          const rows = [mk("TF", "TaskFlux", pal.build, true), mk("B2", "Start over", pal.leave), mk("B3b", "Compare build orders", pal.leave)];
          return (
            <div className="v-bars">
              <p className="caption">{step === 0 ? "Seconds from the operator's sentence to a finished B." : "Share of runs in which a part was damaged."} Gearbox, {U.TF.n} simulated runs each.</p>
              <Bars rows={rows} max={max} />
            </div>
          );
        }
        const t = R.truncation; const ir = R.irreversible;
        return (
          <div className="v-bars two">
            <div>
              <p className="caption">Nothing has to come off</p>
              <Bars max={260} rows={[
                { key: "a", label: "TaskFlux", value: t.TF.time, display: `${t.TF.time} s`, color: pal.build, strong: true },
                { key: "b", label: "Plain replan", value: t.B3a.time, display: `${t.B3a.time} s`, color: pal.leave },
                { key: "c", label: "Start over", value: t.B2.time, display: `${t.B2.time} s`, color: pal.leave },
              ]} />
            </div>
            <div>
              <p className="caption">Something cannot come off</p>
              <Bars max={400} rows={[
                { key: "a", label: "TaskFlux", value: ir.TF.time, display: `${ir.TF.time} s`, color: pal.build, strong: true },
                { key: "b", label: "Start over", value: ir.B2.time, display: `${ir.B2.time} s`, color: pal.leave },
                { key: "c", label: "Compare build orders", value: ir.B3b.time, display: `${ir.B3b.time} s`, color: pal.leave, note: "destroys the part every time" },
              ]} />
            </div>
          </div>
        );
      }}
    </Chapter>
  );
}

/* ---------------------------------------------------------------- 9. missing */
const DONE = [
  "The reconciler, with a proof and exhaustive checks",
  "Triage, hedging and a refusal that says why",
  "A simulator, four baselines and 244 tests",
  "A second process, ablations and noise experiments",
  "This page: every number is computed by the code",
];
const NOT = [
  "Nothing has run on a robot",
  "No OpenVLA model was used: the 7B model does not fit a 4 GB GPU",
  "No real operator speech, only phrasings we wrote",
  "The second process has not been independently annotated",
  "Geometry is a stub, not robot kinematics",
  "The Docker image has not been built",
];

export function Missing() {
  const steps = [
    { title: "What works, in simulation.", body: "The planning layer is complete, tested and reproducible: one command reruns every experiment and produces identical results." },
    { title: "What does not exist yet.", body: "Every number here comes from a simulator with assumed rates. The next step is a real policy in the loop, then a real cell." },
  ];
  return (
    <Chapter id="missing" title="What is still missing" steps={steps}>
      {({ step }) => (
        <div className="v-missing">
          <motion.ul className="list done" initial={false} animate={{ opacity: step === 0 ? 1 : 0.4 }}>
            {DONE.map((d, i) => (
              <motion.li key={d} initial={false} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}><span className="mark ok">{"✓"}</span>{d}</motion.li>
            ))}
          </motion.ul>
          <motion.ul className="list not" initial={false} animate={{ opacity: step === 1 ? 1 : 0, y: step === 1 ? 0 : 20 }} transition={{ duration: 0.5 }}>
            {NOT.map((d, i) => (
              <motion.li key={d} initial={false} animate={{ opacity: step === 1 ? 1 : 0, x: step === 1 ? 0 : 24 }} transition={{ delay: step === 1 ? 0.15 + i * 0.1 : 0 }}><span className="mark no">{"✕"}</span>{d}</motion.li>
            ))}
          </motion.ul>
        </div>
      )}
    </Chapter>
  );
}
