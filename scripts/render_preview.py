"""Renderiza prévias rápidas (Cycles) de blender/apartamento.blend, sem tetos.

    python scripts/render_preview.py -- saida_dir [amostras]
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
out = Path(argv[0] if argv else ROOT / "preview")
samples = int(argv[1]) if len(argv) > 1 else 16
out.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(ROOT / "blender" / "apartamento.blend"))
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = samples
scene.cycles.use_denoising = False
scene.render.resolution_x, scene.render.resolution_y = 1200, 800

for ob in bpy.data.objects:
    if ob.name.startswith("teto"):
        ob.hide_render = True

if not any(o.type == "LIGHT" for o in bpy.data.objects):
    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sun.data.energy = 3
    sun.rotation_euler = (math.radians(40), 0, math.radians(20))
    scene.collection.objects.link(sun)
if scene.world is None:
    scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam

shots = {
    "dollhouse": ((5.6, -7.5, 13.0), (5.6, 4.2, 0.0), 35),
    "dollhouse_norte": ((5.6, 17.0, 12.0), (5.6, 4.2, 0.0), 35),
    "sala": ((3.9, 6.3, 1.6), (1.4, 0.4, 1.1), 22),
    "spa": ((6.9, 4.8, 1.6), (5.6, 0.6, 0.9), 22),
    "suite": ((8.2, 4.6, 1.6), (10.6, 1.2, 0.9), 22),
    "cozinha": ((5.4, 7.0, 1.6), (6.4, 9.4, 1.1), 18),
}
only = argv[2].split(",") if len(argv) > 2 else list(shots)
for name in only:
    pos, look, lens = shots[name]
    cam.location = pos
    d = Vector(look) - Vector(pos)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    scene.render.filepath = str(out / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("ok", name)
