# uCore Integration Contract

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

## Local Dev

Use:

```bash
smx capabilities
```

and pass output to uCore extension registry integration.
