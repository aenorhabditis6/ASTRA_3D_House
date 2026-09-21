"""Build the deterministic logical-room Blender scene and GLB export."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import bpy
from mathutils import Vector

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from astra_house.geometry import (  # noqa: E402
    BoxSpec,
    PolygonSpec,
    build_ceiling_spec,
    build_floor_spec,
    build_opening_boxes,
    build_wall_boxes,
)
from astra_house.io import load_room  # noqa: E402
from astra_house.model import RoomModel, SourceRef  # noqa: E402

if TYPE_CHECKING:
    from bpy.types import Collection, Material, Object

COLLECTION_NAMES = (
    "STRUCTURE",
    "OPENINGS",
    "FIXTURES",
    "FURNITURE_PROXY",
    "PHOTO_REFERENCE",
    "APPEARANCE",
)


def _arguments() -> tuple[Path, Path, Path, Path]:
    if "--" not in sys.argv:
        raise ValueError(
            "usage: blender ... -- <room.json> <house_master.blend> <house.glb> "
            "<schematic.png>"
        )
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 4:
        raise ValueError(
            "expected exactly four arguments: room.json, output.blend, output.glb, "
            "schematic.png"
        )
    return tuple(_repository_path(value) for value in arguments)  # type: ignore[return-value]


def _repository_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPOSITORY_ROOT / path).resolve()


def _clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)


def _create_collections() -> dict[str, "Collection"]:
    collections = {}
    root = bpy.context.scene.collection
    for name in COLLECTION_NAMES:
        collection = bpy.data.collections.new(name)
        root.children.link(collection)
        collections[name] = collection
    return collections


def _material(name: str, color: tuple[float, float, float, float]) -> "Material":
    material = bpy.data.materials.new(name=name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = 0.72
    return material


def _look_at(obj: "Object", target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _configure_schematic(
    room: RoomModel,
    collections: dict[str, "Collection"],
    schematic_path: Path,
) -> None:
    """Create a reusable axonometric camera and deterministic presentation rig."""
    scene = bpy.context.scene
    points = room.floor_polygon
    minimum_x = min(point.x for point in points)
    maximum_x = max(point.x for point in points)
    minimum_y = min(point.y for point in points)
    maximum_y = max(point.y for point in points)
    center_x = (minimum_x + maximum_x) / 2.0
    center_y = (minimum_y + maximum_y) / 2.0
    span = max(maximum_x - minimum_x, maximum_y - minimum_y)

    camera_data = bpy.data.cameras.new("CAMERA.axonometric")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span * 1.42
    camera = bpy.data.objects.new("APPEARANCE.camera-axonometric", camera_data)
    collections["APPEARANCE"].objects.link(camera)
    camera.location = (
        center_x - span * 1.35,
        center_y - span * 1.45,
        room.ceiling_height_m + span * 1.08,
    )
    _look_at(camera, (center_x, center_y, room.ceiling_height_m * 0.30))
    camera_data.lens = 50.0
    scene.camera = camera

    sun_data = bpy.data.lights.new("LIGHT.sun-soft", type="SUN")
    sun_data.energy = 2.0
    sun_data.angle = 0.35
    sun = bpy.data.objects.new("APPEARANCE.sun-soft", sun_data)
    collections["APPEARANCE"].objects.link(sun)
    sun.rotation_euler = (0.55, -0.35, -0.55)

    area_data = bpy.data.lights.new("LIGHT.area-key", type="AREA")
    area_data.energy = 900.0
    area_data.shape = "DISK"
    area_data.size = span * 1.2
    area = bpy.data.objects.new("APPEARANCE.area-key", area_data)
    collections["APPEARANCE"].objects.link(area)
    area.location = (
        center_x - span * 0.25,
        center_y - span * 0.4,
        room.ceiling_height_m + span * 0.95,
    )
    _look_at(area, (center_x, center_y, 0.0))

    world = bpy.data.worlds.new("WORLD.schematic")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.96, 0.97, 0.98, 1.0)
        background.inputs["Strength"].default_value = 0.75
    scene.world = world

    # The source model remains complete. Only the render omits the ceiling and
    # camera-facing boundary, producing a conventional dollhouse cutaway.
    bpy.data.objects["STRUCTURE.ceiling"].hide_render = True
    camera_direction = Vector(
        (camera.location.x - center_x, camera.location.y - center_y)
    )
    hidden_wall_ids = {
        wall.id
        for wall in room.walls
        if Vector(
            (
                (wall.start.x + wall.end.x) / 2.0 - center_x,
                (wall.start.y + wall.end.y) / 2.0 - center_y,
            )
        ).dot(camera_direction)
        > 0.0
    }
    for obj in collections["STRUCTURE"].objects:
        semantic_id = str(obj.get("semantic_id", ""))
        if any(semantic_id.startswith(f"{wall_id}:") for wall_id in hidden_wall_ids):
            obj.hide_render = True
    openings_by_id = {opening.id: opening for opening in room.openings}
    for obj in collections["OPENINGS"].objects:
        opening = openings_by_id[str(obj.get("semantic_id"))]
        if opening.wall_id in hidden_wall_ids:
            obj.hide_render = True

    schematic_path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.filepath = str(schematic_path)
    scene.render.image_settings.color_management = "FOLLOW_SCENE"
    scene.render.use_file_extension = True
    scene["schematic_kind"] = "orthographic_dollhouse"
    scene["schematic_resolution"] = "1600x1200"


def _create_box(
    spec: BoxSpec,
    collection: "Collection",
    material: "Material",
) -> "Object":
    half_x = spec.size.x / 2.0
    half_y = spec.size.y / 2.0
    half_z = spec.size.z / 2.0
    vertices = [
        (-half_x, -half_y, -half_z),
        (half_x, -half_y, -half_z),
        (half_x, half_y, -half_z),
        (-half_x, half_y, -half_z),
        (-half_x, -half_y, half_z),
        (half_x, -half_y, half_z),
        (half_x, half_y, half_z),
        (-half_x, half_y, half_z),
    ]
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    mesh = bpy.data.meshes.new(f"MESH.{spec.collection}.{spec.id}")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"{spec.collection}.{spec.id}", mesh)
    collection.objects.link(obj)
    obj.location = (spec.center.x, spec.center.y, spec.center.z)
    obj.rotation_euler = (0.0, 0.0, spec.yaw_rad)
    obj.data.materials.append(material)
    return obj


def _create_polygon(
    spec: PolygonSpec,
    collection: "Collection",
    material: "Material",
) -> "Object":
    base_z = spec.vertices[0].z
    vertices = [(point.x, point.y, point.z - base_z) for point in spec.vertices]
    mesh = bpy.data.meshes.new(f"MESH.{spec.collection}.{spec.id}")
    mesh.from_pydata(vertices, [], [tuple(range(len(vertices)))])
    mesh.update()
    obj = bpy.data.objects.new(f"{spec.collection}.{spec.id}", mesh)
    collection.objects.link(obj)
    obj.location.z = base_z
    obj.data.materials.append(material)
    return obj


def _set_properties(
    obj: "Object",
    room: RoomModel,
    geometry_source: SourceRef,
    height_source: SourceRef,
    semantic_id: str,
) -> None:
    obj["room_id"] = room.room_id
    obj["schema_version"] = room.schema_version
    obj["semantic_id"] = semantic_id
    obj["geometry_source_kind"] = geometry_source.kind
    obj["geometry_source_confidence"] = geometry_source.confidence
    obj["height_source_kind"] = height_source.kind
    obj["height_source_confidence"] = height_source.confidence


def _source_for_structure(
    room: RoomModel, source_id: str
) -> tuple[SourceRef, SourceRef]:
    walls = {wall.id: wall for wall in room.walls}
    openings = {opening.id: opening for opening in room.openings}
    if source_id in walls:
        return walls[source_id].geometry_source, room.ceiling_height_source
    opening = openings[source_id]
    return opening.position_source, opening.vertical_source


def build_scene(
    room_path: Path,
    blend_path: Path,
    glb_path: Path,
    schematic_path: Path,
) -> None:
    """Build, save, and export a logical scene from a validated room file."""
    room_path = Path(room_path).resolve()
    blend_path = Path(blend_path).resolve()
    glb_path = Path(glb_path).resolve()
    schematic_path = Path(schematic_path).resolve()

    # Validate every input and derive all geometry before touching output files.
    room = load_room(room_path)
    wall_boxes = build_wall_boxes(room)
    opening_boxes = build_opening_boxes(room)
    floor_spec = build_floor_spec(room)
    ceiling_spec = build_ceiling_spec(room)

    _clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    collections = _create_collections()
    materials = {
        "wall": _material("MAT.wall-warm-white", (0.82, 0.80, 0.75, 1.0)),
        "floor": _material("MAT.floor-light-gray", (0.67, 0.70, 0.73, 1.0)),
        "bed": _material("MAT.bed-blue", (0.18, 0.42, 0.82, 1.0)),
        "work": _material("MAT.work-orange", (0.94, 0.42, 0.14, 1.0)),
        "storage": _material("MAT.storage-yellow", (0.92, 0.65, 0.12, 1.0)),
        "opening": _material("MAT.opening-cyan", (0.12, 0.68, 0.78, 1.0)),
    }

    for spec in wall_boxes:
        obj = _create_box(spec, collections[spec.collection], materials["wall"])
        geometry_source, height_source = _source_for_structure(room, spec.source_id)
        _set_properties(obj, room, geometry_source, height_source, spec.id)

    for spec in (floor_spec, ceiling_spec):
        material = materials["floor"] if spec.id == "floor" else materials["wall"]
        obj = _create_polygon(spec, collections[spec.collection], material)
        _set_properties(
            obj,
            room,
            room.provenance[0],
            room.ceiling_height_source,
            spec.id,
        )

    openings_by_id = {opening.id: opening for opening in room.openings}
    for spec in opening_boxes:
        obj = _create_box(spec, collections[spec.collection], materials["opening"])
        opening = openings_by_id[spec.id]
        _set_properties(
            obj,
            room,
            opening.position_source,
            opening.vertical_source,
            spec.id,
        )

    for proxy in room.proxies:
        collection_name = (
            "FIXTURES" if proxy.kind == "fixed_closet" else "FURNITURE_PROXY"
        )
        spec = BoxSpec(
            id=proxy.id,
            center=proxy.center,
            size=proxy.size,
            yaw_rad=proxy.yaw_rad,
            collection=collection_name,
            source_id=proxy.id,
        )
        if proxy.kind == "bed":
            material = materials["bed"]
        elif proxy.kind in {"desk", "chair"}:
            material = materials["work"]
        else:
            material = materials["storage"]
        obj = _create_box(spec, collections[collection_name], material)
        _set_properties(
            obj,
            room,
            proxy.footprint_source,
            proxy.height_source,
            proxy.id,
        )

    scene["room_id"] = room.room_id
    scene["schema_version"] = room.schema_version
    scene["generator"] = "astra_house logical-room MVP"
    _configure_schematic(room, collections, schematic_path)

    blend_path.parent.mkdir(parents=True, exist_ok=True)
    glb_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        export_apply=True,
        export_cameras=False,
        export_lights=False,
    )
    bpy.ops.render.render(write_still=True)


def main() -> None:
    room_path, blend_path, glb_path, schematic_path = _arguments()
    build_scene(room_path, blend_path, glb_path, schematic_path)
    print(f"ASTRA_BLEND={blend_path}")
    print(f"ASTRA_GLB={glb_path}")
    print(f"ASTRA_SCHEMATIC={schematic_path}")


if __name__ == "__main__":
    main()
