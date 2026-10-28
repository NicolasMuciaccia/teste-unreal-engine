# Análise das fotos (fase 0)

São 33 fotos de 720 × 960 px. Elas foram renomeadas por cômodo em `reference/fotos/`.
É uma resolução baixa (parece compressão de WhatsApp ou download do anúncio), mas
basta para tirar cores, materiais, proporções e os quadros.

## Mapa das fotos

| Cômodo | Fotos | O que mostram |
|---|---|---|
| Sala de estar | `sala-01`, `sala-02` | Sala envidraçada em canto (frente + lateral), painel de madeira com TV, rack branco, sofá retrátil cinza-bege, 2 poltronas brancas giratórias, mesa lateral redonda de vidro, sanca de gesso |
| Jantar | `jantar-01`, `jantar-02`, `detalhe-tabua-01`, `detalhe-champanhe-01` | Mesa quadrada de vidro com base preta, 4 cadeiras de couro marrom com pés cromados, quadro grande (barco), coluna com mosaico de madeira, carrinho-bar |
| Hall / corredor | `hall-01`, `hall-02` | Corredor com quadro grande, espelho, mosaico de madeira e portas brancas com guarnição |
| Cozinha | `cozinha-01`, `cozinha-02` | Pastilha de vidro amarela com pastilhas espelhadas, bancada de quartzo amarelo, armários brancos com puxadores de inox, cooktop, forno, coifa inox, armário aéreo de vidro com iluminação |
| Área de serviço | `lavanderia-01` | Máquina de lavar, aquecedor a gás, bancada de granito, armários brancos, janela |
| Banheiro | `banheiro-01`, `banheiro-02` | Porcelanato branco, cuba de vidro artesanal (laranja/vermelha/preta), bancada branca suspensa, box de vidro, toalheiro térmico, faixa de pastilha escura no box, janela alta |
| Spa (hidromassagem) | `spa-01` a `spa-08`, `detalhe-hidro-01` | Banheira de hidromassagem em deck de ipê com degraus, janelas do piso ao teto com vista para o mar, persianas de madeira, revestimento ripado escuro, barra cromada, quadro clássico (mulher), portas de correr espelhadas |
| Suíte | `suite-01` a `suite-08`, `detalhe-cama-01` | Cama de casal com edredom de veludo azul-marinho, painel de madeira escura na cabeceira, tapete felpudo creme, guarda-roupa com portas de vidro, TV na parede com nichos, cortinas rosé, abertura para o spa |
| Fachada | `fachada-01`, `fachada-02` | Prédio alto na orla; entrada do condomínio |

## Materiais (cores tiradas das fotos)

| Material | Cor média | Onde |
|---|---|---|
| Porcelanato preto polido com veios brancos | `#211f1e` (+ veios) | Piso de todo o apê, exceto o banheiro |
| Parede bege texturizada | `#dacdb9` | Sala, corredor, suíte |
| Parede branca | `#eceae6` | Spa, cozinha, área de serviço |
| Ipê (ripado e deck) | `#5a2e20` | Spa |
| Mosaico de filetes de madeira | `#a07665` | Coluna do jantar / hall |
| Pastilha de vidro amarela | `#b49a12` | Cozinha |
| Quartzo amarelo | `#c98a0c` | Bancadas da cozinha |
| Veludo azul-marinho | `#1e2a4c` | Edredom |

## Matriz de cobertura e incertezas

| Item | Situação |
|---|---|
| Interior de cada cômodo | ✅ Bem coberto, salvo a área de serviço (só uma foto) |
| **Como os cômodos se ligam** (planta) | ⚠️ **Estimado.** Nenhuma foto mostra a planta, e os espelhos confundem a leitura |
| Medidas | ⚠️ Estimadas por objetos de tamanho padrão (portas, bancadas, cama) |
| Porta de entrada, geladeira | ❌ Não aparecem nas fotos (foram colocadas em posições plausíveis) |
| Parede atrás do sofá, lado da cama oposto ao guarda-roupa | ❌ Não aparecem |

### Planta estimada (v0)

```
             ┌──────────┬───────────────┬──────────┐
             │ Área de  │    Cozinha    │ Banheiro │
             │ serviço  │               │          │
 ┌───────────┴──┬───────┴───┬───────────┴──┬───────┴──┐
 │   Jantar     │        Hall de entrada   │  Entrada │
 │              ├───────────┬──────────────┴───┬──────┘
 │   Sala de    │    Spa    │      Suíte       │
 │   estar      │  (hidro)  │                  │
 └──────────────┴───────────┴──────────────────┘
       ~~~~~~~~~~~~~~~~ MAR ~~~~~~~~~~~~~~~~
```

Fica em `blender/layout.json`. Para corrigir a planta, basta editar esse arquivo e rodar
os scripts de novo (veja `docs/COMO-GERAR.md`).

## Perguntas para o proprietário

1. **Um rascunho da planta**, mesmo à mão: posição dos cômodos e da porta de entrada.
   Esse é o item que mais melhora o resultado.
2. Medidas aproximadas da sala e da suíte (largura × comprimento).
3. O spa com hidromassagem é aberto para a suíte ou tem porta própria pelo corredor?
4. A sala é voltada para o mar ou para a lateral (vista da praia com os prédios)?
5. Onde ficam a geladeira e a porta de entrada?
6. Quais comodidades destacar no tour (Wi-Fi rápido, ar-condicionado, garagem…)?
