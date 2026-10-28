# Como gerar o modelo e o site

Todo o pipeline roda por scripts e não precisa de interface gráfica, nem do Blender instalado.

```
blender/layout.json ─┐
reference/fotos/ ────┼─► scripts/make_textures.py ─► blender/textures/*.jpg
                     │
                     └─► scripts/build_scene.py ─► blender/apartamento.blend
                                               ├─► web/public/models/apartamento_raw.glb
                                               └─► web/public/scene.json
                         web/scripts/optimize.mjs ─► web/public/models/apartamento.glb
```

## 1. Pré-requisitos

- Python 3.13 com o pacote `bpy` (o Blender 5.x como módulo Python):
  ```bash
  python3 -m venv .venv && .venv/bin/pip install bpy numpy pillow
  ```
  Também funciona com o Blender instalado: `blender -b -P scripts/build_scene.py -- --bake`
- Node.js 22.

## 2. Gerar

```bash
python3 scripts/make_textures.py                                        # texturas
.venv/bin/python scripts/build_scene.py --bake --samples 128 --lm-size 2048  # cena + luz (~10 min em 4 núcleos)
cd web && npm install && npm run optimize-model                       # GLB otimizado
npm run dev                                                           # abre em http://localhost:5173
```

- Sem `--bake`, a cena é gerada em segundos, mas sem iluminação (bom para testar a planta).
- `scripts/render_preview.py -- pasta_saida` renderiza prévias no Cycles.

## 3. Ajustar

| Quero mudar… | Onde |
|---|---|
| Paredes, portas, janelas, medidas | `blender/layout.json` → `walls` |
| Posição ou tamanho de um móvel | `blender/layout.json` → `furniture` |
| Nome dos cômodos, ponto de vista inicial | `blender/layout.json` → `rooms` |
| Pontos de interesse (textos, fotos) | `blender/layout.json` → `hotspots` |
| Cores e materiais | `scripts/make_textures.py` e `MATERIALS` em `scripts/build_scene.py` |
| Formato dos móveis | funções `f_*` em `scripts/build_scene.py` |
| Brilho geral do site | `exposure` em `web/public/scene.json` (ou `?exp=0.6` na URL para testar) |

Para ajustes finos, abra `blender/apartamento.blend` no Blender, edite e exporte
para glTF (`.glb`), incluindo os dois mapas UV.

## 4. Parâmetros de URL úteis

- `?room=spa`: abre já no cômodo indicado.
- `?mode=walk`: começa no modo caminhar.
- `?exp=0.6`: testa outro brilho.
