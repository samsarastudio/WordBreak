# Game updates

Version 1.1.0 introduces an update client. Install this version once; older builds do not contain the updater.

## Player behavior

The content endpoint is fixed to `https://game.inmomentservices.com`. Saved profiles migrate to it at startup. Players no longer enter or edit the endpoint. Car catalogs/packages refresh automatically outside races and remain usable offline. Release builds hide the developer LAN host/join screen: the HTTPS catalog service does not host NGO races.

Windows checks the official GitHub release feed on launch and every ten minutes in menus. A newer build downloads automatically. The client verifies its declared size and SHA-256, then stages it without interrupting a race. Exiting starts a separate updater which verifies the archive again, rejects unsafe paths and incomplete players, waits for the owning game process to exit, and swaps the installation directory. It retains the previous directory and rolls back if replacement fails. The player can also choose **Restart to update**. Use a writable install folder; failures leave the current installation intact and record `GameUpdates/install.log` under the user's game-data folder. User profiles and downloaded cars are outside the installation directory and are preserved.

iOS and Windows automatically download DLC as data, including courses, disaster schedules, handling/braking/drift settings, boost recharge, reset penalties and the existing jump slow-motion feature switch. New car meshes/textures continue through the production car catalog. The first published course is **Aftershock Run** (2.2 km, five disaster events, 85-second escape deadline). Garage course buttons choose between bundled Metro Quake and downloaded courses; selection persists. The app checks for DLC on launch and every 60 seconds outside races, validates its minimum app version, size and SHA-256, and bounds all course/physics settings. New content applies only outside races and network sessions. Cached DLC works offline; a backup is tried if the cache is damaged. Developer LAN sessions use the bundled course and default tuning to avoid unsynchronized content.

These are automatic DLC and data-driven feature updates, not executable-code hot reload. New mechanics outside the installed schema, new shaders or native plugins still require a new app version. An app signed with a free Apple ID cannot replace its own executable; a new IPA still needs signing/installing on the computer. Sideloadly signature refresh does not fetch new builds. TestFlight can handle automatic executable updates with Apple Developer Program membership. Physical-device update testing is still required.

## Publish DLC without building Unity or an IPA

Edit `Tools/LiveContent/gameplay-v1.json`, increment `revision`, and keep `minAppVersion` at the earliest compatible app version. Supported disaster kinds are 0 = falling-building quake, 1 = falling sign, 2 = train crossing, 3 = fault gap. Courses use the installed city art; they are procedural layouts rather than downloadable scene binaries. The schema supports up to four DLC courses, each 1–4 km, with up to sixteen spaced disaster events. Validate with `LiveContentTests` before publication.

Run `python Tools/iOS-Codemagic/ci/publish_update.py --local --platform content --version 1.1.0 --file Tools/LiveContent/gameplay-v1.json`. Here `--version` matches the pack's minimum app version. The publisher uploads an immutable JSON asset and advances the `content` entry atomically. Already-installed compatible Windows and iOS apps receive it automatically. No app rebuilding, Codemagic run or Apple signing is needed for these DLC updates.

## Publishing

The public manifest is `https://raw.githubusercontent.com/samsarastudio/WordBreak/codex/game-updates/updates.json`. Entries are separate for Windows and iOS. Immutable build assets live in the repository's `game-updates` GitHub release. HTTPS plus the repository's write permissions establish publisher trust; SHA-256 detects damaged/substituted downloads. The client accepts build URLs only from this repository's GitHub release path.

1. Increment Unity's **Bundle Version** in Project Settings (numeric, e.g. `1.1.1`) before both exports. Never publish different binaries with the same version.
2. Build Windows using `WorldBreak.Editor.ProjectSetup.BuildWindowsRelease`; export iOS with `WorldBreak.Editor.IOSBuild.Export`.
3. Package Windows: `python Tools/Package-GameUpdate.py --version 1.1.1`.
4. Publish: `python Tools/iOS-Codemagic/ci/publish_update.py --local --platform windows --version 1.1.1 --file Builds/Releases/WorldBreakRush-Windows-1.1.1.zip`.
5. Push the updated iOS export and run Codemagic. Its unsigned workflow includes IPA packaging and publication. To enable publication, create a Codemagic secret group `game_updates` containing `GITHUB_TOKEN`, a fine-grained GitHub token restricted to this repository with Contents read/write. Add `groups: [game_updates]` under that workflow's `environment`. Do not paste the token into source or chat. Without it, Codemagic still produces the IPA artifact and clearly reports publication skipped. Alternatively publish a downloaded IPA using the same script with `--local --platform ios`.

The publisher uploads the immutable asset before changing the feed. Feed writes use the GitHub file SHA for optimistic concurrency and retry on conflicts so independent platform updates are retained. Downgrades and same-version/different-content replacements are rejected. Existing saved profiles survive executable upgrades because the company, product and bundle identifiers stay unchanged.

Sources: [Sideloadly updating an app](https://sideloadly.io/faq), [TestFlight automatic updates](https://testflight.apple.com/), [Codemagic GitHub release publishing](https://docs.codemagic.io/yaml-publishing/github-releases/).
