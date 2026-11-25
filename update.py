#!/usr/bin/env python3
"""Build a local searchable reference from Arm's versioned XML/HTML archives."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
from shutil import copyfileobj, which
import subprocess
import tarfile
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen


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


def archive_exists(url):
    try:
        with urlopen(Request(url, method="HEAD"), timeout=15) as response:
            if response.headers.get_content_type() in {
                "application/gzip", "application/x-gzip", "application/x-tar",
                "application/octet-stream",
            }:
                return True
            raise ValueError(f"Unexpected content type for {url}: {response.headers.get_content_type()}")
    except HTTPError as error:
        if error.code == 404:
            return False
        raise


def latest_release():
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month
    while (year, month) >= (2026, 9):
        release = f"{year:04d}-{month:02d}"
        if all(archive_exists(archive_url(package, release)) for package, _ in PACKAGES.values()):
            return release
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
    raise ValueError("Arm's CDN did not list a matching monthly release. Try --release YYYY-MM.")


def cached_build(release):
    pattern = f"{release or '*'}-????????T????????????Z"
    return max(
        (path for path in BUILDS.glob(pattern)
         if (path / "index.html").is_file() and (path / "pagefind/pagefind-entry.json").is_file()),
        default=None,
    )


def indexer(pagefind):
    if pagefind:
        executable = pagefind.resolve()
        if not executable.is_file():
            raise ValueError(f"Pagefind executable not found: {executable}")
        return [str(executable)]
    if executable := which("pagefind"):
        return [executable]
    if executable := which("npx"):
        return [executable, "--yes", "pagefind@1.6.0"]
    raise ValueError("Install Pagefind or Node.js with npx, or pass --pagefind PATH.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", nargs="?", help="Arm release identifier, e.g. 2026-09")
    parser.add_argument("--isa-archive", type=Path, help="Use a previously downloaded ISA archive")
    parser.add_argument("--sysreg-archive", type=Path, help="Use a previously downloaded register archive")
    parser.add_argument("--pagefind", type=Path, help="Path to an installed Pagefind executable")
    args = parser.parse_args()
    if args.release and not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])(?:_\d+)?", args.release):
        parser.error("release must be YYYY-MM, optionally with an Arm suffix such as _96")

    try:
        release = args.release or latest_release()
        published = None
        if args.release is None and args.isa_archive is None and args.sysreg_archive is None:
            published = cached_build(release)
        if published is None:
            published = build(release, indexer(args.pagefind), args.isa_archive, args.sysreg_archive)
            print(f"Built {published}")
        else:
            print(f"Already up to date: {published}")
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.exit(1, f"{error}\n")
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
