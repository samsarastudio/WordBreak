"""Check this export before spending time compiling it; restore Mac tool permissions."""
import json
import os
from pathlib import Path
import plistlib
import stat
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
IOS = ROOT / "ios"
ENDPOINT = "https://game.inmomentservices.com"
project = IOS / "Unity-iPhone.xcodeproj/project.pbxproj"
assert project.is_file(), "Missing Unity Xcode export in ios/"
assert "com.worldbreak.rush" in project.read_text(), "Wrong application identifier"
config = json.loads((IOS / "Data/Raw/car-catalog.json").read_text(encoding="utf-8-sig"))
assert config["url"] == ENDPOINT, f"Wrong server configuration: {config['url']}"
with (IOS / "Info.plist").open("rb") as source:
    info = plistlib.load(source)
orientations = info.get("UISupportedInterfaceOrientations", [])
assert orientations and all("Landscape" in item for item in orientations), orientations
# Online races use the HTTPS service; do not show an obsolete LAN permission explanation.
info.pop("NSLocalNetworkUsageDescription", None)
with (IOS / "Info.plist").open("wb") as target:
    plistlib.dump(info, target, sort_keys=False)

# Git on Windows does not retain executable permissions for the exported Mac tools.
mach_o = {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}
fixed = 0
for base in (IOS / "Il2CppOutputProject", IOS / "Libraries"):
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        with path.open("rb") as source:
            start = source.read(128)
        assert not start.startswith(b"version https://git-lfs.github.com/spec/v1"), f"Unfetched LFS pointer: {path}"
        header = start[:4]
        if header in mach_o or header.startswith(b"#!") or path.suffix == ".sh":
            if path.suffix == ".sh" or header.startswith(b"#!"):
                content = path.read_bytes()
                if b"\r\n" in content:
                    path.write_bytes(content.replace(b"\r\n", b"\n"))
            if os.name != "nt":
                path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            fixed += 1
for route in ("health", "v1/catalog"):
    request = Request(f"{ENDPOINT}/{route}", headers={"User-Agent": "WorldBreakBuild/1.0"})
    with urlopen(request, timeout=30) as response:
        assert response.status == 200
        payload = json.load(response)
    if route == "health":
        assert payload.get("ok") is True
        assert 8 in payload.get("protocols", []), "Deploy protocol-8 matchmaking before building this client"
    else:
        assert payload.get("schema") == 1 and any(car.get("enabled") for car in payload["cars"])
        print(f"Live catalog revision {payload['revision']}; enabled cars: {sum(bool(c.get('enabled')) for c in payload['cars'])}")
print(f"iOS export verified: landscape, {ENDPOINT}, {fixed} executable tool/script files")
