# WORLD BREAK RUSH: iOS through Codemagic

The `ios/` directory is a release Xcode export from Unity 6000.2.6f2. Codemagic only needs its macOS/Xcode runner; it does not need Unity or a Unity license for this export. Bundle ID: `com.worldbreak.rush`. iPhone/iPad, iOS 15+, landscape. The bundled car-catalog endpoint is `https://game.inmomentservices.com`.

## Start a build

1. At https://codemagic.io/apps, add/select `samsarastudio/WordBreak` using the **Other / native iOS** project configuration.
2. Select branch **codex/ios-codemagic** and scan its root `codemagic.yaml`.
3. Run **ios-compile-check** first. It fetches Git LFS, validates the endpoint and export, and compiles an unsigned device archive. This archive is a compile check, not an installable app.
4. For an installable IPA, upload an Apple Distribution certificate (including its private key) and an **Ad Hoc** provisioning profile for `com.worldbreak.rush` under your Codemagic team's **Code signing identities**. The profile must include your test iPhone's UDID. Then run **ios-device-ipa** and download the IPA from build artifacts.

The **ios-app-store-ipa** workflow instead uses an App Store profile and creates an IPA for subsequent App Store Connect/TestFlight upload. No workflow automatically publishes or submits the app. Apple signing material belongs in Codemagic's secure settings, never Git.

References: [Codemagic signing](https://docs.codemagic.io/yaml-code-signing/signing-ios/), [native iOS workflows](https://docs.codemagic.io/yaml-quick-start/building-a-native-ios-app/).

## What this export contains

The current Unity game includes train launch ramps, jump slow motion and orbit camera, a 90-second escape deadline with city collapse, and a finish drift celebration. The HTTPS health and catalog endpoints returned 200, and the Unity player fetched the live catalog and drove its selected car successfully. No iPhone or Xcode compile has run on the Windows authoring machine; the first workflow performs that compile on Codemagic.

The domain is the **car-catalog service**. Race multiplayer remains the separate UDP 7777 host/join system. Previously saved catalog addresses are retained by existing installations; change those in Settings > Car Downloads if needed.

## Updating the game later

Edit the Unity source project, set `Assets/StreamingAssets/car-catalog.json`, and run `WorldBreak.Editor.IOSBuild.Export` using the installed editor with `-batchmode -nographics -buildTarget iOS`. Replace `ios/` with the new `Builds/iOS-Codemagic/ios` export and push it with Git LFS. Server catalog changes to cars do not require a new export.

The existing server source and deployment files remain in this repository. `ios/` is generated client source/data, not the editable Unity Assets project. Native build artifacts go in ignored `build/`.
