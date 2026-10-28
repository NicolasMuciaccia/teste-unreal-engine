// Otimiza o GLB exportado pelo Blender para a web:
//  - compressão de geometria meshopt
//  - texturas em WebP (cores até 1024 px; lightmap mantém a resolução)
// Uso: node scripts/optimize.mjs public/models/apartamento_raw.glb public/models/apartamento.glb
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, prune, meshopt, quantize, textureCompress } from '@gltf-transform/functions';
import { MeshoptEncoder } from 'meshoptimizer';
import sharp from 'sharp';

const [input, output] = process.argv.slice(2);
await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder });
const doc = await io.read(input);

await doc.transform(
  dedup(),
  prune(),
  textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 82, resize: [1024, 1024], slots: /^baseColor/ }),
  textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 90, slots: /^occlusion/ }),
  quantize({ quantizeTexcoord: 16 }),
  meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
);
await io.write(output, doc);
console.log('ok', output);
