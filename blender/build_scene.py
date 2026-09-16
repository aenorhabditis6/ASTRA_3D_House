"""Build the deterministic logical-room Blender scene and GLB export."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import bpy

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


def _arguments() -> tuple[Path, Path, Path]:
    if "--" not in sys.argv:
        raise ValueError(
            "usage: blender ... -- <room.json> <house_master.blend> <house.glb>"
        )
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 3:
        raise ValueError(
            "expected exactly three arguments: room.json, output.blend, output.glb"
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
    return material


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


def build_scene(room_path: Path, blend_path: Path, glb_path: Path) -> None:
    """Build, save, and export a logical scene from a validated room file."""
    room_path = Path(room_path).resolve()
    blend_path = Path(blend_path).resolve()
    glb_path = Path(glb_path).resolve()

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
        "structure": _material("MAT.structure", (0.72, 0.74, 0.78, 1.0)),
        "fixture": _material("MAT.fixture", (0.58, 0.62, 0.68, 1.0)),
        "proxy": _material("MAT.proxy", (0.31, 0.52, 0.76, 1.0)),
        "opening": _material("MAT.opening", (0.26, 0.72, 0.78, 1.0)),
    }

    for spec in wall_boxes:
        obj = _create_box(spec, collections[spec.collection], materials["structure"])
        geometry_source, height_source = _source_for_structure(room, spec.source_id)
        _set_properties(obj, room, geometry_source, height_source, spec.id)

    for spec in (floor_spec, ceiling_spec):
        obj = _create_polygon(spec, collections[spec.collection], materials["structure"])
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
        material = materials["fixture"] if collection_name == "FIXTURES" else materials["proxy"]
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


def main() -> None:
    room_path, blend_path, glb_path = _arguments()
    build_scene(room_path, blend_path, glb_path)
    print(f"ASTRA_BLEND={blend_path}")
    print(f"ASTRA_GLB={glb_path}")


if __name__ == "__main__":
    main()
