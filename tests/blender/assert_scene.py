import bpy

expected_collections = {
    "STRUCTURE",
    "OPENINGS",
    "FIXTURES",
    "FURNITURE_PROXY",
    "PHOTO_REFERENCE",
    "APPEARANCE",
}
actual_collections = {collection.name for collection in bpy.data.collections}
assert expected_collections <= actual_collections, expected_collections - actual_collections
assert "STRUCTURE.floor" in bpy.data.objects
assert "STRUCTURE.ceiling" in bpy.data.objects
assert "OPENINGS.entry-door" in bpy.data.objects
assert "OPENINGS.window-west" in bpy.data.objects
assert "OPENINGS.window-east" in bpy.data.objects
assert "OPENINGS.window-north" not in bpy.data.objects
assert "FURNITURE_PROXY.bed-full" in bpy.data.objects
assert "FIXTURES.closet" in bpy.data.objects
assert abs(bpy.data.objects["STRUCTURE.ceiling"].location.z - 3.3528) < 1e-6
assert abs(bpy.data.objects["OPENINGS.window-west"].dimensions.x - 1.27) < 1e-6
assert abs(bpy.data.objects["OPENINGS.window-west"].dimensions.z - 1.78) < 1e-6
assert abs(bpy.data.objects["OPENINGS.window-west"].location.z - 1.66) < 1e-6
assert abs(bpy.data.objects["FURNITURE_PROXY.bed-full"].dimensions.x - 2.13) < 1e-6
assert abs(bpy.data.objects["FURNITURE_PROXY.bed-full"].dimensions.y - 1.45) < 1e-6
assert abs(bpy.data.objects["OPENINGS.entry-door"].dimensions.x - 1.0) < 1e-6
assert (
    bpy.data.objects["OPENINGS.window-west"]["height_source_kind"]
    == "confirmed_measurement"
)
assert bpy.context.scene.unit_settings.system == "METRIC"
assert abs(bpy.context.scene.unit_settings.scale_length - 1.0) < 1e-9
