# Tour 3D do apartamento: Airbnb

Site com um tour 3D interativo de um apartamento do Airbnb. O hóspede abre um link
(ou lê um QR code) e explora o apê pelo navegador, no celular ou no computador,
sem instalar nada.

O planejamento completo está em [`docs/PLANEJAMENTO.md`](docs/PLANEJAMENTO.md).
A lista do que precisamos receber do cliente está em
[`docs/CHECKLIST-CLIENTE.md`](docs/CHECKLIST-CLIENTE.md).

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `docs/` | Planejamento, decisões técnicas e guias |
| `reference/fotos/` | Fotos originais do anúncio (entrada do projeto) |
| `reference/plantas/` | Planta baixa, medidas, croquis |
| `blender/` | Arquivos `.blend` (fonte da modelagem, via Git LFS) |
| `unreal/` | Projeto Unreal Engine 5 (vídeo cinematográfico, via Git LFS) |
| `scripts/` | Scripts Python do Blender (gerar cena, bake, exportar) e de otimização |
| `web/` | Site do tour 3D (Vite + TypeScript + Three.js) |

## Fluxo resumido

```
Fotos + medidas ──► Blender (modelagem + iluminação "bakeada") ──► GLB otimizado ──► Site (Three.js)
                          │
                          └──► Unreal Engine 5 ──► vídeo cinematográfico (Instagram / anúncio)
```
