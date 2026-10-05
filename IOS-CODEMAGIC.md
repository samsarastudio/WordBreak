# WORLD BREAK RUSH: iOS through Codemagic

The `ios/` directory is a release Xcode export from Unity 6000.2.6f2. Codemagic only needs its macOS/Xcode runner; it does not need Unity or a Unity license for this export. Bundle ID: `com.worldbreak.rush`. iPhone/iPad, iOS 15+, landscape. The bundled car-catalog endpoint is `https://game.inmomentservices.com`.

## Start a build

1. At https://codemagic.io/apps, add/select `samsarastudio/WordBreak` using the **Other / native iOS** project configuration.
2. Select branch **codex/ios-codemagic** and scan its root `codemagic.yaml`.
3. With a free Apple ID, run **ios-compile-check** (display name: **unsigned IPA for personal sideloading**). It fetches Git LFS, validates the endpoint/export, compiles the app, and produces `WorldBreakRush-unsigned.ipa`. This is unsigned: use [Sideloadly](https://sideloadly.io/) on your computer to sign it with your free Apple ID and install it on your connected iPhone. Free-account signing lasts seven days and needs refresh. Enter Apple credentials only in your chosen signing tool, not the repository or Codemagic workflow.
4. For an installable IPA, upload an Apple Distribution certificate (including its private key) and an **Ad Hoc** provisioning profile for `com.worldbreak.rush` under your Codemagic team's **Code signing identities**. The profile must include your test iPhone's UDID. Then run **ios-device-ipa** and download the IPA from build artifacts.

The **ios-app-store-ipa** workflow instead uses an App Store profile and creates an IPA for subsequent App Store Connect/TestFlight upload. No workflow automatically publishes or submits the app. Apple signing material belongs in Codemagic's secure settings, never Git.

References: [Codemagic signing](https://docs.codemagic.io/yaml-code-signing/signing-ios/), [native iOS workflows](https://docs.codemagic.io/yaml-quick-start/building-a-native-ios-app/).

## What this export contains

Current export: **1.6.0**, protocol **8**. Online races use the dedicated Windows laptop worker through `https://game.inmomentservices.com`. All player clients use local prediction, authoritative reconciliation and remote interpolation. The first player is no longer physics authority. Matchmaking stays on the waiting screen before the race countdown. Online jump slow-motion is disabled; solo cinematics remain enabled. Player-to-player collision and tailspin tests passed with five Windows clients and the dedicated worker. iOS device performance and the Xcode archive still require Codemagic/device validation.

Version **1.1.0** adds automatic data-only DLC: course/disaster layouts, supported gameplay tuning and feature switches, plus existing car/model downloads. The first pack supplies Aftershock Run. Compatible iOS apps download and cache DLC automatically in the garage, without reinstalling or signing a new IPA. Server configuration is fixed; there is no editable server field. See `GAME-UPDATES.md` for publishing future DLC. Completely new executable functionality still requires a new IPA.

Driving uses the mobile joystick and circular action controls. Analog throttle controls engine force, releasing throttle coasts, and reverse has a lower speed limit. Reset adds a recovery penalty while the city countdown continues. Driving remains an arcade path-based model with chassis collision sweeps.

The current Unity game includes train launch ramps, jump slow motion and orbit camera, a 90-second escape deadline with city collapse, and a finish drift celebration. The HTTPS health and catalog endpoints returned 200, and the Unity player fetched the live catalog and drove its selected car successfully. The user returned a successful Codemagic Xcode archive; its compiled ARM64 app was repackaged and checked as an unsigned IPA. Personal-device signing and installation have not been tested here.

The domain serves catalog/admin, matchmaking and the authenticated WebSocket relay. Race physics run on the separately hosted Windows laptop. Keep the laptop server awake and connected for online play. This iOS export is a client; Codemagic does not host matchmaking or race physics. Deploy Pi server changes from `main`, not this generated iOS branch.

## Updating the game later

Edit the Unity source project, set `Assets/StreamingAssets/car-catalog.json`, and run `WorldBreak.Editor.IOSBuild.Export` using the installed editor with `-batchmode -nographics -buildTarget iOS`. Replace `ios/` with the new `Builds/iOS-Codemagic/ios` export and push it with Git LFS. Server catalog changes to cars do not require a new export.

The existing server source and deployment files remain in this repository. `ios/` is generated client source/data, not the editable Unity Assets project. Native build artifacts go in ignored `build/`.
