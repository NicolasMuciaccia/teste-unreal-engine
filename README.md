# Tour 3D do apartamento: Airbnb

Site com um tour 3D interativo de um apartamento do Airbnb. O hóspede abre um link
(ou lê um QR code) e explora o apê pelo navegador, no celular ou no computador,
sem instalar nada.

- Planejamento: [`docs/PLANEJAMENTO.md`](docs/PLANEJAMENTO.md)
- Análise das fotos e planta estimada: [`docs/analise-fotos.md`](docs/analise-fotos.md)
- Como gerar o modelo e o site: [`docs/COMO-GERAR.md`](docs/COMO-GERAR.md)
- Vídeo no Unreal Engine 5: [`docs/guia-unreal.md`](docs/guia-unreal.md)
- O que precisamos do cliente: [`docs/CHECKLIST-CLIENTE.md`](docs/CHECKLIST-CLIENTE.md)

## Status (v0, protótipo)

- [x] Fotos analisadas e organizadas por cômodo
- [x] Planta **estimada** (`blender/layout.json`), à espera de confirmação do proprietário
- [x] Cena 3D gerada por script no Blender, com texturas das fotos e luz calculada no Cycles
- [x] Site com casa de bonecas, modo caminhar, menu de cômodos, minimapa, pontos de interesse e PT/EN/ES
- [ ] Ajustar a planta com o rascunho do proprietário
- [ ] Refinar móveis (sofá, cama, cortinas) e a luz
- [ ] Publicar (GitHub Pages) e gerar o QR code
- [ ] Vídeo cinematográfico no UE5 (opcional)

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
| `.github/workflows/` | Publicação automática no GitHub Pages |

## Fluxo resumido

```
Fotos + medidas ──► Blender (modelagem + iluminação "bakeada") ──► GLB otimizado ──► Site (Three.js)
                          │
                          └──► Unreal Engine 5 ──► vídeo cinematográfico (Instagram / anúncio)
```
