# swabb — Cloud Housekeeping CLI (M0 skeleton)

**swabb** is a safe‑by‑default CLI that will scan → report → (later) clean unused cloud resources.
This M0 delivers a runnable repo with:

- ✅ `src` layout, single argparse entrypoint
- ✅ `-V/--version` (banner supports future build metadata injection)
- ✅ `scan` command (loads config, iterates regions — **no AWS calls yet**)
- ✅ Audit logger (rotating file) and table/JSON printers

> The version banner is compatible with a future packaging step that injects
> `_build_meta.py`, mirroring the approach from the whyx build scripts. :contentReference[oaicite:1]{index=1}
