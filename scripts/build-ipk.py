#!/usr/bin/env python3
"""Package ../app into a webOS .ipk (what ares-package makes), with no SDK needed.

An .ipk is an ar archive of debian-binary, control.tar.gz and data.tar.gz;
data holds the app under usr/palm/applications/<id>/ and its packageinfo.json
under usr/palm/packages/<id>/.

Usage: build-ipk.py [out-dir]   (default: ../dist)
"""
import io
import json
import os
import sys
import tarfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "dist")
NOW = int(time.time())


def add_bytes(tar, name, data, mode=0o644):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mtime = NOW
    info.mode = mode
    tar.addfile(info, io.BytesIO(data))


def add_dir(tar, name):
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mtime = NOW
    info.mode = 0o755
    tar.addfile(info)


def targz(fill):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        fill(tar)
    return buf.getvalue()


def ar_member(name, data):
    # Common (System V / GNU) ar header, 60 bytes.
    hdr = "%-16s%-12d%-6d%-6d%-8s%-10d`\n" % (name + "/", NOW, 0, 0, "100644", len(data))
    out = hdr.encode("ascii") + data
    return out + (b"\n" if len(data) % 2 else b"")


def main():
    with open(os.path.join(APP, "appinfo.json")) as f:
        info = json.load(f)
    app_id, version = info["id"], info["version"]
    app_dir = "./usr/palm/applications/%s" % app_id
    pkg_dir = "./usr/palm/packages/%s" % app_id

    if not os.path.isfile(os.path.join(APP, "config.js")):
        sys.exit("app/config.js is missing: copy app/config.example.js to app/config.js and edit it")

    files = []
    size = 0
    for base, dirs, names in os.walk(APP):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for n in sorted(names):
            # The example config is documentation, not part of the app.
            if n.startswith(".") or n == "config.example.js":
                continue
            full = os.path.join(base, n)
            files.append((os.path.relpath(full, APP), full))
            size += os.path.getsize(full)

    packageinfo = json.dumps({
        "app": app_id, "id": app_id, "loc_name": info.get("title", app_id),
        "package_format_version": 2, "vendor": info.get("vendor", ""), "version": version,
    }, indent=2).encode()

    def fill_data(tar):
        for d in ["./usr", "./usr/palm", "./usr/palm/applications", app_dir,
                  "./usr/palm/packages", pkg_dir]:
            add_dir(tar, d)
        seen = set()
        for rel, full in files:
            # Every ancestor directory gets its own entry, however deep.
            parts = os.path.dirname(rel).split(os.sep) if os.path.dirname(rel) else []
            for depth in range(1, len(parts) + 1):
                sub = "/".join(parts[:depth])
                if sub not in seen:
                    add_dir(tar, "%s/%s" % (app_dir, sub))
                    seen.add(sub)
            with open(full, "rb") as f:
                add_bytes(tar, "%s/%s" % (app_dir, rel), f.read())
        add_bytes(tar, "%s/packageinfo.json" % pkg_dir, packageinfo)

    control = (
        "Package: %s\nVersion: %s\nSection: misc\nPriority: optional\nArchitecture: all\n"
        "Installed-Size: %d\nMaintainer: homelab\nDescription: %s\n"
        "webOS-Package-Format-Version: 2\nwebOS-Packager-Version: x.y.x\n"
        % (app_id, version, (size + 1023) // 1024, info.get("title", app_id))
    ).encode()

    def fill_control(tar):
        add_dir(tar, ".")
        add_bytes(tar, "./control", control)

    data = (b"!<arch>\n"
            + ar_member("debian-binary", b"2.0\n")
            + ar_member("control.tar.gz", targz(fill_control))
            + ar_member("data.tar.gz", targz(fill_data)))

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "%s_%s_all.ipk" % (app_id, version))
    with open(path, "wb") as f:
        f.write(data)
    print(path)


if __name__ == "__main__":
    main()
