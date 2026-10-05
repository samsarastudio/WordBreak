# Delivery status and remaining acceptance work

Version 1.2.0 contains six offline campaign tracks: Metro Quake, Dockyard Domino, Foundry Run, Canyon Fracture, Midnight Grid and Last Light. Aftershock Run remains optional downloadable content. The default player and AI model is Cinder Disaster GT; other catalog cars remain selectable for the player. Cars currently share handling tuning.

The environment uses authored modular geometry, the existing comic textures, batched architectural detail and per-district lighting. Destruction includes hinged towers, falling signs, train crossings, fractured-road ramps, breakable cargo, debris particles and deadline collapse. It is not arbitrary mesh fracture or deformable vehicle bodywork.

Driving remains analytical path-based arcade handling with PhysX chassis sweeps and car-to-car impacts, rather than a wheel/suspension simulator. Local multiplayer continues to use Metro Quake; the six-track campaign is single-player. One race per dedicated-server process is the supported server lifecycle.

Windows executable updates and data-only DLC use the release feed. New iOS executable features require a newly compiled and personally signed app; compatible DLC can update inside the installed app. Codemagic compiles the exported Xcode project; no local Mac compilation is claimed.

Outstanding production work includes physical iPhone touch/safe-area QA, GPU/thermal profiling, broader network-condition testing, hosted matchmaking, secure server-backed profiles/economy, distinct car handling and broader progression/customization. The IMGUI HUD should be replaced with retained UI for production mobile performance. No 60-FPS-on-device claim is made.

See PERFORMANCE_REPORT.md for actual verification results and ENVIRONMENT-CAMPAIGN-PLAN.md for the campaign design.
