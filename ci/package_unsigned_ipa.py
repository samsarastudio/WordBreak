"""Package a device xcarchive as an unsigned IPA for subsequent local signing."""
import argparse
import copy
import plistlib
from pathlib import Path, PurePosixPath
import shutil
import zipfile


def package(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        apps = list((source / "Products/Applications").glob("*.app"))
        if len(apps) != 1:
            raise ValueError("Expected exactly one archived iPhone app")
        app = apps[0]
        with (app / "Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
        if not (app / info["CFBundleExecutable"]).is_file():
            raise ValueError("Compiled app executable is missing")
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as out:
            for path in app.rglob("*"):
                if path.is_file():
                    out.write(path, "Payload/" + path.relative_to(app.parent).as_posix())
    else:
        with zipfile.ZipFile(source) as archive:
            plists = [entry for entry in archive.namelist()
                      if ".xcarchive/Products/Applications/" in entry
                      and entry.endswith(".app/Info.plist") and not entry.startswith("__MACOSX/")]
            if len(plists) != 1:
                raise ValueError("Expected exactly one archived iPhone app")
            prefix = plists[0][:-len("Info.plist")]
            app_name = PurePosixPath(prefix.rstrip("/")).name
            info = plistlib.loads(archive.read(plists[0]))
            if prefix + info["CFBundleExecutable"] not in archive.namelist():
                raise ValueError("Compiled app executable is missing")
            with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as out:
                for entry in archive.infolist():
                    if not entry.filename.startswith(prefix) or entry.is_dir():
                        continue
                    relative = entry.filename[len(prefix):]
                    if ".." in PurePosixPath(relative).parts:
                        raise ValueError("Invalid archive path")
                    target = copy.copy(entry)
                    target.filename = f"Payload/{app_name}/{relative}"
                    target.compress_type = zipfile.ZIP_DEFLATED
                    with archive.open(entry) as src, out.open(target, "w") as dst:
                        shutil.copyfileobj(src, dst)
    with zipfile.ZipFile(destination) as result:
        if result.testzip() is not None:
            raise ValueError("IPA integrity check failed")
        assert all(name.startswith("Payload/") for name in result.namelist())
    print(f"Created {destination} ({destination.stat().st_size // 1048576} MB). UNSIGNED: sign locally before installation.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    package(args.archive, args.output)
