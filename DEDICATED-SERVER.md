# Windows laptop race server — 1.6.0

The Pi keeps the catalog, admin, matchmaking and WebSocket relay. A Windows 11 Intel/AMD laptop runs authoritative Unity race physics. Players send controls, never authoritative positions. Every player, including the first to join, uses prediction and reconciliation. The laptop connects OUTBOUND to `https://game.inmomentservices.com`; it opens no listening port. No router forwarding, paid relay or AWS resource is required. Electricity and existing internet usage still apply.

## Deploy the Pi first

Pull `main`, rebuild the existing Docker image from `Backend/CarCatalog`, and recreate the container using its current deployment configuration, HTTPS route and persistent `/data` volume. Preserve all current admin settings. Add a new `RACE_WORKER_KEY` environment variable with at least 32 random characters. Generate one locally on the Pi using `openssl rand -hex 32`; store it privately in your deployment environment, not Git. The exact same key is entered on the laptop. Do not reuse the admin password/token. Do not paste it into chat.

If using Docker Compose, add this under the existing service's `environment` mapping:

```yaml
RACE_WORKER_KEY: ${RACE_WORKER_KEY:?Set the private worker key}
```

Put the value in the deployment's private `.env` file. With `docker run`, use your existing recreation command with `--env-file /path/to/private.env`. Do not replace the existing volume or blindly copy an unrelated example container command.

Permit WebSocket upgrades for `/v1/matchmaking/worker` as well as `/v1/matchmaking/stream`. `/health` must report `matchmaking: 8`. It shows `dedicatedWorkers: 0` until the laptop connects. Older protocol 6/7 clients still use their separate legacy rooms; only the new 1.6.0 client uses dedicated authority.

## Start the laptop

1. Extract the entire `WorldBreakRaceServer-Windows-1.6.0.zip` on the laptop. Unity Editor and Python are not required.
2. Double-click `Start-Server.cmd`. On first launch, paste the Pi worker key at the hidden prompt. It is encrypted using Windows DPAPI for the current user and machine. Do not move `worker-key.encrypted` between PCs; enter the key again on each PC.
3. Read `server.log`. `WBR_WORKER_CONNECTED` confirms authentication. `WBR_WORKER_READY` alone means the process started, not that the Pi accepted it.
4. Keep the laptop plugged in, awake and preferably on Ethernet. No inbound Windows Firewall exception is required. Allow outbound HTTPS if local security software blocks it.
5. Test with the new Windows 1.6.0 client. Online races wait for the starting grid, then all clients receive laptop-authoritative state. iOS has not been exported or updated.
6. Double-click `Stop-Server.cmd` when finished. This ends active races. A sleeping/offline laptop makes new dedicated races unavailable.

One process supports one six-car room. This package deliberately starts one process; capacity is limited until profiling on the actual laptop. The relay currently accepts at most four authenticated workers. To add workers later, use separate extracted folders and benchmark first. There is no autoscaling, cloud fallback or paid service.

## Recovery and security

The worker retries a lost relay connection every five seconds. An interrupted race ends; it is not migrated or resumed. New races can start after reconnection. A disconnected player's seat becomes AI after the timeout; the first player's departure does not shut down the race. Existing room tickets are invalidated when the authority disappears. If the key changes, stop the laptop process, delete only `worker-key.encrypted`, and start again.

The shared worker key authorizes trusted physics workers, not admin operations. Keep it private. Snapshots are bounded, worker versions are checked, and clients cannot impersonate an authority using their player tickets. This is not a full anti-cheat or account/progression backend.

## Implementation limits

The package runs Unity desktop headless mode (`-batchmode -nographics`) with a dedicated worker entry point. It is not Unity's separately installed, asset-stripped Dedicated Server build target. Rendering and player UI are not started, but the package retains scene assets needed to construct matching collision geometry.

Online matchmaking currently uses the existing default track/campaign race rules. This change does not add online track/mode selection. The Pi still relays traffic over TCP WebSockets, which can stall with packet loss. Local prediction reduces input delay; authoritative hosting alone does not eliminate latency or reconciliation corrections. Full internet testing requires Pi deployment and the laptop running.
