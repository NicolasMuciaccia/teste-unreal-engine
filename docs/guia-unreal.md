# Guia: vídeo cinematográfico no Unreal Engine 5

O UE5 não roda no navegador (veja `PLANEJAMENTO.md`, seção 2.1). Aqui ele serve para
produzir um **vídeo de alta qualidade** do apartamento para o Instagram e o anúncio,
reaproveitando o mesmo modelo do site.

> Requisitos: PC Windows ou Linux com placa de vídeo dedicada (RTX 2060 ou superior
> recomendada) e o Unreal Engine 5.4 ou mais novo (grátis pela Epic Games Launcher).

## 1. Exportar do Blender

1. Gere a cena: `python scripts/build_scene.py` (o bake não é necessário: o UE5 calcula a luz com o Lumen).
2. Abra `blender/apartamento.blend` e use *File → Export → FBX* com:
   - *Apply Scalings*: **FBX All**; *Forward*: **-Y Forward**; *Up*: **Z Up**
   - *Geometry → Smoothing*: **Face**
   - marque *Path Mode: Copy* e o botão ao lado, para embutir as texturas
3. Outra opção é importar direto `web/public/models/apartamento_raw.glb` pelo plugin
   glTF Importer (*Edit → Plugins → glTF*).

## 2. Montar a cena no UE5

1. Crie um projeto **Film / Video & Live Events → Blank**, com *Raytracing* ligado.
2. Importe o FBX em `Content/Apartamento` (*Combine Meshes* desligado).
3. Ajuste os materiais:
   - piso preto: *Roughness* 0.08 a 0.12 (reflexo forte, como nas fotos);
   - vidro: *Blend Mode* **Translucent**, *Opacity* 0.1, *Refraction* 1.5;
   - espelho: *Metallic* 1, *Roughness* 0.
4. Iluminação:
   - *Directional Light* (sol) + *Sky Atmosphere* + *Sky Light* (Real Time Capture);
   - *Post Process Volume* (Infinite Extent) → *Global Illumination*: **Lumen**, *Reflections*: **Lumen**,
     *Exposure*: Manual, com EV100 ≈ 9 a 10;
   - fora das janelas: um plano de mar com o material `M_Water` (pacote Water) ou um HDRI de praia.

## 3. Animar a câmera

1. *Cinematics → Add Level Sequence*.
2. Adicione uma *Cine Camera Actor* (lente de 18 a 24 mm para interiores; *Aperture* f/5.6).
3. Percurso sugerido (cerca de 30 s, como os Reels de tour):
   1. entrada → hall (4 s);
   2. revelação da sala com o mar ao fundo (6 s);
   3. jantar e cozinha (6 s);
   4. suíte (6 s);
   5. **final no spa**: aproximação lenta da hidromassagem com o mar (8 s).
4. Use *keyframes* com interpolação *Auto* e movimentos lentos (no máximo 0,5 m/s).

## 4. Renderizar

*Window → Cinematics → Movie Render Queue*:

| Formato | Resolução | Uso |
|---|---|---|
| Vertical | 1080 × 1920 | Reels / Stories |
| Horizontal | 1920 × 1080 | Anúncio, YouTube |

Configurações: *Anti-aliasing* com *Spatial Samples* 1 e *Temporal Samples* 8; saída em
**Apple ProRes** ou PNG em sequência. Para o máximo de qualidade, troque para
**Path Tracer** (bem mais lento).
