# WordBreak — Car Catalog Server

Server and browser admin for WORLD//BREAK vehicle content. Upload a car ZIP, review its 3D model and studio images, repair wheel assignments, and publish catalog updates to compatible game clients without rebuilding the game.

This repository contains the server source and a curated built-in preview deployment ZIP. It does not contain the Unity project, game binaries, original model sources, production catalog, or admin credentials.

## Run locally

Requirements: Python 3.11+ and Blender installed. No third-party Python packages are needed. The browser's Three.js dependency is bundled locally.

```powershell
python Backend/CarCatalog/server.py --blender 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe'
```

Open <http://127.0.0.1:8787/admin>. The first start creates `Backend/CarCatalog/data/admin-token.txt`; paste that token into **Unlock editing**. Each installation generates its own token. Alternatively, supply `CAR_ADMIN_TOKEN` through the server environment.

On Windows, `Manage-Cars.cmd` starts the service if necessary and opens the admin. Its helper supports `-Python` and `-Blender` executable paths. This convenience launcher listens on all interfaces for LAN testing; the Python command above defaults to loopback. Use `--host 0.0.0.0` explicitly when running the Python entry point for LAN access.

## Import and publish a car

1. Choose **Add car** and upload a ZIP containing exactly one FBX or GLB plus its base-color textures. Scripts inside ZIPs are ignored.
2. Review the interactive 3D preview, five studio angles, triangle count, and warnings. New cars start disabled/in review.
3. Use **Test wheel spin** and the steering slider to check the wheel assignments. A 4/4 count alone does not guarantee correct geometry.
4. If needed, open **Set up / repair tires**, position the four wheel cylinders, and build a test preview. Inspect all four wheels in motion before applying. **Neutral inner wheel faces** can cover unwanted paint on inward-facing tire surfaces. The original setup is kept for restore.
5. Enable the car and choose **Publish changes**. You can also manage names, ordering, default selection, and overrides of saved player choices.

Wheel repair cuts existing triangles, including connected meshes, while preserving UVs. It does not reconstruct missing wheels, close cut surfaces, or repair arbitrary melted geometry. Poor source meshes may still need Blender cleanup. Applying a repair or replacing the ZIP of an already available car updates that car for clients on their next sync; preview generation alone does not publish it.

Models are normalized to 4.2 metres long. Separate wheel objects named with `wheel`, `tire`, or `tyre` are the most reliable input. The importer also detects plausible disconnected wheel geometry. Limits include a 100 MB ZIP, 400 MB extracted content, 200,000 triangles, and a 64 MB converted package. Only base-color materials are imported; no downloaded executable game code is supported.

The seeded catalog includes the game's built-in car IDs. Install the included deployment ZIP below to enable their admin previews; uploaded cars generate their previews automatically. The optional `prepare_gallery.py` backfill utility expects the original game's `ArtSource/Model7071/` and `ArtSource/KenneyCarKit/` directories at the repository root.

## Persistence and hosting

The default data directory is `Backend/CarCatalog/data/`; override it with `--data`. Persist and back up this whole directory, including the catalog, token, immutable packages, studio previews, and optional built-in preview registry. Applied wheel repairs and their original packages survive server restarts. Pending import/preview job records are in memory and must be regenerated after a restart.

```sh
docker build -t wordbreak-cars Backend/CarCatalog
docker run -d --restart unless-stopped --name wordbreak-cars \
  -p 127.0.0.1:8787:8787 -v wordbreak-cars:/data \
  --memory 2g --cpus 2 wordbreak-cars
```

For internet use, put the service behind an HTTPS reverse proxy and restrict admin access. Allow uploads up to 100 MB. Conversion and image rendering are background jobs, polled by the admin. Keep Blender updated. The Docker image runs as a non-root user; its build has not been verified on this Windows development machine.

Game clients need the existing runtime catalog support installed. This repository includes HTTPS matchmaking and race-state relay, but does not implement dedicated-server physics or cross-device player accounts. Compatible clients fetch the catalog and immutable WBCAR001 mesh packages; the game supplies driving physics, input, collision, and wheel animation. Existing older game builds without that loader need a one-time client update.

## API

Public reads: `GET /health`, `GET /v1/catalog`, `GET /v1/previews`, and package/preview URLs returned by these endpoints.

Admin routes require `Authorization: Bearer <token>`:

- `GET /admin/session` and `GET /admin/jobs/<job-id>`
- `POST /admin/upload?id=<id>&name=<name>&yaw=0` with a ZIP body
- `POST /admin/catalog` with catalog changes and the current revision
- `POST /admin/wheels/preview`, `/admin/wheels/apply`, and `/admin/wheels/restore`

Catalog writes use revision checks to reject stale changes. The browser UI is the reference client. `Backend/CarCatalog/upload.py` also supports command-line imports; omit `--publish` and `--default` to stage a car for review.

## Automatic previews on a Raspberry Pi

Each new ZIP is converted and automatically rendered into a thumbnail plus front, rear, left, and right JPEGs. Wheel repairs use the same renderer. The default `CAR_PREVIEW_QUALITY=lite` profile uses CPU rendering at 480 x 300, 512-pixel preview textures, two render threads, limited light bounces, and no denoiser. This reduces render working memory; Blender and model import still have their own memory requirements. The actual peak depends on the uploaded model and has not been measured on a Pi.

One import/repair runs at a time. Complete galleries are reused by model hash. Images persist under `/data/previews` in Docker; keep the `/data` volume when updating the container. Render failures are recorded in `/data/last-preview.log` and do not prevent interactive 3D preview or model import. Interactive 3D rendering runs in the administrator's browser.

Set `CAR_PREVIEW_QUALITY=studio` in the server/container environment to use the original 720 x 450 denoised profile for newly rendered galleries. Existing cached images are retained.

The six seeded built-in entries are names/IDs only. They need their model packages and `builtin-previews.json` copied separately; the deployment ZIP described below supplies those assets. ZIP uploads carry their own model and generate previews automatically.

Update the server code and rebuild/recreate your container using the same persistent data volume to enable the lightweight default. No game build update is required.

## Install built-in previews

The repository includes `deploy/WorldBreak-Builtin-Previews.zip` with six built-in model packages, their registry, and 30 gallery images. It contains no admin token or catalog settings. After pulling this repository on the Pi, run from the repository root (the container name below is `wordbreak-cars`):

```sh
git pull --ff-only
unzip -o deploy/WorldBreak-Builtin-Previews.zip -d builtin-previews
sudo docker cp builtin-previews/. wordbreak-cars:/data/
sudo docker exec -u 0 wordbreak-cars chown -R catalog:catalog /data
```

Refresh `/admin`; no container rebuild or restart is needed for this asset copy. Keep `/data` on the existing persistent volume. For a direct Python installation, extract into its configured `--data` directory instead. New model ZIP uploads generate their own previews automatically.

## Tests

```sh
python -m unittest discover -s Backend/CarCatalog -p "test*.py"
```

Tests cover durable catalog changes, ZIP path validation, connected mesh cuts, UV preservation, wheel-region validation, staged previews, stale updates, and restoring original models. Browser and real-model checks were also performed in the game workspace; no Unity files or test-player binaries are included here.

## Third-party notice

Three.js 0.180.0 is distributed under the MIT license. Its license is included at `Backend/CarCatalog/static/vendor/THREE-LICENSE.txt`.

## FBX import reports missing NumPy

The Docker image explicitly installs Debian `python3-numpy` for Debian Blender and verifies the import inside Blender during the image build. Installing NumPy with the image's default `pip` targets a different Python interpreter and may not fix Blender.

If an older deployed container reports `ModuleNotFoundError: No module named 'numpy'`, pull the updated source, rebuild the image, and recreate the container with the existing `/data` volume. Retry the failed ZIP upload afterward. No game build changes are required.

To verify the running container:

```sh
sudo docker exec wordbreak-cars blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python-expr "import numpy; print('BLENDER_NUMPY_OK', numpy.__version__)"
```

## Prepared wheels and car deletion

New uploads require separate mesh objects named exactly `WheelFL`, `WheelFR`, `WheelRL`, and `WheelRR`. Set their object origins at the axle centers, with the axle along the car's left/right axis. Left/right refer to the driver's seat. Keep bumper, suspension and axle-stub geometry in the body. The importer preserves these prepared wheel pivots and does not automatically reclassify body fragments when the four explicit wheel objects exist. Legacy offline gallery conversion still supports older models.

The experimental tiny-fragment cleanup and automatic pivot-centering options have been removed. Prepare the source model instead. A tire with an oval mesh still needs modeling work; pivot changes alone cannot make it round.

Uploaded cars retain **Delete car permanently**, with a confirmation. Publish another default first if necessary. Deletion updates the catalog and removes known current, original-repair, and staged assets that are not shared with another car, built-in preview, or repair job. Previously downloaded client caches are not remotely erased. Built-in cars can be disabled rather than deleted. The authenticated `POST /admin/cars/delete` endpoint requires `id` and the current `revision`; deletion is blocked while an import or repair runs.


## Matchmaking deployment

The `main` branch includes the car admin, catalog, and protocol-6 HTTPS matchmaking in the same Docker service. Pull `main`, rebuild `wordbreak-cars` from `Backend/CarCatalog`, then recreate the container using your existing deployment configuration and persistent `/data` volume. No iOS export or Windows game binaries are included in this server change.

```sh
git pull --ff-only origin main
sudo docker build -t wordbreak-cars Backend/CarCatalog
# Recreate the service with your existing deployment configuration.
curl -fsS https://game.inmomentservices.com/v1/matchmaking
curl -fsS https://game.inmomentservices.com/health
```

After recreation, matchmaking metadata should report `protocol: 6`, `version: "1.4.0"`, `queueSeconds: 12`, and `seats: 6`; health should include `matchmaking: 6`. The version is the matchmaking compatibility version, also used by the 1.4.1 UI-only client patch.

The service allocates rooms and relays inputs/snapshots. One player runs race physics; host disconnect ends the room. Rooms are in memory, so run one replica and expect active sessions to end on redeployment. Empty seats use AI. This is not a dedicated authoritative simulation or a cross-device account service. No additional UDP port is needed.

Validation: 28 Python tests passed on the server branch. Docker/ARM execution must be verified on the Pi after deployment.
