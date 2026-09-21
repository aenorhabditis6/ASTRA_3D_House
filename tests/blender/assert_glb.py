import bpy
import sys

glb_path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_path)
names = {obj.name for obj in bpy.data.objects if obj.type == "MESH"}
assert "STRUCTURE.floor" in names
assert "OPENINGS.entry-door" in names
assert "OPENINGS.window-west" in names
assert "OPENINGS.window-east" in names
assert "OPENINGS.window-north" not in names
assert "FURNITURE_PROXY.bed-full" in names
assert len(names) >= 10
