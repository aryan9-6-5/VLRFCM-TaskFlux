import { motion, useReducedMotion } from "framer-motion";
import data from "./data.json";
import { usePalette } from "./theme";

const { w: W, h: H, width: VW, height: VH } = data.box;
const S = Object.fromEntries(data.steps.map((s) => [s.id, s]));
const FONT = 'Bahnschrift, "DIN Alternate", "Roboto Condensed", "Arial Narrow", "Segoe UI", system-ui, sans-serif';

function wrap(t, max = 18) {
  const lines = [""];
  for (const w of t.split(" ")) {
    const cur = lines[lines.length - 1];
    if (cur && `${cur} ${w}`.length > max) lines.push(w);
    else lines[lines.length - 1] = cur ? `${cur} ${w}` : w;
  }
  return lines.length > 2 ? [lines[0], lines.slice(1).join(" ")] : lines;
}

function look(role, pal) {
  const clear = `${pal.panel}00`;
  switch (role) {
    case "keep": return { fill: pal.keepBg, stroke: pal.keep, text: pal.ink, op: 1 };
    case "undo":
    case "lost": return { fill: pal.undoBg, stroke: pal.undo, text: pal.ink, op: 1 };
    case "build": return { fill: pal.buildBg, stroke: pal.build, text: pal.ink, op: 1 };
    case "built": return { fill: pal.build, stroke: pal.build, text: pal.onSolid, op: 1 };
    case "leave": return { fill: pal.leaveBg, stroke: pal.leave, text: pal.ink, op: 1 };
    case "removed": return { fill: clear, stroke: pal.undo, text: pal.ink2, op: 0.9, dash: "5 4" };
    case "hidden": return { fill: clear, stroke: pal.rule, text: pal.ink2, op: 0 };
    default: return { fill: clear, stroke: pal.rule, text: pal.ink2, op: 0.7 };
  }
}

function path(a, b) {
  let x1, y1, x2, y2;
  if (a.x + W + 8 <= b.x) { x1 = a.x + W; y1 = a.y + H / 2; x2 = b.x; y2 = b.y + H / 2; const dx = (x2 - x1) / 2; return `M${x1} ${y1}C${x1 + dx} ${y1} ${x2 - dx} ${y2} ${x2} ${y2}`; }
  if (b.x + W + 8 <= a.x) { x1 = a.x; y1 = a.y + H / 2; x2 = b.x + W; y2 = b.y + H / 2; const dx = (x2 - x1) / 2; return `M${x1} ${y1}C${x1 + dx} ${y1} ${x2 - dx} ${y2} ${x2} ${y2}`; }
  if (a.y < b.y) { x1 = a.x + W / 2; y1 = a.y + H; x2 = b.x + W / 2; y2 = b.y; const dy = (y2 - y1) / 2; return `M${x1} ${y1}C${x1} ${y1 + dy} ${x2} ${y2 - dy} ${x2} ${y2}`; }
  x1 = a.x + W / 2; y1 = a.y; x2 = b.x + W / 2; y2 = b.y + H;
  const dy = (y2 - y1) / 2;
  return `M${x1} ${y1}C${x1} ${y1 + dy} ${x2} ${y2 - dy} ${x2} ${y2}`;
}

function Lock({ hot, pal }) {
  const c = hot ? pal.amber : pal.ink2;
  return (
    <g transform={`translate(${W - 21} 4)`}>
      <path d="M3 6V4.5a3 3 0 0 1 6 0V6" fill="none" stroke={c} strokeWidth="1.5" />
      <rect x="1.5" y="6" width="9" height="6.5" rx="1" fill={c} />
    </g>
  );
}

function Badge({ text, kind, x, delay, pal }) {
  const w = text.length * 7 + 12;
  return (
    <g transform={`translate(${x} -8)`}>
      <motion.g
        initial={{ scale: 0.3, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 420, damping: 22, delay }}
        style={{ originX: 0, originY: 0.5 }}
      >
        <rect width={w} height="16" rx="2" fill={kind === "undo" ? pal.undo : pal.build} />
        <text x={w / 2} y="12" textAnchor="middle" fontSize="11.5" fontWeight="700" fill={pal.onSolid} style={{ fontFamily: FONT }}>{text}</text>
      </motion.g>
    </g>
  );
}

function Node({ s, role, badges = [], pulse, lit, pal, reduce, enter }) {
  const l = look(role, pal);
  const lines = wrap(s.label);
  const t = { duration: 0.45, delay: enter || 0 };
  let bx = 8;
  return (
    <motion.g transform={`translate(${s.x} ${s.y})`} initial={enter !== undefined ? { opacity: 0 } : false} animate={{ opacity: l.op }} transition={t}>
      <motion.polygon
        points={`0,0 ${W - 10},0 ${W},10 ${W},${H} 10,${H} 0,${H - 10}`}
        strokeWidth="1.6"
        strokeDasharray={l.dash}
        initial={false}
        animate={{ fill: l.fill, stroke: l.stroke }}
        transition={t}
      />
      {lines.map((ln, i) => (
        <motion.text key={i} x="10" y={lines.length === 1 ? 29 : 21 + i * 15} fontSize="12.5" initial={false} animate={{ fill: l.text }} transition={t} style={{ fontFamily: FONT }}>
          {ln}
        </motion.text>
      ))}
      {s.irreversible ? <Lock hot={lit} pal={pal} /> : null}
      {badges.map((b) => {
        const el = <Badge key={`${b.kind}${b.text}`} text={b.text} kind={b.kind} x={bx} delay={b.delay || 0} pal={pal} />;
        bx += b.text.length * 7 + 16;
        return el;
      })}
      {pulse && !reduce ? (
        <motion.polygon
          points={`-4,-4 ${W - 6},-4 ${W + 4},6 ${W + 4},${H + 4} 6,${H + 4} -4,${H - 6}`}
          fill="none" stroke={pal.ink} strokeWidth="2.4"
          animate={{ opacity: [1, 0.15, 1] }} transition={{ repeat: Infinity, duration: 1.3, ease: "easeInOut" }}
        />
      ) : null}
    </motion.g>
  );
}

/**
 * The gearbox as a graph. `roles` maps a step id to how it is drawn; `badges` maps an id to
 * [{kind: "undo"|"build", text, delay}]. `hot` lists edges to emphasise as "a>b".
 */
export default function Workpiece({ roles = {}, badges = {}, pulse = [], lit = [], hot = [], showCovers = true, edgeOpacity = 0.5, stagger = false, label }) {
  const pal = usePalette();
  const reduce = useReducedMotion();
  const groups = { A: "Only in variant A", shared: "In both variants", B: "Only in variant B" };
  return (
    <svg viewBox={`0 0 ${VW} ${VH}`} role="img" aria-label={label || "Gearbox build steps"} className="workpiece">
      {Object.entries(groups).map(([g, name]) => {
        const ys = data.steps.filter((s) => s.group === g).map((s) => s.y);
        return <text key={g} x="16" y={Math.min(...ys) - 12} fontSize="13" fill={pal.ink2} style={{ fontFamily: FONT }}>{name}</text>;
      })}
      {data.edges.requires.map(([a, b]) => {
        const isHot = hot.includes(`${a}>${b}`);
        return (
          <motion.path key={`r${a}${b}`} d={path(S[a], S[b])} fill="none" initial={false}
            animate={{ stroke: isHot ? pal.amber : pal.ink2, strokeWidth: isHot ? 2.6 : 1.3, opacity: isHot ? 1 : edgeOpacity }} transition={{ duration: 0.4 }} />
        );
      })}
      {data.edges.covers.map(([u, s]) => {
        const isHot = hot.includes(`${u}>${s}`);
        return (
          <motion.path key={`c${u}${s}`} d={path(S[u], S[s])} fill="none" strokeDasharray="6 4" initial={false}
            animate={{ stroke: pal.amber, strokeWidth: isHot ? 3 : 2, opacity: showCovers ? (isHot ? 1 : 0.55) : 0 }} transition={{ duration: 0.4 }} />
        );
      })}
      {data.steps.map((s, i) => (
        <Node key={s.id} s={s} role={roles[s.id] || "skip"} badges={badges[s.id]} pulse={pulse.includes(s.id)} lit={lit.includes(s.id)}
          pal={pal} reduce={reduce} enter={stagger ? 0.05 * i : undefined} />
      ))}
    </svg>
  );
}
