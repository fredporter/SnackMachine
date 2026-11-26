"""Capability manifest for uCore extension handshake."""
from __future__ import annotations


def capability_manifest() -> dict:
    return {
        "id": "snackmachine-extension",
        "version": "0.1.0",
        "display_name": "SnackMachine Extension",
        "provides": [
            "snacks.catalog",
            "snacks.packages.install",
            "snacks.packages.uninstall",
            "snacks.packages.list",
            "snacks.submit",
            "snacks.bridge.apple_intelligence",
        ],
        "requires_ucore": ">=4.0.0",
        "status": "active",
        "bridge": {
            "available": True,
            "version": "0.1.0",
            "description": "macOS Shortcuts capture with Apple Intelligence optional transform,",
            "requires_profile_grant": True,
        },
    }
