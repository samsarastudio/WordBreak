# Server deployment

Local Windows: run the Windows player with `-batchmode -nographics -server`. The service owns simulation and input validation. It begins one race after the configured queue plus countdown; use a fresh process for each match. Real public matchmaking and process allocation are not included.

Linux: install Linux Dedicated Server support for 6000.2.6f2, build Bootstrap for StandaloneLinux64 with the Server subtarget to `Builds/LinuxServer/WorldBreakServer`, then run `docker build -f Server/Dockerfile -t worldbreak-server .`. Start with `docker run --rm -p 7777:7777/udp worldbreak-server`. The Dockerfile is supplied for the later Linux build and has not itself been validated with a Linux binary.

Optional chat container: `docker build -t worldbreak-chat Backend/BotChat`. Bind its port to loopback on the game server host with `-p 127.0.0.1:8787:8787`. Set OLLAMA_BASE_URL to an endpoint reachable from the container and explicitly enable the model. Never expose an unauthenticated Ollama endpoint to clients.

## Online matchmaking — 1.4.0

Deploy branch `codex/ios-codemagic` from samsarastudio/WordBreak. Build the existing Dockerfile with context `Backend/CarCatalog`; it now copies `matchmaking.py` alongside the catalog server. Keep the existing `/data` volume and HTTPS routing to container port 8787. Do not replace or clear catalog data. No new UDP port, dependency or secret is required for this beta matchmaking service.

After manually rebuilding/redeploying the container, GET `https://game.inmomentservices.com/v1/matchmaking` must return protocol 6, version 1.4.0, queueSeconds 12 and seats 6. `/health` also includes matchmaking: 6. The mobile client uses this fixed domain and has no address field. Until this server update is deployed, online matchmaking is unavailable; solo modes continue to work.

The server allocates compatible players to six-seat Metro Quake rooms, issues unguessable session tickets, freezes new admissions after the 12-second queue, relays controls/state and expires rooms. Empty/disconnected non-host seats are explicitly AI racers. Online races standardize on Cinder GT without upgrades. Clients need 1.4.0; older clients do not join this protocol.

Architecture limits: this is a small-beta HTTPS relay with an elected client running Unity physics. It is not a dedicated authoritative Unity simulation or cheat-resistant economy. If that client disconnects, the room ends and remaining players can find another race; host migration is not implemented. Rooms live in memory and are lost on container restart. Run one replica; horizontal scaling requires a shared room store. Internet/mobile latency and capacity remain to be profiled; local two-client testing does not establish WAN performance. An inactive driver's inputs neutralize after one second and their seat becomes a bot after eight seconds.

Server checks: `python -m unittest discover -s Backend/CarCatalog -p 'test_*.py'`. Windows builds are local test artifacts only from 1.4.0 onward and are not uploaded to GitHub or the Windows update feed. Codemagic remains responsible for compiling/signing the iOS export.
