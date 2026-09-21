import { useEffect, useRef, useState } from "react";
import { animate, motion, useInView, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { ArrowLineUp, ArrowsClockwise, Check, Eye, Hammer, Lock, Warning } from "@phosphor-icons/react";
import { C } from "../tokens.js";

/*
 * One car on a line. The design changes, the line forks into four lanes (one robot each), and the lanes
 * come back together. Meaning is carried by shape, position, motion and icons: there is no text in the drawing.
 * The picture is a pure function of `step` (which the Chapter derives from scroll). Steps ease in over 0.7 s.
 * This is an illustration. The repo plans one process at a time; parallel robots are not built or measured.
 */
const pal = { keep: C.keep, undo: C.undo, amber: C.limit, build: C.accent, ink: C.text, panel: C.surface, ink2: C.muted, rule: C.line, onSolid: C.onSolid, paper: C.bg };
const EASE = [0.22, 1, 0.36, 1];
const T = 0.7;
const LANE_COLOUR = [pal.undo, pal.amber, pal.build, pal.ink2];
const LANE_ICON = [ArrowLineUp, Lock, Hammer, Eye];
const LANE_NAME = ["take off what sits on top first", "a step that cannot be undone", "build the new-design parts", "check what the robot sees"];
const PARTS = ["chassis", "wheels", "motor", "seats", "doors", "roof", "paint"];

/* Geometry is written in (u, d): u runs along the line, d is the distance from the main line. pt() maps it to the page. */
const LAND = {
  w: 1000, h: 560, r: 26, node: 15, badge: 20, lockR: 22, arm: [26, 26], off: 30, armW: 7,
  pt: (u, d) => [u, 500 - d],
  d: [410, 300, 190, 80],
  nodes: [50, 105, 160, 215, 270, 325, 380], fork: 430, end: [915, 970], start: 20, stop: 992,
  riser: [458, 482, 506, 530], badgeU: 556, lane: [610, 672, 734], laneEnd: 786, lockU: 734, drop: [858, null, 834, 810],
  snap: { w: 72, h: 33 }, snapAt: (i) => [536, 500 - (LAND_D[i] + 78)],
  car: { x: 40, y: 262, w: 400 }, card: { x: 50, y: 30, w: 230, h: 124 },
};
const LAND_D = LAND.d;
const PORT = {
  w: 390, h: 660, r: 14, node: 11, badge: 16, lockR: 17, arm: [20, 20], off: 24, armW: 6,
  pt: (u, d) => [32 + d, u],
  d: [293, 213, 133, 60],
  nodes: [24, 52, 80, 108, 136, 164, 192], fork: 226, end: [596, 632], start: 8, stop: 650,
  riser: [246, 264, 282, 300], badgeU: 344, lane: [384, 424, 464], laneEnd: 496, lockU: 464, drop: [552, null, 534, 516],
  snap: { w: 44, h: 21 }, snapAt: (i) => [32 + PORT_D[i] + 16, 310],
  car: { x: 92, y: 10, w: 280 }, card: { x: 96, y: 152, w: 130, h: 70 },
};
const PORT_D = PORT.d;

const num = (n) => Math.round(n * 10) / 10;
const P = (G, u, d) => G.pt(u, d).map(num).join(" ");
const outPath = (G, i) => {
  const { r } = G, di = G.d[i], u0 = G.riser[i], end = i === 1 ? G.lockU - G.lockR : G.laneEnd;
  return `M${P(G, G.fork, 0)} L${P(G, u0 - r, 0)} Q${P(G, u0, 0)} ${P(G, u0, r)} L${P(G, u0, di - r)} Q${P(G, u0, di)} ${P(G, u0 + r, di)} L${P(G, end, di)}`;
};
const backPath = (G, i) => {
  const { r } = G, di = G.d[i], u1 = G.drop[i];
  return `M${P(G, G.laneEnd, di)} L${P(G, u1 - r, di)} Q${P(G, u1, di)} ${P(G, u1, di - r)} L${P(G, u1, r)} Q${P(G, u1, 0)} ${P(G, u1 + r, 0)}`;
};

function useNarrow() {
  const q = "(max-width: 900px)";
  const [n, setN] = useState(() => typeof window !== "undefined" && window.matchMedia(q).matches);
  useEffect(() => {
    const m = window.matchMedia(q);
    const on = () => setN(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return n;
}

/* ---------------------------------------------------------------- the car: separate groups so parts can slide on and off */
function CarArt({ lit = 7, roof = "old", quick = false }) {
  const tr = (i, extra = 0) => ({ duration: quick ? 0 : T, ease: EASE, delay: quick ? 0 : i * 0.14 + extra });
  const on = (i) => (i < lit ? 1 : 0.18);
  const showRails = roof === "lifted" || roof === "new";
  return (
    <g strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" stroke="var(--carline)">
      <motion.g role="img" aria-label="chassis" initial={false} animate={{ opacity: on(0) }} transition={tr(0)}>
        <rect x="24" y="82" width="212" height="12" rx="6" fill="var(--carline)" />
      </motion.g>
      <motion.g role="img" aria-label="paint and panels" initial={false} animate={{ opacity: on(6) }} transition={tr(6)}>
        <path d="M22 82 V64 Q22 54 34 52 L70 47 H188 L226 53 Q238 55 238 66 V82 Z" fill="var(--car)" />
      </motion.g>
      <motion.g role="img" aria-label="motor" initial={false} animate={{ opacity: on(2) }} transition={tr(2)}>
        <rect x="196" y="55" width="34" height="23" rx="6" fill="var(--old)" />
        <circle cx="213" cy="66.5" r="5" fill="var(--glass)" />
      </motion.g>
      <motion.g role="img" aria-label="doors and windows" initial={false} animate={{ opacity: on(4) }} transition={tr(4)}>
        <path d="M76 47 Q86 27 112 25 H168 Q190 28 200 47 Z" fill="var(--glass)" />
        <path d="M108 49 V80 H166 V49" fill="none" />
        <path d="M148 60 H158" fill="none" />
      </motion.g>
      <motion.g role="img" aria-label="seats" initial={false} animate={{ opacity: on(3) }} transition={tr(3)}>
        <path d="M90 50 V23 Q90 17 96 17 H104 Q110 17 110 23 V50 Z" fill="var(--carline)" />
        <path d="M134 50 V23 Q134 17 140 17 H148 Q154 17 154 23 V50 Z" fill="var(--carline)" />
      </motion.g>
      <motion.g role="img" aria-label="wheels" initial={false} animate={{ opacity: on(1) }} transition={tr(1)}>
        <circle cx="66" cy="94" r="16" fill="var(--carline)" stroke="var(--bg)" />
        <circle cx="66" cy="94" r="5" fill="var(--glass)" stroke="none" />
        <circle cx="196" cy="94" r="16" fill="var(--carline)" stroke="var(--bg)" />
        <circle cx="196" cy="94" r="5" fill="var(--glass)" stroke="none" />
      </motion.g>
      <motion.g role="img" aria-label="rails for the roof" initial={false} animate={{ opacity: showRails ? 1 : 0 }} transition={{ duration: quick ? 0 : T, ease: EASE }} stroke="var(--dim)">
        <path d="M84 -46 V14 M196 -46 V14" fill="none" />
      </motion.g>
      <motion.g role="img" aria-label="old roof" initial={false} animate={{ y: roof === "old" ? 0 : -46, opacity: roof === "old" || roof === "lifted" ? on(5) : 0 }} transition={tr(5)}>
        <path d="M80 30 Q90 8 118 6 H156 Q184 8 196 30 Z" fill="var(--car)" />
      </motion.g>
      <motion.g role="img" aria-label="new roof" initial={false} animate={{ y: roof === "new" ? 0 : -70, opacity: roof === "new" ? 1 : 0 }} transition={{ duration: quick ? 0 : T, ease: EASE, delay: quick ? 0 : roof === "new" ? 0.8 : 0 }}>
        <path d="M70 34 Q100 10 140 8 Q176 8 204 34 Z" fill="var(--accent)" />
      </motion.g>
    </g>
  );
}

function CarBox({ x, y, w, ...props }) {
  return <svg x={x} y={y} width={w} height={(w * 120) / 260} viewBox="0 0 260 120" overflow="visible"><CarArt {...props} /></svg>;
}

/* ---------------------------------------------------------------- pieces of the line */
function Dot({ x, y, r, fill, on, delay = 0, label, show = true }) {
  return (
    <motion.circle cx={x} cy={y} stroke={pal.ink} strokeWidth={3} role="img" aria-label={label} initial={false}
      animate={{ r: on ? r : r * 0.72, fill: on ? fill : pal.panel, opacity: show ? 1 : 0 }} transition={{ duration: T, ease: EASE, delay }} />
  );
}

function Draw({ d, on, to = 1, delay = 0, label, stroke = pal.ink }) {
  return (
    <motion.path d={d} fill="none" stroke={stroke} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" aria-label={label} initial={false}
      animate={{ pathLength: on ? to : 0, opacity: on ? 1 : 0 }} transition={{ duration: 0.9, ease: EASE, delay }} />
  );
}

function Mark({ G, at, tone, Icon, on, label, r }) {
  const [x, y] = G.pt(at[0], at[1]);
  const fill = tone === "ok" ? pal.keep : "#fbead2";
  return (
    <motion.g role="img" aria-label={label} initial={false} animate={{ opacity: on ? 1 : 0 }} transition={{ duration: T, ease: EASE }}>
      <motion.circle cx={x} cy={y} r={r} strokeWidth={3} initial={false} animate={{ fill, stroke: tone === "ok" ? pal.keep : pal.amber }} transition={{ duration: T, ease: EASE }} />
      <Icon x={x - r * 0.55} y={y - r * 0.55} size={r * 1.1} weight="bold" color={tone === "ok" ? pal.onSolid : pal.amber} />
    </motion.g>
  );
}

/* A two-joint arm on a rail. Its hand reaches for a target on its own lane; joints are worked out from the target. */
function ik(G, lane, t) {
  const [l1, l2] = G.arm;
  const bu = t - 8, bd = G.d[lane] + G.off;
  const du = t - bu, dd = G.d[lane] - bd;
  const dist = Math.min(Math.max(Math.hypot(du, dd), Math.abs(l1 - l2) + 0.5), l1 + l2 - 0.5);
  const a = Math.atan2(dd, du);
  const b = Math.acos(Math.max(-1, Math.min(1, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist))));
  const c1 = [bu + l1 * Math.cos(a + b), bd + l1 * Math.sin(a + b)];
  const c2 = [bu + l1 * Math.cos(a - b), bd + l1 * Math.sin(a - b)];
  const e = c1[1] > c2[1] ? c1 : c2;
  const m = (q) => G.pt(q[0], q[1]);
  return { b: m([bu, bd]), e: m(e), h: m([bu + dist * Math.cos(a), bd + dist * Math.sin(a)]) };
}

const VISIT = { 0: [2, 1, 0], 1: [0, 1], 2: [0, 1, 2], 3: [0, 1, 2] }; // which lane node the hand visits, in order
const HOP = 0.9;
const fillDelay = (lane, k, step) => {
  const at = VISIT[lane].indexOf(k);
  return step === 4 && at >= 0 ? (at + 1) * HOP - 0.25 : 0;
};

function Arm({ G, lane, step, reduce }) {
  const N = G.lane;
  const rest = N[0];
  const tu = useMotionValue(rest);
  useEffect(() => {
    const seq = VISIT[lane].map((k) => N[k]);
    if (step === 4 && !reduce) {
      tu.set(rest);
      const c = animate(tu, [rest, ...seq], { duration: seq.length * HOP, ease: "easeOut" });
      return () => c.stop();
    }
    tu.set(step >= 4 ? seq[seq.length - 1] : rest);
    return undefined;
  }, [step, reduce, lane, N, rest, tu]);
  const pts = useTransform(tu, (t) => ik(G, lane, t));
  const arm = useTransform(pts, (p) => `M${p.b.join(" ")} L${p.e.join(" ")} L${p.h.join(" ")}`);
  const bx = useTransform(pts, (p) => p.b[0]);
  const by = useTransform(pts, (p) => p.b[1]);
  const ex = useTransform(pts, (p) => p.e[0]);
  const ey = useTransform(pts, (p) => p.e[1]);
  const hx = useTransform(pts, (p) => p.h[0]);
  const hy = useTransform(pts, (p) => p.h[1]);
  const c = LANE_COLOUR[lane];
  return (
    <motion.g role="img" aria-label={`robot arm: ${LANE_NAME[lane]}`} initial={false} animate={{ opacity: step >= 3 ? 1 : 0 }} transition={{ duration: T, ease: EASE, delay: step === 3 ? 0.5 + lane * 0.1 : 0 }}>
      <motion.path d={arm} fill="none" stroke={c} strokeWidth={G.armW} strokeLinecap="round" strokeLinejoin="round" />
      <motion.circle cx={bx} cy={by} r={G.armW * 1.2} fill={c} />
      <motion.circle cx={ex} cy={ey} r={G.armW * 0.75} fill={pal.panel} stroke={c} strokeWidth={3} />
      <motion.circle cx={hx} cy={hy} r={G.armW * 0.6} fill={pal.panel} stroke={c} strokeWidth={3} />
    </motion.g>
  );
}

/* ---------------------------------------------------------------- the scene */
export default function Concept({ step }) {
  const narrow = useNarrow();
  const G = narrow ? PORT : LAND;
  const reduce = useReducedMotion();
  const ref = useRef(null);
  const seen = useInView(ref, { once: true, amount: 0.3 });
  const s = step;
  const lit = seen || s > 0 ? 7 : 0;
  const roof = s >= 7 ? "new" : s >= 4 ? "lifted" : "old";
  const [fx, fy] = G.pt(G.fork, 0);
  const merged = s >= 8;
  const col = (lane) => (merged && lane !== 1 ? pal.keep : LANE_COLOUR[lane]);
  const laneKeys = [0, 1, 2, 3];
  const count = (lane) => (lane === 1 ? 2 : 3);
  const mid = (G.drop[0] + G.drop[2]) / 2;
  const quick = reduce;

  return (
    <div className="cl" ref={ref}>
      <svg className="cl-svg" viewBox={`0 0 ${G.w} ${G.h}`} role="group" aria-label="A car line. The design changes, four robots each take one small problem, and their work joins the line again.">
        {/* the line: what is built stays; what is still to build is faint until the end */}
        <path d={`M${P(G, G.start, 0)} L${P(G, G.stop, 0)}`} fill="none" stroke={pal.rule} strokeWidth={3} strokeLinecap="round" aria-label="line still to build" />
        <path d={`M${P(G, G.start, 0)} L${P(G, G.fork, 0)}`} fill="none" stroke={pal.ink} strokeWidth={3} strokeLinecap="round" aria-label="finished line" />
        <Draw d={`M${P(G, G.fork, 0)} L${P(G, G.stop, 0)}`} on={merged} delay={0.2} label="line carries on" />

        {/* lanes leave the line, and come back if they can */}
        {laneKeys.map((i) => <Draw key={`o${i}`} d={outPath(G, i)} on={s >= 3} delay={i * 0.12} label={`lane: ${LANE_NAME[i]}`} />)}
        {laneKeys.filter((i) => i !== 1).map((i) => {
          const clash = i === 0 || i === 2; // these two reach for the same part first
          return <Draw key={`b${i}`} d={backPath(G, i)} on={clash ? s >= 6 : s >= 7} to={clash && s === 6 ? 0.93 : 1} delay={s >= 7 ? (i === 0 ? 0 : i === 2 ? 0.9 : 0.45) : 0} label={`lane joins the line: ${LANE_NAME[i]}`} />;
        })}

        {/* finished parts on the line */}
        {G.nodes.map((u, i) => {
          const [x, y] = G.pt(u, 0);
          return <Dot key={u} x={x} y={y} r={G.node} fill={pal.keep} on={lit > 0} delay={quick ? 0 : 0.1 + i * 0.14} label={`finished part: ${PARTS[i]}`} />;
        })}
        <Mark G={G} at={[G.nodes[6], 0]} tone="lock" Icon={Lock} on={s >= 5} label="cured paint cannot be undone" r={G.node * 0.72} />

        {/* the same snapshot for every robot */}
        {laneKeys.map((i) => {
          const [sx, sy] = G.snapAt(i);
          return (
            <motion.g key={`s${i}`} role="img" aria-label="snapshot of the car with the finished parts lit" initial={false}
              animate={{ x: s >= 2 ? 0 : fx - sx, y: s >= 2 ? 0 : fy - sy, opacity: s >= 2 ? 1 : 0 }} transition={{ duration: 0.8, ease: EASE, delay: quick ? 0 : i * 0.12 }}>
              <CarBox x={sx} y={sy} w={G.snap.w} lit={7} roof="old" quick />
            </motion.g>
          );
        })}

        {/* lane heads: a symbol for the problem, then that lane's parts */}
        {laneKeys.map((i) => {
          const [bx, by] = G.pt(G.badgeU, G.d[i]);
          const Icon = LANE_ICON[i];
          return (
            <motion.g key={`h${i}`} role="img" aria-label={`problem: ${LANE_NAME[i]}`} initial={false} animate={{ opacity: s >= 3 ? 1 : 0 }} transition={{ duration: T, ease: EASE, delay: 0.3 + i * 0.12 }}>
              <circle cx={bx} cy={by} r={G.badge} fill={pal.panel} stroke={pal.ink} strokeWidth={3} />
              <Icon x={bx - G.badge * 0.58} y={by - G.badge * 0.58} size={G.badge * 1.16} weight="bold" color={LANE_COLOUR[i]} />
            </motion.g>
          );
        })}
        {laneKeys.map((i) => G.lane.slice(0, count(i)).map((u, k) => {
          const [x, y] = G.pt(u, G.d[i]);
          const worked = s >= 4;
          return <Dot key={`n${i}${k}`} x={x} y={y} r={G.node} fill={col(i)} on={worked} show={s >= 3} delay={quick ? 0 : fillDelay(i, k, s)} label={`${LANE_NAME[i]}: part ${k + 1}`} />;
        }))}
        <Mark G={G} at={[G.lockU, G.d[1]]} tone="lock" Icon={Lock} on={s >= 5} label="locked: the line stops here and does not rejoin" r={G.lockR} />
        <Mark G={G} at={[mid, 0]} tone={s >= 7 ? "ok" : "lock"} Icon={s >= 7 ? Check : Warning} on={s >= 6} label={s >= 7 ? "two lanes reached the same part, and the order settled it" : "two lanes reach for the same part"} r={G.lockR} />
        {G.end.map((u, i) => {
          const [x, y] = G.pt(u, 0);
          return <Dot key={u} x={x} y={y} r={G.node} fill={pal.keep} on={merged} show delay={quick ? 0 : 0.7 + i * 0.3} label="part built after the change" />;
        })}

        {/* the new design arrives */}
        <motion.g role="img" aria-label="the new roofline arrives" initial={false} animate={{ opacity: s === 1 || s === 2 ? 1 : 0, x: s === 1 || s === 2 ? 0 : -24 }} transition={{ duration: T, ease: EASE }}>
          <rect x={G.card.x} y={G.card.y} width={G.card.w} height={G.card.h} rx="14" fill={pal.panel} stroke={pal.build} strokeWidth={3} />
          <CarBox x={G.card.x + 12} y={G.card.y + (G.card.h - ((G.card.w - 24) * 120) / 260) / 2} w={G.card.w - 24} lit={7} roof="new" quick />
          <circle cx={G.card.x + G.card.w} cy={G.card.y} r={G.badge} fill={pal.build} />
          <ArrowsClockwise x={G.card.x + G.card.w - G.badge * 0.6} y={G.card.y - G.badge * 0.6} size={G.badge * 1.2} weight="bold" color={pal.onSolid} />
        </motion.g>

        {/* the car being built */}
        <CarBox x={G.car.x} y={G.car.y} w={G.car.w} lit={lit} roof={roof} quick={quick} />

        {laneKeys.map((i) => <Arm key={`r${i}`} G={G} lane={i} step={s} reduce={reduce} />)}
      </svg>
    </div>
  );
}

