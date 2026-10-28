"""Gera as texturas do apartamento em blender/textures/.

Duas fontes:
  * recortes das fotos do anúncio com a perspectiva corrigida (quadros);
  * texturas procedurais "tileáveis" com as cores amostradas das fotos
    (mármore, ripado de ipê, pastilha, tecidos...).

Uso:  python3 scripts/make_textures.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
FOTOS = ROOT / "reference" / "fotos"
OUT = ROOT / "blender" / "textures"
RNG = np.random.default_rng(42)


# ---------------------------------------------------------------- utilidades

def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0


def pnoise(n, freq, rng=RNG, aniso=(1.0, 1.0)):
    """Ruído periódico (tileável) por filtragem no domínio da frequência."""
    white = rng.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None] * n / aniso[1]
    fx = np.fft.fftfreq(n)[None, :] * n / aniso[0]
    r = np.sqrt(fx ** 2 + fy ** 2)
    filt = np.exp(-(r / freq) ** 2)
    out = np.real(np.fft.ifft2(np.fft.fft2(white) * filt))
    out -= out.mean()
    return out / (out.std() + 1e-8)


def save(arr, name, quality=88):
    img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    path = OUT / name
    img.save(path, quality=quality) if name.endswith(".jpg") else img.save(path)
    print("ok", path.relative_to(ROOT), img.size)


def colorize(base_hex, noise, amount):
    base = hex2rgb(base_hex)
    return np.clip(base[None, None, :] * (1.0 + amount * noise[..., None]), 0, 1)


def homography(src, dst):
    a = []
    for (x, y), (u, v) in zip(src, dst):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(a))
    return vt[-1].reshape(3, 3) / vt[-1][-1]


def rectify(photo, corners, size):
    """Recorta um quadrilátero (TL, TR, BR, BL) da foto como retângulo `size`."""
    w, h = size
    dst = [(0, 0), (w, 0), (w, h), (0, h)]
    # PIL precisa do mapeamento saída -> entrada
    m = homography(dst, corners)
    coeffs = m.flatten()[:8]
    img = Image.open(FOTOS / photo).convert("RGB")
    return img.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)


# ---------------------------------------------------------------- texturas

def marmore_preto(n=1024):
    # piso de porcelanato preto polido com veios brancos finos (2x2 placas de 90 cm)
    mott = pnoise(n, 6) * 0.5 + pnoise(n, 24) * 0.25
    img = colorize("#211f1e", mott, 0.18)
    for level, freq, strength in ((0.0, 4, 0.7), (1.3, 7, 0.4), (-1.5, 11, 0.25)):
        field = pnoise(n, freq) + 0.3 * pnoise(n, freq * 5)
        vein = np.exp(-((field - level) / 0.018) ** 2) * strength
        img = img * (1 - vein[..., None]) + hex2rgb("#d6d1c8")[None, None, :] * vein[..., None]
    seam = np.zeros((n, n))
    for k in (0, n // 2):
        seam[k:k + 2, :] = 1
        seam[:, k:k + 2] = 1
    img = img * (1 - 0.35 * seam[..., None])
    save(img, "marmore_preto.jpg")


def parede(name, hex_color, amount=0.025, n=512):
    noise = pnoise(n, 60) * 0.6 + pnoise(n, 200) * 0.4
    save(colorize(hex_color, noise, amount), name)


def ripado(name, base_hex, slat=10, gap=0.08, n=1024, vertical=False):
    """Ripas de madeira: `slat` ripas por metro (textura = 1 m)."""
    y = np.arange(n)
    slat_px = n / slat
    idx = (y // slat_px).astype(int)
    pos = (y % slat_px) / slat_px
    tones = 1.0 + RNG.normal(0, 0.12, slat + 1)
    grain = pnoise(n, 40, aniso=(8, 0.6)) * 0.5 + pnoise(n, 120, aniso=(10, 1)) * 0.3
    img = colorize(base_hex, grain, 0.12)
    img *= tones[idx][:, None, None]
    gap_mask = (pos > 1 - gap)
    edge = np.clip(1 - np.abs(pos - 0.5) * 2, 0, 1) ** 0.15
    img *= (0.85 + 0.15 * edge)[:, None, None]
    img[gap_mask] *= 0.25
    if vertical:
        img = np.transpose(img, (1, 0, 2))
    save(img, name)


def mosaico_madeira(n=1024):
    # filetes de madeira de comprimentos variados (coluna do hall); textura = 0.5 m
    base = Image.open(FOTOS / "jantar-01.jpg").convert("RGB").crop((640, 40, 700, 520))
    palette = np.asarray(base).reshape(-1, 3).astype(np.float32) / 255.0
    palette = palette[(palette.sum(1) > 0.6) & (palette.sum(1) < 1.9)]
    img = np.zeros((n, n, 3), np.float32)
    row_h = n // 24
    grain = pnoise(n, 50, aniso=(6, 1)) * 0.5
    for r in range(24):
        x = int(RNG.integers(0, 40))
        y0 = r * row_h
        while x < n + 120:
            L = int(RNG.integers(40, 160))
            c = palette[RNG.integers(0, len(palette))] * RNG.uniform(0.8, 1.15)
            xs = np.arange(x, x + L) % n
            img[y0 + 2:y0 + row_h - 2, xs] = c
            x += L + 3
    img *= (1 + 0.15 * grain[..., None])
    save(img, "mosaico_madeira.jpg")


def pastilha(n=1024, tiles=50):
    # pastilha de vidro amarela 2x2 cm com algumas pastilhas espelhadas; textura = 1 m
    px = n / tiles
    yy, xx = np.mgrid[0:n, 0:n]
    ty, tx = (yy // px).astype(int), (xx // px).astype(int)
    fy, fx = (yy % px) / px, (xx % px) / px
    tone = RNG.normal(0, 0.07, (tiles + 1, tiles + 1))
    mirror = RNG.random((tiles + 1, tiles + 1)) < 0.03
    base = hex2rgb("#b49a12")
    img = base[None, None, :] * (1 + tone[ty, tx])[..., None]
    shine = np.exp(-((fx - 0.3) ** 2 + (fy - 0.3) ** 2) / 0.05) * 0.18
    img += shine[..., None]
    img[mirror[ty, tx]] = hex2rgb("#d9d9d4")
    grout = (fx < 0.09) | (fy < 0.09)
    img[grout] = hex2rgb("#cfc49a")
    save(img, "pastilha_amarela.jpg")


def quartzo(n=512):
    speck = (RNG.random((n, n)) ** 30) * 2.5
    noise = pnoise(n, 80) * 0.3 + speck
    save(colorize("#c98a0c", noise, 0.12), "quartzo_amarelo.jpg")


def veneer(name, hex_color, n=1024):
    grain = pnoise(n, 30, aniso=(0.5, 10)) * 0.6 + pnoise(n, 150, aniso=(0.5, 12)) * 0.3
    stripes = np.sin(np.linspace(0, 2 * np.pi * 6, n))[None, :] * 0.15
    save(colorize(hex_color, grain + stripes, 0.15), name)


def veludo(n=1024):
    # edredom de veludo amassado azul-marinho com pespontos (textura = 0.5 m)
    crush = pnoise(n, 25) * 0.7 + pnoise(n, 90) * 0.4
    img = colorize("#1e2a4c", crush, 0.35)
    yy, xx = np.mgrid[0:n, 0:n]
    q = n // 2
    seam = (np.minimum(yy % q, q - yy % q) < 3) | (np.minimum(xx % q, q - xx % q) < 3)
    puff = (np.sin(np.pi * (yy % q) / q) * np.sin(np.pi * (xx % q) / q)) ** 0.5
    img *= (0.75 + 0.3 * puff)[..., None]
    img[seam] *= 0.55
    save(img, "veludo_azul.jpg")


def felpudo(n=512):
    fur = pnoise(n, 160) * 0.6 + pnoise(n, 40) * 0.4
    save(colorize("#e4d9c3", fur, 0.12), "tapete_felpudo.jpg")


def tecido(name, hex_color, n=512, amount=0.06):
    weave = pnoise(n, 200) * 0.5 + pnoise(n, 30) * 0.5
    save(colorize(hex_color, weave, amount), name)


def cortina(n=512):
    x = np.linspace(0, 2 * np.pi * 8, n)
    folds = (np.sin(x) * 0.6 + np.sin(2.3 * x) * 0.2)[None, :].repeat(n, 0)
    save(colorize("#cfae9e", folds + pnoise(n, 100) * 0.1, 0.12), "cortina.jpg")


def porcelanato_branco(n=1024):
    img = colorize("#e9e7e3", pnoise(n, 20) * 0.5, 0.02)
    k = n // 2
    for c in (0, k):
        img[c:c + 2, :] *= 0.85
        img[:, c:c + 2] *= 0.85
    save(img, "porcelanato_branco.jpg")


def quadros():
    # (foto, cantos TL TR BR BL incluindo a moldura, tamanho de saída)
    save_img(rectify("jantar-01.jpg", [(152, 108), (583, 110), (558, 443), (175, 443)], (1024, 790)),
             "quadro_barco.jpg")
    save_img(rectify("spa-07.jpg", [(127, 295), (297, 310), (299, 500), (148, 526)], (600, 800)),
             "quadro_mulher.jpg")
    # o quadro do corredor aparece muito de lado; usamos só a tela, com correção forte
    save_img(rectify("hall-01.jpg", [(45, 0), (180, 120), (185, 515), (45, 545)], (600, 800))
             .filter(ImageFilter.GaussianBlur(1.2)), "quadro_corredor.jpg")


def save_img(img, name):
    img.save(OUT / name, quality=90)
    print("ok", (OUT / name).relative_to(ROOT), img.size)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    marmore_preto()
    parede("parede_bege.jpg", "#dccfbb")
    parede("parede_branca.jpg", "#ecebe8", amount=0.012)
    ripado("ripado_ipe_h.jpg", "#5a2e20")
    ripado("ripado_ipe_v.jpg", "#4e281c", slat=12, vertical=True)
    mosaico_madeira()
    pastilha()
    quartzo()
    veneer("madeira_painel_tv.jpg", "#8a6a52")
    veneer("madeira_escura.jpg", "#3a2a22")
    veludo()
    felpudo()
    tecido("tecido_sofa.jpg", "#a89d8c")
    tecido("couro_marrom.jpg", "#4c3628", amount=0.12)
    tecido("couro_branco.jpg", "#ece8df", amount=0.03)
    cortina()
    porcelanato_branco()
    quadros()


if __name__ == "__main__":
    main()
