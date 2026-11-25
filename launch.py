#!/usr/bin/env python3
"""Update and serve a local Arm reference portal."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import subprocess
import tarfile

from update import build, cached_build, indexer, latest_release


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
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
