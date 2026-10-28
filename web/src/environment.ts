import * as THREE from 'three';

/**
 * Paisagem vista pelas janelas: céu, mar, praia, avenida, morros e prédios
 * de Balneário Camboriú. Tudo sem luz (MeshBasic) para não interferir no
 * interior, que usa a iluminação "assada" no Blender.
 *
 * Coordenadas: o apartamento fica em y = 0 (piso); o chão da cidade em -floorHeight.
 * O mar fica para +z (corresponde a y < 0 na planta).
 */
export function createEnvironment(floorHeight: number, aptCenterX: number): THREE.Group {
  const g = new THREE.Group();
  g.name = 'exterior';
  const ground = -floorHeight;

  // céu: degradê + brilho do sol
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(1800, 32, 16),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      fog: false,
      uniforms: { sunDir: { value: new THREE.Vector3(0.25, 0.45, 0.85).normalize() } },
      vertexShader: `varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: `
        uniform vec3 sunDir; varying vec3 vDir;
        void main(){
          float h = clamp(vDir.y, -0.2, 1.0);
          vec3 horizon = vec3(0.86, 0.92, 0.97);
          vec3 zenith = vec3(0.24, 0.52, 0.86);
          vec3 c = mix(horizon, zenith, pow(max(h, 0.0), 0.55));
          float s = max(dot(normalize(vDir), sunDir), 0.0);
          c += vec3(1.0, 0.95, 0.85) * (pow(s, 300.0) * 2.0 + pow(s, 8.0) * 0.15);
          gl_FragColor = vec4(c, 1.0);
          #include <colorspace_fragment>
        }`,
    }),
  );
  sky.renderOrder = -10;
  g.add(sky);

  const basic = (color: string) => new THREE.MeshBasicMaterial({ color });

  // mar (com leve variação de cor pela distância via neblina da cena)
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(4000, 2000), basic('#2f86a8'));
  sea.rotation.x = -Math.PI / 2;
  sea.position.set(0, ground, 1000 + 70);
  g.add(sea);

  // faixa de areia, calçadão e avenida (entre o prédio e o mar)
  const strips: Array<[number, number, string]> = [
    [4, 9, '#9a9a96'], // avenida
    [9, 14, '#c9b9a0'], // calçadão
    [14, 70, '#e9dcbc'], // areia
    [70, 74, '#d8cfb4'], // areia molhada
  ];
  for (const [z0, z1, color] of strips) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(3000, z1 - z0), basic(color));
    m.rotation.x = -Math.PI / 2;
    m.position.set(0, ground + 0.02, (z0 + z1) / 2);
    g.add(m);
  }
  const land = new THREE.Mesh(new THREE.PlaneGeometry(3000, 1500), basic('#b9b5ab'));
  land.rotation.x = -Math.PI / 2;
  land.position.set(0, ground, 4 - 750);
  g.add(land);

  // morros (a ponta com mata à direita, como nas fotos, e a serra ao fundo)
  const hill = (x: number, z: number, rx: number, rz: number, h: number, color: string) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), basic(color));
    m.scale.set(rx, h, rz);
    m.position.set(x, ground, z);
    g.add(m);
  };
  hill(aptCenterX + 520, 520, 260, 160, 120, '#4c6b46');
  hill(aptCenterX + 900, 380, 300, 200, 160, '#557550');
  hill(aptCenterX - 900, 300, 380, 260, 180, '#5d7a58');
  hill(aptCenterX - 200, -900, 900, 300, 260, '#6f8a6a');

  // prédios vizinhos ao longo da orla (Balneário tem muitos arranha-céus)
  const rnd = mulberry32(7);
  const shade = (hex: string) => {
    const base = new THREE.Color(hex);
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const colors: number[] = [];
    const n = geo.attributes.normal;
    for (let i = 0; i < n.count; i++) {
      const k = n.getY(i) > 0.5 ? 1 : n.getX(i) !== 0 ? 0.72 : 0.86;
      colors.push(base.r * k, base.g * k, base.b * k);
    }
    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    return geo;
  };
  const palette = ['#e8e3d9', '#d9dfe4', '#c9d3db', '#efe9df', '#b9c4cc', '#d8cbbb', '#c45a4a'];
  const towerMat = new THREE.MeshBasicMaterial({ vertexColors: true });
  for (let i = 0; i < 70; i++) {
    const side = i % 2 === 0 ? -1 : 1;
    const along = 30 + rnd() * 600;
    const x = aptCenterX + side * along;
    const z = -10 - rnd() * 120 * (along > 200 ? 1 : 0.3);
    const w = 18 + rnd() * 22;
    const d = 18 + rnd() * 20;
    const h = 40 + rnd() * (along < 250 ? 140 : 90);
    const m = new THREE.Mesh(shade(palette[Math.floor(rnd() * palette.length)]), towerMat);
    m.scale.set(w, h, d);
    m.position.set(x, ground + h / 2, z);
    g.add(m);
  }
  // fileira de prédios atrás
  for (let i = 0; i < 60; i++) {
    const x = aptCenterX - 700 + rnd() * 1400;
    const z = -150 - rnd() * 400;
    const h = 30 + rnd() * 110;
    const m = new THREE.Mesh(shade(palette[Math.floor(rnd() * 6)]), towerMat);
    m.scale.set(20 + rnd() * 25, h, 20 + rnd() * 25);
    m.position.set(x, ground + h / 2, z);
    g.add(m);
  }
  return g;
}

/** Torre do próprio prédio (acima e abaixo do apartamento), vista em "casa de bonecas" fica oculta. */
export function createOwnTower(bounds: [number, number, number, number], floorHeight: number, H: number) {
  const [x0, y0, x1, y1] = bounds;
  const w = x1 - x0 + 0.6;
  const d = y1 - y0 + 0.6;
  const mat = new THREE.MeshBasicMaterial({ color: '#d8d6d0' });
  const g = new THREE.Group();
  g.name = 'torre';
  const below = new THREE.Mesh(new THREE.BoxGeometry(w, floorHeight - 0.35, d), mat);
  below.position.set((x0 + x1) / 2, -0.35 - (floorHeight - 0.35) / 2, -(y0 + y1) / 2);
  const above = new THREE.Mesh(new THREE.BoxGeometry(w, 40, d), mat);
  above.position.set((x0 + x1) / 2, H + 0.3 + 20, -(y0 + y1) / 2);
  g.add(below, above);
  return g;
}

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
