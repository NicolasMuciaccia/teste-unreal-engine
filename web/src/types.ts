export type Lang = 'pt' | 'en' | 'es';
export type I18nText = Record<Lang, string>;
export type Vec2 = [number, number];

export interface Room {
  id: string;
  floor: string;
  polygon: Vec2[];
  view: { pos: Vec2; look: Vec2 };
  name: I18nText;
}

export interface Hotspot {
  id: string;
  room: string;
  pos: [number, number, number];
  title: I18nText;
  text: I18nText;
  photo: string;
}

export type Collider =
  | { kind: 'seg'; a: Vec2; b: Vec2 }
  | { kind: 'poly'; id: string; pts: Vec2[] };

export interface SceneData {
  meta: { nome: string; cidade: string; airbnb_url: string; pe_direito: number; andar_altura: number };
  bounds: [number, number, number, number];
  rooms: Room[];
  hotspots: Hotspot[];
  colliders: Collider[];
  lightmap: { scale: number } | null;
  exposure?: number;
}
