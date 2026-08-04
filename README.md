# SnackMachine Extension

SnackMachine is an optional extension for uCore that provides packaged snack catalogs,
install flows, and advanced snack operations.

## Purpose

- Keep uCore core runtime lean and reliable.
- Deliver optional snack bundles and workflows independently.
- Provide a stable capability contract back to uCore.

## Scope

This extension owns:
- snack package discovery
- package install/uninstall metadata
- optional snack catalogs
- extension capability handshake

uCore core owns:
- backend daemon
- popcorn menu and launchers
- health checks and lifecycle
- baseline snack queue/status APIs

## Product Model

This model is practical with the current split and should be treated as a
first-class contract:

- `Snackbar` (uCore core): runtime API and queue/orchestration substrate.
- `Popcorn Menu` (uCore core): lightweight launcher and status controls.
- `SnackMachine` (extension): package manager and advanced snack tooling.
- `SnackShack` (extension UX): snack store/catalog browser.
- `Snack` (extension content unit): a small script or code action.
- `Snackbox` (extension bundle unit): a collection of related snacks.

Keep SnackShack as the store metaphor and avoid using it for runtime
components.

## Quick Start

```bash
cd /Users/fredbook/Code/SnackMachine
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
smx doctor
smx capabilities
```

## Contract

See docs/INTEGRATION_CONTRACT.md for uCore integration details.
See docs/SNACK_TAXONOMY.md for the canonical domain vocabulary.
