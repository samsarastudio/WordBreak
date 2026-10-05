# Environment and campaign implementation plan — 1.2.0

## Scope
Keep Metro Quake and add five offline campaign courses using existing car models, comic texture atlas, sky texture and modular geometry. Keep Aftershock Run as optional DLC. All campaign tracks remain selectable; completing a course exposes a next-level action and records the highest completed level.

## Course design
| Level | Course | Length / deadline | Identity | Challenge |
|---|---|---|---|---|
| 1 | Metro Quake | 2.6 km / 90 s | Warm metropolitan avenue | Existing baseline |
| 2 | Dockyard Domino | 2.4 km / 80 s | Teal warehouses, container stacks, cranes | Alternating tower falls and freight crossing |
| 3 | Foundry Run | 2.8 km / 85 s | Copper factories, elevated pipes, smokestacks | Two freight crossings and late fault jump |
| 4 | Canyon Fracture | 3.0 km / 86 s | Sandstone terraces and roadside buildings | Two boost gaps separated by recharge distance |
| 5 | Midnight Grid | 3.3 km / 90 s | Blue evening city, bright window grids | Dense alternating hazards and two trains |
| 6 | Last Light | 3.7 km / 95 s | Sunrise civic district, damaged skyline | 16 combined disasters and two fault jumps |

## Implementation
1. Extend track definitions with district, level, briefing and bounded curve/elevation variation. Generate persistent assets with a dedicated editor method (do not rerun project setup).
2. Resolve all bundled courses alongside DLC; preserve saved course selection. Add level/briefing UI and next-level navigation.
3. Add reusable architectural details and street furniture with district-specific placement. Merge static decorative boxes into 96 m chunks grouped by shared material to limit draw calls; retain collision bodies and animated hazards separately.
4. Add matching details to collapsing towers so attachments move with their parent. Keep ramp approaches free of new collision geometry.
5. Add themed key light, ambient/fog and sky tint. Improve the existing stylized shader with main-light color/shadow reception and softer tonal bands; preserve readable road markings.
6. Validate campaign geometry/spacing, increasing time pressure, selection and base-car completion. Capture representative real player views, check runtime exceptions, build Windows and export iOS, then publish version 1.2.0 and refresh the Codemagic branch.

## Acceptance
Five additional bundled courses, distinct visible scenarios, progressively tighter seconds/km, all routes completable with the base Cinder, functioning deadline collapse and existing ramps, no lost DLC or profile progress, no unsupported claim of on-device iOS performance. Adjust deadlines/hazard positions only from simulation evidence, preserving progression.
