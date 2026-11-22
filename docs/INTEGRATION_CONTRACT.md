# uCore Integration Contract

## Canonical Terms

- `Snack`: small executable unit (script/code action).
- `Snackbox`: grouped package of related Snacks.
- `SnackShack`: catalog/store interface for browsing/installing Snackboxes and
  Snacks.
- `SnackMachine`: extension runtime that manages SnackShack, install state, and
  extension capabilities.
- `Snackbar`: uCore core daemon API/runtime (not the extension store).

## Extension Identity

- id: snackmachine-extension
- minimum uCore: >= 4.0.0

## Capability Handshake

The extension must provide a capabilities payload that uCore can read.

Required keys:

- id
- version
- provides[]
- requires_ucore
- status

## Initial Capabilities

- snacks.catalog
- snacks.packages.install
- snacks.packages.uninstall
- snacks.packages.list

## uCore Behavior

When extension is unavailable:

- uCore keeps popcorn menu and core snack workspace active.
- Packaged snack actions are hidden or disabled.

When extension is available:

- uCore enables packaged snack install/uninstall actions.
- uCore may expose extension routes/actions in Server/System surfaces.

## Ownership Boundary

uCore core:

- daemon lifecycle and health
- popcorn menu and launchers
- baseline snack queue/status routes

SnackMachine extension:

- SnackShack store/catalog
- Snack and Snackbox metadata
- package install/uninstall/update flow
- submission and validation workflow

If removing a capability breaks backend startup, health checks, menu startup,
or opening core surfaces, that capability belongs in uCore core.

## Local Dev

Use:

```bash
smx capabilities
```

and pass output to uCore extension registry integration.

## Planned Apple Intelligence bridge

The [bridge plan](APPLE_INTELLIGENCE_BRIDGE.md) describes the macOS Shortcuts
pilot, capability ownership and uFlow receipt. The initial capability handshake
above describes the currently available extension.
