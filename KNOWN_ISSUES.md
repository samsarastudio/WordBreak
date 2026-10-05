# Delivery status and remaining acceptance work

Version 1.2.0 contains six offline campaign tracks: Metro Quake, Dockyard Domino, Foundry Run, Canyon Fracture, Midnight Grid and Last Light. Aftershock Run remains optional downloadable content. The default player and AI model is Cinder Disaster GT; other catalog cars remain selectable for the player. Cars currently share handling tuning.

The environment uses authored modular geometry, the existing comic textures, batched architectural detail and per-district lighting. Destruction includes hinged towers, falling signs, train crossings, fractured-road ramps, breakable cargo, debris particles and deadline collapse. It is not arbitrary mesh fracture or deformable vehicle bodywork.

Driving remains analytical path-based arcade handling with PhysX chassis sweeps and car-to-car impacts, rather than a wheel/suspension simulator. Local multiplayer continues to use Metro Quake; the six-track campaign is single-player. One race per dedicated-server process is the supported server lifecycle.

Windows executable updates and data-only DLC use the release feed. New iOS executable features require a newly compiled and personally signed app; compatible DLC can update inside the installed app. Codemagic compiles the exported Xcode project; no local Mac compilation is claimed.

Outstanding production work includes physical iPhone touch/safe-area QA, GPU/thermal profiling, broader network-condition testing, hosted matchmaking, secure server-backed profiles/economy, distinct car handling and broader progression/customization. The IMGUI HUD should be replaced with retained UI for production mobile performance. No 60-FPS-on-device claim is made.

See PERFORMANCE_REPORT.md for actual verification results and ENVIRONMENT-CAMPAIGN-PLAN.md for the campaign design.

Version 1.3.0 adds gated car/track purchases using Race Points, Campaign/Time Attack/Stunt Run selection and local-network host/join access. Level 1 and Cinder are free; other content requires the displayed campaign milestone and RP. The new hazards are authored cargo drops, steam vents, rockfall and swinging loads. LAN participants must all update to protocol 5. Ownership and currency are local-profile data, not tamper-resistant server entitlements. Research, rules and the AI button prompt are recorded in CHALLENGES-PROGRESSION.md.

Version 1.4.0 replaces the public LAN interface with server-managed HTTPS matchmaking, a 12-second queue and explicit AI backfill. The race physics host is an elected player, not a dedicated Unity server. Host disconnection ends the room; internet/mobile latency and capacity have not been validated. The live Docker service must be manually redeployed from codex/ios-codemagic before the new client can match. See SERVER_DEPLOYMENT.md. Windows test builds are no longer published. Rear collapse can now eliminate slow drivers before the final deadline; PIT hits require deliberate rear-quarter contact.
