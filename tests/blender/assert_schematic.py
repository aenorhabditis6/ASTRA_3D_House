import sys
from array import array
from pathlib import Path

import bpy


if "--" not in sys.argv:
    raise AssertionError("expected schematic PNG path after --")

path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
assert path.is_file(), path
assert path.stat().st_size > 10_000, path.stat().st_size

image = bpy.data.images.load(str(path), check_existing=False)
assert tuple(image.size) == (1600, 1200), tuple(image.size)

pixels = image.pixels
pixel_count = image.size[0] * image.size[1]
pixel_values = array("f", [0.0]) * len(pixels)
pixels.foreach_get(pixel_values)
step = max(1, pixel_count // 5000)
sampled = []
for pixel_index in range(0, pixel_count, step):
    base = pixel_index * 4
    sampled.append(
        tuple(round(float(pixel_values[base + channel]), 2) for channel in range(3))
    )

unique_colors = set(sampled)
assert len(unique_colors) >= 12, len(unique_colors)
assert any(max(color) - min(color) > 0.20 for color in unique_colors)
assert any(max(color) < 0.90 for color in unique_colors)

print(f"ASTRA_SCHEMATIC_OK={path}")
