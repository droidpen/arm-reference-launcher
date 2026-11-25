#!/usr/bin/env python3
"""Update and serve a local Arm reference portal."""

import argparse
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from shutil import which
import subprocess
import tarfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from update import BUILDS, PACKAGES, archive_url, build


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
        return [str(pagefind.resolve())]
    if executable := which("pagefind"):
        return [executable]
    if executable := which("npx"):
        return [executable, "--yes", "pagefind@1.6.0"]
    raise ValueError("Install Pagefind or Node.js with npx, or pass --pagefind PATH.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", help="Select a specific Arm release (YYYY-MM)")
    parser.add_argument("--offline", action="store_true", help="Use a cached build without network access")
    parser.add_argument("--pagefind", type=Path, help="Use an existing Pagefind executable")
    parser.add_argument("--port", type=int, default=8001, help="Local HTTP port (default: 8001)")
    args = parser.parse_args()
    if args.release and not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", args.release):
        parser.error("--release must be YYYY-MM")
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")

    try:
        with ThreadingHTTPServer(("127.0.0.1", args.port), SimpleHTTPRequestHandler) as server:
            release = args.release
            if not args.offline and release is None:
                release = latest_release()
                print(f"Latest matching Arm release: {release}", flush=True)
            site = cached_build(release)
            if site is None:
                if args.offline:
                    raise ValueError("No cached build matches this request. Run once without --offline.")
                site = build(release, indexer(args.pagefind))
            server.RequestHandlerClass = partial(SimpleHTTPRequestHandler, directory=site)
            print(f"Serving {site.name} at http://127.0.0.1:{server.server_port}/", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return
    except (OSError, URLError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
