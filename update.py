#!/usr/bin/env python3
"""Build a local searchable reference from Arm's versioned XML/HTML archives."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
from shutil import copyfileobj
import subprocess
import tarfile
from tempfile import TemporaryDirectory
from urllib.request import urlopen


ARM_DOWNLOADS = "https://developer.arm.com/-/cdn-downloads/permalink"
ROOT = Path(__file__).resolve().parent
BUILDS = ROOT / "builds"
PACKAGES = {
    "latest_aarch64": (
        "Exploration-Tools-A64-ISA/ISA_A64/ISA_A64_xml_A_profile",
        ("index.html", "fpsimdindex.html", "sveindex.html", "mortlachindex.html"),
    ),
    "latest_sysreg": (
        "Exploration-Tools-Arm-Architecture-System-Registers/SysReg/SysReg_xml_A_profile",
        ("AArch64-regindex.html", "AArch32-regindex.html"),
    ),
}


def archive_url(package, release):
    return f"{ARM_DOWNLOADS}/{package}-{release}.tar.gz"


def import_package(archive, destination, release_directory, indexes, scratch):
    extracted = scratch / destination.name
    with tarfile.open(archive, "r:*") as package:
        package.extractall(extracted, members=(
            member for member in package
            if (member.isfile() or member.isdir())
            and Path(member.name).parts[:2] == (release_directory, "xhtml")
        ), filter="data")

    html = extracted / release_directory / "xhtml"
    if not all((html / index).is_file() for index in indexes):
        raise ValueError(f"{archive}: expected {release_directory}/xhtml with {', '.join(indexes)}")
    html.rename(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", help="Arm release identifier, e.g. 2026-09")
    parser.add_argument("--isa-archive", type=Path, help="Use a previously downloaded ISA archive")
    parser.add_argument("--sysreg-archive", type=Path, help="Use a previously downloaded register archive")
    parser.add_argument("--pagefind", type=Path, required=True, help="Path to an installed Pagefind executable")
    args = parser.parse_args()
    if not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])(?:_\d+)?", args.release):
        parser.error("release must be YYYY-MM, optionally with an Arm suffix such as _96")

    pagefind = args.pagefind.resolve()
    if not pagefind.is_file():
        parser.error(f"Pagefind executable not found: {pagefind}")

    published = build(args.release, [str(pagefind)], args.isa_archive, args.sysreg_archive)
    print(f"Built {published}")
    print(f"python3 -m http.server 8001 --bind 127.0.0.1 --directory {published}")


def build(release, pagefind, isa_archive=None, sysreg_archive=None):
    BUILDS.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix=".build-", dir=BUILDS) as temporary:
        scratch = Path(temporary)
        site = scratch / "site"
        site.mkdir()
        for (directory, (package, indexes)), archive in zip(
            PACKAGES.items(), (isa_archive, sysreg_archive), strict=True
        ):
            if archive is None:
                url = archive_url(package, release)
                archive = scratch / f"{directory}.tar.gz"
                print(f"Downloading {url}", flush=True)
                with urlopen(url, timeout=60) as response, archive.open("wb") as output:
                    copyfileobj(response, output)
            release_directory = f"{package.rsplit('/', 1)[-1]}-{release}"
            import_package(archive, site / directory, release_directory, indexes, scratch)

        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        (site / "index.html").write_text(homepage.replace("{{release}}", release), encoding="utf-8")
        subprocess.run([*pagefind, "--site", str(site), "--exclude-selectors", "nav"], check=True)
        if not (site / "pagefind" / "pagefind-entry.json").is_file():
            raise RuntimeError("Pagefind did not produce a search index")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        published = BUILDS / f"{release}-{timestamp}"
        site.rename(published)
        return published


if __name__ == "__main__":
    main()
