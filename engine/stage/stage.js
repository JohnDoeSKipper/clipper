// CLIPPER stage: a small 3D theatre driven entirely by a JSON spec (work/<id>/spec.json).
// Two looks from the same spec:  clay (glossy toy, pastel, blurred background layer)  |  ps2 (low-poly, pixel textures, fog, 1/3 res, scanlines)
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const Q = new URLSearchParams(location.search);
const SPEC = await (await fetch(`work/${Q.get('id')}/spec.json`)).json();
const PROPS = await (await fetch('props.json')).json();
const STYLE = Q.get('style') || SPEC.style || 'clay';
const PS2 = STYLE === 'ps2';
const W = 1080, H = 1920, TL = SPEC.TL;
const $ = id => document.getElementById(id);
if (PS2) $('stage').classList.add('ps2');
const warn = [];

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, u) => a + (b - a) * u;
const EASE = { inout: u => { u = clamp(u); return u * u * (3 - 2 * u); }, out: u => 1 - Math.pow(1 - clamp(u), 3), linear: u => clamp(u) };
const ease = EASE.inout, easeOut = EASE.out;
const rad = d => d * Math.PI / 180;
function rng(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }

// ---------------------------------------------------------------- renderers
let bgR = null, fgR;
if (PS2) {
  $('bg').style.display = 'none';
  const c = $('fg'); c.width = W / 3; c.height = H / 3;
  fgR = new THREE.WebGLRenderer({ canvas: c, antialias: false, preserveDrawingBuffer: true });
  fgR.setSize(W / 3, H / 3, false);
} else {
  bgR = new THREE.WebGLRenderer({ canvas: $('bg'), antialias: false, preserveDrawingBuffer: true });
  bgR.setSize(W / 2, H / 2, false);
  fgR = new THREE.WebGLRenderer({ canvas: $('fg'), antialias: true, alpha: true, preserveDrawingBuffer: true });
  fgR.setSize(W, H, false);
  fgR.setClearColor(0x000000, 0);
  for (const r of [bgR, fgR]) r.toneMapping = THREE.NoToneMapping;
}
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(46, W / H, 0.1, 400);

// ---------------------------------------------------------------- textures, lights
function canvasTex(w, h, draw, pixel = false) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  if (pixel) { t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; }
  return t;
}
function pixelTex(hex, seed = 1, n = 8, amt = 0.16) {
  const base = new THREE.Color(hex), r = rng(seed * 7919 + 13);
  return canvasTex(n, n, (g) => {
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const k = 1 + (r() - 0.5) * 2 * amt;
      g.fillStyle = `rgb(${clamp(base.r * k) * 255 | 0},${clamp(base.g * k) * 255 | 0},${clamp(base.b * k) * 255 | 0})`;
      g.fillRect(x, y, 1, 1);
    }
  }, true);
}
const world = SPEC.world || {};
const skyTex = canvasTex(4, 256, (g, w, h) => {
  const grd = g.createLinearGradient(0, 0, 0, h);
  if (PS2) { grd.addColorStop(0, '#1E1640'); grd.addColorStop(0.42, '#7A3565'); grd.addColorStop(0.62, '#E0634F'); grd.addColorStop(0.74, '#FFA24F'); grd.addColorStop(1, '#FFC978'); }
  else { grd.addColorStop(0, '#FFD9C4'); grd.addColorStop(0.5, '#FFE9DB'); grd.addColorStop(0.75, '#FFF4EA'); grd.addColorStop(1, '#E6F6EC'); }
  g.fillStyle = grd; g.fillRect(0, 0, w, h);
});
scene.background = skyTex;
scene.fog = PS2 ? new THREE.Fog(0xD8705A, 16, 78) : new THREE.Fog(0xFFEADB, 38, 150);
const blobTex = canvasTex(64, 64, (g) => {
  const grd = g.createRadialGradient(32, 32, 2, 32, 32, 31);
  grd.addColorStop(0, 'rgba(40,50,80,0.55)'); grd.addColorStop(0.55, 'rgba(40,50,80,0.25)'); grd.addColorStop(1, 'rgba(40,50,80,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 64, 64);
});
const allLayers = o => { o.layers.enableAll(); return o; };
if (PS2) {
  scene.add(allLayers(new THREE.AmbientLight(0xFFE2C4, 2.3)));
  const sun = allLayers(new THREE.DirectionalLight(0xFFB070, 1.5)); sun.position.set(-6, 5, -10); scene.add(sun);
} else {
  scene.add(allLayers(new THREE.HemisphereLight(0xFFF8F2, 0xCFEFE0, 1.55)));
  const sun = allLayers(new THREE.DirectionalLight(0xFFF1E0, 1.25)); sun.position.set(-5, 9, 6); scene.add(sun);
  const fill = allLayers(new THREE.DirectionalLight(0xFFE3D2, 0.45)); fill.position.set(6, 4, -4); scene.add(fill);
}
let envFg = null, envBg = null;
if (!PS2) {
  envFg = new THREE.PMREMGenerator(fgR).fromScene(new RoomEnvironment(), 0.04).texture;
  envBg = new THREE.PMREMGenerator(bgR).fromScene(new RoomEnvironment(), 0.04).texture;
}

// ---------------------------------------------------------------- materials + shapes
const matCache = new Map();
function mat(hex, kind = 'plastic') {
  const key = hex + kind;
  if (matCache.has(key)) return matCache.get(key);
  let m;
  if (PS2) m = new THREE.MeshLambertMaterial({ map: pixelTex(hex, matCache.size + 1, 8, kind === 'flat' ? 0.05 : 0.17), flatShading: true });
  else if (kind === 'clay') m = new THREE.MeshPhysicalMaterial({ color: hex, roughness: 0.62, clearcoat: 0.18, clearcoatRoughness: 0.5, envMapIntensity: 0.55 });
  else if (kind === 'matte') m = new THREE.MeshStandardMaterial({ color: hex, roughness: 0.92, envMapIntensity: 0.35 });
  else if (kind === 'glow') m = new THREE.MeshBasicMaterial({ color: hex, fog: false });
  else if (kind === 'glass') m = new THREE.MeshPhysicalMaterial({ color: hex, roughness: 0.08, clearcoat: 1, envMapIntensity: 1.4, transparent: true, opacity: 0.55 });
  else m = new THREE.MeshPhysicalMaterial({ color: hex, roughness: 0.3, clearcoat: 0.85, clearcoatRoughness: 0.18, envMapIntensity: 0.9 });
  if (PS2 && kind === 'glow') m = new THREE.MeshBasicMaterial({ color: hex, fog: false });
  if (PS2 && kind === 'glass') { m.transparent = true; m.opacity = 0.6; }
  matCache.set(key, m);
  return m;
}
const basic = (hex, opts = {}) => new THREE.MeshBasicMaterial({ color: hex, ...opts });
const mesh = (g, m) => new THREE.Mesh(g, m);
const G = {
  capsule: (r, len) => PS2 ? new THREE.BoxGeometry(r * 1.8, len + r * 1.4, r * 1.8) : new THREE.CapsuleGeometry(r, len, 8, 20),
  sphere: (r) => PS2 ? new THREE.BoxGeometry(r * 1.7, r * 1.7, r * 1.7) : new THREE.SphereGeometry(r, 32, 24),
  ball: (r) => PS2 ? new THREE.IcosahedronGeometry(r, 0) : new THREE.SphereGeometry(r, 28, 20),
  box: (w, h, d, rr = 0.06) => PS2 ? new THREE.BoxGeometry(w, h, d) : new RoundedBoxGeometry(w, h, d, 4, Math.min(rr, w / 2.2, h / 2.2, d / 2.2)),
  cyl: (r, h, seg = 28) => new THREE.CylinderGeometry(r, r, h, PS2 ? 6 : seg),
  cone: (r, h, seg = 24) => new THREE.ConeGeometry(r, h, PS2 ? 5 : seg),
};
function blob(sx, sz, a = 1) {
  const m = mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false, opacity: a, fog: false }));
  m.rotation.x = -Math.PI / 2; m.scale.set(sx, sz, 1); m.position.y = 0.02; m.renderOrder = 2;
  return m;
}
// a style colour: clay and ps2 can differ; a spec may pass "#hex" (used for both) or ["#clay", "#ps2"]
// one colour is enough: in ps2 it is automatically made deeper and richer
function deep(hex) { const c = new THREE.Color(hex).convertLinearToSRGB(), g = (c.r + c.g + c.b) / 3, f = v => clamp(g + (v - g) * 1.2); return '#' + new THREE.Color().setRGB(f(c.r), f(c.g), f(c.b), THREE.SRGBColorSpace).getHexString(); }
const col = c => !c ? c : Array.isArray(c) ? c[PS2 ? 1 : 0] : (PS2 ? deep(c) : c);

// ---------------------------------------------------------------- people
const PAL = PS2
  ? { pants: '#3A4466', skin: ['#E0B088', '#B07848', '#E8C8A0', '#7A4A2C', '#E0B088'], shirts: ['#C0403C', '#3C6FB0', '#7A4CB0', '#2F9488', '#C8702C'] }
  : { pants: '#7385AD', skin: ['#F4CCA8', '#CC9468', '#F8DCC0', '#96664A', '#F4CCA8'], shirts: ['#FF8E8E', '#8EC5FF', '#C7A6F5', '#7DDBC8', '#FFB37A'] };
const HAIR = ['#1E1E24', '#1E1E24', '#D9A441', '#1E1E24', '#8B4A2B'], HSTYLE = ['short', 'bun', 'long', 'short', 'short'];
const LOOKS = {
  you: { skin: PAL.skin[0], shirt: PS2 ? '#E8B020' : '#FFC53D', hair: '#3B2A20' },
  stranger: { skin: PAL.skin[1], shirt: PS2 ? '#3F8A4C' : '#7CCB93', hair: '#1E1E24', bulk: 1.18, pack: true, pants: PS2 ? '#4A3A2C' : '#A08A74' },
  one: { skin: PAL.skin[2], shirt: PS2 ? '#C8508C' : '#F7A1C8', hair: '#8B4A2B', style: 'long' },
  elder: { skin: PAL.skin[2], shirt: PS2 ? '#6A6FA0' : '#B9C2F0', hair: '#D8D8DC', style: 'short' },
};
'abcde'.split('').forEach((k, i) => { LOOKS[k] = { skin: PAL.skin[i], shirt: PAL.shirts[i], hair: HAIR[i], style: HSTYLE[i] }; });
function faceTex(skin) {
  return canvasTex(8, 8, (g) => { g.fillStyle = skin; g.fillRect(0, 0, 8, 8); g.fillStyle = '#1D2742'; g.fillRect(1, 3, 2, 2); g.fillRect(5, 3, 2, 2); g.fillRect(3, 6, 2, 1); }, true);
}
function makePerson({ skin, shirt, pants = PAL.pants, hair = '#3B2A20', style = 'short', bulk = 1, pack = false }) {
  const root = new THREE.Group();
  const hips = new THREE.Group(); hips.position.y = 0.86; root.add(hips);
  const spine = new THREE.Group(); hips.add(spine);
  const skinM = mat(skin, 'clay'), shirtM = mat(shirt), pantsM = mat(pants, 'clay');
  const torso = mesh(G.capsule(0.25 * bulk, 0.42), shirtM); torso.position.y = 0.36; spine.add(torso);
  const headG = new THREE.Group(); headG.position.y = 0.98; spine.add(headG);
  headG.add(PS2 ? mesh(new THREE.BoxGeometry(0.46, 0.46, 0.44), [skinM, skinM, skinM, skinM, new THREE.MeshLambertMaterial({ map: faceTex(skin) }), skinM]) : mesh(G.sphere(0.3), skinM));
  const hairM = mat(hair, 'clay');
  let mouth = null;
  if (PS2) {
    const cap = mesh(new THREE.BoxGeometry(0.5, 0.2, 0.48), hairM); cap.position.set(0, 0.17, -0.02); headG.add(cap);
    if (style === 'long') { const b = mesh(new THREE.BoxGeometry(0.5, 0.42, 0.14), hairM); b.position.set(0, -0.02, -0.2); headG.add(b); }
    if (style === 'bun') { const b = mesh(new THREE.BoxGeometry(0.2, 0.18, 0.2), hairM); b.position.set(0, 0.34, -0.05); headG.add(b); }
  } else {
    const cap = mesh(new THREE.SphereGeometry(0.315, 32, 16, 0, Math.PI * 2, 0, Math.PI * 0.46), hairM); cap.rotation.x = -0.32; headG.add(cap);
    if (style === 'long') { const b = mesh(new THREE.SphereGeometry(0.3, 24, 16), hairM); b.scale.set(1.02, 1.15, 0.7); b.position.set(0, -0.1, -0.13); headG.add(b); }
    if (style === 'bun') { const b = mesh(new THREE.SphereGeometry(0.13, 20, 14), hairM); b.position.set(0, 0.34, -0.08); headG.add(b); }
    const eyeM = basic('#1D2742');
    for (const sx of [-1, 1]) { const e = mesh(new THREE.SphereGeometry(0.034, 12, 10), eyeM); e.position.set(sx * 0.105, 0.03, 0.272); headG.add(e); }
    mouth = mesh(new THREE.SphereGeometry(0.04, 12, 10), eyeM); mouth.position.set(0, -0.1, 0.275); mouth.scale.set(1.3, 0.35, 0.5); headG.add(mouth);
  }
  if (pack) { const b = mesh(G.box(0.4, 0.5, 0.22, 0.08), mat(PS2 ? '#7A5230' : '#C98B5E')); b.position.set(0, 0.4, -0.3); spine.add(b); }
  const arm = (sx) => {
    const sh = new THREE.Group(); sh.position.set(sx * 0.34 * bulk, 0.64, 0); spine.add(sh);
    const up = mesh(G.capsule(0.078, 0.26), shirtM); up.position.y = -0.19; sh.add(up);
    const el = new THREE.Group(); el.position.y = -0.38; sh.add(el);
    const lo = mesh(G.capsule(0.072, 0.24), shirtM); lo.position.y = -0.17; el.add(lo);
    const hand = mesh(G.sphere(0.095), skinM); hand.position.y = -0.37; el.add(hand);
    return { sh, el };
  };
  const leg = (sx) => {
    const hp = new THREE.Group(); hp.position.set(sx * 0.13 * bulk, 0.02, 0); hips.add(hp);
    const l = mesh(G.capsule(0.1, 0.56), pantsM); l.position.y = -0.4; hp.add(l);
    const foot = mesh(G.box(0.2, 0.12, 0.34, 0.05), mat(PS2 ? '#22283C' : '#4A5878', 'clay')); foot.position.set(0, -0.8, 0.07); hp.add(foot);
    return hp;
  };
  const armL = arm(1), armR = arm(-1), legL = leg(1), legR = leg(-1);
  const shadow = blob(1.5, 1.5); root.add(shadow);
  const setPose = (p) => {
    spine.rotation.x = rad(p.lean); spine.rotation.z = rad(p.sway);
    headG.rotation.z = rad(p.tilt); headG.rotation.x = rad(p.nod); headG.rotation.y = rad(p.turn || 0);
    armL.sh.rotation.set(rad(p.lx), 0, rad(p.lz)); armR.sh.rotation.set(rad(p.rx), 0, rad(p.rz));
    armL.el.rotation.x = rad(p.le); armR.el.rotation.x = rad(p.re);
    legL.rotation.x = rad(p.ll); legR.rotation.x = rad(p.rl);
    hips.position.y = 0.86 - (p.sit || 0) * 0.42;
    if (mouth) mouth.scale.set(lerp(1.3, 1.0, p.open), lerp(0.35, 1.25, p.open), 0.5);
  };
  return { root, setPose, shadow };
}
const STAND = { lean: 0, sway: 0, tilt: 0, nod: 0, turn: 0, lx: 0, lz: 8, rx: 0, rz: -8, le: -6, re: -6, ll: 0, rl: 0, open: 0, sit: 0 };
const POSES = {
  stand: STAND,
  pull: { ...STAND, rx: -62, re: -18, lean: 6 },
  push: { ...STAND, lx: -86, rx: -86, le: -4, re: -4, lean: 12, ll: -10, rl: 12 },
  think: { ...STAND, rx: -30, re: -128, rz: 6, tilt: -7, nod: 4, lz: 6 },
  pushed: { ...STAND, lean: 26, lx: -40, rx: -50, lz: 55, rz: -55, open: 1 },
  point: { ...STAND, rx: -82, re: -4, lean: 3 },
  reach: { ...STAND, lx: -70, rx: -70, le: -20, re: -20, lean: 8 },
  cheer: { ...STAND, lz: 150, rz: -150, le: -14, re: -14, open: 1 },
  shrug: { ...STAND, lz: 38, rz: -38, le: -70, re: -70, tilt: 6 },
  wave: { ...STAND, rz: -150, re: -30, open: 0.5 },
  sad: { ...STAND, nod: 22, lean: 8, lz: 4, rz: -4 },
  shock: { ...STAND, lz: 60, rz: -60, le: -60, re: -60, lean: -6, open: 1 },
  sit: { ...STAND, ll: -85, rl: -85, sit: 1, lean: 2 },
  walk1: { ...STAND, ll: -24, rl: 24, lx: 18, rx: -18 },
  walk2: { ...STAND, ll: 24, rl: -24, lx: -18, rx: 18 },
  carry: { ...STAND, lx: -55, rx: -55, le: -50, re: -50 },
};
const mixPose = (a, b, u) => { const o = {}; for (const k in STAND) o[k] = lerp(a[k] ?? STAND[k], b[k] ?? STAND[k], u); return o; };
const panicPose = (t, ph) => ({ ...STAND, lz: 150 + 15 * Math.sin(t * 9 + ph), rz: -150 - 15 * Math.sin(t * 9 + ph + 1.3), le: -14, re: -14, sway: 3 * Math.sin(t * 4 + ph), open: 1 });
const walkPose = (t, ph) => { const k = Math.sin(t * 9 + ph); return { ...STAND, ll: 30 * k, rl: -30 * k, lx: -24 * k, rx: 24 * k, le: -18, re: -18, lean: 3 }; };
const poseOf = p => typeof p === 'string' ? (POSES[p] || (warn.push('unknown pose ' + p), STAND)) : { ...STAND, ...p };

// ---------------------------------------------------------------- builders for each object kind
const C_BALLAST = PS2 ? '#8C7560' : '#FBE3D1', C_TIE = PS2 ? '#4A3426' : '#E8B79A', C_RAIL = PS2 ? '#9AA0A8' : '#F4F1EC';
function smooth(pts, per = 6) {            // Catmull-Rom through [x, z] points
  const v = pts.map(p => new THREE.Vector3(p[0], 0, p[1]));
  return new THREE.CatmullRomCurve3(v, false, 'centripetal').getPoints((pts.length - 1) * per);
}
const pathPts = o => o.smooth ? smooth(o.path) : o.path.map(p => new THREE.Vector3(p[0], 0, p[1]));
function makeTrack(o) {
  const pts = pathPts(o), g = new THREE.Group();
  let acc = 0, next = 0.3;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i], dx = b.x - a.x, dz = b.z - a.z, len = Math.hypot(dx, dz), ang = Math.atan2(dx, dz);
    const mid = new THREE.Vector3((a.x + b.x) / 2, 0, (a.z + b.z) / 2);
    const bal = mesh(new THREE.BoxGeometry(2.9, 0.08, len + 0.05), mat(C_BALLAST, 'matte')); bal.position.copy(mid).setY(0.04); bal.rotation.y = ang; g.add(bal);
    for (const sx of [-0.72, 0.72]) {
      const rail = mesh(new THREE.BoxGeometry(0.1, 0.13, len + 0.05), mat(C_RAIL));
      rail.position.set(mid.x + Math.cos(ang) * sx, 0.2, mid.z - Math.sin(ang) * sx); rail.rotation.y = ang; g.add(rail);
    }
    while (next <= acc + len) {
      const u = (next - acc) / len;
      const tie = mesh(G.box(2.3, 0.1, 0.28, 0.04), mat(C_TIE, 'clay')); tie.position.set(a.x + dx * u, 0.11, a.z + dz * u); tie.rotation.y = ang; g.add(tie);
      next += 0.85;
    }
    acc += len;
  }
  return { root: g };
}
function makeArrows(o) {
  const pts = pathPts(o), g = new THREE.Group(), arrows = [];
  for (let i = 0; i < (o.count || 12); i++) { const a = mesh(new THREE.ConeGeometry(0.34, 0.62, 3), basic(o.color || '#FF4040', { fog: false })); a.scale.set(1, 1, 0.22); g.add(a); arrows.push(a); }
  let total = 0; for (let i = 1; i < pts.length; i++) total += pts[i].distanceTo(pts[i - 1]);
  const along = (d) => { for (let i = 1; i < pts.length; i++) { const len = pts[i].distanceTo(pts[i - 1]); if (d <= len) return { p: pts[i - 1].clone().lerp(pts[i], d / len), ang: Math.atan2(pts[i].x - pts[i - 1].x, pts[i].z - pts[i - 1].z) }; d -= len; } return { p: pts[pts.length - 1], ang: 0 }; };
  return { root: g, tick: (t) => arrows.forEach((a, i) => { const q = along((i * total / arrows.length + t * (o.speed || 3.2)) % total); a.position.copy(q.p).setY((o.y || 0) + 0.32); a.rotation.set(Math.PI / 2, 0, 0); a.rotation.order = 'YXZ'; a.rotation.y = q.ang; }) };
}
function makeTrolley() {
  const g = new THREE.Group();
  const body = mesh(G.box(2.2, 2.0, 4.6, 0.32), mat(PS2 ? '#B8322F' : '#FF9484')); body.position.y = 1.75; g.add(body);
  const band = mesh(G.box(2.24, 0.34, 4.64, 0.1), mat(PS2 ? '#E8D8A8' : '#FFF3E4')); band.position.y = 1.32; g.add(band);
  const roof = mesh(G.box(2.0, 0.22, 4.3, 0.1), mat(PS2 ? '#6E2A28' : '#FFD0C2')); roof.position.y = 2.84; g.add(roof);
  const winM = PS2 ? basic('#FFD27A', { fog: false }) : new THREE.MeshPhysicalMaterial({ color: '#C8ECF5', roughness: 0.08, clearcoat: 1, envMapIntensity: 1.4 });
  for (const z of [-1.4, 0, 1.4]) for (const sx of [-1, 1]) { const w = mesh(G.box(0.08, 0.72, 0.95, 0.03), winM); w.position.set(sx * 1.1, 2.15, z); g.add(w); }
  const front = mesh(G.box(1.5, 0.72, 0.08, 0.03), winM); front.position.set(0, 2.15, -2.3); g.add(front);
  const back = front.clone(); back.position.z = 2.3; g.add(back);
  const lamp = mesh(G.ball(0.2), basic('#FFF2B0', { fog: false })); lamp.position.set(0, 1.3, -2.36); g.add(lamp);
  const beam = mesh(new THREE.ConeGeometry(1.7, 7, PS2 ? 6 : 24, 1, true), new THREE.MeshBasicMaterial({ color: '#FFF2B0', transparent: true, opacity: PS2 ? 0.1 : 0.16, depthWrite: false, side: THREE.DoubleSide, fog: false }));
  beam.rotation.x = Math.PI / 2; beam.position.set(0, 1.15, -5.8); g.add(beam);
  for (const z of [-1.5, 1.5]) for (const sx of [-1, 1]) { const w = mesh(G.cyl(0.38, 0.2), mat(PS2 ? '#2A2E3A' : '#7C8AA3')); w.rotation.z = Math.PI / 2; w.position.set(sx * 0.78, 0.5, z); g.add(w); }
  g.add(blob(4.4, 7.2));
  const inner = new THREE.Group(); while (g.children.length) inner.add(g.children[0]); g.add(inner);
  return { root: g, tick: (t, s) => { const w = s.wobble ?? 1; inner.position.set(0.03 * Math.sin(t * 31) * w, 0.02 * Math.sin(t * 27) * w, 0); inner.rotation.z = 0.008 * Math.sin(t * 23) * w; } };
}
function makeLever() {
  const g = new THREE.Group(), armG = new THREE.Group(); armG.position.y = 0.2; g.add(armG);
  const base = mesh(G.box(0.7, 0.24, 0.5, 0.08), mat(PS2 ? '#5A6070' : '#DCE3EA')); base.position.y = 0.12; g.add(base);
  const stick = mesh(G.cyl(0.05, 1.05, 16), mat(PS2 ? '#8A909C' : '#9AA7BB')); stick.position.y = 0.52; armG.add(stick);
  const knob = mesh(G.ball(0.15), mat(PS2 ? '#C83030' : '#FF6F61')); knob.position.y = 1.08; armG.add(knob);
  g.add(blob(1.3, 1.3, 0.8));
  return { root: g, parts: { arm: armG }, up: 0.95 };
}
function makeBridge(o) {
  const g = new THREE.Group(), DECK = o.height || 3.6, L = o.length || 15;
  const cB = PS2 ? '#7A6A60' : '#FFE1CC', cR = PS2 ? '#3E4658' : '#9ADBC0';
  const deck = mesh(G.box(L, 0.36, 1.9, 0.12), mat(cB)); deck.position.set(0, DECK - 0.18, 0); g.add(deck);
  for (const sx of [-1, 1]) {
    const p = mesh(G.box(1.0, DECK - 0.3, 1.5, 0.14), mat(cB)); p.position.set(sx * 3.6, (DECK - 0.3) / 2, 0); g.add(p);
    const b = blob(3.4, 3.8, 0.9); b.position.x = sx * 3.6; g.add(b);
  }
  for (const z of [-0.88, 0.88]) {
    const rail = mesh(G.box(L, 0.1, 0.1, 0.04), mat(cR)); rail.position.set(0, DECK + 1.0, z); g.add(rail);
    for (let x = -Math.floor(L / 2); x <= L / 2; x += 1) { const post = mesh(G.box(0.09, 1.0, 0.09, 0.03), mat(cR)); post.position.set(x, DECK + 0.5, z); g.add(post); }
  }
  return { root: g };
}
function makeProp(o) {      // anything else: a named prop from props.json, or primitive parts listed in the spec
  const g = new THREE.Group(), parts = {};
  const lib = o.use ? PROPS[o.use] : (PROPS[o.kind] || null);
  if ((o.use || !o.parts) && !lib) warn.push(`unknown prop "${o.use || o.kind}" (id ${o.id})`);
  const def = lib || {};
  const tint = o.tint ? (c => c === '$' ? o.tint : c) : (c => c === '$' ? (def.tint || '#FF9484') : c);
  for (const p of o.parts || def.parts || []) {
    const s = p.size || [1, 1, 1];
    const geo = p.s === 'box' ? G.box(s[0], s[1], s[2], p.round ?? 0.08) : p.s === 'ball' ? G.ball(s[0]) : p.s === 'cyl' ? G.cyl(s[0], s[1], p.seg || 28) : p.s === 'cone' ? G.cone(s[0], s[1], p.seg || 24) : p.s === 'capsule' ? G.capsule(s[0], s[1]) : p.s === 'plane' ? new THREE.PlaneGeometry(s[0], s[1]) : G.box(1, 1, 1);
    const m = mesh(geo, mat(col(tint(p.color || '#DDDDDD')), p.mat || 'plastic'));
    m.position.set(...(p.at || [0, 0, 0]));
    if (p.rot) m.rotation.set(rad(p.rot[0]), rad(p.rot[1]), rad(p.rot[2]));
    if (p.id) { const pivot = new THREE.Group(); pivot.position.copy(m.position); m.position.set(...(p.offset || [0, 0, 0])); pivot.add(m); g.add(pivot); parts[p.id] = pivot; } else g.add(m);
  }
  const sh = o.shadow || def.shadow;
  if (sh) g.add(blob(sh[0], sh[1], 0.85));
  return { root: g, parts, up: o.up ?? def.up };
}
function makeArc(o) {
  const g = new THREE.Group(), dots = [];
  const a = new THREE.Vector3(...o.from), c = new THREE.Vector3(...o.via), b = new THREE.Vector3(...o.to);
  for (let i = 0; i < (o.count || 12); i++) {
    const q = i / ((o.count || 12) - 1), d = mesh(new THREE.SphereGeometry(0.11, 10, 8), basic(o.color || '#FF4040', { fog: false }));
    d.position.set((1 - q) * (1 - q) * a.x + 2 * (1 - q) * q * c.x + q * q * b.x, (1 - q) * (1 - q) * a.y + 2 * (1 - q) * q * c.y + q * q * b.y, (1 - q) * (1 - q) * a.z + 2 * (1 - q) * q * c.z + q * q * b.z);
    d.userData.q = q; g.add(d); dots.push(d);
  }
  return { root: g, absolute: true, tick: (t, s) => dots.forEach(d => { d.visible = (s.progress || 0) > 0 && d.userData.q <= (s.progress || 0) + 0.001; }) };
}
function ghostify(root, shadow) {
  root.traverse(o => { if (o.isMesh && o !== shadow) { const ms = (Array.isArray(o.material) ? o.material : [o.material]).map(m => { const c = m.clone(); c.transparent = true; c.opacity = 0.42; c.depthWrite = false; return c; }); o.material = Array.isArray(o.material) ? ms : ms[0]; } });
}

// ---------------------------------------------------------------- instantiate the spec
const OBJ = {};
let phase = 0;
for (const o of SPEC.objects) {
  let b;
  if (o.kind === 'person') {
    const look = typeof o.look === 'string' ? (LOOKS[o.look] || (warn.push('unknown look ' + o.look), LOOKS.a)) : { ...LOOKS.a, ...o.look };
    b = makePerson({ ...look, ...(o.wear || {}) }); b.person = true; b.up = 2.38; b.phase = (phase++) * 1.1;
    if (o.ghost) { ghostify(b.root, b.shadow); b.ghost = true; }
  } else if (o.kind === 'track') b = makeTrack(o);
  else if (o.kind === 'arrows') b = makeArrows(o);
  else if (o.kind === 'trolley') b = makeTrolley();
  else if (o.kind === 'lever') b = makeLever();
  else if (o.kind === 'bridge') b = makeBridge(o);
  else if (o.kind === 'arc') b = makeArc(o);
  else b = makeProp(o);
  b.id = o.id; b.kind = o.kind;
  b.init = { tip: o.tip || 0, roll: o.roll || 0, pos: o.at || [0, 0, 0], face: o.face || 0, scale: o.scale ?? 1, show: o.show !== false, pose: poseOf(o.pose || 'stand'), panic: o.behave === 'panic' ? 1 : 0, wobble: o.wobble === false ? 0 : 1, progress: o.progress || 0, parts: { ...(o.set || {}) } };
  b.actions = (SPEC.actions || []).filter(a => a.id === o.id || (Array.isArray(a.id) && a.id.includes(o.id))).sort((x, y) => x.at - y.at);
  if (b.person) b.rad = 0.6; else if (!['track', 'arrows', 'arc', 'bridge'].includes(o.kind)) { const bb = new THREE.Box3().setFromObject(b.root), sz = bb.getSize(new THREE.Vector3()); b.rad = Math.min(3, Math.max(sz.x, sz.z) / 2) * (o.scale ?? 1); if (b.up === undefined) b.up = sz.y; }
  scene.add(b.root); OBJ[o.id] = b;
}
for (const a of SPEC.actions || []) for (const id of [].concat(a.id)) if (!OBJ[id]) warn.push('action for unknown object ' + id);
const GROUPS = SPEC.groups || {};
const expand = names => names === 'all' ? Object.keys(OBJ) : [].concat(names).flatMap(n => GROUPS[n] || [n]);

const lerpAng = (a, b, u) => a + ((((b - a) % 360) + 540) % 360 - 180) * u;
function faceOf(b, f, pos) {
  if (typeof f !== 'string') return f;
  const ids = expand(f).filter(i => OBJ[i]); if (!ids.length) { warn.push(`${b.id}: cannot face unknown "${f}"`); return 0; }
  let x = 0, z = 0; for (const i of ids) { const p = OBJ[i].state ? OBJ[i].state.pos : OBJ[i].init.pos; x += p[0] / ids.length; z += p[2] / ids.length; }
  return Math.atan2(x - pos[0], z - pos[2]) * 180 / Math.PI;
}
function stateAt(b, t) {
  const s = { tip: b.init.tip, roll: b.init.roll, pos: [...b.init.pos], face: faceOf(b, b.init.face, b.init.pos), scale: b.init.scale, show: b.init.show, pose: b.init.pose, panic: b.init.panic, walk: 0, wobble: b.init.wobble, progress: b.init.progress, parts: {} };
  for (const k in b.init.parts) s.parts[k] = [...b.init.parts[k]];
  for (const a of b.actions) {
    if (t < a.at) break;
    if (a.osc) { if (t < a.to) { const k = EASE.inout(0.5 + 0.5 * Math.sin((t - a.at) * 2 * Math.PI / (a.period || 0.8) + Math.PI / 2)); s.parts[a.part] = [0, 0, lerp(a.osc[0], a.osc[1], k)]; } continue; }
    const dur = a.dur ?? 0.4, u = (EASE[a.ease] || EASE.inout)(dur > 0 ? (t - a.at) / dur : 1);
    if (a.pos) s.pos = s.pos.map((v, i) => lerp(v, a.pos[i], u));
    if (a.walk && dur > 0 && t - a.at < dur) s.walk = Math.min(1, (t - a.at) / 0.15, (a.at + dur - t) / 0.15);
    if (a.y !== undefined) s.pos[1] = lerp(s.pos[1], a.y, u);
    if (a.face !== undefined) s.face = lerpAng(s.face, faceOf(b, a.face, a.pos || s.pos), u);
    if (a.scale !== undefined) s.scale = lerp(s.scale, a.scale, u);
    if (a.tip !== undefined) s.tip = lerp(s.tip, a.tip, u);
    if (a.roll !== undefined) s.roll = lerp(s.roll, a.roll, u);
    if (a.pose) s.pose = mixPose(s.pose, poseOf(a.pose), u);
    if (a.panic !== undefined) s.panic = lerp(s.panic, a.panic, u);
    if (a.wobble !== undefined) s.wobble = lerp(s.wobble, a.wobble, u);
    if (a.progress !== undefined) s.progress = lerp(s.progress, a.progress, u);
    if (a.part) { const cur = s.parts[a.part] || [0, 0, 0]; s.parts[a.part] = cur.map((v, i) => lerp(v, (a.rot || cur)[i], u)); }
    if (a.show !== undefined) s.show = a.show;
  }
  return s;
}
function applyAll(t) {
  for (const b of Object.values(OBJ)) {
    const s = stateAt(b, t); b.state = s;
    b.root.visible = s.show;
    if (!b.absolute) { b.root.position.set(...s.pos); b.root.rotation.set(rad(s.tip), rad(s.face), rad(s.roll), 'YXZ'); b.root.scale.setScalar(s.scale); }
    if (b.person) b.setPose(s.panic > 0 ? mixPose(s.pose, panicPose(t, b.phase), s.panic) : s.walk > 0 ? mixPose(s.pose, walkPose(t, b.phase), s.walk) : s.pose);
    for (const k in s.parts) if (b.parts && b.parts[k]) b.parts[k].rotation.set(rad(s.parts[k][0]), rad(s.parts[k][1]), rad(s.parts[k][2]));
    if (b.tick) b.tick(t, s);
  }
}

// ---------------------------------------------------------------- camera
const SHOTS = [...SPEC.shots].sort((a, b) => a.at - b.at);
const V = (a) => new THREE.Vector3(...a);
function centreOf(ids) { const c = new THREE.Vector3(); const list = expand(ids).filter(i => OBJ[i]); list.forEach(i => c.add(OBJ[i].root.position)); return c.multiplyScalar(1 / Math.max(1, list.length)); }
function spreadOf(ids, c) { return Math.max(0, ...expand(ids).filter(i => OBJ[i]).map(i => OBJ[i].root.position.distanceTo(c))); }
const ray = new THREE.Raycaster(); ray.layers.enableAll();
const solid = h => { const m = Array.isArray(h.object.material) ? h.object.material[0] : h.object.material; return m && !m.transparent; };
function hiddenBy(camPos, ids, extra = [], mutual = true) {      // which object stands between the camera and the subjects? (null = clear view)
  const subj = expand(ids).filter(i => OBJ[i] && OBJ[i].root.visible);
  const things = Object.values(OBJ).filter(b => b.root.visible && !['track', 'arrows', 'arc'].includes(b.kind));
  for (const id of subj) {
    const b = OBJ[id]; if (['track', 'arrows', 'arc', 'bridge'].includes(b.kind)) continue;
    for (const h of [0.82, 0.3]) {
      const target = b.root.position.clone(); target.y += (b.up ?? 2) * h;
      const dir = target.clone().sub(camPos), dist = dir.length(); ray.set(camPos, dir.normalize()); ray.far = dist - Math.max(0.5, b.rad || 0.5);
      for (const k of things) if (k !== b && !((h < 0.5 || !mutual) && subj.includes(k.id)) && ray.intersectObject(k.root, true).some(solid)) return k.id;
      if (extra.length && ray.intersectObjects(extra, true).some(solid)) return 'the scenery';
    }
  }
  return null;
}
const ROOM = (SPEC.world || {}).scenery === 'room' ? ((SPEC.world || {}).room || [26, 22]) : null;
const inWorld = p => !ROOM || (Math.abs(p.x) < ROOM[0] / 2 - 0.8 && Math.abs(p.z) < ROOM[1] / 2 - 0.8 && p.y < 8.4);
const FOV = { tight: 40, mid: 46, wide: 50, side: 50, close: 44 };
function presetCam(c, az, u) {
  const list = expand(c.on || []).filter(i => OBJ[i]);
  const ctr = c.center ? V(c.center) : centreOf(list), a = rad(az), dir = new THREE.Vector3(Math.sin(a), 0, Math.cos(a)), right = new THREE.Vector3(Math.cos(a), 0, -Math.sin(a));
  let lat = c.center ? (c.radius || 4) : 0, depth = 0;      // how far the subjects reach sideways and towards the camera
  for (const i of list) { const d = OBJ[i].root.position.clone().sub(ctr), r = OBJ[i].rad || 0.6; lat = Math.max(lat, Math.abs(d.dot(right)) + r); depth = Math.max(depth, d.dot(dir) + r); }
  const fov = c.fov || FOV[c.preset] || 44, tanH = Math.tan(rad(fov / 2)) * W / H;
  let dist, hy, ly;
  if (c.preset === 'tight') { dist = 2.7 + lat * 0.6; hy = 1.35; ly = 1.52; }
  else if (c.preset === 'mid') { dist = Math.max(5.2, (lat + 0.45) / tanH, depth + 3.8); hy = 1.9; ly = 1.25; }
  else if (c.preset === 'wide') { dist = Math.max(10, (lat + 1.2) / tanH * 0.8, depth + 7); hy = c.height ?? Math.min(8.2, Math.max(6, dist * 0.7)); ly = 0.6; }
  else if (c.preset === 'side') { dist = Math.max(9, (lat + 1) / tanH); hy = c.height ?? 2.4; ly = 1.6; }
  else { dist = Math.max(4.3, (lat + 0.2) / tanH * 0.8, depth + 3.2); hy = 0.85; ly = 1.2; }
  dist *= (c.dist ?? 1) * lerp(1, 0.94, u);
  return { pos: ctr.clone().add(dir.multiplyScalar(dist)).setY(ctr.y + hy), look: ctr.clone().setY(ctr.y + ly + (c.lift || 0)), fov, dist };
}
const PRESETS = ['close', 'tight', 'mid', 'wide', 'side'];
function chooseAzimuth(shot) {
  if (!PRESETS.includes(shot.cam.preset)) warn.push('unknown camera preset ' + shot.cam.preset);
  for (const i of [].concat(shot.cam.on || [])) if (!OBJ[i] && !GROUPS[i]) warn.push(`shot at ${shot.at}: camera is on unknown object "${i}"`);                     // called once per shot, with the stage set to the middle of the shot
  const c = shot.cam; if (c.azimuth !== undefined) return c.azimuth;
  const ids = expand(c.on || []).filter(i => OBJ[i]), side = c.side ?? -1;
  let base, offs;
  if (ids.length >= 2 && c.preset !== 'side') {    // a group: look along it at an angle, so it stacks in depth and fills the tall frame
    const p0 = OBJ[ids[0]].root.position, p1 = OBJ[ids[ids.length - 1]].root.position;
    base = Math.atan2(p1.x - p0.x, p1.z - p0.z) * 180 / Math.PI + 180;      // from behind the last one... no: facing the first, past the last
    offs = [30 * side, -30 * side, 50 * side, -50 * side, 180 + 30 * side, 180 - 30 * side, 180 + 50 * side, 180 - 50 * side, 75 * side, -75 * side, 90, -90, 0, 180];
  } else if (ids.length >= 2) {
    const p0 = OBJ[ids[0]].root.position, p1 = OBJ[ids[1]].root.position;
    base = Math.atan2(-(p1.z - p0.z), p1.x - p0.x) * 180 / Math.PI; if (Math.cos(rad(base)) < 0) base += 180;
    offs = [0, 180, 20 * side, -20 * side];
  } else {
    base = ids.length ? OBJ[ids[0]].state.face : 0; const k = c.preset === 'wide' ? 28 : 36;
    offs = [k * side, -k * side, 62 * side, -62 * side, 12 * side, 95 * side, -95 * side, 130 * side, -130 * side, 180];
  }
  scene.updateMatrixWorld(true);
  let best = null;
  const probe = new THREE.PerspectiveCamera(46, W / H, 0.1, 400), ndc = (id, h) => { const b = OBJ[id], v = b.root.position.clone(); v.y += (b.up ?? 2) * h; const d = v.distanceTo(probe.position); v.project(probe); return { x: v.x, y: v.y, d }; };
  offs.forEach((o, n) => {
    const k = presetCam(c, base + o, 0.5), bad = (inWorld(k.pos) ? 0 : 200) + (hiddenBy(k.pos, c.on || []) ? 50 : 0);
    probe.position.copy(k.pos); probe.fov = k.fov; probe.lookAt(k.look); probe.updateProjectionMatrix(); probe.updateMatrixWorld();
    const sub = ids.map(i => ndc(i, 0.6)), near = Math.min(...sub.map(q => q.d));
    let clutter = 0;                                                         // other things poking into the foreground, subjects hiding one another
    for (const b of Object.values(OBJ)) if (!ids.includes(b.id) && b.root.visible && !['track', 'arrows', 'arc', 'bridge'].includes(b.kind)) { const q = ndc(b.id, 0.5); if (Math.abs(q.x) < 1.15 && Math.abs(q.y) < 1.2 && q.d < near - 0.2) clutter++; }
    for (let i = 0; i < sub.length; i++) for (let j = i + 1; j < sub.length; j++) if (Math.abs(sub[i].x - sub[j].x) < 0.5) clutter += 0.6;
    const score = (ids.length >= 2 ? k.dist : 0) + n * 0.6 + clutter * 5 + bad;    // groups: the closest clear view wins; a single subject: the first clear view
    if (!best || score < best.score) best = { az: base + o, score };
  });
  return best ? best.az : base + offs[0];
}
function camOf(shot, u) {
  const c = shot.cam;
  if (c.preset) return presetCam(c, shot._az ?? c.azimuth ?? 0, u);
  const base = c.rel && OBJ[c.rel] ? OBJ[c.rel].root.position : new THREE.Vector3();
  const t0 = c, t1 = c.to || c;
  return { pos: V(t0.pos).lerp(V(t1.pos || t0.pos), u).add(base), look: V(t0.look).lerp(V(t1.look || t0.look), u).add(base), fov: lerp(t0.fov || 46, t1.fov || t0.fov || 46, u) };
}
function blendCam(a, b, w) {      // orbit-style blend: the look point slides, the camera swings around it
  const look = a.look.clone().lerp(b.look, w), oa = a.pos.clone().sub(a.look), ob = b.pos.clone().sub(b.look);
  let ya = Math.atan2(oa.x, oa.z), yb = Math.atan2(ob.x, ob.z), d = Math.atan2(Math.sin(yb - ya), Math.cos(yb - ya));
  const y = ya + d * w, r = lerp(Math.hypot(oa.x, oa.z), Math.hypot(ob.x, ob.z), w), h = lerp(oa.y, ob.y, w);
  return { pos: look.clone().add(new THREE.Vector3(Math.sin(y) * r, h, Math.cos(y) * r)), look, fov: lerp(a.fov, b.fov, w) };
}
function setCam(k) { camera.position.copy(k.pos); camera.fov = k.fov; camera.lookAt(k.look); camera.updateProjectionMatrix(); camera.updateMatrixWorld(); }

// ---------------------------------------------------------------- scenery (after the cast, so it can keep clear of them and of the cameras)
const sceneryG = new THREE.Group(); scene.add(sceneryG);
{
  applyAll(0);
  const clearPts = Object.values(OBJ).filter(b => !b.absolute && b.kind !== 'track' && b.kind !== 'arrows').map(b => b.root.position.clone());
  for (const b of Object.values(OBJ)) for (const a of b.actions) if (a.pos) clearPts.push(V(a.pos));
  for (const o of SPEC.objects) if (o.kind === 'track' || o.kind === 'arrows') for (const p of pathPts(o)) clearPts.push(p.clone());
  SHOTS.forEach((sh, i) => {
    const mid = (sh.at + (i + 1 < SHOTS.length ? SHOTS[i + 1].at : TL.total)) / 2;
    applyAll(mid); applyAll(mid);
    if (sh.cam.preset) sh._az = chooseAzimuth(sh);
    for (const u of [0, 1]) { const k = camOf(sh, u); for (const q of [0, 0.25, 0.5, 0.75]) clearPts.push(k.pos.clone().lerp(k.look, q)); }
  });
  const clear = (x, z, r) => clearPts.every(p => Math.hypot(p.x - x, p.z - z) > r);
  const gcol = world.ground;
  const groundM = PS2 ? new THREE.MeshLambertMaterial({ map: (() => { const t = pixelTex(col(gcol) || '#6E8C46', 5, 16, 0.2); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(90, 90); return t; })() })
                      : new THREE.MeshBasicMaterial({ color: col(gcol) || '#C4ECD9' });
  const ground = mesh(new THREE.PlaneGeometry(400, 400), groundM); ground.rotation.x = -Math.PI / 2; sceneryG.add(ground);
  const r0 = rng(SPEC.seed || 42), kind = world.scenery ?? 'default';
  if (kind === 'room') {
    // an office: floor, two walls with windows, a few plants (clay: peach and mint; ps2: sunset through the windows)
    const [RW, RD] = world.room || [26, 22], RH = 9;
    ground.material = PS2 ? new THREE.MeshLambertMaterial({ map: (() => { const t = pixelTex('#B79AAE', 6, 16, 0.14); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(60, 60); return t; })() }) : new THREE.MeshBasicMaterial({ color: col(gcol) || '#FBE0CF' });
    const wallM = PS2 ? mat('#C9A0B4', 'matte') : basic('#FFDCC9'), trimM = mat(PS2 ? '#2E2238' : '#9ADBC0'), paneM = basic(PS2 ? '#FFB45A' : '#EAF8FF', { fog: false });
    const wallM2 = PS2 ? wallM : basic('#F7CFBB');
    const wall = (w, x, z, ry) => {
      const g = new THREE.Group();
      const m = mesh(new THREE.BoxGeometry(w, RH, 0.4), Math.abs(Math.sin(ry)) > 0.5 ? wallM2 : wallM); m.position.y = RH / 2; g.add(m);
      const skirt = mesh(new THREE.BoxGeometry(w, 0.5, 0.5), trimM); skirt.position.y = 0.25; g.add(skirt);
      for (let i = 0; i < Math.floor(w / 6); i++) {
        const wx = -w / 2 + 3 + i * 6;
        const fr = mesh(new THREE.BoxGeometry(3.6, 4.2, 0.5), trimM); fr.position.set(wx, 4.6, 0.05); g.add(fr);
        const pane = mesh(new THREE.PlaneGeometry(3.1, 3.7), paneM); pane.position.set(wx, 4.6, 0.32); g.add(pane);
        const bar = mesh(new THREE.BoxGeometry(0.14, 3.7, 0.1), trimM); bar.position.set(wx, 4.6, 0.34); g.add(bar);
        if (PS2) { const glow = mesh(new THREE.PlaneGeometry(3.4, 6), new THREE.MeshBasicMaterial({ color: '#FF9A4A', transparent: true, opacity: 0.16, depthWrite: false, fog: false })); glow.rotation.x = -Math.PI / 2; glow.position.set(wx, 0.03, 3.4); g.add(glow); }
      }
      g.position.set(x, 0, z); g.rotation.y = ry; sceneryG.add(g);
    };
    wall(RW, 0, -RD / 2, 0); wall(RD, -RW / 2, 0, Math.PI / 2); wall(RW, 0, RD / 2, Math.PI); wall(RD, RW / 2, 0, -Math.PI / 2);
    for (let i = 0; i < 7; i++) {
      const x = i < 4 ? -RW / 2 + 2 + i * (RW - 4) / 3.5 : -RW / 2 + 1.6, z = i < 4 ? -RD / 2 + 1.5 : -RD / 2 + 4 + (i - 4) * 5;
      if (!clear(x, z, 3)) continue;
      const pl = new THREE.Group();
      const pot = mesh(G.cyl(0.5, 0.8), mat(PS2 ? '#7A4A30' : '#FFB8A0')); pot.position.y = 0.4; pl.add(pot);
      const leaf = mesh(PS2 ? G.cone(0.9, 2.2) : new THREE.SphereGeometry(0.85, 20, 14), mat(PS2 ? '#2F5A34' : '#8FD6B8')); leaf.position.y = PS2 ? 1.9 : 1.5; leaf.scale.y = PS2 ? 1 : 1.35; pl.add(leaf);
      if (!PS2) pl.add(blob(2, 2, 0.7));
      pl.position.set(x, 0, z); sceneryG.add(pl);
    }
    scene.fog = PS2 ? new THREE.Fog(0xB0606A, 22, 90) : new THREE.Fog(0xFFEADB, 30, 110);
  } else if (kind === 'open') {
    // nothing on the ground: just the sky (use world.ground for sea, sand, snow...)
    if (PS2) { const sun = mesh(new THREE.CircleGeometry(9, 10), basic('#FFE08A', { fog: false })); sun.position.set(-14, 9, -120); sceneryG.add(sun); }
    else for (let i = 0; i < 9; i++) { const cl = new THREE.Group(); for (const [dx, dy, r] of [[0, 0, 1.6], [1.8, -0.2, 1.3], [-1.7, -0.3, 1.2], [0.7, 0.7, 1.2]]) { const sp = mesh(new THREE.SphereGeometry(r, 20, 14), basic('#FFFFFF', { fog: false })); sp.position.set(dx, dy, 0); cl.add(sp); } cl.position.set(-50 + r0() * 100, 13 + r0() * 11, -75 + r0() * 30 + (i > 5 ? 130 : 0)); cl.scale.setScalar(1.3 + r0()); sceneryG.add(cl); }
  } else if (kind !== 'none') {
    if (PS2) {
      const sun = mesh(new THREE.CircleGeometry(9, 10), basic('#FFE08A', { fog: false })); sun.position.set(-14, 9, -120); sceneryG.add(sun);
      const winTex = canvasTex(16, 16, (g) => { g.fillStyle = '#2E2238'; g.fillRect(0, 0, 16, 16); const r = rng(9); for (let y = 1; y < 16; y += 4) for (let x = 1; x < 16; x += 4) { g.fillStyle = r() > 0.35 ? '#FFC45A' : '#4A3550'; g.fillRect(x, y, 2, 2); } }, true);
      for (let i = 0; i < 18; i++) {
        const w = 5 + r0() * 6, h = 6 + r0() * 16, side = i % 2 ? 1 : -1, x = side * (16 + r0() * 34), z = -34 - r0() * 40 + (i > 12 ? 90 : 0);
        const t = winTex.clone(); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(Math.round(w / 3), Math.round(h / 3)); t.needsUpdate = true;
        const b = mesh(new THREE.BoxGeometry(w, h, 5), new THREE.MeshBasicMaterial({ map: t })); b.position.set(x, h / 2, z); if (clear(x, z, 10)) sceneryG.add(b);
      }
    } else {
      for (let i = 0; i < 9; i++) { const h = mesh(new THREE.SphereGeometry(1, 32, 20), mat(i % 2 ? '#A9E0C8' : '#9AD8BE', 'matte')); const side = i % 2 ? 1 : -1; h.scale.set(16 + r0() * 14, 4 + r0() * 5, 12 + r0() * 10); h.position.set(side * (30 + r0() * 30), -0.6, -60 + r0() * 110); sceneryG.add(h); }
      for (let i = 0; i < 7; i++) { const cl = new THREE.Group(); for (const [dx, dy, r] of [[0, 0, 1.6], [1.8, -0.2, 1.3], [-1.7, -0.3, 1.2], [0.7, 0.7, 1.2]]) { const s = mesh(new THREE.SphereGeometry(r, 20, 14), basic('#FFFFFF', { fog: false })); s.position.set(dx, dy, 0); cl.add(s); } cl.position.set(-40 + r0() * 80, 15 + r0() * 9, -70 + r0() * 30 + (i > 4 ? 120 : 0)); cl.scale.setScalar(1.3 + r0()); sceneryG.add(cl); }
    }
    for (let i = 0; i < 44; i++) {
      const side = i % 2 ? 1 : -1, x = side * (5 + r0() * 26), z = -42 + r0() * 86, sc = 0.8 + r0() * 0.75, tr = new THREE.Group();
      if (PS2) { const trunk = mesh(G.cyl(0.18, 1.2), mat('#4A3426')); trunk.position.y = 0.6; tr.add(trunk); const top = mesh(G.cone(1.1, 2.8), mat('#2F5A34')); top.position.y = 2.5; tr.add(top); }
      else { const trunk = mesh(G.cyl(0.16, 1.5), mat('#E5BFA6', 'clay')); trunk.position.y = 0.75; tr.add(trunk); const top = mesh(new THREE.SphereGeometry(1.05, 24, 18), mat(['#9EDBC2', '#FFC9B3', '#B6E6D2'][i % 3])); top.position.y = 2.2; tr.add(top); tr.add(blob(3, 3, 0.8)); }
      tr.position.set(x, 0, z); tr.scale.setScalar(sc);
      if (clear(x, z, 6.5)) sceneryG.add(tr);
    }
  }
}
function setFocus(names) {
  const on = new Set(expand(names));
  for (const b of Object.values(OBJ)) b.root.traverse(c => c.layers.set(on.has(b.id) ? 1 : 0));
}

// ---------------------------------------------------------------- overlays (HTML on top of the canvas)
$('title').textContent = SPEC.title || '';
$('hook').textContent = SPEC.hook_text || '';
const tmp = new THREE.Vector3();
const TEMPLATES = {
  label: o => `<div class="ui pill" style="font-size:26px;${o.color === 'yellow' ? 'background:#FFD23F' : ''}">${o.text}</div>`,
  number: o => `<div class="ui num">${o.text}</div>`,
  pill: o => `<div class="ui pill" style="font-size:44px;padding:16px 34px 14px">${o.text}</div>`,
  question: o => `<div class="ui q">?</div>`,
  check: o => `<svg class="badge" viewBox="0 0 230 230"><circle cx="115" cy="115" r="104" fill="#fff" stroke="#1D2742" stroke-width="8"/><path d="M62 120 L100 158 L170 78" fill="none" stroke="#2DBE6C" stroke-width="24" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg>`,
  cross: o => `<svg class="badge" viewBox="0 0 230 230"><circle cx="115" cy="115" r="104" fill="#fff" stroke="#1D2742" stroke-width="8"/><path d="M72 72 L158 158" fill="none" stroke="#E63946" stroke-width="24" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/><path d="M158 72 L72 158" fill="none" stroke="#E63946" stroke-width="24" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg>`,
  xmark: o => `<svg class="badge" viewBox="0 0 230 230" style="width:200px;height:200px"><path d="M50 50 L180 180" fill="none" stroke="#1D2742" stroke-width="40" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/><path d="M180 50 L50 180" fill="none" stroke="#1D2742" stroke-width="40" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/><path d="M50 50 L180 180" fill="none" stroke="#E63946" stroke-width="24" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/><path d="M180 50 L50 180" fill="none" stroke="#E63946" stroke-width="24" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg>`,
  stop: o => `<svg class="badge" viewBox="0 0 230 230" style="width:190px;height:190px"><polygon points="72,12 158,12 218,72 218,158 158,218 72,218 12,158 12,72" fill="#E63946" stroke="#1D2742" stroke-width="9" stroke-linejoin="round"/><text x="115" y="136" text-anchor="middle" font-family="InterB" font-size="60" fill="#fff">${o.text || 'STOP'}</text></svg>`,
};
const ICONS = {
  heart: '<path d="M115 178 C60 132 42 104 42 80 C42 56 60 42 80 42 C96 42 108 50 115 62 C122 50 134 42 150 42 C170 42 188 56 188 80 C188 104 170 132 115 178 Z" fill="#E63946"/>',
  star: '<polygon points="115,34 137,88 195,92 150,130 164,187 115,156 66,187 80,130 35,92 93,88" fill="#FFC53D" stroke="#1D2742" stroke-width="6" stroke-linejoin="round"/>',
  bolt: '<polygon points="128,30 62,128 108,128 96,200 168,98 122,98" fill="#FFC53D" stroke="#1D2742" stroke-width="6" stroke-linejoin="round"/>',
  coin: '<circle cx="115" cy="115" r="62" fill="#FFC53D" stroke="#1D2742" stroke-width="7"/><text x="115" y="142" text-anchor="middle" font-family="InterB" font-size="80" fill="#1D2742">$</text>',
  clock: '<circle cx="115" cy="115" r="64" fill="#fff" stroke="#1D2742" stroke-width="9"/><path d="M115 72 V115 L146 134" fill="none" stroke="#1D2742" stroke-width="10" stroke-linecap="round"/>',
  eye: '<path d="M32 115 C62 68 168 68 198 115 C168 162 62 162 32 115 Z" fill="#fff" stroke="#1D2742" stroke-width="8"/><circle cx="115" cy="115" r="26" fill="#1D2742"/>',
  lock: '<rect x="62" y="104" width="106" height="84" rx="14" fill="#FFC53D" stroke="#1D2742" stroke-width="8"/><path d="M82 104 V82 C82 40 148 40 148 82 V104" fill="none" stroke="#1D2742" stroke-width="12"/>',
  crown: '<polygon points="46,170 38,74 82,116 115,56 148,116 192,74 184,170" fill="#FFC53D" stroke="#1D2742" stroke-width="7" stroke-linejoin="round"/>',
  skull: '<path d="M115 40 C68 40 46 74 46 108 C46 134 60 148 74 154 V184 H156 V154 C170 148 184 134 184 108 C184 74 162 40 115 40 Z" fill="#fff" stroke="#1D2742" stroke-width="8"/><circle cx="90" cy="112" r="15" fill="#1D2742"/><circle cx="140" cy="112" r="15" fill="#1D2742"/>',
  mountain: '<polygon points="30,180 96,62 132,122 152,96 200,180" fill="#7DDBC8" stroke="#1D2742" stroke-width="7" stroke-linejoin="round"/>',
  brain: '<path d="M112 52 C84 40 56 60 60 88 C40 100 42 132 62 142 C64 170 96 182 112 164 Z" fill="#F7A1C8" stroke="#1D2742" stroke-width="7" stroke-linejoin="round"/><path d="M118 52 C146 40 174 60 170 88 C190 100 188 132 168 142 C166 170 134 182 118 164 Z" fill="#F7A1C8" stroke="#1D2742" stroke-width="7" stroke-linejoin="round"/>',
  zzz: '<text x="115" y="150" text-anchor="middle" font-family="InterB" font-size="96" fill="#8EC5FF" stroke="#1D2742" stroke-width="5">Zz</text>',
};
TEMPLATES.icon = o => `<svg class="badge" viewBox="0 0 230 230" style="width:${o.size || 190}px;height:${o.size || 190}px"><circle cx="115" cy="115" r="106" fill="#fff" stroke="#1D2742" stroke-width="8"/>${ICONS[o.icon] || (warn.push('unknown icon ' + o.icon), '')}</svg>`;
const OVER = (SPEC.overlays || []).map(o => {
  if (!TEMPLATES[o.type]) warn.push('unknown overlay type ' + o.type);
  const holder = document.createElement('div'); holder.innerHTML = (TEMPLATES[o.type] || TEMPLATES.label)(o);
  const el = holder.firstElementChild; el.style.position = 'absolute'; el.style.display = 'none'; $('overlays').appendChild(el);
  return { ...o, el, paths: [...el.querySelectorAll('path[pathLength]')] };
});
function drawOverlays(t) {
  for (const o of OVER) {
    const from = o.from ?? o.at, to = o.to ?? 1e9, on = t >= from && t < to;
    let x, y, ok = on;
    if (on && o.on !== undefined) {
      const b = typeof o.on === 'string' ? OBJ[o.on] : null;
      if (b) tmp.copy(b.root.position).setY(b.root.position.y + (o.up ?? b.up ?? 2.4)); else tmp.set(...o.on);
      tmp.project(camera); ok = tmp.z < 1 && (!b || b.root.visible);
      x = (tmp.x * 0.5 + 0.5) * W; y = (-tmp.y * 0.5 + 0.5) * H;
    } else if (on) { [x, y] = o.pos || (o.type === 'pill' ? [540, 1330] : o.type === 'question' ? [800, 580] : [540, 470]); }
    o.el.style.display = ok ? 'block' : 'none';
    if (!ok) continue;
    const k = easeOut((t - from) / 0.28);
    let sc = o.type === 'label' ? 1 : 0.75 + 0.25 * k;
    if (o.type === 'question') y -= 14 * Math.sin(t * 4.5);
    if (o.type === 'stop') sc = k;
    o.el.style.left = x + 'px'; o.el.style.top = y + 'px'; o.el.style.transform = `translate(-50%, -50%) scale(${sc})`;
    if (o.type === 'pill') o.el.style.opacity = clamp((t - from) / 0.3);
    const d = (t - from) / (o.draw || 0.35);
    if (o.type === 'check') o.paths[0].setAttribute('stroke-dashoffset', 1 - clamp(d));
    if (o.type === 'cross') { o.paths[0].setAttribute('stroke-dashoffset', 1 - clamp(d * 2)); o.paths[1].setAttribute('stroke-dashoffset', 1 - clamp(d * 2 - 1)); }
    if (o.type === 'xmark') { [0, 2].forEach(i => o.paths[i].setAttribute('stroke-dashoffset', 1 - clamp(d * 2))); [1, 3].forEach(i => o.paths[i].setAttribute('stroke-dashoffset', 1 - clamp(d * 2 - 1))); }
  }
}
function caption(t) {
  let html = '';
  for (const s of TL.sentences) {
    if (!(s.start <= t && t < s.end_scene)) continue;
    for (let i = 0; i < s.chunks.length; i++) {
      const ch = s.chunks[i], c0 = ch[0][1], c1 = i + 1 < s.chunks.length ? s.chunks[i + 1][0][1] : s.end + 0.3;
      if (c0 - 0.04 <= t && t < c1 - 0.04) { const a = easeOut((t - c0 + 0.04) / 0.14); html = ch.map(w => `<span style="opacity:${((w[1] - 0.04 <= t) ? 1 : 0.72) * a}">${w[0]}</span>`).join(''); }
    }
  }
  $('caption').innerHTML = html;
}

// ---------------------------------------------------------------- one frame
function frame(t) {
  applyAll(t);
  let si = 0; for (let i = 0; i < SHOTS.length; i++) if (t >= SHOTS[i].at) si = i;
  const sh = SHOTS[si], end = si + 1 < SHOTS.length ? SHOTS[si + 1].at : TL.total;
  let k = camOf(sh, clamp((t - sh.at) / Math.max(0.01, end - sh.at)));
  const g = sh.cut ? 0 : (sh.glide ?? 0.7);
  if (si > 0 && g > 0 && t - sh.at < g) {      // glide from where the last shot ended instead of a hard cut, when the angle change is small
    const kp = camOf(SHOTS[si - 1], 1), k0 = camOf(sh, 0);
    const yaw = q => Math.atan2(q.pos.x - q.look.x, q.pos.z - q.look.z);
    let d = yaw(k0) - yaw(kp); d = Math.atan2(Math.sin(d), Math.cos(d));
    if (Math.abs(d) < rad(75) && kp.look.distanceTo(k0.look) < 9) k = blendCam(kp, k, ease((t - sh.at) / g));
  }
  setCam(k);
  const hu = SPEC.hook_until || 0;
  $('hook').style.opacity = SPEC.hook_text ? (t < hu - 0.35 ? 1 : clamp((hu - t) / 0.35)) : 0;
  setFocus(sh.focus || 'all');
  drawOverlays(t); caption(t);
  if (PS2) { camera.layers.enableAll(); fgR.render(scene, camera); }
  else {
    sceneryG.traverse(c => c.layers.set(0));
    $('bg').style.filter = `blur(${sh.blur ?? (sh.focus && sh.focus !== 'all' ? 10 : 3)}px)`;
    scene.environment = envBg; scene.background = skyTex; camera.layers.set(0); bgR.render(scene, camera);
    scene.environment = envFg; scene.background = null; camera.layers.set(1); fgR.render(scene, camera);
  }
}
// which focused objects are off-screen at the middle of each shot? (reported to the build log)
window.audit = () => {
  const out = [...warn], seenPairs = new Set();
  SHOTS.forEach((sh, i) => {
    const end = i + 1 < SHOTS.length ? SHOTS[i + 1].at : TL.total, t = (sh.at + end) / 2;
    applyAll(t); setCam(camOf(sh, 0.5));
    if (sh.focus && sh.focus !== 'all') for (const id of expand(sh.focus)) {
      const b = OBJ[id]; if (!b || !b.root.visible || b.kind === 'track' || b.kind === 'bridge' || b.kind === 'arrows') continue;
      tmp.copy(b.root.position).setY(b.root.position.y + (b.person ? 1.5 : 0.8)).project(camera);
      if (tmp.z > 1 || Math.abs(tmp.x) > 1.02 || Math.abs(tmp.y) > 1.02) out.push(`shot ${i} (t=${sh.at.toFixed(1)}): "${id}" is out of frame`);
    }
    scene.updateMatrixWorld(true);
    const subj = sh.focus && sh.focus !== 'all' ? sh.focus : (sh.cam.on || []);
    const blocker = hiddenBy(camera.position, subj, [sceneryG], false);
    if (blocker) out.push(`shot ${i} (t=${sh.at.toFixed(1)}): the view of the subject is blocked by ${blocker}`);
    const vis = Object.values(OBJ).filter(b => b.root.visible && b.rad && !b.ghost);
    for (let a = 0; a < vis.length; a++) for (let b2 = a + 1; b2 < vis.length; b2++) {
      const A = vis[a].root.position, B = vis[b2].root.position;
      if (Math.abs(A.y - B.y) < 0.5 && Math.hypot(A.x - B.x, A.z - B.z) < (vis[a].rad + vis[b2].rad) * 0.55 && !seenPairs.has(vis[a].id + vis[b2].id)) { seenPairs.add(vis[a].id + vis[b2].id); out.push(`t=${t.toFixed(1)}: "${vis[a].id}" and "${vis[b2].id}" overlap - move them apart`); }
    }
    if (!inWorld(camera.position)) out.push(`shot ${i} (t=${sh.at.toFixed(1)}): the camera is outside the room`);
  });
  return out;
};
await document.fonts.load('700 80px Playfair'); await document.fonts.load('700 28px InterB'); await document.fonts.ready;
window.renderAt = async (t) => { frame(t); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); return true; };
frame(0);
window.ready = true;
