# Capture route geometry blockers

Date: 2026-09-21. Status: route revision required; neither supplied route is publishable.

The analyzer is implemented, but the requirement to obtain zero errors by editing
only aim/framing coordinates is mathematically incompatible with the frozen
stations and targets. The source capture plan, camera profile, station coordinates,
shot counts, target IDs, instructions, and schema-1.0 migration fixture are unchanged.

## Aim-independent infeasibility proof

The camera's reviewed horizontal field is 70 degrees, with a 5-degree margin at
each edge: **60 degrees usable**. An aim point rotates this interval; it cannot
make the interval wider.

At S01 = (1.35, 1.65), the north wall `wall-05` runs from
(0, 1.2693861863) to (0, 4.2266375213). Its possible bearings occupy the arc
117.6518 degrees through 180 degrees to -164.2549 degrees. The entry door on
`wall-04` runs from (1.3713807875, 1.2693861863) to
(2.3713807875, 1.2693861863), with bearings -86.7848 to -20.4377 degrees.
The smallest gap between these two arcs is:

`-86.7848177841 - (-164.2549365528) = 77.4701187687 degrees`.

Thus even ONE selected point on each target needs at least 77.47 degrees. This
blocks `lite-24/L01-A` and the frozen `standard-48/C04-A` for every aim point.
The 1 cm geometric membership tolerance cannot close a 17.47-degree deficit:
the maximum endpoint angular relaxation is less than 2 degrees. Replacing full
target extents with convenient landmarks cannot solve this pair.

An additional necessary-condition audit projected each target's convex horizontal
geometry into a circular angular interval, then found the narrowest circular
interval intersecting every declared target interval. This deliberately ignores
LOS, vertical FOV, and required full extents, so the following are lower bounds:

| Mode | Shots | Station | Minimum nominal span |
| --- | --- | --- | ---: |
| lite-24 | L01-A | S01 | 77.47° |
| lite-24 | L02-A | S02 | 71.05° |
| lite-24 | L03-A | S03 | 63.77° |
| lite-24 | L07-A, L10-A, L10-B | S07 | 80.49° |
| standard-48 | C04-A | S01 | 77.47° |

Full double-window framing independently needs these spans between x=0.79 and
x=3.82 on y=4.2266375213:

| Station | Minimum full-window span | Relevant shots |
| --- | ---: | --- |
| S05 | 70.46° | D03, L05-A |
| S06 | 93.30° | D02, L11-A |
| S07 | 84.19° | D01, L07-A, L10-A, L10-B |

These measurements use room coordinates and `atan2`, then decimal half-up
quantization to 0.01 degrees. The standard instructions explicitly request both
windows with surrounding wall, and C04-A requests the entry door and north-wall
connection. These constraints cannot be satisfied by shrinking the framing data.

## Diagnostics on the unchanged source

The corrected analyzer reports 48 errors and 18 warnings for lite-24, and 72
errors and 20 warnings for standard-48. Counts include cascading anchor-baseline
errors because invisible anchor landmarks cannot earn station credit.

| Category | lite-24 | standard-48 |
| --- | ---: | ---: |
| E_HORIZONTAL_FOV | 24 | 47 |
| E_VERTICAL_FOV | 18 | 17 |
| E_LOS_OUTSIDE_ROOM | 0 | 1 |
| E_ANCHOR_BASELINE | 6 | 7 |

All lite shots fail horizontal framing. All standard shots except A03-L fail
horizontal framing with the current explicit landmarks. Many whole-wall endpoint
requirements can be corrected by choosing meaningful local wall landmarks, but
the lower-bound examples above cannot.

Vertical errors: lite L01-A, L02-A, L03-A/B, L04-A/B, L05-A/B, L07-A,
L08-B, L09-A/B, L10-A/B, L11-A, L12-A, L13-A, L14-A; standard B01-U,
C01-A/B, C02-A/B, C03-A/B, C04-A/B, D01–D08. Every explicitly declared 3D
landmark is checked at both camera-height extremes. The interrupted implementation
incorrectly skipped all level-shot vertical checks whenever any landmark was at
1.45 m, and skipped non-ceiling/non-floor points in pitched shots.

A02-R has a framing-point LOS across the room notch. Lite anchor-baseline failures
affect both windows, entry door, bathroom door, bed, and desk; standard affects
all seven anchors. Both modes retain visible floor-seam and wall-redundancy
warnings, including the required lite `W_WALL_REDUNDANCY:wall-03`.

## Decisions needed to correct the routes

1. Prioritize geometric feasibility: move relevant stations and/or split framing
   into additional photographs, revising counts and the frozen migration contract
   explicitly. Full-window spans alone require substantially more distance.
2. Retain the 24/48 counts: redistribute target combinations between photographs
   and revise instructions, allowing the standard target/instruction migration
   contract to change. Some shots can show one window or door context while
   another covers the adjacent wall; the complete route must still meet anchor
   baseline requirements.

Both choices require a reviewed source revision and a fresh geometry/hash/warning
review. Neither is implemented without the user's route decision. Raising the FOV,
shrinking margins, suppressing errors, or deleting required landmark extents would
not establish feasibility. Real Xiaomi device/FOV validation remains required
after the route is corrected.

## Verification and mathematical corrections

- Geometry tests: 25 run, 24 passed, one explicitly skipped acceptance for the
  unresolved real-route zero-error condition.
- Combined domain/geometry: 51 run, 50 passed, the same single blocked acceptance.
- Other model/geometry/measurement/manifest/plan/review tests: 16 passed.
- A synthetic two-station full-window survey has zero errors and a 1.0 m anchor
  baseline. It is test data only and does not replace either project route.
- Boundary intersection partitioning now accepts a tangent touch and rejects a
  true notch crossing. The brief's (1,1)→(3,3) notch example only touches the
  reflex vertex (2,2); it is inside/on throughout and must be accepted by the
  specified midpoint algorithm. The actual crossing regression uses (1,1)→(3,4).
- Wall intervals split at reflex-vertex visibility transitions. Floor and ceiling
  seam spans split analytically at vertical-FOV circle intersections and union
  overlapping shots. Ceiling spans are advisory metrics only.
- Adjacency includes the S08→S01 return leg and follows first station visits.
  Vertical-overlap warnings require compatible horizontal bearings. Derived
  distances and angles use decimal half-up quantization before threshold checks.
- Canonical mode hashes isolate modes and exclude coverage-review records.

The full application suite was also attempted during concurrent packaging work;
the latest observed run had 75 tests, with one failure and one error in legacy
pack/CLI success expectations because the new release gate correctly rejects the
unchanged invalid project. Integration-test updates are owned by the controller.
