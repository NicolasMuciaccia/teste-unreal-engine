# Planejamento: tour 3D do apartamento no navegador

## 1. Objetivo

Entregar ao cliente um **site com o apartamento em 3D** que os hóspedes do Airbnb
possam abrir pelo celular ou computador para "andar" pelo apê antes ou durante a
estadia, como no Reel de referência.

Critérios de sucesso:

- Abre em **qualquer celular** com um link ou QR code, sem app nem login.
- Carrega em **menos de 10 s em 4G**, roda a 30–60 fps em celular intermediário.
- Visual **fiel às fotos** do anúncio (layout, cores, móveis e luz).
- Navegação simples: visão "casa de bonecas" de cima, caminhar pelos cômodos
  e menu de cômodos.
- Hospedagem com custo baixo ou zero.

## 2. Decisão técnica principal: onde entra cada ferramenta

### 2.1 O Unreal Engine 5 não exporta para o navegador

O UE4 tinha exportação HTML5/WebGL, mas ela foi **removida na versão 4.24** e
não existe no UE5. Para rodar um projeto UE5 "no navegador" restam dois caminhos:

| Caminho | Como funciona | Problema para este projeto |
|---|---|---|
| **Pixel Streaming** (oficial) | O jogo roda num servidor com GPU na nuvem e o navegador recebe um vídeo | Custa cerca de US$ 0,50–1,50 **por hora por hóspede conectado**, precisa de servidor sempre ligado ou de fila, e tem latência. Desproporcional para um Airbnb. |
| Plugins de terceiros para WebGPU/WebGL | Empresas externas portam o UE5 para web | Pagos, experimentais e com downloads de centenas de MB. Risco alto. |

### 2.2 Arquitetura recomendada

```
                ┌───────────────────────────┐
 Fotos + medidas│  BLENDER (fonte única)    │
 ──────────────►│  modelagem, materiais,    │
                │  iluminação bakeada       │
                └─────────┬─────────┬───────┘
                          │         │
              GLB otimizado         FBX / USD
                          │         │
                          ▼         ▼
            ┌──────────────────┐  ┌──────────────────────────┐
            │ SITE (Three.js)  │  │ UNREAL ENGINE 5          │
            │ tour interativo  │  │ vídeo cinematográfico    │
            │ celular + PC     │  │ (Lumen / Path Tracer)    │
            │ hospedagem grátis│  │ para Instagram e anúncio │
            └──────────────────┘  │ (opcional: Pixel         │
                                  │  Streaming "premium")    │
                                  └──────────────────────────┘
```

- **Blender** é a fonte única da verdade: toda a modelagem acontece lá.
- **Site** em **Three.js**: o modelo exportado do Blender em glTF/GLB, com a luz
  "assada" (*baked*) nas texturas. Dá um visual quase fotorrealista com custo de
  GPU baixíssimo, e por isso roda bem até em celular simples.
- **Unreal Engine 5** reaproveita a mesma cena para o que ele faz de melhor:
  **renders e vídeos cinematográficos** (Movie Render Queue, Lumen, Path Tracer)
  para o Reel do Instagram e as fotos do anúncio. Se no futuro o cliente quiser
  uma versão "ultra" interativa, o mesmo projeto UE5 pode ir para Pixel Streaming.

> Se o requisito for "tem que ser UE5 rodando no navegador, custe o que custar",
> o plano muda para Pixel Streaming (seção 9). Recomendo começar pelo Three.js e
> só subir para o Pixel Streaming se o cliente pedir.

### 2.3 Alternativa futura: Gaussian Splatting

Com um **vídeo de 2–3 minutos gravado no apartamento** (celular andando devagar
por todos os cômodos), dá para gerar um *Gaussian Splat*: uma "captura 3D"
fotográfica, ultrarrealista, que também roda no navegador. **Não funciona com
poucas fotos do anúncio**, porque precisa de centenas de ângulos sobrepostos. Se
o cliente puder gravar esse vídeo, vale testar como complemento (ou substituto)
da modelagem manual.

## 3. Pipeline: das fotos ao site

### Fase 0: Recebimento e análise das fotos (½ dia)

1. Organizar as fotos em `reference/fotos/` com nomes por cômodo.
2. Para cada foto, identificar: cômodo, paredes visíveis, móveis, materiais
   (piso, revestimento, tecidos), fontes de luz e janelas.
3. Montar uma **matriz de cobertura**: o que aparece em quais fotos e o que
   **não aparece em nenhuma** (será inferido ou perguntado ao cliente).
4. Levantar as medidas: planta do cliente ou, na falta dela, estimativa a partir
   de objetos de tamanho padrão (porta ≈ 2,10 m × 0,80 m, bancada ≈ 0,90 m de
   altura, cama casal ≈ 1,38 m × 1,88 m, tomadas a ≈ 0,30 m do chão).

**Entregável:** `docs/analise-fotos.md` com a matriz de cobertura e a lista de
dúvidas para o cliente.

### Fase 1: Planta e volumetria (1–2 dias)

1. Descrever a planta num arquivo `blender/layout.json` (cômodos, paredes,
   portas, janelas e alturas).
2. Um script Python do Blender (`scripts/build_layout.py`) gera
   **automaticamente** paredes, piso, teto, vãos de portas e janelas a partir
   desse JSON. Mudou uma medida? É só rodar o script de novo.
3. **Casamento de câmera** (*camera matching*) com o **fSpy**: para cada foto
   principal, recriar a câmera exata que tirou a foto. Importada no Blender, ela
   permite sobrepor a foto ao modelo e ajustar paredes e móveis até coincidirem.

**Entregável:** "caixa" do apartamento com as dimensões corretas, validada
contra as fotos.

### Fase 2: Móveis e objetos (3–5 dias)

Estratégia por tipo de objeto:

| Tipo | Estratégia |
|---|---|
| Móveis genéricos (cadeiras, mesas, camas, sofás) | Assets **CC0** (Poly Haven, BlenderKit grátis, Sketchfab CC) ajustados em forma e cor |
| Móveis marcantes ou planejados (cabeceira, painel ripado, armário sob medida) | Modelados à mão a partir das fotos e das câmeras do fSpy |
| Quadros, tapetes, almofadas, cortinas | Geometria simples com a **textura recortada da própria foto** (projeção de câmera) |
| Eletrodomésticos | Assets genéricos com as cores e proporções certas |
| Plantas e decoração | Assets CC0 de baixa contagem de polígonos |

Orçamento de polígonos do site: **até cerca de 300 mil triângulos no total**.

### Fase 3: Materiais e texturas (2–3 dias)

- Materiais **PBR** (cor, rugosidade e normal) para piso, paredes, madeira,
  tecidos e metais, usando texturas CC0 do Poly Haven e do ambientCG, com a cor
  calibrada pelas fotos.
- Elementos únicos com textura extraída das fotos (correção de perspectiva no
  Blender ou no GIMP).

### Fase 4: Iluminação e *bake* (2 dias)

1. Iluminação realista no **Cycles**: luz do dia entrando pelas janelas (HDRI +
   sol) e as luminárias do apê.
2. **Bake** da iluminação (luz + sombras + oclusão ambiente) em *lightmaps*, num
   segundo canal UV. Esse passo dá o aspecto fotográfico no navegador sem custo
   de GPU.
3. Opcional: duas versões de luz, **dia** e **noite**, com um botão no site para
   alternar.

### Fase 5: Exportação e otimização (1 dia)

Pipeline automatizado (`scripts/export_web.sh`):

1. Blender → **GLB** (glTF binário).
2. `gltf-transform`: compressão de geometria **Meshopt/Draco**, texturas em
   **KTX2/Basis** (ocupam muito menos memória de GPU no celular), deduplicação
   e redimensionamento.
3. Duas qualidades: **mobile** (texturas de 1K) e **desktop** (2K), escolhidas
   automaticamente.

Metas: **≤ 15 MB** no mobile e **≤ 30 MB** no desktop, com menos de 100
*draw calls*.

### Fase 6: Site / visualizador 3D (4–6 dias)

**Stack:** Vite + TypeScript + Three.js. A interface fica em HTML/CSS leve, sem
framework pesado.

Funcionalidades (MVP em negrito):

- **Tela de carregamento** com logo, foto de capa e barra de progresso.
- **Modo "casa de bonecas"**: vista de cima com o teto removido, girando e dando
  zoom com o dedo ou o mouse (como nos Reels de tour 3D).
- **Modo caminhar** em primeira pessoa:
  - celular: joystick virtual + arrastar para olhar + **tocar no chão para ir até lá**;
  - PC: WASD/setas + mouse, ou clicar no chão.
  - Colisão com as paredes e altura dos olhos fixa (1,60 m).
- **Menu de cômodos**: botões "Sala, Cozinha, Quarto…" com transição suave da
  câmera.
- **Minimapa / planta** com a posição do visitante.
- **Pontos de interesse (hotspots)**: ícones clicáveis com texto e foto, por
  exemplo "Cama queen", "Smart TV com Netflix" ou "Cafeteira Nespresso".
- **Português / inglês / espanhol** (hóspedes estrangeiros).
- Alternar **dia/noite** (se o *bake* duplo for feito).
- Botão "**Reservar no Airbnb**" com o link do anúncio.
- Extras opcionais: modo VR (WebXR), visita guiada automática, áudio ambiente.

Desempenho: limitar a resolução de renderização em celulares (DPR ≤ 1,5),
carregar a qualidade certa por dispositivo e pausar a renderização com a aba
oculta.

### Fase 7: Vídeo cinematográfico no Unreal Engine 5 (2–3 dias, opcional)

1. Exportar a cena do Blender (FBX ou USD) e importar no UE5.
2. Reconfigurar os materiais no UE5 e usar **Lumen** para a iluminação dinâmica.
3. Animar a câmera no **Sequencer** (percurso pelo apê, como no Reel).
4. Renderizar no **Movie Render Queue** (vertical 1080×1920 para Reels e
   horizontal para o anúncio).

> O UE5 precisa de um PC com placa de vídeo dedicada (Windows ou Linux). Ele
> **não roda neste ambiente de nuvem**, então essa fase é feita na sua máquina,
> seguindo um guia passo a passo que vou escrever em `docs/guia-unreal.md`.

### Fase 8: Publicação (½ dia)

- Hospedagem estática gratuita: **GitHub Pages**, **Cloudflare Pages** ou
  **Vercel**.
- Domínio próprio opcional (ex.: `tour.nomedoape.com.br`).
- **QR code** para imprimir e deixar no apê ou enviar ao hóspede.
- Meta-tags de compartilhamento (prévia bonita no WhatsApp e no Instagram).

> ⚠️ **Política do Airbnb:** o Airbnb restringe links externos e dados de
> contato no texto do anúncio e nas mensagens **antes da reserva**. O caminho
> seguro é enviar o link **depois da reserva confirmada** (nas instruções de
> check-in ou no guia da casa) e divulgar no Instagram ou em site próprio.
> Vale o cliente confirmar as regras atuais.

## 4. Estrutura do repositório

```
teste-unreal-engine/
├── docs/
│   ├── PLANEJAMENTO.md        ← este documento
│   ├── CHECKLIST-CLIENTE.md   ← o que precisamos receber
│   ├── analise-fotos.md       (fase 0)
│   └── guia-unreal.md         (fase 7)
├── reference/
│   ├── fotos/                 fotos do anúncio (Git LFS)
│   └── plantas/               planta e medidas
├── blender/
│   ├── layout.json            planta paramétrica
│   └── apartamento.blend      cena principal (Git LFS)
├── scripts/
│   ├── build_layout.py        gera paredes/piso/teto a partir do layout.json
│   ├── bake_lightmaps.py      bake de iluminação no Cycles
│   ├── export_glb.py          exporta GLB do Blender
│   └── export_web.sh          otimização com gltf-transform
├── unreal/                    projeto UE5 (Git LFS)
└── web/
    ├── index.html
    ├── src/                   código do visualizador (TypeScript)
    └── public/models/         GLB final otimizado (git normal, sem LFS)
```

Observação: o **GitHub Pages não serve arquivos do Git LFS**. Por isso o GLB
final do site fica no Git normal (ele é pequeno, depois de otimizado), e só os
arquivos-fonte pesados vão para o LFS. A cota grátis do LFS é de 1 GB.

## 5. O que eu (Claude) consigo fazer aqui, e o que depende de você

| Tarefa | Quem |
|---|---|
| Análise das fotos, planejamento e documentação | Claude |
| `layout.json` e scripts Python do Blender (gerar a cena, bake, exportar) | Claude |
| Rodar o Blender em modo *headless* (sem interface) aqui na nuvem | Claude, **se** o download do Blender for liberado (hoje `download.blender.org` está bloqueado pela rede desta sessão; a alternativa é o pacote `bpy` do PyPI) |
| Ajuste fino visual no Blender (comparar com as fotos, retocar móveis) | Você, com os scripts e guias prontos, ou um artista 3D |
| Otimização do GLB e todo o site (Three.js) | Claude |
| Publicação no GitHub Pages | Claude (configuração) + você (ativar o Pages no repositório) |
| Vídeo no Unreal Engine 5 | Você, seguindo o guia que eu escrevo |

Sendo direto: sem interface gráfica, o primeiro modelo gerado por script vai
acertar **planta, proporções, cores e materiais**, mas detalhes finos (o caimento
de uma cortina, a forma exata de um sofá) ficam melhores com alguns ajustes
manuais no Blender. O plano prevê essa rodada de ajustes.

## 6. Cronograma estimado

| Fase | Duração |
|---|---|
| 0. Análise das fotos | ½ dia |
| 1. Planta e volumetria | 1–2 dias |
| 2. Móveis e objetos | 3–5 dias |
| 3. Materiais | 2–3 dias |
| 4. Iluminação e bake | 2 dias |
| 5. Exportação e otimização | 1 dia |
| 6. Site | 4–6 dias |
| 7. Vídeo UE5 (opcional) | 2–3 dias |
| 8. Publicação | ½ dia |
| **Total** | **cerca de 3 a 4 semanas** para um apê de 1–2 quartos |

As fases 2–4 (modelagem) e a fase 6 (site) andam **em paralelo**: o site começa
com a "caixa" da fase 1 e recebe o modelo final depois.

## 7. Custos

| Item | Custo |
|---|---|
| Blender, Three.js, fSpy, gltf-transform, assets CC0 | Grátis |
| Unreal Engine 5 | Grátis (os royalties não se aplicam a uso como visualização) |
| Hospedagem (GitHub Pages / Cloudflare Pages) | Grátis |
| Domínio próprio (opcional) | cerca de R$ 40/ano (.com.br) |
| Pixel Streaming (somente se escolhido) | cerca de US$ 0,50–1,50 por hora de uso, mais a configuração |

## 8. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Fotos não mostram todas as paredes ou cantos | Matriz de cobertura na fase 0 e perguntas ao cliente; em último caso, completar de forma coerente com o estilo |
| Medidas imprecisas | Pedir a planta; usar objetos de tamanho padrão e o fSpy para calibrar |
| Fotos de anúncio com grande-angular ou HDR exagerado | O fSpy compensa a lente; as cores são calibradas por amostragem, não copiadas cruas |
| Modelo pesado demais para o celular | Orçamento de polígonos e texturas desde o início; KTX2 + Meshopt; versão mobile separada |
| Hóspede se perde na navegação | Começar no modo "casa de bonecas", com menu de cômodos e "tocar para ir" |
| Direitos das fotos ou assets | Usar as fotos do próprio cliente e somente assets CC0 ou com licença comercial |

## 9. Plano B: UE5 via Pixel Streaming

Se o cliente exigir o UE5 interativo:

1. Montar a cena no UE5 (a partir do Blender) com Lumen e materiais completos.
2. Empacotar com o plugin **Pixel Streaming 2**.
3. Hospedar em uma instância com GPU (AWS g4dn/g5, Azure NV ou um provedor
   gerenciado como Arcware ou Vagon) ligada sob demanda.
4. Página web com o player e uma "fila" para quando houver muitos acessos.

Custo e manutenção são bem maiores. Sugiro usar só como upgrade, depois que o
tour em Three.js estiver no ar.

## 10. Próximos passos imediatos

1. **Você envia as fotos** (veja a seção "Como enviar" em
   `docs/CHECKLIST-CLIENTE.md`).
2. Eu faço a **fase 0**: análise das fotos, matriz de cobertura e dúvidas.
3. Em paralelo, eu crio o **esqueleto do site** (Vite + Three.js) com navegação
   funcionando sobre um modelo provisório.
4. Fase 1: `layout.json` e geração da planta no Blender.
