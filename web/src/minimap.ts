import { i18n } from './i18n';
import type { Room, SceneData, Vec2 } from './types';

const SVG = 'http://www.w3.org/2000/svg';

/** Planta 2D com a posição e a direção do visitante. O mar fica embaixo. */
export class Minimap {
  private me: SVGCircleElement;
  private cone: SVGPathElement;
  private rooms = new Map<string, SVGPolygonElement>();
  private texts = new Map<string, SVGTextElement>();
  private active: string | null = null;

  constructor(host: HTMLElement, private data: SceneData, onRoom: (r: Room) => void) {
    const [x0, y0, x1, y1] = data.bounds;
    const pad = 0.4;
    const svg = document.createElementNS(SVG, 'svg');
    svg.setAttribute('viewBox', `${x0 - pad} ${-y1 - pad} ${x1 - x0 + pad * 2} ${y1 - y0 + pad * 2 + 0.8}`);
    const sea = document.createElementNS(SVG, 'rect');
    sea.setAttribute('class', 'sea');
    sea.setAttribute('x', String(x0 - pad));
    sea.setAttribute('y', String(-y0 + 0.15));
    sea.setAttribute('width', String(x1 - x0 + pad * 2));
    sea.setAttribute('height', '1');
    svg.appendChild(sea);
    for (const r of data.rooms) {
      const poly = document.createElementNS(SVG, 'polygon');
      poly.setAttribute('points', r.polygon.map(([x, y]) => `${x},${-y}`).join(' '));
      poly.setAttribute('class', 'room');
      poly.addEventListener('click', () => onRoom(r));
      svg.appendChild(poly);
      this.rooms.set(r.id, poly);
      const xs = r.polygon.map((p) => p[0]);
      const ys = r.polygon.map((p) => p[1]);
      const t = document.createElementNS(SVG, 'text');
      t.setAttribute('x', String((Math.min(...xs) + Math.max(...xs)) / 2));
      t.setAttribute('y', String(-(Math.min(...ys) + Math.max(...ys)) / 2 + 0.15));
      svg.appendChild(t);
      this.texts.set(r.id, t);
    }
    this.cone = document.createElementNS(SVG, 'path');
    this.cone.setAttribute('class', 'cone');
    this.me = document.createElementNS(SVG, 'circle');
    this.me.setAttribute('class', 'me');
    this.me.setAttribute('r', '0.22');
    svg.append(this.cone, this.me);
    host.appendChild(svg);
  }

  setLabels() {
    for (const r of this.data.rooms) {
      const name = i18n.pick(r.name);
      this.texts.get(r.id)!.textContent = name.length > 14 ? name.split(' ')[0] : name;
    }
  }

  update(pos: Vec2 | null, yaw: number, roomId: string | null) {
    if (roomId !== this.active) {
      if (this.active) this.rooms.get(this.active)?.classList.remove('active');
      if (roomId) this.rooms.get(roomId)?.classList.add('active');
      this.active = roomId;
    }
    if (!pos) {
      this.me.style.display = this.cone.style.display = 'none';
      return;
    }
    this.me.style.display = this.cone.style.display = '';
    const [x, y] = pos;
    this.me.setAttribute('cx', String(x));
    this.me.setAttribute('cy', String(-y));
    const r = 1.6;
    const a0 = yaw - 0.55;
    const a1 = yaw + 0.55;
    // direção na planta: (-sin yaw, cos yaw); no SVG o y é invertido
    const p = (a: number) => `${x - Math.sin(a) * r},${-(y + Math.cos(a) * r)}`;
    this.cone.setAttribute('d', `M${x},${-y} L${p(a0)} A${r},${r} 0 0 0 ${p(a1)} Z`);
  }
}
