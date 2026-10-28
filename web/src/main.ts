import './style.css';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { Reflector } from 'three/addons/objects/Reflector.js';
import { Collision, pointInPolygon } from './collision';
import { createEnvironment, createOwnTower } from './environment';
import { i18n } from './i18n';
import { Minimap } from './minimap';
import type { Hotspot, Lang, Room, SceneData, Vec2 } from './types';

const BASE = import.meta.env.BASE_URL;
const EYE = 1.6;
const params = new URLSearchParams(location.search);
const isTouch = matchMedia('(pointer: coarse)').matches;
document.body.classList.toggle('touch', isTouch);

// ----------------------------------------------------------------- coordenadas
// planta (x, y, z-altura) -> three (x, z, -y)
const toWorld = (x: number, y: number, z = 0) => new THREE.Vector3(x, z, -y);
const toPlan = (v: THREE.Vector3): Vec2 => [v.x, -v.z];

// ----------------------------------------------------------------- renderer
const canvas = document.getElementById('c') as HTMLCanvasElement;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, isTouch ? 1.5 : 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
const scene = new THREE.Scene();
scene.fog = new THREE.Fog('#cfe2ee', 120, 1400);
const camera = new THREE.PerspectiveCamera(70, 1, 0.05, 4000);
camera.rotation.order = 'YXZ';

function resize() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.fov = w < h ? 80 : 68;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

// ----------------------------------------------------------------- estado
type Mode = 'dollhouse' | 'walk';
let mode: Mode = 'dollhouse';
let data: SceneData;
let collision: Collision;
let minimap: Minimap;
const floors: THREE.Mesh[] = [];
const ceilings: THREE.Object3D[] = [];
const solids: THREE.Mesh[] = [];
const mirrors: THREE.Mesh[] = [];
let exterior: THREE.Group;
let tower: THREE.Group;
let dollTarget = new THREE.Vector3();

const walk = { pos: [0, 0] as Vec2, yaw: 0, pitch: -0.05 };
const keys = new Set<string>();
const joy = { x: 0, y: 0 };

interface Flight {
  t: number;
  dur: number;
  fromPos: THREE.Vector3;
  fromQuat: THREE.Quaternion;
  toPos: THREE.Vector3;
  toQuat: THREE.Quaternion;
  done: () => void;
}
let flight: Flight | null = null;
let ready = false;

const orbit = new OrbitControls(camera, canvas);
orbit.enableDamping = true;
orbit.dampingFactor = 0.08;
orbit.minDistance = 5;
orbit.maxDistance = 32;
orbit.minPolarAngle = 0.15;
orbit.maxPolarAngle = 1.2;
orbit.enablePan = false;
orbit.rotateSpeed = 0.6;

// ----------------------------------------------------------------- carregamento
const loadingEl = document.getElementById('loading')!;
loadingEl.style.backgroundImage = `linear-gradient(180deg, rgba(10,30,45,.55), rgba(10,20,30,.9)), url(${BASE}fotos/capa.jpg)`;
const barFill = document.getElementById('bar-fill')!;
const pct = document.getElementById('pct')!;

async function load() {
  data = await (await fetch(`${BASE}scene.json`)).json();
  collision = new Collision(data.colliders);
  renderer.toneMappingExposure = Number(params.get('exp') ?? data.exposure ?? 0.5);

  const manager = new THREE.LoadingManager();
  const loader = new GLTFLoader(manager).setMeshoptDecoder(MeshoptDecoder);
  const gltf = await loader.loadAsync(`${BASE}models/apartamento.glb`, (e) => {
    const p = e.total ? e.loaded / e.total : 0;
    barFill.style.width = `${Math.round(p * 100)}%`;
    pct.textContent = `${Math.round(p * 100)}%`;
  });

  const lmScale = (data.lightmap?.scale ?? 1) * Math.PI * Number(params.get('lm') ?? 1);
  gltf.scene.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    const name = (mesh.parent && mesh.parent.type === 'Group' && mesh.parent !== gltf.scene ? mesh.parent.name : mesh.name) || '';
    const mat = mesh.material as THREE.MeshStandardMaterial;
    const glass = name.startsWith('vidro') || mat.transparent || mat.name.startsWith('vidro');
    if (mat.aoMap) {
      if (!glass) {
        const lm = mat.aoMap;
        lm.colorSpace = THREE.SRGBColorSpace;
        lm.channel = 1;
        mat.lightMap = lm;
        mat.lightMapIntensity = lmScale;
      }
      mat.aoMap = null;
    }
    if (glass) {
      mat.transparent = true;
      mat.opacity = Math.min(mat.opacity, 0.18);
      mat.depthWrite = false;
      mat.envMapIntensity = 1.0;
      mesh.renderOrder = 2;
    } else if (mat.metalness > 0.5) {
      mat.envMapIntensity = 1.0;
    } else {
      // reflexos discretos (piso polido, laca); a luz difusa vem do lightmap
      mat.envMapIntensity = mat.roughness < 0.3 ? 0.35 : 0.08;
    }
    mat.needsUpdate = true;
    if (mat.name.startsWith('espelho')) mirrors.push(mesh);
    if (name.startsWith('piso_')) floors.push(mesh);
    if (name.startsWith('teto_')) {
      ceilings.push(mesh);
      // o bake só tem luz rebatida no teto (as luzes de área apontam para baixo); compensa os spots embutidos
      if (!mat.userData.boosted) {
        mat.userData.boosted = true;
        mat.lightMapIntensity *= 1.8;
        mat.emissive.set('#f1eee8');
        mat.emissiveIntensity = 0.32;
      }
    }
    if (!glass) solids.push(mesh);
  });
  scene.add(gltf.scene);
  gltf.scene.updateMatrixWorld(true);
  mirrors.forEach(makeMirror);

  const [x0, y0, x1, y1] = data.bounds;
  exterior = createEnvironment(data.meta.andar_altura, (x0 + x1) / 2);
  tower = createOwnTower(data.bounds, data.meta.andar_altura, data.meta.pe_direito);
  scene.add(exterior, tower);
  dollTarget = toWorld((x0 + x1) / 2, (y0 + y1) / 2, 0);

  captureReflections();
  buildUI();

  const start = data.rooms.find((r) => r.id === (params.get('room') ?? 'sala')) ?? data.rooms[0];
  walk.pos = [...start.view.pos] as Vec2;
  lookAtPlan(start.view.look);
  setMode(params.get('mode') === 'walk' ? 'walk' : 'dollhouse', true);
  ready = true;
  loadingEl.classList.add('done');
}

/** Troca a caixa do espelho por um espelho plano de verdade (reflexo em tempo real). */
function makeMirror(mesh: THREE.Mesh) {
  const box = new THREE.Box3().setFromObject(mesh);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const thinX = size.x < size.z;
  const room = roomAt(toPlan(center));
  let sign = 1;
  if (room) {
    const c = toWorld(...centroid(room.polygon));
    sign = Math.sign(thinX ? c.x - center.x : c.z - center.z) || 1;
  }
  const w = thinX ? size.z : size.x;
  const res = isTouch ? 512 : 1024;
  const mirror = new Reflector(new THREE.PlaneGeometry(w, size.y), {
    textureWidth: res,
    textureHeight: Math.round((res * size.y) / w),
    color: 0xc8cacc,
    clipBias: 0.003,
  });
  const n = thinX ? new THREE.Vector3(sign, 0, 0) : new THREE.Vector3(0, 0, sign);
  mirror.position.copy(center).addScaledVector(n, (thinX ? size.x : size.z) / 2 + 0.003);
  mirror.lookAt(mirror.position.clone().add(n));
  mesh.visible = false;
  scene.add(mirror);
}

/** Reflexos: um cubemap tirado de dentro da sala, com a iluminação já aplicada. */
function captureReflections() {
  const rt = new THREE.WebGLCubeRenderTarget(256, { type: THREE.HalfFloatType });
  const cubeCam = new THREE.CubeCamera(0.05, 2000, rt);
  const sala = data.rooms[0];
  const c = centroid(sala.polygon);
  cubeCam.position.copy(toWorld(c[0], c[1], 1.3));
  scene.add(cubeCam);
  cubeCam.update(renderer, scene);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromCubemap(rt.texture).texture;
  scene.remove(cubeCam);
  pmrem.dispose();
}

// ----------------------------------------------------------------- modos
function setMode(m: Mode, instant = false) {
  const prev = mode;
  mode = m;
  document.body.classList.toggle('walk', m === 'walk');
  document.querySelectorAll<HTMLButtonElement>('.mode').forEach((b) => b.classList.toggle('active', b.dataset.mode === m));
  updateHint();
  if (m === 'dollhouse') {
    setInside(false);
    orbit.enabled = true;
    const pose = dollPose(prev === 'walk' ? walk.pos : null);
    if (instant) {
      camera.position.copy(pose.pos);
      orbit.target.copy(dollTarget);
      camera.lookAt(dollTarget);
      orbit.update();
    } else {
      fly(pose.pos, quatLooking(pose.pos, dollTarget), 1.1, () => {
        orbit.target.copy(dollTarget);
        orbit.update();
      });
    }
  } else {
    orbit.enabled = false;
    const pos = toWorld(walk.pos[0], walk.pos[1], EYE);
    const quat = walkQuat();
    if (instant) {
      camera.position.copy(pos);
      camera.quaternion.copy(quat);
      setInside(true);
    } else {
      fly(pos, quat, 1.3, () => setInside(true));
    }
  }
}

function setInside(inside: boolean) {
  ceilings.forEach((c) => (c.visible = inside));
  exterior.visible = inside;
  tower.visible = inside;
  scene.background = inside ? null : new THREE.Color('#1b2733');
  scene.fog = inside ? new THREE.Fog('#cfe2ee', 120, 1400) : null;
}

function dollPose(near: Vec2 | null) {
  // câmera alta, olhando o apartamento pelo lado do mar
  const off = new THREE.Vector3(1.5, 11.5, 9.5);
  if (near) {
    const p = toWorld(near[0], near[1], 0);
    const dir = new THREE.Vector3(p.x - dollTarget.x, 0, p.z - dollTarget.z);
    if (dir.length() > 0.5) off.set(dir.x * 1.2, 11.5, Math.max(5, dir.z + 8));
  }
  return { pos: dollTarget.clone().add(off) };
}

function quatLooking(from: THREE.Vector3, to: THREE.Vector3) {
  const m = new THREE.Matrix4().lookAt(from, to, new THREE.Vector3(0, 1, 0));
  return new THREE.Quaternion().setFromRotationMatrix(m);
}

function walkQuat() {
  return new THREE.Quaternion().setFromEuler(new THREE.Euler(walk.pitch, walk.yaw, 0, 'YXZ'));
}

function lookAtPlan(target: Vec2) {
  const dx = target[0] - walk.pos[0];
  const dy = target[1] - walk.pos[1];
  walk.yaw = Math.atan2(-dx, dy);
  walk.pitch = -0.08;
}

function fly(toPos: THREE.Vector3, toQuat: THREE.Quaternion, dur: number, done: () => void = () => {}) {
  flight = { t: 0, dur, fromPos: camera.position.clone(), fromQuat: camera.quaternion.clone(), toPos, toQuat, done };
}

/** Vai até um ponto da planta no modo caminhar (com transição). */
function goTo(pos: Vec2, look?: Vec2) {
  const target = collision.resolve(pos);
  if (mode !== 'walk') {
    walk.pos = target;
    if (look) lookAtPlan(look);
    setMode('walk');
    return;
  }
  walk.pos = target;
  if (look) lookAtPlan(look);
  fly(toWorld(target[0], target[1], EYE), walkQuat(), look ? 1.0 : 0.6);
}

function goToRoom(room: Room) {
  goTo(room.view.pos, room.view.look);
}

// ----------------------------------------------------------------- entrada
const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
let drag: { x: number; y: number; t: number; moved: boolean; id: number } | null = null;

canvas.addEventListener('pointerdown', (e) => {
  drag = { x: e.clientX, y: e.clientY, t: performance.now(), moved: false, id: e.pointerId };
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener('pointermove', (e) => {
  if (!drag || drag.id !== e.pointerId) return;
  const dx = e.clientX - drag.x;
  const dy = e.clientY - drag.y;
  if (Math.abs(dx) + Math.abs(dy) > 6) drag.moved = true;
  if (mode === 'walk' && drag.moved && !flight) {
    const k = isTouch ? 0.005 : 0.004;
    walk.yaw += dx * k;
    walk.pitch = THREE.MathUtils.clamp(walk.pitch + dy * k, -1.2, 1.2);
    drag.x = e.clientX;
    drag.y = e.clientY;
  }
});
canvas.addEventListener('pointerup', (e) => {
  if (!drag || drag.id !== e.pointerId) return;
  const tap = !drag.moved && performance.now() - drag.t < 450;
  drag = null;
  if (tap) onTap(e.clientX, e.clientY);
});

function onTap(x: number, y: number) {
  ndc.set((x / window.innerWidth) * 2 - 1, -(y / window.innerHeight) * 2 + 1);
  raycaster.setFromCamera(ndc, camera);
  const hits = raycaster.intersectObjects(mode === 'walk' ? solids : [...floors, ...solids], false);
  const hit = hits[0];
  if (!hit) return;
  if (mode === 'walk') {
    if (!floors.includes(hit.object as THREE.Mesh)) return;
    const p = toPlan(hit.point);
    const d = Math.hypot(p[0] - walk.pos[0], p[1] - walk.pos[1]);
    if (d < 0.3) return;
    goTo(p);
  } else {
    // no modo casa de bonecas: entrar no cômodo tocado
    const p = toPlan(hit.point);
    const room = roomAt(p);
    if (!room) return;
    const c = centroid(room.polygon);
    const from = room.view.pos;
    // entra pelo ponto tocado, olhando para o centro do cômodo (ou para o ponto de vista padrão)
    const look: Vec2 = Math.hypot(p[0] - c[0], p[1] - c[1]) > 0.8 ? c : room.view.look;
    goTo(Math.hypot(p[0] - c[0], p[1] - c[1]) > 0.8 ? p : from, look);
  }
}

window.addEventListener('keydown', (e) => {
  if ((e.target as HTMLElement).tagName === 'SELECT') return;
  keys.add(e.key.toLowerCase());
  if (mode !== 'walk' && ['w', 'a', 's', 'd', 'arrowup', 'arrowdown'].includes(e.key.toLowerCase())) setMode('walk');
});
window.addEventListener('keyup', (e) => keys.delete(e.key.toLowerCase()));
window.addEventListener('blur', () => keys.clear());

// joystick (celular)
const joyEl = document.getElementById('joystick')!;
const knob = joyEl.querySelector('.knob') as HTMLElement;
joyEl.addEventListener('pointerdown', (e) => {
  joyEl.setPointerCapture(e.pointerId);
  moveJoy(e);
});
joyEl.addEventListener('pointermove', (e) => {
  if (e.buttons || e.pointerType === 'touch') moveJoy(e);
});
const endJoy = () => {
  joy.x = joy.y = 0;
  knob.style.transform = '';
};
joyEl.addEventListener('pointerup', endJoy);
joyEl.addEventListener('pointercancel', endJoy);
function moveJoy(e: PointerEvent) {
  const r = joyEl.getBoundingClientRect();
  let x = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
  let y = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
  const l = Math.hypot(x, y);
  if (l > 1) {
    x /= l;
    y /= l;
  }
  joy.x = x;
  joy.y = y;
  knob.style.transform = `translate(${x * 32}px, ${y * 32}px)`;
}

// ----------------------------------------------------------------- loop
const clock = new THREE.Clock();
let hotspotTick = 0;

renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  if (!ready) return;

  if (flight) {
    flight.t += dt / flight.dur;
    const k = easeInOut(Math.min(flight.t, 1));
    camera.position.lerpVectors(flight.fromPos, flight.toPos, k);
    camera.quaternion.slerpQuaternions(flight.fromQuat, flight.toQuat, k);
    if (flight.t >= 1) {
      const f = flight;
      flight = null;
      f.done();
    }
  } else if (mode === 'walk') {
    updateWalk(dt);
  } else {
    orbit.update();
  }

  if (++hotspotTick % 6 === 0) updateLabels(true);
  else updateLabels(false);
  minimap.update(mode === 'walk' || flight ? walk.pos : null, walk.yaw, currentRoom()?.id ?? null);
  renderer.render(scene, camera);
});

function updateWalk(dt: number) {
  const fwd: Vec2 = [-Math.sin(walk.yaw), Math.cos(walk.yaw)];
  const right: Vec2 = [Math.cos(walk.yaw), Math.sin(walk.yaw)];
  let f = -joy.y;
  let s = joy.x;
  if (keys.has('w') || keys.has('arrowup')) f += 1;
  if (keys.has('s') || keys.has('arrowdown')) f -= 1;
  if (keys.has('d')) s += 1;
  if (keys.has('a')) s -= 1;
  if (keys.has('arrowleft')) walk.yaw += dt * 1.6;
  if (keys.has('arrowright')) walk.yaw -= dt * 1.6;
  const speed = 1.6;
  if (f || s) {
    const l = Math.max(1, Math.hypot(f, s));
    const nx = walk.pos[0] + ((fwd[0] * f + right[0] * s) / l) * speed * dt;
    const ny = walk.pos[1] + ((fwd[1] * f + right[1] * s) / l) * speed * dt;
    walk.pos = collision.resolve([nx, ny]);
  }
  camera.position.copy(toWorld(walk.pos[0], walk.pos[1], EYE));
  camera.quaternion.copy(walkQuat());
}

const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

function centroid(pts: Vec2[]): Vec2 {
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
}

function roomAt(p: Vec2): Room | undefined {
  return data.rooms.find((r) => pointInPolygon(p[0], p[1], r.polygon));
}

let lastRoom: string | null = null;
function currentRoom(): Room | undefined {
  if (mode !== 'walk') return undefined;
  const r = roomAt(walk.pos);
  if ((r?.id ?? null) !== lastRoom) {
    lastRoom = r?.id ?? null;
    document.querySelectorAll<HTMLButtonElement>('.room-chip').forEach((b) => b.classList.toggle('active', b.dataset.room === lastRoom));
  }
  return r;
}

// ----------------------------------------------------------------- UI
const labelsEl = document.getElementById('labels')!;
const roomLabels: Array<{ el: HTMLElement; pos: THREE.Vector3 }> = [];
const hotspotEls: Array<{ el: HTMLElement; pos: THREE.Vector3; h: Hotspot; visible: boolean }> = [];

function buildUI() {
  const langSel = document.getElementById('lang') as HTMLSelectElement;
  langSel.value = i18n.lang;
  langSel.addEventListener('change', () => i18n.set(langSel.value as Lang));
  (document.getElementById('book') as HTMLAnchorElement).href = data.meta.airbnb_url;

  document.querySelectorAll<HTMLButtonElement>('.mode').forEach((b) =>
    b.addEventListener('click', () => {
      const m = b.dataset.mode as Mode;
      if (m === 'walk' && mode !== 'walk') {
        const r = data.rooms[0];
        walk.pos = [...r.view.pos] as Vec2;
        lookAtPlan(r.view.look);
      }
      if (m !== mode) setMode(m);
    }),
  );

  const roomsEl = document.getElementById('rooms')!;
  for (const r of data.rooms) {
    const b = document.createElement('button');
    b.className = 'room-chip';
    b.dataset.room = r.id;
    b.addEventListener('click', () => goToRoom(r));
    roomsEl.appendChild(b);

    const lab = document.createElement('button');
    lab.className = 'label';
    lab.dataset.room = r.id;
    lab.addEventListener('click', () => goToRoom(r));
    labelsEl.appendChild(lab);
    const c = centroid(r.polygon);
    roomLabels.push({ el: lab, pos: toWorld(c[0], c[1], 0.3) });
  }

  for (const h of data.hotspots) {
    const b = document.createElement('button');
    b.className = 'hotspot';
    b.textContent = '+';
    b.style.display = 'none';
    b.addEventListener('click', () => openCard(h));
    labelsEl.appendChild(b);
    hotspotEls.push({ el: b, pos: toWorld(h.pos[0], h.pos[1], h.pos[2]), h, visible: false });
  }

  const card = document.getElementById('card')!;
  card.querySelector('.card-close')!.addEventListener('click', () => card.classList.add('hidden'));

  minimap = new Minimap(document.getElementById('minimap')!, data, (r) => goToRoom(r));
  applyTexts();
  i18n.onChange(applyTexts);
}

function applyTexts() {
  document.querySelectorAll<HTMLElement>('[data-i18n]').forEach((el) => {
    el.textContent = i18n.t(el.dataset.i18n as Parameters<typeof i18n.t>[0]);
  });
  document.querySelectorAll<HTMLElement>('[data-room]').forEach((el) => {
    const r = data.rooms.find((x) => x.id === el.dataset.room);
    if (r) el.textContent = i18n.pick(r.name);
  });
  minimap.setLabels();
  updateHint();
}

let hintTimer = 0;
function updateHint() {
  const el = document.getElementById('hint')!;
  el.textContent = mode === 'walk' ? i18n.t(isTouch ? 'hintWalkTouch' : 'hintWalkDesktop') : i18n.t('hintDollhouse');
  el.classList.remove('fade');
  clearTimeout(hintTimer);
  hintTimer = window.setTimeout(() => el.classList.add('fade'), 6000);
}

function openCard(h: Hotspot) {
  const card = document.getElementById('card')!;
  (document.getElementById('card-img') as HTMLImageElement).src = `${BASE}fotos/${h.photo}`;
  document.getElementById('card-title')!.textContent = i18n.pick(h.title);
  document.getElementById('card-text')!.textContent = i18n.pick(h.text);
  card.classList.remove('hidden');
}

const tmp = new THREE.Vector3();
const occl = new THREE.Raycaster();
function updateLabels(checkOcclusion: boolean) {
  const w = window.innerWidth;
  const h = window.innerHeight;
  const showRooms = mode === 'dollhouse' && !flight;
  for (const l of roomLabels) {
    tmp.copy(l.pos).project(camera);
    const on = showRooms && tmp.z < 1;
    l.el.style.display = on ? '' : 'none';
    if (on) l.el.style.transform = `translate(${(tmp.x * 0.5 + 0.5) * w}px, ${(-tmp.y * 0.5 + 0.5) * h}px) translate(-50%, -50%)`;
  }
  for (const s of hotspotEls) {
    if (mode !== 'walk' || flight) {
      s.el.style.display = 'none';
      continue;
    }
    const dist = camera.position.distanceTo(s.pos);
    if (checkOcclusion) {
      s.visible = false;
      if (dist < 7.5) {
        tmp.copy(s.pos).sub(camera.position).normalize();
        occl.set(camera.position, tmp);
        occl.far = dist;
        const hit = occl.intersectObjects(solids, false)[0];
        s.visible = !hit || hit.distance > dist - 0.6;
      }
    }
    tmp.copy(s.pos).project(camera);
    const on = s.visible && tmp.z < 1 && Math.abs(tmp.x) < 1.1 && Math.abs(tmp.y) < 1.1;
    s.el.style.display = on ? '' : 'none';
    if (on) s.el.style.transform = `translate(${(tmp.x * 0.5 + 0.5) * w}px, ${(-tmp.y * 0.5 + 0.5) * h}px) translate(-50%, -50%)`;
  }
}

load().catch((err) => {
  console.error(err);
  pct.textContent = String(err);
});

// usado nos testes automatizados (Playwright)
Object.assign(window, {
  __tour: {
    setMode: (m: Mode) => setMode(m, true),
    goTo: (x: number, y: number, lx: number, ly: number) => {
      walk.pos = [x, y];
      lookAtPlan([lx, ly]);
      setMode('walk', true);
    },
    ready: () => ready,
  },
});
