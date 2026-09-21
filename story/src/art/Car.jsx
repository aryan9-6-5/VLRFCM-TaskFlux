import React from 'react'
import { motion } from 'framer-motion'

/**
 * A right-facing, low, wide sports coupe with a fastback roofline (911-style), built from separate parts so each
 * can slide, fade and be highlighted on its own. `parts` maps a part name to { o, x, y, stroke }, each a number or
 * a MotionValue. Anything left out is fully drawn. Parts:
 *   shadow    ground shadow
 *   shell     body shell in primer (falls back to `chassis`)
 *   chassis   sill and rear diffuser
 *   paint     the red coat over the shell and over the cabin (its `o` fades the paint, not the shell)
 *   intake    side air intake
 *   roof      the cabin: roof skin, pillars and glass. It sits flush in the roofline and lifts straight up
 *   windows   the glass alone (inside `roof`)
 *   seats     two seat backs, inside the cabin
 *   doors     door cut line and handle          (alias: `door`)
 *   motor     headlight and front air intake    (alias: `headlight`)
 *   tailLight, mirror, wheels (also `spin`, degrees, turns each alloy), badge
 *   Small trim follows its parent when not given: shadow and tailLight follow `chassis`, intake follows `doors`,
 *   mirror and badge follow `paint`, so scrapping or moving a part takes its trim with it.
 *   newRoof   a taller replacement cabin, hidden until given `o`; oldGhost / newGhost are dashed outlines of the
 *             old and new cabin, hidden until given `o`. `rails` is accepted and ignored.
 * A part's `stroke` recolours its outline, which is how a part is highlighted.
 *
 * viewBox 0 0 260 120, one coordinate system. The roofline, cabin, glass, door and wheels are all derived from the
 * anchors below, taken from the reference profile. The car is symmetric about MID for the wheelbase, the wheels
 * are centred on WHEEL_Y, and the body's underside is SILL_Y.
 */
const D = { o: 1, x: 0, y: 0 }
const pick = (parts, keys, def = {}) => ({ ...D, ...def, ...(parts[keys.find((k) => parts[k])] || {}) })

// ---- anchors -------------------------------------------------------------------------------------------------
const REAR_X = 18.5
const FRONT_X = 241.5
const MID = (REAR_X + FRONT_X) / 2 // 130: middle of the body and of the wheelbase
const GROUND = 108.5 // bottom of the tyres
const SILL_Y = 99.5 // bottom of the body
const BELT_Y = 62.5 // beltline: the cabin's base and the bottom of the side glass
const DECK = { x: 50, y: 58.5 } // where the rear deck meets the fastback
const ROOF = { x: 131, y: 43.5 } // crown of the roof
const SCREEN_TOP = { x: 139, y: 45.5 } // where the windscreen leaves the roof
const COWL = { x: 172, y: BELT_Y } // where the windscreen meets the bonnet
const CABIN_REAR = 72 // where the beltline starts, behind the door

const WHEEL_R = 17.5
const WHEEL_Y = GROUND - WHEEL_R // 91
const WHEEL_DX = 63.5 // wheels at MID -+ WHEEL_DX: 66.5 and 193.5
const ARCH_R = WHEEL_R + 3.5

// ---- shapes: shell and cabin share the beltline, so the cabin lifts off cleanly ------------------------------------
const BELTLINE_BACK = `C56 61 64 ${BELT_Y} ${CABIN_REAR} ${BELT_Y}` // deck to beltline, running forward
const SHELL = [
  'M22 96',
  `C19.5 96 ${REAR_X} 92 ${REAR_X} 86`,
  `L${REAR_X} 79`,
  `C${REAR_X} 72 22 67 29 65`, // tail
  `C37 62.5 44 60.5 ${DECK.x} ${DECK.y}`, // rear deck
  BELTLINE_BACK,
  `H${COWL.x}`, // beltline
  'C182 63.5 194 65 204 66', // bonnet
  'C212 67 219 68.5 224 71', // headlight shoulder
  'C231 74 238 76 240.5 80', // nose
  `C${FRONT_X} 82 ${FRONT_X} 86 ${FRONT_X} 90`,
  `V96 Q${FRONT_X} ${SILL_Y} 236 ${SILL_Y}`,
  `H28 Q22 ${SILL_Y} 22 96 Z`,
].join(' ')

const CABIN = [
  `M${DECK.x} ${DECK.y}`,
  'C64 54 76 50 90 47.2', // fastback slope
  `C105 44.3 120 43.2 ${ROOF.x} ${ROOF.y}`, // roof crown
  `C135 43.6 138 44.5 ${SCREEN_TOP.x} ${SCREEN_TOP.y}`,
  `L${COWL.x} ${COWL.y}`, // windscreen
  `H${CABIN_REAR} C64 ${BELT_Y} 56 61 ${DECK.x} ${DECK.y} Z`,
].join(' ')

const SIDE_GLASS = `M103 ${BELT_Y} V51.5 C113 49.5 123 47.6 133 47.4 C141 47.2 147 51 157 ${BELT_Y} Z`
const QUARTER_GLASS = `M71 ${BELT_Y - 1} C76 57 82 53.5 91 51.6 C94 51 97 50.8 100 50.8 V${BELT_Y - 1} Z`
const SCREEN = `M${SCREEN_TOP.x} ${SCREEN_TOP.y} L${COWL.x + 0.5} ${COWL.y} L158 ${BELT_Y + 0.7} L142 48 Z`

const DOOR = `M101 ${BELT_Y + 0.5} C99 76 102 88 112 92 C130 94.5 150 95 160 93.5 C165 92.5 167 89 167 84 V74 C167 70 164 66 160 ${BELT_Y + 1}`

/** A seat back sitting on the beltline, top rounded, inside the glass. */
const seat = (x0, w, top) => `M${x0} ${BELT_Y} V${top + 3} Q${x0} ${top} ${x0 + 3} ${top} H${x0 + w - 3} Q${x0 + w} ${top} ${x0 + w} ${top + 3} V${BELT_Y} Z`

// The replacement cabin is the same cabin, taller: scaled up from the beltline, so it lands exactly on the shell.
const NEW_SCALE = `translate(0 ${BELT_Y}) scale(1 1.24) translate(0 ${-BELT_Y})`

const polar = (cx, cy, r, deg) => [cx + r * Math.cos((deg * Math.PI) / 180), cy + r * Math.sin((deg * Math.PI) / 180)]

function G({ name, s, children }) {
  const st = { opacity: s.o, x: s.x, y: s.y }
  if (s.stroke) st.stroke = s.stroke
  return <motion.g role="img" aria-label={name} style={st}>{children}</motion.g>
}

/** Arch, tyre, alloy with ten spokes, brake disc and red caliper. Only the alloy turns. The tyre takes the part's stroke. */
function Wheel({ cx, spin }) {
  const spokes = Array.from({ length: 10 }, (_, i) => {
    const [x1, y1] = polar(cx, WHEEL_Y, 4, i * 36)
    const [x2, y2] = polar(cx, WHEEL_Y, 12.6, i * 36)
    return <path key={i} d={`M${x1} ${y1} L${x2} ${y2}`} />
  })
  const [a1x, a1y] = polar(cx, WHEEL_Y, 5.6, -8)
  const [a2x, a2y] = polar(cx, WHEEL_Y, 10.2, -8)
  const [b1x, b1y] = polar(cx, WHEEL_Y, 5.6, 34)
  const [b2x, b2y] = polar(cx, WHEEL_Y, 10.2, 34)
  const chord = Math.sqrt(ARCH_R * ARCH_R - (SILL_Y - WHEEL_Y) ** 2)
  return (
    <g>
      <path d={`M${cx - chord} ${SILL_Y} A${ARCH_R} ${ARCH_R} 0 1 1 ${cx + chord} ${SILL_Y} Z`} fill="var(--carline)" stroke="none" />
      <circle cx={cx} cy={WHEEL_Y} r={WHEEL_R + 1.8} fill="none" stroke="var(--bg)" strokeWidth="1.6" />
      <circle cx={cx} cy={WHEEL_Y} r={WHEEL_R} fill="var(--carline)" />
      <circle cx={cx} cy={WHEEL_Y} r="13.4" fill="var(--rim)" stroke="none" />
      <circle cx={cx} cy={WHEEL_Y} r="10.6" fill="var(--dim)" stroke="none" />
      <motion.g style={{ rotate: spin }}>
        <g stroke="var(--glass)" strokeWidth="1" strokeLinecap="round" opacity="0.85">{spokes}</g>
        <circle cx={cx} cy={WHEEL_Y} r="12.6" fill="none" stroke="var(--carline)" strokeWidth="0.9" />
      </motion.g>
      <path d={`M${a1x} ${a1y} L${a2x} ${a2y} A10.2 10.2 0 0 1 ${b2x} ${b2y} L${b1x} ${b1y} A5.6 5.6 0 0 0 ${a1x} ${a1y} Z`} fill="var(--car-red-dark)" stroke="none" />
      <circle cx={cx} cy={WHEEL_Y} r="3.4" fill="var(--carline)" stroke="none" />
      <circle cx={cx} cy={WHEEL_Y} r="1.5" fill="var(--limit)" stroke="none" />
    </g>
  )
}

export default function Car({ parts = {}, label = 'A red sports coupe', className = '', width = '100%', style, x, y }) {
  const p = (keys, def) => pick(parts, keys, def)
  const paint = p(['paint'])
  const coat = { opacity: paint.o } // the red coat fades; the primer shell underneath stays with its own part
  const spin = parts.wheels && parts.wheels.spin
  const chassis = p(['chassis'])
  return (
    <svg x={x} y={y} viewBox="0 0 260 120" width={width} height={typeof width === 'number' ? (width * 120) / 260 : undefined} className={className} style={{ overflow: 'visible', ...style }} role="img" aria-label={label}>
      <g strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" stroke="var(--carline)">
        <G name="ground shadow" s={parts.shadow ? p(['shadow']) : { ...D, o: chassis.o }}>
          <ellipse cx={MID} cy={GROUND + 1.5} rx="112" ry="3" fill="var(--carline)" opacity="0.14" stroke="none" />
        </G>

        <G name="body shell" s={pick(parts, ['shell', 'chassis'])}>
          <path d={SHELL} fill="var(--car-primer)" />
        </G>

        <G name="paint" s={{ ...paint, o: 1 }}>
          <motion.path d={SHELL} fill="var(--car-red)" style={coat} />
          <motion.g style={coat}>
            <path d="M32 70 C60 62 90 63 120 65 C140 66 165 66 205 68" fill="none" stroke="var(--car-red-light)" strokeWidth="2.2" opacity="0.55" />
            <path d="M176 63.6 C186 64.2 196 65.2 206 67.2" fill="none" stroke="var(--car-red-light)" strokeWidth="1.4" opacity="0.5" />
            <path d={`M24 88 Q60 92 120 92.6 T236 89 V${SILL_Y - 3} H24 Z`} fill="var(--car-red-dark)" opacity="0.5" stroke="none" />
          </motion.g>
        </G>

        <G name="sill and rear diffuser" s={chassis}>
          <path d={`M30 95 H236 V${SILL_Y} H30 Q26 ${SILL_Y} 26 97 Q26 95 30 95 Z`} fill="var(--carline)" />
          <path d="M19.5 86 Q33 88 45 90 V97 Q30 97 22 96 Q19.5 92 19.5 86 Z" fill="var(--carline)" />
        </G>

        <G name="side air intake" s={p(['intake', 'doors'])}>
          <path d="M91 68 Q95 67 98 69 L98 78 Q95 79.5 91 78 Z" fill="var(--carline)" />
          <path d="M92.6 71 H96.6 M92.6 73.6 H96.6 M92.6 76.2 H96.6" stroke="var(--car-red-dark)" strokeWidth="0.9" fill="none" />
        </G>

        <G name="roof and cabin" s={p(['roof'])}>
          <path d={CABIN} fill="var(--car-primer)" />
          <motion.path d={CABIN} fill="var(--car-red)" style={coat} />
          <G name="windows" s={p(['windows'])}>
            <path d={QUARTER_GLASS} fill="var(--glass)" strokeWidth="3" />
            <path d={SIDE_GLASS} fill="var(--glass)" strokeWidth="3" />
            <path d={SCREEN} fill="var(--glass)" strokeWidth="1.2" />
            <path d="M112 55 L126 49.5 M119 58 L132 52.6" stroke="var(--bg)" strokeWidth="1.4" opacity="0.45" fill="none" />
          </G>
        </G>

        <G name="seats" s={p(['seats'])}>
          <path d={seat(84, 12, 55)} fill="var(--carline)" strokeWidth="2" />
          <path d={seat(106, 13, 52)} fill="var(--carline)" strokeWidth="2" />
        </G>

        <G name="door" s={p(['door', 'doors'])}>
          <path d={DOOR} fill="none" strokeWidth="1.8" />
          <rect x="105" y="71" width="11" height="2.6" rx="1.3" fill="var(--car-red-dark)" strokeWidth="1" />
        </G>

        <G name="headlight and front intake" s={p(['headlight', 'motor'])}>
          <path d="M214.5 66.5 Q223 67 229 75 Q230 77.5 227.5 78 Q219 74 214.5 67.2 Z" fill="var(--carline)" strokeWidth="1.6" />
          <path d="M218.6 68.6 Q224 70 227 74.6" fill="none" stroke="var(--glass)" strokeWidth="1" opacity="0.9" />
          <path d="M226 86.5 H240 V94 H228 Q226 94 226 92 Z" fill="var(--carline)" />
          <path d="M228.5 89 H239 M228.5 91.6 H239" stroke="var(--glass)" strokeWidth="0.8" opacity="0.7" fill="none" />
        </G>

        <G name="tail light" s={p(['tailLight', 'chassis'])}>
          <path d="M19 69 Q32 66.5 46 69.5 L46 72 Q32 69.8 19 72.5 Z" fill="var(--carline)" strokeWidth="1" />
          <path d="M20.5 70.4 Q32 68.2 44.5 70.8" fill="none" stroke="var(--car-red-light)" strokeWidth="1.6" />
        </G>

        <G name="side mirror" s={p(['mirror', 'paint'])}>
          <path d="M150 66.2 L154.6 66.8" strokeWidth="2" fill="none" />
          <path d="M142 60.5 Q143 58 148 58.3 Q154 58.6 154.6 62.5 Q154.8 66 151 67 L146 66.5 Q142 65 142 60.5 Z" fill="var(--car-red)" strokeWidth="1.6" />
        </G>

        <G name="wheels" s={p(['wheels'])}>
          <Wheel cx={MID - WHEEL_DX} spin={spin} />
          <Wheel cx={MID + WHEEL_DX} spin={spin} />
        </G>

        <G name="badge" s={p(['badge', 'paint'])}>
          <text x="153" y="92.6" fontSize="4.6" fontWeight="700" fontStyle="italic" fill="var(--car-red-dark)" stroke="none" aria-hidden="true">GTS</text>
        </G>

        <G name="planned old cabin" s={p(['oldGhost'], { o: 0 })}>
          <path d={CABIN} fill="none" stroke="var(--dim)" strokeDasharray="6 6" />
        </G>
        <G name="planned new cabin" s={p(['newGhost'], { o: 0 })}>
          <g transform={NEW_SCALE}><path d={CABIN} fill="none" stroke="var(--accent)" strokeDasharray="6 6" vectorEffect="non-scaling-stroke" /></g>
        </G>
        <G name="new roof and cabin" s={p(['newRoof'], { o: 0, y: -70 })}>
          <g transform={NEW_SCALE}><path d={CABIN} fill="var(--accent)" vectorEffect="non-scaling-stroke" /></g>
        </G>
      </g>
    </svg>
  )
}
