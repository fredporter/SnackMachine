"""Dynamic Product Launcher Discovery.

Discovers installed host applications and uDOS ecosystem products.
Enforces the Zen Ecosystem Contract: Absent products remain completely hidden.
"""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

CODE_ROOT = Path.home() / "Code"
APPLICATIONS_DIRS = [
    Path("/Applications"),
    Path("/System/Applications"),
    Path.home() / "Applications",
]


def _app_bundle_exists(app_name: str) -> Optional[Path]:
    """Check if an .app bundle exists in standard macOS application directories."""
    bundle_name = f"{app_name}.app" if not app_name.endswith(".app") else app_name
    for app_dir in APPLICATIONS_DIRS:
        candidate = app_dir / bundle_name
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def get_all_product_definitions() -> List[Dict[str, Any]]:
    """Master catalogue of supported ecosystem and host applications."""
    return [
        {
            "id": "obsidian",
            "name": "Obsidian Vault",
            "category": "vault",
            "icon": "folder_special",
            "description": "Personal knowledge base & Markdown vault",
            "type": "host_app",
            "app_names": ["Obsidian"],
            "launch_command": ["open", "-a", "Obsidian"],
            "open_target": str(Path.home() / "Vault"),
        },
        {
            "id": "ucore",
            "name": "uCore Desktop",
            "category": "ecosystem",
            "icon": "desktop_windows",
            "description": "Sovereign desktop host & notebook production pipeline",
            "type": "repo",
            "repo_path": CODE_ROOT / "uCore",
            "launch_command": ["python3", "-m", "app.main"],
        },
        {
            "id": "ucode",
            "name": "uCode Studio",
            "category": "ecosystem",
            "icon": "terminal",
            "description": "GridCore 2D BASIC & Amiga NetHack pod",
            "type": "repo",
            "repo_path": CODE_ROOT / "uCode",
            "launch_command": ["python3", "-m", "ucode_runtime"],
        },
        {
            "id": "ucode2",
            "name": "uCode 2 (Spatial)",
            "category": "ecosystem",
            "icon": "view_in_ar",
            "description": "3D spatial scene interpreter & Minecraft voxel lifter",
            "type": "repo",
            "repo_path": CODE_ROOT / "uCode2",
            "launch_command": ["python3", "-m", "ucode2.cli", "lift"],
        },
        {
            "id": "ucore-publish",
            "name": "uCore Publish",
            "category": "ecosystem",
            "icon": "publish",
            "description": "Clean edition static compiler and publication pipeline",
            "type": "repo",
            "repo_path": CODE_ROOT / "uCore-Publish" if (CODE_ROOT / "uCore-Publish").exists() else CODE_ROOT / "udos-publishing",
        },
        {
            "id": "homenest",
            "name": "HomeNest",
            "category": "ecosystem",
            "icon": "tv",
            "description": "Living-room media server & entertainment hub",
            "type": "repo",
            "repo_path": CODE_ROOT / "HomeNest",
        },
        {
            "id": "uvector",
            "name": "uVector Studio",
            "category": "ecosystem",
            "icon": "draw",
            "description": "Vector illustration & SVG optimization engine",
            "type": "repo",
            "repo_path": CODE_ROOT / "uVector",
        },
        {
            "id": "groovebox",
            "name": "Groovebox",
            "category": "ecosystem",
            "icon": "music_note",
            "description": "Standalone pattern music synthesis suite",
            "type": "repo",
            "repo_path": CODE_ROOT / "Groovebox",
        },
        {
            "id": "sonicscrewdriver",
            "name": "Sonic Screwdriver",
            "category": "ecosystem",
            "icon": "build",
            "description": "Hardware diagnostics, device revival, and provisioning",
            "type": "repo",
            "repo_path": CODE_ROOT / "SonicScrewdriver",
        },
        {
            "id": "apple-notes",
            "name": "Apple Notes",
            "category": "host_pim",
            "icon": "note",
            "description": "Host-native quick notes and clip storage",
            "type": "host_app",
            "app_names": ["Notes"],
            "launch_command": ["open", "-a", "Notes"],
        },
        {
            "id": "apple-reminders",
            "name": "Apple Reminders",
            "category": "host_pim",
            "icon": "checklist",
            "description": "Host-native task and reminder checklists",
            "type": "host_app",
            "app_names": ["Reminders"],
            "launch_command": ["open", "-a", "Reminders"],
        },
        {
            "id": "apple-calendar",
            "name": "Apple Calendar",
            "category": "host_pim",
            "icon": "calendar_month",
            "description": "Host-native calendar schedules and events",
            "type": "host_app",
            "app_names": ["Calendar"],
            "launch_command": ["open", "-a", "Calendar"],
        },
        {
            "id": "apple-mail",
            "name": "Apple Mail",
            "category": "host_pim",
            "icon": "mail",
            "description": "Host-native email communications",
            "type": "host_app",
            "app_names": ["Mail"],
            "launch_command": ["open", "-a", "Mail"],
        },
    ]


def discover_launchers(include_absent: bool = False) -> List[Dict[str, Any]]:
    """Inspect environment and return active product launchers.
    
    Absent products are strictly filtered out by default.
    """
    is_mac = platform.system().lower() == "darwin"
    all_defs = get_all_product_definitions()
    results: List[Dict[str, Any]] = []

    for item in all_defs:
        installed = False
        resolved_path: Optional[str] = None

        if item["type"] == "repo":
            rpath: Path = item["repo_path"]
            if rpath.is_dir() and (rpath / ".git").exists():
                installed = True
                resolved_path = str(rpath)
        elif item["type"] == "host_app":
            if is_mac:
                for app_name in item.get("app_names", []):
                    bundle = _app_bundle_exists(app_name)
                    if bundle:
                        installed = True
                        resolved_path = str(bundle)
                        break
            else:
                # On non-Mac, check CLI binary
                bin_name = item["id"].replace("apple-", "")
                if shutil.which(bin_name):
                    installed = True
                    resolved_path = shutil.which(bin_name)

        if installed or include_absent:
            entry = {
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "icon": item["icon"],
                "description": item["description"],
                "installed": installed,
                "path": resolved_path,
                "launch_command": item.get("launch_command", []),
            }
            if item.get("open_target"):
                entry["open_target"] = item["open_target"]
            results.append(entry)

    return results
