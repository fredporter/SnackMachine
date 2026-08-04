# Snack Taxonomy

## Purpose

Define a stable vocabulary for SnackMachine so docs, APIs, UI labels, and
plugin contracts remain consistent.

## Definitions

- `Snack`
  - Small executable unit.
  - Usually one focused action or script.
  - Examples: restart a service, transform text, run a local task.

- `Snackbox`
  - Collection of related Snacks.
  - Versioned package with metadata and optional dependencies.
  - Installed/uninstalled as one unit.

- `SnackShack`
  - The store/catalog UX where users browse, install, and submit Snacks or
    Snackboxes.
  - Product-facing term, not a runtime daemon.

- `SnackMachine`
  - Extension/plugin that powers SnackShack and manages package lifecycle.
  - Provides capability handshake to uCore.

- `Snackbar`
  - Core uCore runtime service and API substrate.
  - Not the store/catalog.

- `Popcorn Menu`
  - Core uCore menu bar launcher/status interface.
  - Opens core surfaces and extension-aware entry points.

## Practical Mapping

This taxonomy matches the current architecture and is practical:

- Core remains stable and minimal (Snackbar + Popcorn Menu).
- Extension can iterate rapidly (SnackMachine + SnackShack + package workflows).
- Naming reduces confusion between runtime and marketplace concepts.

## UI Label Guidance

- Use `Snacks Workspace` for core route labels.
- Use `SnackShack` for store/catalog labels only.
- Use `Snackbox` in package install dialogs and bundle listings.
- Avoid labeling runtime health/status with `SnackShack`.

## API Naming Guidance

- Core queue/status APIs can stay under existing snacks routes.
- Extension APIs should use explicit package nouns:
  - `snackboxes.list`
  - `snackboxes.install`
  - `snackboxes.remove`
  - `snacks.submit`

## Lifecycle

1. User opens Popcorn Menu (core).
2. User opens Snacks Workspace (core).
3. If extension present, user can open SnackShack (extension store).
4. User installs Snackboxes and runs Snacks.
