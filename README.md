# Local Arm reference updater

## Launch from a clone

This directory is a standalone source tree. When published on GitHub, clone it
and run this from the clone's root (or use `python3 updater/launch.py` from the
current workspace).

```bash
python3 launch.py
```

The launcher checks Arm's CDN for the newest monthly release with both archives,
starting at the current UTC month and looking back to the known 2026-09 release.
It recognizes the standard `YYYY-MM` archive names. It builds once per release
and serves the cached site on [localhost:8001](http://127.0.0.1:8001/). Press
Ctrl+C to stop. On a cache miss it uses Pagefind on PATH or runs
`npx --yes pagefind@1.6.0`. This requires Python 3.12+ and either Pagefind
or Node.js with npx. Review Arm's archive terms before running the first build.

Use `--offline` for an immediate cached launch with no network access,
`--release 2026-09` to select a release, `--pagefind /path/to/pagefind` to
select an installed indexer, or `--port 8002` if port 8001 is occupied.

Publish the files in this directory as the GitHub repository root. Keep
`builds/` and the original mirror out of the published repository.

## Update without starting the server

Run `python3 update.py` to check the latest release, build it if needed, and
print a command to serve it later. It uses the same Pagefind selection as the
launcher. You can also select a release and Pagefind executable explicitly.

Run from the repository root with Python 3.12+ and an existing Pagefind executable
that provides the Component UI. This command uses the Pagefind 1.6.0 executable
previously downloaded on this machine.

```bash
python3 updater/update.py 2026-09 \
  --pagefind /tmp/armspeck-npm-approved/_npx/*/node_modules/.bin/pagefind
```

If that temporary npm cache is gone, supply the path to another Pagefind
executable (for example, `--pagefind "$(command -v pagefind)"` when installed
on PATH). The updater itself installs no dependencies.

Choose a release from [Arm's architecture collateral listing](https://support.arm.com/documentation/ddi0487/mc/Preface/About-this-Manual/Corresponding-Collateral)
and review the download terms. The default source is Arm's two versioned CDN
archives. To use archives you've already downloaded, pass both paths.

```bash
python3 updater/update.py 2026-09 \
  --isa-archive /path/to/ISA_A64_xml_A_profile-2026-09.tar.gz \
  --sysreg-archive /path/to/SysReg_xml_A_profile-2026-09.tar.gz \
  --pagefind /path/to/pagefind
```

Each archive must contain the selected release's `xhtml` tree and expected
index pages. The updater uses Arm's rendered HTML and its bundled styles.
It adds a searchable homepage and preserves the instruction and register URL
prefixes. It indexes only the selected release, excluding the old releases
and diff trees shipped alongside it.

A successful build prints the exact command for serving it on port 8001.
Generated builds are gitignored and stored separately under `updater/builds/`.
To switch versions or roll back, serve a different build directory.
