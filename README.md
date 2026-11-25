# Arm Reference Launcher

Build and browse a searchable local copy of Arm's A64 instruction and system
register documentation.

## Quick start

You need Python 3.12 or newer and either Pagefind 1.6 or newer on your PATH
or Node.js with `npx`. On the first build, the launcher uses
`npx --yes pagefind@1.6.0` if Pagefind is absent. Review the terms of Arm's
archives before downloading them.

```bash
git clone https://github.com/droidpen/arm-reference-launcher.git
cd arm-reference-launcher
python3 launch.py
```

Open [http://127.0.0.1:8001/](http://127.0.0.1:8001/) when the launcher prints
the URL. Press Ctrl+C to stop the server.

The launcher checks Arm's CDN for the newest monthly release with both
archives, builds and indexes it if needed, then serves the cached site.
It recognizes standard `YYYY-MM` archive names from 2026-09 onward.
If port 8001 is busy, use `python3 launch.py --port 8002`.

## Update without serving

```bash
python3 update.py
```

Run this from the clone directory. It checks for the latest release,
builds it if needed, and exits without starting a server.
Use `python3 launch.py --offline` to start the cached portal without
another network check. The flag is optional.

## Choose a release or use local archives

Use `python3 launch.py --release 2026-09` to serve a specific release,
or `python3 update.py 2026-09` to build it. Both commands accept
`--pagefind /path/to/pagefind` to select a specific executable.

To build from archives you've already downloaded, pass both paths:

```bash
python3 update.py 2026-09 \
  --isa-archive /path/to/ISA_A64_xml_A_profile-2026-09.tar.gz \
  --sysreg-archive /path/to/SysReg_xml_A_profile-2026-09.tar.gz
```

The updater uses the selected release's bundled HTML and styles. Generated
builds are stored locally under `builds/` and ignored by Git. See
[Arm's collateral listing](https://support.arm.com/documentation/ddi0487/md/251-chdhfbec)
for the archive descriptions.
