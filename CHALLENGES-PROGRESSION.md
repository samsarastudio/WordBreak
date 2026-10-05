# Challenge, progression and UI update — 1.3.0

## Research and design decisions
- Burnout Paradise Remastered's official manual describes separate race, Road Rage and Stunt Run events, linking stunts into combinations, and earning license progress/cars through events: https://eaassets-a.akamaihd.net/eahelp/manuals/bpr-pc-en.pdf . Adaptation here: visible mode selection, drift/jump/takedown combinations and personal bests. No claim of implementing Burnout's open world or Road Rage mode.
- Wreckfest's official site describes career championships, experience and unlocking upgrades/cars: https://wreckfest.thqnordic.com/ . Adaptation here: campaign milestones plus explicit earned-currency purchase requirements.
- Gameloft's official Asphalt material describes a guided Career and distinct events: https://mkt-web.gameloft.com/game/asphalt-9 . Adaptation here: understandable event goals, required points and a dedicated track selection screen.

## Implemented scope
- Campaign, Time Attack (no rival cars, target 86% of the district deadline), Stunt Run (drift/jump/takedown score target), and access to existing local-network host/join. No internet matchmaking is implied.
- Campaign is the only mode that advances the completed-level milestone. Side modes earn RP. Completion records store best time, best score and up to three medals. Time-up still collapses the world in all modes.
- Level 1 and Cinder remain free. Other levels require completing the preceding campaign level and paying 150 x level RP. Aftershock DLC requires level 2 and 600 RP. Cars use stable IDs with milestones 1–6 and 300 x required level RP. Credits remain separate for performance upgrades.
- Old saves preserve credits, XP and completed levels; once only, completed historical races grant 350 RP each. Non-starter content obeys the new purchase requirements. Failed/unfinished races do not advance the campaign. A finished side-mode attempt below its target earns only 100 RP.
- New collision obstacles: falling cargo; cycling steam vents with mesh-particle bursts; falling rocks; swinging demolition loads. Advance lane markings and HUD warnings telegraph hazards. Level 1 introduces cargo, Dockyard mixes cargo/swinging loads, Foundry adds steam, Canyon adds rockfall, and later districts mix all four.

## AI button asset
Built-in image_gen tool, generated 2026-10-05. Saved project asset: Assets/WB/Resources/UI/DisasterButton.png. The same plate is tinted for primary, secondary, pressed and driving-control surfaces, with runtime text for clarity. Source retained in the Codex generated_images folder.

Final generation prompt:
Create a production game UI texture asset, not a screenshot or mockup: ONE single wide horizontal blank button plate, aspect ratio 3:1, tightly filling the canvas edge to edge. World Break Rush is a stylized comic-book disaster street racing game. The button is ivory off-white worn painted metal with heavy dark charcoal hand-inked border, angular clipped corners, small black halftone grit and scratches only around the perimeter, restrained tiny diagonal hazard marks near ends. Large central 70 percent absolutely clean flat ivory space for programmatic text. Flat front orthographic view, no perspective, no lettering, no words, no symbols in center, no icons, no multiple buttons, no surrounding scene, no drop shadow outside the button. Transparent background only outside clipped corners. Crisp graphic silhouette. Mostly neutral ivory and black so the game can tint it orange, cyan or dark slate for selected, hover and disabled states. Output a high quality raster image suitable for a Unity nine-sliced GUI button.

## Verification targets
Purchase gates and persistence, one-time migration, mode targets and isolation, hazard timing and safe lanes, six-course collision-world completion, all new menu screens and AI-art readability, Windows release build and iOS export. Network protocol advances to 5 because Metro Quake's authored obstacle layout changed; all LAN participants must update.

## Final driving-control revision
The plate artwork is now restricted to menus. The race HUD uses six compact circular pictograms (accelerate, brake, reverse, drift, boost and reset), a matching circular pause control, and a smaller joystick with separate generated base/thumb artwork. Permanent driving labels were removed; the pause screen contains the control legend. Visible circle geometry and touch hit tests share DrivingControls.cs. The generated icon atlas is masked to circular bounds at rendering time; its source pixels remain unchanged.

Additional built-in image_gen assets:
- Assets/WB/Resources/UI/JoystickBase.png
- Assets/WB/Resources/UI/JoystickThumb.png
- Assets/WB/Resources/UI/DrivingIcons.png

Joystick base prompt:
Production raster game UI asset: ONE circular virtual joystick BASE RING for World Break Rush, a comic-book disaster street racing game. Square canvas, isolated centered circle filling 92 percent of canvas, transparent background outside the circular silhouette. Top-down flat orthographic, no perspective. Charcoal gunmetal center disc kept dark and visually quiet, bold worn ivory outer ring, small bright cyan inset ring, four small ivory directional ticks at north south east west, subtle halftone ink and chipped painted-metal perimeter, small restrained orange hazard accents. The inner central 65 percent stays empty dark slate for a separate movable thumb cap. No thumb cap in this image, no letters, no text, no arrows crossing the central area, no extra objects, no shadow outside silhouette. Crisp readable gaming control matching an inked comic racing HUD, not photorealistic.

Joystick thumb prompt:
Production raster game UI asset: ONE circular virtual joystick THUMB CAP for World Break Rush, comic-book disaster street racing game. Square canvas; single compact round control cap centered and filling 92 percent of canvas, transparent outside circular silhouette. Flat front orthographic view, no perspective. Cyan painted metal circular face, ivory thin inner highlight ring and thick charcoal hand-inked outline, angular ring accents, subtle chipped edge paint and halftone texture only at outer edge. Clean cyan middle with four tiny dark diamond grip marks in a cross. Crisp and readable when reduced to 60 pixels wide. No letters, no text, no joystick base ring, no extra pieces, no outside drop shadow. Match gritty ivory, charcoal and cyan comic arcade racing HUD artwork. Not photorealistic.

Driving icon atlas prompt:
Create a production 3-column by 2-row sprite atlas of SIX circular icon-only touch buttons for World Break Rush, a comic disaster racing game. Landscape canvas aspect ratio exactly 3:2. Six equal square cells in a precise regular grid, each circle centered in its cell and filling 84 percent of cell width, generous transparent gutters and transparent background everywhere outside circles. Each circle charcoal metal with thin worn ivory outer ring, restrained ink halftone edges, bright ivory or cyan clean pictogram in center. Flat orthographic bold game icons readable at 64px. No letters, no words, no captions, no numbers anywhere. Order is essential: TOP LEFT ACCELERATE icon = two bold upward chevrons, orange center field; TOP MIDDLE BRAKE icon = bold square stop symbol enclosed by two curved brake brackets, charcoal center; TOP RIGHT REVERSE icon = bold downward U-turn arrow, charcoal center. BOTTOM LEFT DRIFT icon = rear-view car silhouette with two strongly curved skid trails, charcoal center; BOTTOM MIDDLE BOOST icon = single bold lightning bolt, vivid cyan center with black lightning; BOTTOM RIGHT RESET icon = car silhouette inside one clockwise circular arrow, charcoal center. All circles same diameter, same border thickness, no perspective, no external drop shadows, no connecting elements. Crisp stylistically consistent ivory/cyan/orange/charcoal comic racing UI. This is a sprite sheet to be sliced into exactly six square tiles by code.

Atlas refinement prompt:
Edit this UI sprite atlas. Preserve exactly the six circular buttons, their icon designs, colors, sizes and 3-column 2-row arrangement. Remove ALL the gray/brown surrounding background and drop shadows outside each button's dark outer circular edge, replacing those pixels with genuine alpha transparency, including gutters between circles. Do not add checkerboards or a matte. Keep each circular icon opaque inside its edge. No text, no labels, no new elements. Output PNG with transparent background. Each button must be centered within its equal-sized square grid cell; keep all six the same diameter.

## UI review — 1.3.1
- Primary flow: Garage > Play > Choose mode > Choose track > Start race. Choosing or purchasing a track stays on the track screen and preserves the mode. Mode selection never depends on the previously selected track. Back buttons name their destination.
- Track selection shows selected state, distance, deadline, mode-specific target, price and missing campaign/point requirements. Buying is separate from starting. Locked car previews offer an explicit switch to the free Cinder GT.
- Removed redundant accelerator/reverse touch buttons. Joystick up accelerates, down brakes before reversing, sides steer, and release coasts. Only brake, drift and boost remain as circular race controls. Reset is in the pause menu with its live time penalty; an online menu clearly says the race continues.
- Added an illustrated How to Drive page accessible from garage, modes, settings, pause and failure. Menu help text explains icon actions, coasting, reverse, reset and keyboard equivalents.
- Replaced garage track browsing with campaign progress and a single Play entry point. Costs state RP or CR; unavailable purchases/upgrades are disabled. Results show each mode's actual target, earned currencies, and explicit replay/track/mode choices.
- Local multiplayer setup explains same-Wi-Fi requirements and labels the friend's local IP field. It no longer defaults to loopback or presents technical port instructions as the main flow.
- All UI and touch coordinates share a uniform safe-area viewport. Circles remain circular at wider phone/tablet ratios; pixel-to-touch mapping includes safe-area offsets.
- Existing generated artwork is reused. No new AI image generation was needed for this review.
