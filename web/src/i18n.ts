import type { I18nText, Lang } from './types';

const STRINGS = {
  loading: { pt: 'Carregando o apartamento…', en: 'Loading the apartment…', es: 'Cargando el apartamento…' },
  title: { pt: 'Apartamento frente mar', en: 'Beachfront apartment', es: 'Departamento frente al mar' },
  subtitle: { pt: 'Balneário Camboriú · tour 3D', en: 'Balneário Camboriú · 3D tour', es: 'Balneário Camboriú · tour 3D' },
  book: { pt: 'Reservar', en: 'Book', es: 'Reservar' },
  dollhouse: { pt: 'Casa de bonecas', en: 'Dollhouse', es: 'Maqueta' },
  walk: { pt: 'Caminhar', en: 'Walk', es: 'Caminar' },
  hintDollhouse: {
    pt: 'Gire com o dedo · toque em um cômodo para entrar',
    en: 'Drag to rotate · tap a room to step inside',
    es: 'Arrastre para girar · toque una habitación para entrar',
  },
  hintWalkTouch: {
    pt: 'Arraste para olhar · toque no chão para andar',
    en: 'Drag to look around · tap the floor to move',
    es: 'Arrastre para mirar · toque el piso para moverse',
  },
  hintWalkDesktop: {
    pt: 'Arraste para olhar · clique no chão ou use W A S D',
    en: 'Drag to look around · click the floor or use W A S D',
    es: 'Arrastre para mirar · haga clic en el piso o use W A S D',
  },
  disclaimer: {
    pt: 'Modelo ilustrativo criado a partir das fotos do anúncio.',
    en: 'Illustrative model based on the listing photos.',
    es: 'Modelo ilustrativo creado a partir de las fotos del anuncio.',
  },
} satisfies Record<string, I18nText>;

export type StringKey = keyof typeof STRINGS;

function detect(): Lang {
  const saved = safeGet('lang');
  if (saved === 'pt' || saved === 'en' || saved === 'es') return saved;
  const nav = (navigator.language || 'pt').slice(0, 2);
  return nav === 'en' ? 'en' : nav === 'es' ? 'es' : 'pt';
}

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

let lang: Lang = detect();
const listeners: Array<() => void> = [];

export const i18n = {
  get lang(): Lang {
    return lang;
  },
  set(l: Lang) {
    lang = l;
    try {
      localStorage.setItem('lang', l);
    } catch {
      /* navegação privada: ignora */
    }
    document.documentElement.lang = l === 'pt' ? 'pt-BR' : l;
    listeners.forEach((fn) => fn());
  },
  t(key: StringKey): string {
    return STRINGS[key][lang];
  },
  pick(text: I18nText): string {
    return text[lang] ?? text.pt;
  },
  onChange(fn: () => void) {
    listeners.push(fn);
  },
};
