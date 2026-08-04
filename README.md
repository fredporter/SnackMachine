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
