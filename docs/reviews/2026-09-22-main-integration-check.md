# Main integration check

Checked on 2026-09-22 against feature commit `8ee36d2` and fetched main
`b4c4e3d`. Main is an ancestor of the feature branch; a fast-forward preserves
all original commits and their author attribution. No history rewrite is needed.

## Fresh verification

- Python: 85 tests run, 84 passed, one explicitly skipped acceptance test for
  the known infeasible original 24/48 route.
- Node event/storage regressions: 8 passed.
- Existing Playwright browser suite: 39 passed, including Chinese switching,
  persistence, exports, full-route traversal and responsive screenshot baselines.
- Blender 5.2.2 LTS: rebuilt the logical scene, GLB and colored schematic into
  the ignored `build/merge-verification` directory. All three independent
  `tests/blender/assert_*.py` checks passed with `--python-exit-code 1`.
- Removed two extra EOF blank lines identified by the integration diff check.
- Updated the README source-branch pointer for integration into main.

The browser tests required local listening ports outside the restricted sandbox.
Blender reports non-fatal `use_nodes` deprecation warnings for a future 6.0 API.
No screenshot baselines, capture routes, geometry tolerances or test expectations
were changed for this integration.

## Unchanged limitations

Integration is not field-release approval. The original 24/48 route remains
blocked, the separate 32/64 candidate remains unapproved with 13/27 warnings,
and the Xiaomi field-test matrix remains unrun. See the existing implementation
status and route-geometry blocker reports. Pages continues to serve its separate
generated-artifact branch; merging source does not change the live site's data
or its origin-local capture progress.
