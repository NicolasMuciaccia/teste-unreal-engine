"""Constrói o apartamento no Blender a partir de blender/layout.json.

Roda sem interface (headless), tanto com o Blender instalado quanto com o
módulo `bpy` do PyPI:

    blender -b -P scripts/build_scene.py -- [--bake] [--samples 128] [--lm-size 2048]
    python  scripts/build_scene.py        [--bake] [--samples 128] [--lm-size 2048]

Saídas:
    blender/apartamento.blend      cena completa (abra no Blender para ajustes manuais)
    web/public/models/apartamento.glb
    web/public/models/lightmap.png (com --bake)
    web/public/scene.json          cômodos, colisão, pontos de interesse (para o site)
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy  # noqa: I001  (bpy precisa vir antes de bmesh)
import bmesh
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = ROOT / "blender" / "layout.json"
TEX = ROOT / "blender" / "textures"
WEB = ROOT / "web" / "public"

# --------------------------------------------------------------------- materiais
# nome: (textura ou cor, tamanho da textura em metros, rugosidade, metálico, extras)
MATERIALS = {
    "marmore_preto": dict(tex="marmore_preto.jpg", tile=1.8, rough=0.12),
    "parede_bege": dict(tex="parede_bege.jpg", tile=1.0, rough=0.85),
    "parede_branca": dict(tex="parede_branca.jpg", tile=1.0, rough=0.85),
    "fachada": dict(color="#e8e6e1", rough=0.9),
    "teto": dict(color="#f3f2ef", rough=0.9),
    "rodape": dict(color="#f1efea", rough=0.4),
    "ripado_ipe_h": dict(tex="ripado_ipe_h.jpg", tile=1.0, rough=0.55),
    "ripado_ipe_v": dict(tex="ripado_ipe_v.jpg", tile=1.0, rough=0.55),
    "mosaico_madeira": dict(tex="mosaico_madeira.jpg", tile=0.5, rough=0.6),
    "pastilha_amarela": dict(tex="pastilha_amarela.jpg", tile=1.0, rough=0.15),
    "quartzo_amarelo": dict(tex="quartzo_amarelo.jpg", tile=0.6, rough=0.2),
    "madeira_painel_tv": dict(tex="madeira_painel_tv.jpg", tile=1.2, rough=0.5),
    "madeira_escura": dict(tex="madeira_escura.jpg", tile=1.2, rough=0.45),
    "veludo_azul": dict(tex="veludo_azul.jpg", tile=0.5, rough=0.7),
    "tapete_felpudo": dict(tex="tapete_felpudo.jpg", tile=0.6, rough=1.0),
    "tecido_sofa": dict(tex="tecido_sofa.jpg", tile=0.5, rough=0.95),
    "couro_marrom": dict(tex="couro_marrom.jpg", tile=0.5, rough=0.5),
    "couro_branco": dict(tex="couro_branco.jpg", tile=0.5, rough=0.45),
    "cortina": dict(tex="cortina.jpg", tile=1.0, rough=0.95),
    "porcelanato_branco": dict(tex="porcelanato_branco.jpg", tile=1.2, rough=0.15),
    "branco_laca": dict(color="#efede8", rough=0.3),
    "preto": dict(color="#141414", rough=0.4),
    "cromado": dict(color="#d4d7db", rough=0.12, metal=1.0),
    "inox": dict(color="#b9bdc1", rough=0.3, metal=1.0),
    "aluminio_preto": dict(color="#1d1d1f", rough=0.4, metal=0.6),
    "vidro": dict(color="#d7ebf0", rough=0.02, alpha=0.18),
    "vidro_fosco": dict(color="#dfe5e3", rough=0.5),
    "espelho": dict(color="#e9ecee", rough=0.02, metal=1.0),
    "tela_tv": dict(color="#0b0c0e", rough=0.12),
    "porcelana": dict(color="#f5f4f1", rough=0.15),
    "granito": dict(color="#a39b8f", rough=0.25),
    "vidro_colorido": dict(color="#a8401c", rough=0.1),
    "flores": dict(color="#f0e8d2", rough=0.8),
    "folhas": dict(color="#3d5a2c", rough=0.8),
    "porta_madeira": dict(color="#5a3a28", rough=0.5),
    "travesseiro": dict(color="#2a3350", rough=0.9),
    "lencol": dict(color="#f2f0ec", rough=0.9),
}

_mats = {}


def hex_rgba(h, a=1.0):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)


def material(name, texture=None):
    key = name if texture is None else f"{name}:{texture}"
    if key in _mats:
        return _mats[key]
    spec = dict(MATERIALS.get(name, {"color": "#ff00ff"}))
    if texture:
        spec["tex"] = texture
    m = bpy.data.materials.new(key.replace(":", "_").replace(".jpg", ""))
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = spec.get("rough", 0.5)
    bsdf.inputs["Metallic"].default_value = spec.get("metal", 0.0)
    if "tex" in spec:
        img = bpy.data.images.load(str(TEX / spec["tex"]), check_existing=True)
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        nt.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = hex_rgba(spec["color"])
    if "alpha" in spec:
        bsdf.inputs["Alpha"].default_value = spec["alpha"]
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"
    m["tile"] = spec.get("tile", 1.0)
    _mats[key] = m
    return m


# --------------------------------------------------------------------- geometria

def new_object(name, bm, keep_uv=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob["keep_uv"] = keep_uv
    return ob


class Builder:
    """Acumula peças (caixas, cilindros...) num único bmesh com materiais."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.mats = []

    def _mat_index(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def box(self, size, center, mat, rot=0.0):
        w, d, h = size
        geom = bmesh.ops.create_cube(self.bm, size=1.0)["verts"]
        m = (Matrix.Translation(Vector(center)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
             @ Matrix.Diagonal((w, d, h, 1.0)))
        bmesh.ops.transform(self.bm, matrix=m, verts=geom)
        idx = self._mat_index(mat)
        for f in {f for v in geom for f in v.link_faces}:
            f.material_index = idx
        return geom

    def cylinder(self, radius, height, center, mat, segments=24, scale=(1, 1), caps=True):
        r = bmesh.ops.create_cone(self.bm, cap_ends=caps, segments=segments,
                                  radius1=radius, radius2=radius, depth=height)
        m = Matrix.Translation(Vector(center)) @ Matrix.Diagonal((scale[0], scale[1], 1, 1))
        bmesh.ops.transform(self.bm, matrix=m, verts=r["verts"])
        idx = self._mat_index(mat)
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = idx
        return r["verts"]

    def sphere(self, radius, center, mat, scale=(1, 1, 1), segs=12):
        r = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=segs // 2 + 1, radius=radius)
        m = Matrix.Translation(Vector(center)) @ Matrix.Diagonal((*scale, 1))
        bmesh.ops.transform(self.bm, matrix=m, verts=r["verts"])
        idx = self._mat_index(mat)
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = idx

    def quad(self, pts, mat, uvs=None):
        vs = [self.bm.verts.new(p) for p in pts]
        f = self.bm.faces.new(vs)
        f.material_index = self._mat_index(mat)
        if uvs:
            for loop, uv in zip(f.loops, uvs):
                loop[self.uv].uv = uv
        return f

    def build(self, name, keep_uv=False, transform=None):
        if transform is not None:
            bmesh.ops.transform(self.bm, matrix=transform, verts=self.bm.verts)
        self.bm.normal_update()
        ob = new_object(name, self.bm, keep_uv)
        for m in self.mats:
            ob.data.materials.append(m)
        return ob


def placement(item):
    x, y = item["pos"]
    z = item.get("z", 0.0)
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(item.get("rot", 0)), 4, "Z")


# --------------------------------------------------------------------- paredes

def build_walls(layout, H):
    colliders = []
    b = Builder()
    trims = Builder()
    windows = Builder()
    glass = Builder()
    for wi, w in enumerate(layout["walls"]):
        a, c = Vector((*w["a"], 0)), Vector((*w["b"], 0))
        d = c - a
        L = d.length
        u = d.normalized()
        n_left = Vector((-u.y, u.x, 0))
        t = w["t"]
        ml, mr = material(w["mat"][0]), material(w["mat"][1])
        # peças ao longo da parede: (s0, s1, z0, z1)
        pieces, cursor = [], 0.0
        ops = sorted(w.get("openings", []), key=lambda o: o["offset"])
        for op in ops:
            s0, s1 = op["offset"], op["offset"] + op["width"]
            if s0 > cursor:
                pieces.append((cursor, s0, 0, H))
            sill = op.get("sill", 0.0)
            top = sill + op["height"]
            if sill > 0:
                pieces.append((s0, s1, 0, sill))
            if top < H:
                pieces.append((s0, s1, top, H))
            cursor = s1
            build_opening(op, a, u, n_left, t, w.get("ext", False), windows, glass, trims)
        if cursor < L:
            pieces.append((cursor, L, 0, H))
        # extensões nas pontas para fechar os cantos
        ext = t / 2
        for (s0, s1, z0, z1) in pieces:
            e0 = ext if s0 == 0 else 0
            e1 = ext if abs(s1 - L) < 1e-6 else 0
            mid = a + u * ((s0 - e0 + s1 + e1) / 2)
            length = (s1 + e1) - (s0 - e0)
            if z1 >= H:
                z1 = H + 0.0007 * (wi % 7)
            verts = b.box((length, t, z1 - z0), (mid.x, mid.y, (z0 + z1) / 2), ml,
                          rot=math.degrees(math.atan2(u.y, u.x)))
            b.bm.normal_update()
            for f in {f for v in verts for f in v.link_faces}:
                dn = f.normal.dot(n_left)
                f.material_index = b._mat_index(ml if dn > 0.5 else mr if dn < -0.5 else ml)
            # rodapé nas faces internas
            if z0 == 0 and z1 > 0.5:
                for side, mat_name in ((1, w["mat"][0]), (-1, w["mat"][1])):
                    if mat_name == "fachada" or mat_name == "porcelanato_branco":
                        continue
                    p = mid + n_left * side * (t / 2 + 0.008)
                    trims.box((length, 0.016, 0.15), (p.x, p.y, 0.075), material("rodape"),
                              rot=math.degrees(math.atan2(u.y, u.x)))
        # colisão: trechos sem porta/abertura
        cursor = 0.0
        for op in ops:
            if op.get("sill", 0) < 0.3 and op["type"] in ("door", "opening"):
                colliders.append(seg(a + u * cursor, a + u * op["offset"]))
                cursor = op["offset"] + op["width"]
        colliders.append(seg(a + u * cursor, c))
    b.build("paredes")
    trims.build("rodapes")
    windows.build("esquadrias")
    if glass.bm.faces:
        glass.build("vidro_janelas")
    return colliders


def seg(p, q):
    return {"kind": "seg", "a": [round(p.x, 3), round(p.y, 3)], "b": [round(q.x, 3), round(q.y, 3)]}


def build_opening(op, a, u, n, t, exterior, frames, glass, trims):
    s0, w = op["offset"], op["width"]
    sill = op.get("sill", 0.0)
    h = op["height"]
    rot = math.degrees(math.atan2(u.y, u.x))
    center = a + u * (s0 + w / 2)
    alu = material("aluminio_preto")
    if op["type"] == "window":
        fw = 0.05
        cz = sill + h / 2
        for zc, hh in ((sill + fw / 2, fw), (sill + h - fw / 2, fw)):
            frames.box((w, 0.07, hh), (center.x, center.y, zc), alu, rot)
        panes = op.get("mullions", 2)
        for i in range(panes + 1):
            p = a + u * (s0 + fw / 2 + i * (w - fw) / panes)
            frames.box((fw, 0.07, h), (p.x, p.y, cz), alu, rot)
        glass.box((w, 0.01, h), (center.x, center.y, cz), material("vidro"), rot)
        # peitoril interno
        p = center + n * (t / 2 + 0.03)
        trims.box((w + 0.06, 0.06 + t * 0.0, 0.03), (p.x, p.y, sill), material("granito"), rot)
    elif op["type"] in ("door", "entrance"):
        cas = material("rodape")
        for side in (1, -1):
            p0 = center + n * side * (t / 2 + 0.005)
            for e in (-1, 1):
                q = p0 + u * e * (w / 2 + 0.03)
                trims.box((0.07, 0.012, h + 0.04), (q.x, q.y, (h + 0.04) / 2), cas, rot)
            trims.box((w + 0.13, 0.012, 0.07), (p0.x, p0.y, h + 0.035), cas, rot)


# --------------------------------------------------------------------- pisos/tetos

def build_floors_ceilings(layout, H):
    for room in layout["rooms"]:
        pts = room["polygon"]
        mat = material(room["floor"])
        for kind, z, m in (("piso", 0.0, mat), ("teto", H, material("teto"))):
            bm = bmesh.new()
            vs = [bm.verts.new((x, y, z)) for x, y in pts]
            f = bm.faces.new(vs if kind == "piso" else list(reversed(vs)))
            f.material_index = 0
            ob = new_object(f"{kind}_{room['id']}", bm)
            ob.data.materials.append(m)
    # laje sob cada cômodo (espessura para a vista "casa de bonecas")
    b = Builder()
    for room in layout["rooms"]:
        xs = [p[0] for p in room["polygon"]]
        ys = [p[1] for p in room["polygon"]]
        w, d = max(xs) - min(xs) + 0.2, max(ys) - min(ys) + 0.2
        b.box((w, d, 0.3), ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, -0.151), material("fachada"))
    b.build("laje")


# --------------------------------------------------------------------- móveis

def f_caixa(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material(it.get("material", "branco_laca")))


def f_revestimento(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material(it["material"]))


def f_quadro(b, it, w, d, h):
    # moldura escura + tela com a foto (UV 0..1)
    b.box((w, d, h), (0, 0, h / 2), material("madeira_escura"))
    tex = material("quadro", texture=it["texture"])
    y = -d / 2 - 0.002
    b.quad([(-w / 2, y, 0), (w / 2, y, 0), (w / 2, y, h), (-w / 2, y, h)], tex,
           uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


def f_painel_tv(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("madeira_painel_tv"))
    b.box((1.45, 0.06, 0.95), (0, -0.03, 1.38), material("branco_laca"))
    b.box((1.24, 0.05, 0.72), (0, -0.07, 1.38), material("tela_tv"))


def f_tv(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("tela_tv"))


def f_rack(b, it, w, d, h):
    b.box((w, d, 0.06), (0, 0, h - 0.03), material("branco_laca"))
    b.box((w, d, 0.06), (0, 0, 0.13), material("branco_laca"))
    for e in (-1, 1):
        b.box((0.06, d, h), (e * (w / 2 - 0.03), 0, h / 2), material("branco_laca"))
    b.box((w * 0.45, d * 0.9, 0.2), (w * 0.15, 0, 0.3), material("branco_laca"))


def f_sofa(b, it, w, d, h):
    tec = material("tecido_sofa")
    b.box((w, d - 0.25, 0.22), (0, -0.12, 0.11), tec)            # base
    seat = w - 0.3
    for i in range(3):
        cx = -seat / 2 + seat / 6 + i * seat / 3
        b.box((seat / 3 - 0.02, d - 0.3, 0.2), (cx, -0.13, 0.32), tec)
        b.box((seat / 3 - 0.02, 0.28, 0.42), (cx, d / 2 - 0.3, 0.6), tec)  # encosto
    b.box((w, 0.22, h - 0.05), (0, d / 2 - 0.11, (h - 0.05) / 2), tec)
    for e in (-1, 1):
        b.box((0.15, d - 0.2, 0.58), (e * (w / 2 - 0.075), -0.1, 0.29), tec)


def f_poltrona(b, it, w, d, h):
    c = material("couro_branco")
    b.cylinder(0.025, 0.3, (0, 0, 0.15), material("cromado"), 12)
    b.cylinder(0.28, 0.03, (0, 0, 0.02), material("cromado"), 5)
    b.box((w, d, 0.2), (0, 0, 0.4), c)
    b.box((w, 0.16, 0.45), (0, d / 2 - 0.08, 0.72), c)
    for e in (-1, 1):
        b.box((0.13, d, 0.28), (e * (w / 2 - 0.065), 0, 0.62), c)


def f_mesa_redonda_vidro(b, it, w, d, h):
    b.cylinder(w / 2, 0.015, (0, 0, h), material("vidro"), 32)
    b.cylinder(0.12, h - 0.02, (0, 0, (h - 0.02) / 2), material("couro_marrom"), 16)


def f_flores(b, it, w, d, h):
    b.cylinder(0.06, h * 0.45, (0, 0, h * 0.225), material("vidro_fosco"), 12)
    for i in range(7):
        a = i * 2.4
        r = 0.06 + 0.04 * (i % 3)
        b.sphere(0.06, (math.cos(a) * r, math.sin(a) * r, h * 0.55 + 0.05 * (i % 2)), material("flores"))
    b.sphere(0.13, (0, 0, h * 0.5), material("folhas"), scale=(1, 1, 0.6))


def f_ar_condicionado(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("branco_laca"))


def f_mesa_jantar(b, it, w, d, h):
    b.box((w, d, 0.02), (0, 0, h - 0.01), material("vidro"))
    for e in (-1, 1):
        b.box((0.12, d * 0.55, h - 0.02), (e * 0.15, 0, (h - 0.02) / 2), material("preto"))
    b.box((0.42, 0.12, h - 0.02), (0, 0, (h - 0.02) / 2), material("preto"))


def f_cadeira(b, it, w, d, h):
    c, cr = material("couro_marrom"), material("cromado")
    b.box((w * 0.9, d * 0.85, 0.06), (0, -0.02, 0.47), c)
    b.box((w * 0.9, 0.06, 0.38), (0, d / 2 - 0.08, 0.7), c, rot=0)
    b.cylinder(0.02, 0.4, (0, 0, 0.22), cr, 10)
    for i in range(4):
        a = math.radians(45 + 90 * i)
        b.box((0.35, 0.025, 0.02), (math.cos(a) * 0.17, math.sin(a) * 0.17, 0.03), cr, rot=45 + 90 * i)
    for e in (-1, 1):
        b.box((0.02, d * 0.7, 0.02), (e * w * 0.45, 0, 0.66), cr)


def f_carrinho_bar(b, it, w, d, h):
    p = material("preto")
    for z in (0.15, 0.5, h - 0.02):
        b.box((w, d, 0.02), (0, 0, z), material("madeira_painel_tv"))
    for ex in (-1, 1):
        for ey in (-1, 1):
            b.box((0.02, 0.02, h), (ex * (w / 2 - 0.01), ey * (d / 2 - 0.01), h / 2), p)
    for i in range(3):
        b.cylinder(0.035, 0.3, (-0.2 + i * 0.12, 0, h + 0.15), material("vidro_colorido" if i == 1 else "preto"), 10)


def f_porta(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("porta_madeira"))
    b.box((0.03, 0.06, 0.25), (w / 2 - 0.1, -0.04, 1.05), material("cromado"))


def cabinets(b, w, d, h, top="quartzo_amarelo"):
    b.box((w, d - 0.03, h - 0.12), (0, 0.015, 0.06 + (h - 0.12) / 2), material("branco_laca"))
    b.box((w, d - 0.08, 0.1), (0, 0.04, 0.05), material("preto"))
    for i in range(int(w / 0.5)):
        x = -w / 2 + 0.25 + i * 0.5
        for z in (0.3, 0.55, 0.78):
            b.box((0.4, 0.015, 0.012), (x, -d / 2 - 0.005, z), material("inox"))
    b.box((w + 0.02, d + 0.02, 0.03), (0, 0, h - 0.015), material(top))


def f_bancada_cozinha(b, it, w, d, h):
    cabinets(b, w, d, h)
    b.box((0.55, 0.45, 0.012), (-w / 2 + 0.45, 0, h + 0.006), material("preto"))
    for ex in (-1, 1):
        for ey in (-1, 1):
            b.cylinder(0.06, 0.012, (-w / 2 + 0.45 + ex * 0.13, ey * 0.11, h + 0.014), material("aluminio_preto"), 12)
    b.cylinder(0.2, 0.012, (w / 2 - 0.55, 0, h + 0.004), material("inox"), 24, scale=(1.2, 0.9))
    b.cylinder(0.015, 0.3, (w / 2 - 0.55, 0.25, h + 0.15), material("cromado"), 8)
    b.box((0.55, 0.02, 0.5), (-w / 2 + 0.45, -d / 2 - 0.01, 0.4), material("tela_tv"))   # forno


def f_bancada_simples(b, it, w, d, h):
    cabinets(b, w, d, h, it.get("top", "quartzo_amarelo"))


def f_armario_aereo(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("branco_laca"))
    b.box((w - 0.08, 0.01, h - 0.08), (0, -d / 2 - 0.005, h / 2), material("vidro_fosco"))


def f_coifa(b, it, w, d, h):
    b.box((w, d, 0.06), (0, 0, 0.03), material("inox"))
    b.box((0.25, 0.2, h - 0.06), (0, d / 2 - 0.12, 0.06 + (h - 0.06) / 2), material("inox"))


def f_geladeira(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("inox"))
    b.box((w - 0.02, 0.005, 0.01), (0, -d / 2 - 0.003, h * 0.62), material("preto"))


def f_maquina_lavar(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("branco_laca"))
    b.cylinder(0.2, 0.02, (0, -d / 2 - 0.01, 0.42), material("vidro_fosco"), 24)


def f_bancada_banheiro(b, it, w, d, h):
    b.box((w, d, 0.1), (0, 0, h - 0.05), material("porcelana"))
    b.box((w, d, 0.04), (0, 0, h - 0.4), material("porcelana"))
    b.sphere(0.21, (0, -0.02, h + 0.07), material("vidro_colorido"), scale=(1, 1, 0.38), segs=20)
    b.cylinder(0.015, 0.3, (0, d / 2 - 0.08, h + 0.15), material("cromado"), 8)


def f_vaso_sanitario(b, it, w, d, h):
    p = material("porcelana")
    b.box((w, 0.18, 0.38), (0, d / 2 - 0.09, h - 0.19), p)
    b.cylinder(w / 2, 0.42, (0, -0.05, 0.21), p, 20, scale=(1, 1.25))


def f_vidro(b, it, w, d, h):
    b.box((w, 0.01, h), (0, 0, h / 2), material("vidro"))


def f_hidro(b, it, w, d, h):
    """Deck de ipê com banheira oval embutida."""
    deck_v, deck_top = material("ripado_ipe_v"), material("ripado_ipe_h")
    white = material("porcelana")
    # laterais do deck
    for (sx, sy, cx, cy) in ((w, 0.04, 0, -d / 2 + 0.02), (w, 0.04, 0, d / 2 - 0.02),
                             (0.04, d, -w / 2 + 0.02, 0), (0.04, d, w / 2 - 0.02, 0)):
        b.box((sx, sy, h), (cx, cy, h / 2), deck_v)
    # tampo com furo oval: anel de quads entre a elipse e o retângulo
    rx, ry, segs = 0.92, 0.6, 64
    ox = 0.05
    for i in range(segs):
        quad = []
        for k in (i, i + 1):
            ang = 2 * math.pi * k / segs
            ex, ey = ox + rx * math.cos(ang), ry * math.sin(ang)
            dx, dy = math.cos(ang), math.sin(ang)
            tx = ((w / 2 if dx > 0 else -w / 2) - ox) / dx if abs(dx) > 1e-6 else 1e9
            ty = (d / 2 if dy > 0 else -d / 2) / dy if abs(dy) > 1e-6 else 1e9
            tt = min(tx, ty)
            quad.append(((ex, ey, h), (ox + dx * tt, dy * tt, h)))
        (e0, r0), (e1, r1) = quad
        b.quad([e0, r0, r1, e1], deck_top)
    # borda branca, paredes internas e fundo
    b.cylinder(1.0, 0.025, (ox, 0, h + 0.012), white, 48, scale=(rx + 0.07, ry + 0.07), caps=True)
    inner = b.cylinder(1.0, 0.45, (ox, 0, h - 0.2), white, 48, scale=(rx, ry), caps=False)
    for f in {f for v in inner for f in v.link_faces}:
        f.normal_flip()
    b.cylinder(1.0, 0.01, (ox, 0, h - 0.42), white, 48, scale=(rx - 0.05, ry - 0.05))
    b.cylinder(0.05, 0.03, (ox + 0.6, -ry - 0.1, h + 0.02), material("cromado"), 16)


def f_pole(b, it, w, d, h):
    b.cylinder(0.025, h, (0, 0, h / 2), material("cromado"), 16)


def f_cama(b, it, w, d, h):
    b.box((w, d, 0.3), (0, 0, 0.15), material("branco_laca"))
    b.box((w - 0.04, d - 0.06, 0.25), (0, 0.02, 0.42), material("lencol"))
    b.box((w + 0.12, d - 0.35, 0.08), (0, -0.2, 0.56), material("veludo_azul"))
    for e in (-1, 1):
        b.box((0.06, d - 0.35, 0.3), (e * (w / 2 + 0.06), -0.2, 0.4), material("veludo_azul"))
    for e in (-1, 1):
        b.box((0.65, 0.18, 0.4), (e * 0.37, d / 2 - 0.2, 0.72), material("travesseiro"), rot=0)
        b.box((0.55, 0.14, 0.32), (e * 0.37, d / 2 - 0.36, 0.66), material("veludo_azul"))
    b.box((w + 0.1, 0.08, 0.5), (0, d / 2 + 0.04, 0.95), material("couro_branco"))


def f_tapete(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("tapete_felpudo"))


def f_guarda_roupa(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("branco_laca"))
    for i in range(2):
        x = -w / 4 + i * w / 2
        b.box((w / 2 - 0.04, 0.012, h - 0.1), (x, -d / 2 - 0.006, h / 2), material("vidro_fosco"))


def f_cortina(b, it, w, d, h):
    b.box((w, d, h), (0, 0, h / 2), material("cortina"))


BUILDERS = {k[2:]: v for k, v in globals().items() if k.startswith("f_")}


def build_furniture(layout):
    colliders = []
    for it in layout["furniture"]:
        w, d, h = it["size"]
        b = Builder()
        BUILDERS[it["type"]](b, it, w, d, h)
        name = ("vidro_" if it["type"] == "vidro" else "") + "movel_" + it["id"]
        b.build(name, keep_uv=(it["type"] == "quadro"), transform=placement(it))
        if it.get("collide", True) and it.get("z", 0) < 1.0:
            m = placement(it)
            corners = [m @ Vector((sx * w / 2, sy * d / 2, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            colliders.append({"kind": "poly", "id": it["id"], "pts": [[round(c.x, 3), round(c.y, 3)] for c in corners]})
    return colliders


# --------------------------------------------------------------------- UVs

def world_box_uvs(ob):
    """UV0 por projeção cúbica em coordenadas do mundo, em metros / tamanho da textura."""
    if ob.get("keep_uv"):
        return
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers[0].data
    mw = ob.matrix_world
    tiles = [m.get("tile", 1.0) if m else 1.0 for m in me.materials]
    for poly in me.polygons:
        if ob.get("keep_uv"):
            continue
        n = (mw.to_3x3() @ poly.normal).normalized()
        ax = max(range(3), key=lambda i: abs(n[i]))
        tile = tiles[poly.material_index] if tiles else 1.0
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 2:
                u, v = co.x, co.y
            elif ax == 0:
                u, v = co.y * (1 if n.x > 0 else -1), co.z
            else:
                u, v = co.x * (-1 if n.y > 0 else 1), co.z
            uv[li].uv = (u / tile, v / tile)


def keep_uv_fix(ob):
    """Objetos com tela de quadro: só a tela mantém UV 0..1; o resto recebe projeção."""
    me = ob.data
    uv = me.uv_layers[0].data
    mw = ob.matrix_world
    for poly in me.polygons:
        mat = me.materials[poly.material_index]
        if mat and mat.name.startswith("quadro"):
            continue
        n = (mw.to_3x3() @ poly.normal).normalized()
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = (co.x, co.y) if ax == 2 else (co.y, co.z) if ax == 0 else (co.x, co.z)


def lightmap_uvs(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        if "lightmap" not in ob.data.uv_layers:
            ob.data.uv_layers.new(name="lightmap")
        ob.data.uv_layers.active = ob.data.uv_layers["lightmap"]
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    for ob in objs:
        ob.data.uv_layers.active = ob.data.uv_layers[0]
        ob.data.uv_layers[0].active_render = True


# --------------------------------------------------------------------- luz + bake

def setup_lighting(H):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("ceu")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    for attr, val in (("sky_type", "NISHITA"), ("sun_elevation", math.radians(38)),
                      ("sun_rotation", math.radians(200)), ("altitude", 40.0)):
        try:
            setattr(sky, attr, val)
        except (AttributeError, TypeError):
            pass
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.6
    sun = bpy.data.lights.new("sol", "SUN")
    sun.energy = 5.0
    sun.angle = math.radians(1.5)
    sun.color = (1.0, 0.96, 0.9)
    so = bpy.data.objects.new("sol", sun)
    scene.collection.objects.link(so)
    # sol vindo do mar (-y), um pouco de lado, entrando pelas janelas
    so.rotation_euler = (math.radians(58), 0, math.radians(20))


def add_interior_lights(layout, H):
    for room in layout["rooms"]:
        xs = [p[0] for p in room["polygon"]]
        ys = [p[1] for p in room["polygon"]]
        w, d = max(xs) - min(xs), max(ys) - min(ys)
        la = bpy.data.lights.new(f"luz_{room['id']}", "AREA")
        la.shape = "RECTANGLE"
        la.size, la.size_y = w * 0.7, d * 0.7
        la.energy = 9.0 * w * d
        la.color = (1.0, 0.92, 0.82)
        ob = bpy.data.objects.new(la.name, la)
        ob.location = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, H - 0.02)
        bpy.context.scene.collection.objects.link(ob)


def bake_lightmap(objs, size, samples, out_png, out_json):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 3
    img = bpy.data.images.new("lightmap", size, size, float_buffer=True)
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        node = m.node_tree.nodes.new("ShaderNodeTexImage")
        node.name = "BAKE_TARGET"
        node.image = img
        uvn = m.node_tree.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "lightmap"
        m.node_tree.links.new(uvn.outputs["UV"], node.inputs["Vector"])
        m.node_tree.nodes.active = node
    for ob in bpy.data.objects:
        if ob.name.startswith("vidro"):
            ob.hide_render = True
    # bake num único objeto (cópia unida): uma só passada do Cycles, bem mais rápido
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.duplicate()
    bpy.ops.object.join()
    proxy = bpy.context.view_layer.objects.active
    proxy.name = "BAKE_PROXY"
    # o Cycles grava o bake no mapa UV *ativo*
    proxy.data.uv_layers.active = proxy.data.uv_layers["lightmap"]
    for ob in objs:
        ob.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    proxy.select_set(True)
    bpy.context.view_layer.objects.active = proxy
    scene.render.bake.margin = 6
    scene.render.bake.use_pass_direct = True
    scene.render.bake.use_pass_indirect = True
    scene.render.bake.use_pass_color = False
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, margin=6, use_clear=True)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)[..., :3]
    # remover ruído: média ponderada só entre texels cobertos
    covered = (px.sum(-1) > 1e-6).astype(np.float32)
    px = denoise(px, covered)
    scale = float(np.percentile(px[covered > 0], 99.5)) or 1.0
    enc = srgb_encode(np.clip(px / scale, 0, 1))
    rgba = np.concatenate([enc, np.ones((size, size, 1), np.float32)], -1)
    out = bpy.data.images.new("lightmap_ldr", size, size)
    out.pixels = rgba.flatten()
    out.filepath_raw = str(out_png)
    out.file_format = "PNG"
    out.save()
    bpy.data.objects.remove(proxy, do_unlink=True)
    for ob in bpy.data.objects:
        ob.hide_render = False
    # o lightmap vai no GLB como "occlusion" (canal UV 1); o site o usa como lightMap
    out.source = "FILE"
    out.reload()
    group = gltf_output_group()
    for m in bpy.data.materials:
        nt = m.node_tree
        if nt is None:
            continue
        for n in [n for n in nt.nodes if n.name.startswith("BAKE_TARGET")]:
            n.image = out
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(n.outputs["Color"], sep.inputs["Color"])
            g = nt.nodes.new("ShaderNodeGroup")
            g.node_tree = group
            nt.links.new(sep.outputs["Red"], g.inputs["Occlusion"])
    return {"scale": scale, "encoding": "srgb"}


def gltf_output_group():
    """Grupo de nós que o exportador glTF do Blender reconhece para o canal de occlusion."""
    g = bpy.data.node_groups.get("glTF Material Output")
    if g is None:
        g = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        g.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return g


def srgb_encode(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def denoise(px, mask, radius=2, passes=2):
    for _ in range(passes):
        acc = np.zeros_like(px)
        wsum = np.zeros(mask.shape, np.float32)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                wgt = math.exp(-(dx * dx + dy * dy) / (radius * radius))
                m = np.roll(np.roll(mask, dy, 0), dx, 1) * wgt
                acc += np.roll(np.roll(px, dy, 0), dx, 1) * m[..., None]
                wsum += m
        px = np.where(mask[..., None] > 0, acc / np.maximum(wsum, 1e-6)[..., None], px)
    return px


# --------------------------------------------------------------------- main

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", action="store_true")
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--lm-size", type=int, default=2048)
    args = ap.parse_args(argv)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    layout = json.loads(LAYOUT.read_text())
    H = layout["meta"]["pe_direito"]

    colliders = build_walls(layout, H)
    build_floors_ceilings(layout, H)
    colliders += build_furniture(layout)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for ob in meshes:
        world_box_uvs(ob)
        if ob.get("keep_uv"):
            keep_uv_fix(ob)

    lm_info = None
    bake_objs = [o for o in meshes if not o.name.startswith("vidro")]
    if args.bake:
        lightmap_uvs(bake_objs)
        for ob in meshes:
            if "lightmap" not in ob.data.uv_layers:
                ob.data.uv_layers.new(name="lightmap")
            ob.data.uv_layers.active = ob.data.uv_layers[0]
        setup_lighting(H)
        add_interior_lights(layout, H)
        (WEB / "models").mkdir(parents=True, exist_ok=True)
        lm_info = bake_lightmap(bake_objs, args.lm_size, args.samples, ROOT / "blender" / "lightmap.png", None)
        print("lightmap", lm_info)

    (ROOT / "blender").mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender" / "apartamento.blend"))

    (WEB / "models").mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:
        ob.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(WEB / "models" / "apartamento_raw.glb"),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_lights=False,
        export_cameras=False,
    )

    xs = [p[0] for r in layout["rooms"] for p in r["polygon"]]
    ys = [p[1] for r in layout["rooms"] for p in r["polygon"]]
    scene_json = {
        "meta": layout["meta"],
        "bounds": [min(xs), min(ys), max(xs), max(ys)],
        "rooms": layout["rooms"],
        "hotspots": layout["hotspots"],
        "colliders": colliders,
        "lightmap": lm_info,
        "exposure": 0.5,
    }
    (WEB / "scene.json").write_text(json.dumps(scene_json, ensure_ascii=False, indent=1))
    print("ok: cena construída,", len(meshes), "objetos")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(argv)
