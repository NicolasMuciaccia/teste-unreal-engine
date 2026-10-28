import type { Collider, Vec2 } from './types';

/** Colisão 2D (planta): círculo do visitante contra paredes (segmentos) e móveis (polígonos). */
export class Collision {
  constructor(private colliders: Collider[], private radius = 0.22) {}

  resolve(p: Vec2): Vec2 {
    let [x, y] = p;
    for (let iter = 0; iter < 4; iter++) {
      let moved = false;
      for (const c of this.colliders) {
        if (c.kind === 'seg') {
          const r = pushFromSegment(x, y, c.a, c.b, this.radius);
          if (r) {
            [x, y] = r;
            moved = true;
          }
        } else {
          const r = pushFromPolygon(x, y, c.pts, this.radius);
          if (r) {
            [x, y] = r;
            moved = true;
          }
        }
      }
      if (!moved) break;
    }
    return [x, y];
  }
}

function closestOnSegment(x: number, y: number, a: Vec2, b: Vec2): Vec2 {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len2 = dx * dx + dy * dy || 1e-9;
  const t = Math.max(0, Math.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / len2));
  return [a[0] + t * dx, a[1] + t * dy];
}

function pushFromSegment(x: number, y: number, a: Vec2, b: Vec2, r: number): Vec2 | null {
  const [cx, cy] = closestOnSegment(x, y, a, b);
  const dx = x - cx;
  const dy = y - cy;
  const d = Math.hypot(dx, dy);
  if (d >= r) return null;
  if (d < 1e-6) {
    // exatamente sobre a parede: empurra pela normal
    const nx = -(b[1] - a[1]);
    const ny = b[0] - a[0];
    const n = Math.hypot(nx, ny) || 1;
    return [x + (nx / n) * r, y + (ny / n) * r];
  }
  return [cx + (dx / d) * r, cy + (dy / d) * r];
}

export function pointInPolygon(x: number, y: number, pts: Vec2[]): boolean {
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i];
    const [xj, yj] = pts[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function pushFromPolygon(x: number, y: number, pts: Vec2[], r: number): Vec2 | null {
  let best: Vec2 | null = null;
  let bestD = Infinity;
  for (let i = 0; i < pts.length; i++) {
    const c = closestOnSegment(x, y, pts[i], pts[(i + 1) % pts.length]);
    const d = Math.hypot(x - c[0], y - c[1]);
    if (d < bestD) {
      bestD = d;
      best = c;
    }
  }
  if (!best) return null;
  const inside = pointInPolygon(x, y, pts);
  if (!inside && bestD >= r) return null;
  let dx = x - best[0];
  let dy = y - best[1];
  const d = Math.hypot(dx, dy) || 1e-6;
  if (inside) {
    dx = -dx;
    dy = -dy;
  }
  return [best[0] + (dx / d) * r, best[1] + (dy / d) * r];
}
