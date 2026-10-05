# Verification report

Environment: Windows workstation, Unity 6000.2.6f2, URP 17.2.0, development Windows player at 1280×720. This report does not substitute for phone profiling.

- Unity edit-mode run: 6 tests passed, 0 failed. Simulation completion, deterministic bots, invalid input, boost bounds and atomic/capped spending covered by project tests.
- TypeScript backend: 3 tests passed, 0 failed. Curated fallback length, unsafe output rejection, and unavailable-Ollama fallback covered.
- Windows single-player smoke: completed Metro Quake in 64.47 seconds without steering/boost assistance, displayed results, and saved rewards. Actual renderer screenshots are under Screenshots.
- A runtime-only shader-stripping failure was found and fixed by explicit shader inclusion.
- An initial LAN snapshot exceeded the transport's unreliable-message limit. Replaced the JSON payload with compact binary state.
- Final LAN run: one headless Windows server, two independent clients, four AI backfill slots. Both clients finished. Slot 0 reported 64.43273 seconds on both server and client; slot 1 reported 63.13275 seconds. No managed exceptions in the final run. Headless use of the graphical Windows player produces unsupported-shader warnings; a purpose-built Linux server remains outstanding.
- Final solo run: landscape=true; profile saved version 2 with 495 credits, 100 XP and one completed race. Test saves are isolated by process ID.
- Live chat endpoint returned HTTP success with `source: fallback` while Ollama was disabled. Gameplay also completed with the entire chat backend absent.
- Android builds succeeded using the installed editor toolchain: initial Mono/ARMv7 and final IL2CPP/ARM64. The final APK is `Builds/Android/WorldBreakRush.apk`; the older-device test build is `WorldBreakRush-armv7.apk`. Manifest/package checks confirm com.worldbreak.rush, landscape orientation, minimum API 26 and the intended native architecture. No Android device was connected, so installation, touch interaction and mobile performance remain unverified.

Not measured: mobile FPS, 10-minute thermal behavior, device memory, battery usage, 80–250 ms latency, packet loss, iOS behavior. No claim of meeting those acceptance targets is made.

## Kenney car replacement — 2026-10-03

Replaced the active original car mesh with six CC0 Kenney Car Kit models. Each adapted car has 2,032–2,474 triangles and 13–17 palette materials; the original geometry is preserved and normalized to a 4.2 m length. The initial atlas conversion produced excessive materials and partial body repainting; a hue-based body mask and quantized trim palette corrected both before delivery. Import validation requires a paint material and caps palette materials at 24.

The Windows build compiles with the replacements. A full solo race completed and saved its rewards without managed exceptions (`WB_SMOKE_PASS`, landscape=true). Garage and race screenshots in `Screenshots/kenney-*.png` show the actual renderer; body alignment, forward orientation, wheel placement, distinct opponent silhouettes and preserved trim were inspected. Handling, race authority and network messages are unchanged. Physical Android testing remains outstanding.

The final ARM64 Android APK was rebuilt successfully with the corrected palette and six replacement models. The pre-replacement ARMv7 APK was moved to `Builds/Archive/WorldBreakRush-before-Kenney-armv7.apk` to keep it separate from current builds.

## Physical collision and disaster pass — 2026-10-03

- Unity EditMode: 10 tests passed, 0 failed (9 project tests plus 1 dependency test). New coverage verifies high-speed chassis sweeps against thin obstacles, horizontal escape from an overlapping train body, breakable cargo removal and low-speed cargo contact.
- A full solo race completed with the new solid course (`WB_SMOKE_PASS`, landscape=true), using the automated driver. This supersedes the earlier straight-line smoke scenario.
- The dedicated runtime scenarios passed (`WB_DESTRUCTION_PASS`): cargo destruction, a train collision, 10 effect bursts and restoration on replay. The rendered train-crossing capture shows the vehicle stopped at 0 km/h against moving carriages, with lowered crossing gates. Screenshots `impact-train.png`, `impact-road.png`, `impact-cargo.png` and `destruction-race.png` document the actual renderer.
- Fixed an initially disabled query collider that prevented penetration resolution for a stationary car. Added horizontal escape selection so lane-constrained cars cannot resolve contact by moving vertically.
- Cosmetic debris is bounded to 72 physical fragments and 360 mesh particles. This is a pool limit, not a measured mobile performance guarantee. Vehicles still use arcade path movement and authored collision volumes; arbitrary mesh fracture and vehicle body deformation remain future work.
- Updated LAN verification: both independent clients finished (62.43276 s and 63.53274 s). Slot 0 matched the server finish time exactly; server and both clients reported destruction mask 65471 and 11 local impact events. No managed exceptions or snapshot overflow occurred. Headless graphical-shader warnings remain expected for this Windows server mode.
- Final Windows and Android builds succeeded. APK badging confirms com.worldbreak.rush, ARM64, minimum API 26 and landscape orientation. Android physical-device testing remains outstanding.

## Comic art, cascading towers and fault jump — 2026-10-03

- EditMode suite: 14 passed, 0 failed (13 project tests and 1 dependency test). Four new jump tests cover successful boost-speed clearance, failure at normal speed, missing the ramp, and checkpoint/energy recovery.
- First complete solo run with the expanded course and atlas passed. Six collapse zones now animate 24 towers, with staggered debris bursts. The fault jump uses a shared 72 m gap, 24 m ramp, 4.5 m lip and authoritative ballistic flight.
- Dedicated standalone jump test passed: an unboosted attempt misses, checkpoint recovery completes, and a boosted attempt becomes airborne and lands successfully. Actual runtime screenshots are fault-missed.png, fault-airborne.png and fault-landed.png. The airborne capture shows the open fault, car above the abyss, sinking road slabs and printed storm sky.
- AI-generated facade/concrete/asphalt/paper atlas and storm panorama are stored unchanged in Assets/WB/Art/Textures. The built-in generation tool and exact prompts are documented in AI_TEXTURES.md. Textures are referenced by the theme/sky material and included in builds.
- Visual inspection confirmed working textures, halftone, ink silhouettes, boost streaks and clear HUD text. Removed primitive edge ink from asphalt to reduce the previous artificial road grid.
- Full final-art solo run passed. LAN server and both clients also finished: 61.93277 s and 62.23276 s, both reporting one successful fault jump. Slot 0 matched the server finish time, destruction mask and impact count. No managed exceptions or network-buffer overflow were logged.
- Visual review found cargo in the new chasm; it was relocated beyond the landing, and additional edge-debris bursts were added. The focused runtime jump scenario was rerun after this correction.
- Final corrected Windows and Android IL2CPP/ARM64 builds succeeded. The post-correction solo run and focused jump scenario passed. APK validation confirms the package, ARM64 architecture and landscape feature. Physical Android touch/performance testing remains outstanding.

## Vehicle spinouts — 2026-10-04

- EditMode suite: 21 passed, 0 failed. New cases cover rear-quarter attacks from either side, centered bumps, harmless parallel rubbing, airborne immunity, repeat-hit protection, and faster countersteer recovery.
- Standalone contact scenario passed: actual movement into another chassis triggered one victim spin and one attacker credit, visibly turned the victim sideways, reduced speed, emitted skid smoke and recovered automatically. Screenshot: Screenshots/combat-spinout.png.
- The player and opponents share the same contact rules. This remains an arcade contact/yaw model rather than tire/suspension physics. Countersteering shortens the loss of control; cooldown prevents repeated overlap from continuously restarting a spin.
- Tools/Test-Lan.ps1 -Combat enables an explicit development-only replication probe. The server stages a valid rear-quarter contact through VehicleCombat; server and clients must observe rotation, attacker credit and recovery. This supplements the standalone physical-contact test.
- Controlled multiplayer replication passed on the server and both independent clients: rotation, attacker credit and recovery were all observed (WB_COMBAT_NET_PASS).
- Full solo race passed. Both LAN clients finished and cleared the fault jump after combat; slot 0 matched the server at 61.93277 s with one credited spinout. Slot 1 finished at 63.59941 s after being spun once. No managed exceptions were logged.
- Final Windows and Android IL2CPP/ARM64 builds succeeded; APK badging confirms ARM64 and landscape. Physical Android testing remains outstanding.

## Throttle, drift and AI spin revision — 2026-10-04

- 27 EditMode tests passed, 0 failed. Added throttle/idle/brake tests, drift momentum/charge/exit-boost tests, countersteer direction, actual AI opponent contact, and fast hits on stopped opponents.
- The contact gate previously required lateral closing speed, excluding many offset rear impacts. It now accepts either meaningful lateral contact or a faster rear-corner hit. Bot reaction is delayed during the initial spin phase; stronger yaw and lateral impulse make the result visible. The standalone combat harness now explicitly keeps the victim AI-controlled rather than staging a second human slot.
- Standalone AI contact scenario passed (AI victim=True), including spinout credit and recovery. The handling scenario passed idle, accelerate, visible drift, exit boost and full braking. Screenshots: ai-combat-spinout.png and handling-drift.png.
- W/Up and the touch ACCELERATE button apply throttle; S/Down and BRAKE decelerate. Releasing throttle coasts. Space/DRIFT builds a controlled slide, preserves most speed and charges an exit boost. Shift/BOOST remains available. Impact shoves, chassis lean and a small cosmetic impact hop exaggerate the arcade response.
- The regression launcher hit a transient Unity project-lock error once; the subsequent isolated test run completed successfully with the results above.
- Full solo race and fault-jump regression passed. The multiplayer probe initially inherited natural combat cooldowns; resetting its staged participants before injection isolated the snapshot check. Spin rotation, credit and recovery then passed on the server and both clients; drift angle, charge and exit boost also passed on all three.
- Final LAN race: slot 0 matched the server at 67.99934 s, 14 impacts, one jump, three spins and three takedowns. Slot 1 finished at 70.43264 s with one jump, four spins and one takedown. No managed exceptions were logged.
- Final Windows and Android builds succeeded. APK badging confirms ARM64 and landscape. Touch layout was inspected in the Windows capture; physical Android playtesting remains outstanding.

## Train jumps, countdown collapse and finish cinematics — 2026-10-04

- 41 EditMode tests passed with zero failures. New coverage includes both train ramps clearing the carriage roof, center-lane bypass, slow-motion activation, a clamped deadline with locked input, moving finish drift, finish-time ranking and camera orbit/reset.
- The standalone setpiece test passed actual train clearance and landing, slow motion, a moving finish drift, one-time rewards, time-up input lock, no failure reward, and clean restart. The collapse transformed 3,444 scenery pieces. Captures are in `Documentation/Screenshots/setpiece-*.png`.
- The first runtime test exposed a pending car-catalog update rebuilding the world on the new failure screen. Catalog application now defers throughout race, results and failure presentation. The repeated runtime check passed with the clock held at 90 and the destroyed world retained.
- A dedicated server and two clients all passed the staged network probe: slow motion, airborne height, train landing, finish drift, shared expiration and locked unfinished-car position. Protocol version 3 carries collapse age, slow-motion state, finish age and train-jump counts.
- The final full solo race finished successfully before the deadline. The fault regression passed unboosted failure, checkpoint recovery and boosted clearance with the new slow-motion timing. Both final builds succeeded; APK inspection confirms landscape and ARM64. Windows was reopened for play. Physical Android performance/input testing remains outstanding.

## Camera, joystick and momentum revision — 2026-10-04

- 50 EditMode tests passed (Logs/handling-v2-acceptance.xml). Coverage includes analog throttle, brake-to-reverse, reverse steering and speed limits, coasting, rear-wall collision, road boundaries, five-second reset lockout, held-button debouncing, overlapping hazard approaches and deadline enforcement.
- The standalone handling scenario passed idle, acceleration, drift, drift exit, braking, reverse, reset and coasting (Logs/handling-v2-runtime.log). Captures are Screenshots/handling-v2-{drift,reverse,reset}.png.
- The live train-jump camera check collected 98 settled-flight samples: maximum angular speed 63.08 degrees/second, maximum adjacent angular-speed change 11.14 degrees/second. It passed the 150/60 limits. Train clearance, finish drift and city collapse also passed (Logs/cinematic-v2-runtime.log). This checks camera continuity in the Windows player; subjective feel and physical iPhone frame pacing still need on-device playtesting.
- Both camera position and look direction now use the rendered car as their anchor. Critically damped shot offsets ease takeoff/landing transitions; finish orbit time runs at render cadence; high-frequency cinematic shake is removed. Wheel steering eases and chassis pitch responds to acceleration/braking.
- Two-axis touch joystick with a deadzone and finger ownership; separate gas, brake, reverse, drift, boost and reset controls. Keyboard: W/Up gas, S/Down brake into reverse, A/D steering, B brake, Space drift, Shift boost, R reset.
- Engine force tapers with speed; rolling/aerodynamic resistance allows coasting. Brakes oppose signed motion before reversing, with reverse limited to approximately 36 km/h. This remains arcade path-based driving with PhysX chassis sweeps, not a wheel/suspension simulator.
- Reset rewinds to a clear approach and holds the racer for five simulation seconds while the shared race timer continues. It cannot extend the deadline, skip ahead through a hazard, or repeat while held. Reset cars do not collide with other racers during recovery. Network protocol is now version 4; all participants must run the updated build.
- Final Windows build and full solo race passed. Fault-gap regression passed the unboosted miss, checkpoint recovery and boosted crossing (Logs/handling-v2-fullrace.log and handling-v2-fault.log).
- The server and both independent clients passed reverse/reset replication and the train, finish and deadline sequence (Logs/handling-v2-net-*.log). No managed exceptions or snapshot overflow were logged.
- Release iOS Xcode export succeeded with Unity 6000.2.6f2. The export checker confirmed landscape, the HTTPS server endpoint, live catalog revision 10 with seven enabled cars, and the exported build tools. This export still requires compilation by Codemagic and signing/installing on the personal iPhone.

## Automatic updates and DLC — version 1.1.0

- Production health/catalog endpoints returned HTTP 200. Release clients force https://game.inmomentservices.com and migrate saved legacy addresses. The runtime test seeded an old loopback URL and 789 credits, then verified successful production downloads with credits preserved. The release HUD has no server-address field; the separate developer LAN UI is hidden.
- 64 EditMode tests passed (Logs/dlc-tests.xml). New cases cover version comparisons, publisher URL restrictions, checksum/size metadata, DLC compatibility, unknown disasters, unsafe physics values, overlapping setpieces and actual handling changes from downloaded tuning.
- Windows updater integration tests passed valid replacement, previous-version retention, checksum rejection, path traversal rejection and incomplete-package rejection (Tools/Test-Updater.ps1). The real locally built release ZIP was installed into an isolated directory and the installed executable ran successfully. Automatic approval review blocked a combined public download-and-launch test; no reason beyond policy rejection was supplied. Publication was checked separately through GitHub asset sizes/digests and feed metadata.
- Live DLC verification passed in the release Windows player: official server, car catalog, update check, download of Aftershock Run, and full completion of the 2.2 km course at simulation time 46.57428 seconds (Logs/dlc-live-runtime.log). Screenshots: dlc-updates.png and dlc-dlc-garage.png.
- The installed ZIP reloaded Aftershock Run revision 1 with DLC networking disabled (WB_DLC_CACHE_PASS in Logs/dlc-installed-offline.log). DLC and selected course survived the executable replacement. Car-catalog and app-version checks remained network-enabled for this test; this was specifically an offline DLC-cache check.
- Release Windows build and iOS Xcode export succeeded. Windows ZIP SHA-256: dd4a6fcee2cbde4e1138c626adc64fddb28a3cee76a9b3c3ebd63fdfcd34a732 (37,942,963 bytes). iOS has the same data-only DLC client but still requires Codemagic compilation and physical-device validation.
- DLC JSON and future car updates require no new IPA. New executable mechanics remain app-build updates. GitHub's public raw-content cache can delay new manifest visibility by several minutes; periodic checks pick up the new revision after propagation.

## Cinder showroom and race roster — version 1.1.1

- Replaced the opening garage with a landscape showroom: a front three-quarter Cinder hero, headline, course/deadline card, paint and upgrade controls, and a prominent Race Now action. The layout respects the mobile safe area.
- Existing profiles migrate to Cinder once; later player selections remain available. Every AI starts with Cinder, with distinct paint colors. Disconnected multiplayer drivers also become Cinder relief AI.
- The showroom hides the race world and opposing cars; starting a race restores them immediately.
- 64 EditMode tests passed (Logs/landing-tests.xml). The standalone landing/roster check and full six-Cinder race passed (Logs/landing-runtime-v3.log); the racer finished at 55.14 simulation seconds. Final layout preview passed (Logs/landing-final-preview.log), with visual inspection of Screenshots/landing-final-garage.png.
- Windows release 1.1.1 built and packaged. Physical iPhone layout and frame pacing still require device validation after Codemagic compilation and signing.
- Unity iOS 1.1.1 export succeeded (Logs/landing-ios-final.log). Export validation confirmed landscape and HTTP 200 production health/catalog responses, revision 10 with seven enabled cars. Xcode compilation and personal signing remain Codemagic/device steps.
