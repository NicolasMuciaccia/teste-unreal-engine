# Checklist: o que precisamos do cliente

## Essencial

- [ ] **Fotos do anúncio**, todas as disponíveis e na **resolução original**
      (não use prints de tela nem fotos baixadas pelo WhatsApp, que comprimem a imagem).
- [ ] **Link do anúncio** no Airbnb (para o botão "Reservar" e para conferir as fotos).
- [ ] **Planta baixa** do apartamento: a da construtora, a do condomínio ou um
      desenho à mão com as medidas.
- [ ] Se não houver planta: **medidas de cada cômodo** (largura × comprimento) e
      **altura do pé-direito**.
- [ ] Quantidade e nome dos cômodos (ex.: sala integrada, 1 quarto, 1 banheiro, varanda).

## Muito útil

- [ ] Fotos extras tiradas com o celular, mostrando **paredes e cantos que não aparecem
      no anúncio** (mesmo que fiquem feias, servem só de referência).
- [ ] **Vídeo de 2–3 min** andando devagar pelo apê, passando por todos os cômodos.
      Isso permite testar o *Gaussian Splatting*, o realismo máximo (veja o planejamento, seção 2.3).
- [ ] Medidas dos móveis principais (sofá, cama, mesa, bancada).
- [ ] Marcas e modelos de destaque para os hotspots (TV, cafeteira, colchão…).

## Identidade e conteúdo do site

- [ ] Nome do apartamento / anúncio.
- [ ] Logo e cores (se houver).
- [ ] Idiomas: português, inglês, espanhol?
- [ ] Textos dos pontos de interesse (comodidades a destacar).
- [ ] Domínio próprio? (ex.: `tour.nomedoape.com.br`)
- [ ] Quer versão **dia e noite**?
- [ ] Quer o **vídeo cinematográfico** (Unreal Engine 5) para o Instagram?

> 🔒 Não coloque senha de Wi-Fi, código de fechadura nem endereço exato no site:
> ele é público. Essas informações continuam nas mensagens privadas do Airbnb.

## Como enviar as fotos

Use uma destas opções, em ordem de preferência:

1. **Pelo GitHub**: acesse o repositório, abra a pasta `reference/fotos/`, clique em
   *Add file → Upload files* e arraste as fotos (escolha o branch do projeto).
2. **Google Drive**: crie uma pasta, coloque as fotos e me passe o nome ou o link
   (consigo ler o Drive por aqui).
3. **Anexar no chat**: funciona para eu *ver* as fotos e fazer a análise, mas, para
   recortar texturas e calibrar câmeras, preciso dos arquivos originais (opções 1 ou 2).

Nomeie as fotos por cômodo, se possível: `sala-01.jpg`, `cozinha-01.jpg`, `quarto1-01.jpg`…
