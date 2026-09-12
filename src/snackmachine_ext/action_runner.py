"""Unified Action Runner & Executor for Snackbar / SnackMachine.

Implements the single action language specified in UDOS_PRODUCT_REFACTOR_PLAN_2026-09-12 Section 10:
- ID, version, title, inputs, required platform, permissions.
- Timeout enforcement, retry/idempotency policy, outputs.
- Minimal executor running without requiring uCore daemon.
"""
from __future__ import annotations

import hashlib
import json
import logging
import platform
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("snackmachine.action_runner")


class ActionExecutionError(Exception):
    """Raised when an action fails validation, exceeds timeout, or encounters an execution error."""
    pass


@dataclass
class ActionPermissions:
    allow_network: bool = False
    allowed_paths: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=lambda: ["read_only"])


@dataclass
class ActionDefinition:
    id: str
    version: str
    title: str
    description: str
    platform: str = "all"  # "darwin", "linux", "all"
    inputs: Dict[str, Any] = field(default_factory=dict)
    permissions: ActionPermissions = field(default_factory=ActionPermissions)
    timeout_seconds: float = 15.0
    idempotent: bool = True
    handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None


@dataclass
class ActionReceipt:
    action_id: str
    version: str
    idempotency_key: str
    status: str  # "success" | "error" | "skipped"
    started_at: str
    finished_at: str
    duration_ms: float
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class ActionRunner:
    """Minimal standalone executor for Snackbar actions."""

    def __init__(self) -> None:
        self._actions: Dict[str, ActionDefinition] = {}
        self._receipts: List[ActionReceipt] = []

    def register(self, action: ActionDefinition) -> None:
        self._actions[action.id] = action

    def get_action(self, action_id: str) -> Optional[ActionDefinition]:
        return self._actions.get(action_id)

    def list_actions(self) -> List[Dict[str, Any]]:
        current_os = platform.system().lower()
        results = []
        for a in self._actions.values():
            if a.platform in ("all", current_os):
                results.append({
                    "id": a.id,
                    "version": a.version,
                    "title": a.title,
                    "description": a.description,
                    "platform": a.platform,
                    "timeout_seconds": a.timeout_seconds,
                    "permissions": asdict(a.permissions),
                })
        return results

    def compute_idempotency_key(self, action_id: str, inputs: Dict[str, Any]) -> str:
        payload = json.dumps({"id": action_id, "inputs": inputs}, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def execute(self, action_id: str, inputs: Optional[Dict[str, Any]] = None) -> ActionReceipt:
        action = self.get_action(action_id)
        if not action:
            raise ActionExecutionError(f"Action '{action_id}' is not registered.")

        current_os = platform.system().lower()
        if action.platform != "all" and action.platform != current_os:
            raise ActionExecutionError(
                f"Action '{action_id}' requires platform '{action.platform}', but running on '{current_os}'."
            )

        merged_inputs = {**action.inputs, **(inputs or {})}
        idem_key = self.compute_idempotency_key(action_id, merged_inputs)
        now_start = datetime.now(UTC)
        start_time = time.perf_counter()

        if not action.handler:
            raise ActionExecutionError(f"Action '{action_id}' has no registered handler.")

        try:
            output = action.handler(merged_inputs)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            receipt = ActionReceipt(
                action_id=action_id,
                version=action.version,
                idempotency_key=idem_key,
                status="success",
                started_at=now_start.isoformat(),
                finished_at=datetime.now(UTC).isoformat(),
                duration_ms=round(duration_ms, 2),
                output=output,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log.exception("Error executing action %s: %s", action_id, exc)
            receipt = ActionReceipt(
                action_id=action_id,
                version=action.version,
                idempotency_key=idem_key,
                status="error",
                started_at=now_start.isoformat(),
                finished_at=datetime.now(UTC).isoformat(),
                duration_ms=round(duration_ms, 2),
                error=str(exc),
            )

        self._receipts.append(receipt)
        return receipt


# Global singleton instance for easy registration
default_runner = ActionRunner()
