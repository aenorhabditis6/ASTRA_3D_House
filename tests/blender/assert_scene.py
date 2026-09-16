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
assert "FURNITURE_PROXY.bed-full" in bpy.data.objects
assert "FIXTURES.closet" in bpy.data.objects
assert abs(bpy.data.objects["STRUCTURE.ceiling"].location.z - 3.3528) < 1e-6
assert bpy.context.scene.unit_settings.system == "METRIC"
assert abs(bpy.context.scene.unit_settings.scale_length - 1.0) < 1e-9
