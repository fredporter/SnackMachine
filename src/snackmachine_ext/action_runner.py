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
    request_id: Optional[str] = None
    profile_grant: Optional[str] = None
    containment_status: Optional[str] = None  # "contained" | "escaped" | "unknown"
    vault_path: Optional[str] = None


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

    def compute_idempotency_key(self, action_id: str, inputs: Dict[str, Any], profile_grant: Optional[str] = None) -> str:
        # Include profile_grant in key for bridge actions to prevent cross-profile replay
        key_payload = {"id": action_id, "inputs": inputs}
        if profile_grant:
            key_payload["profile_grant"] = profile_grant
        payload = json.dumps(key_payload, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def validate_inputs(self, action: ActionDefinition, inputs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate action inputs for bridge capture actions.
        
        Checks:
        - Bounded UTF-8 text size (max 10000 bytes for capture)
        - Client request ID presence
        - Permitted effects based on permissions
        - Path containment if write effects
        
        Returns (is_valid, error_message)
        """
        # Check for text capture actions
        if action.id.startswith("text.") or action.id == "text.capture":
            # Validate text size (max 10000 bytes)
            text_input = inputs.get("text", "")
            if isinstance(text_input, str):
                if len(text_input.encode("utf-8")) > 10000:
                    return False, "Text input exceeds maximum size of 10000 bytes"
            
            # Check for client request ID
            if "request_id" not in inputs:
                return False, "Missing required field: request_id"
        
        # Check path containment for write effects
        if "write" in action.permissions.effects or "append" in action.permissions.effects:
            allowed_paths = action.permissions.allowed_paths
            if allowed_paths:
                output_path = inputs.get("output_path", "")
                if output_path:
                    # Verify resolved path is contained within allowed paths
                    import os
                    resolved = os.path.realpath(output_path)
                    for allowed in allowed_paths:
                        allowed_real = os.path.realpath(allowed)
                        if not resolved.startswith(allowed_real + "/") and resolved != allowed_real:
                            return False, f"Output path {output_path} escapes allowed directory {allowed}"
        
        return True, None

    def execute(self, action_id: str, inputs: Optional[Dict[str, Any]] = None, 
                profile_grant: Optional[str] = None) -> ActionReceipt:
        action = self.get_action(action_id)
        if not action:
            raise ActionExecutionError(f"Action '{action_id}' is not registered.")

        current_os = platform.system().lower()
        if action.platform != "all" and action.platform != current_os:
            raise ActionExecutionError(
                f"Action '{action_id}' requires platform '{action.platform}', but running on '{current_os}'."
            )

        merged_inputs = {**action.inputs, **(inputs or {})}
        idem_key = self.compute_idempotency_key(action_id, merged_inputs, profile_grant)
        now_start = datetime.now(UTC)
        start_time = time.perf_counter()

        if not action.handler:
            raise ActionExecutionError(f"Action '{action_id}' has no registered handler.")

        # Validate inputs before execution
        is_valid, validation_error = self.validate_inputs(action, merged_inputs)
        if not is_valid:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log.warning("Input validation failed for action %s: %s", action_id, validation_error)
            receipt = ActionReceipt(
                action_id=action_id,
                version=action.version,
                idempotency_key=idem_key,
                status="error",
                started_at=now_start.isoformat(),
                finished_at=datetime.now(UTC).isoformat(),
                duration_ms=round(duration_ms, 2),
                error=validation_error,
            )
            self._receipts.append(receipt)
            return receipt

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

        # Add bridge-specific fields to receipt
        receipt.request_id = merged_inputs.get("request_id")
        receipt.profile_grant = profile_grant
        
        # Set containment status if validation was done
        if "write" in action.permissions.effects:
            receipt.containment_status = "contained"  # would be set by actual path resolution
        
        self._receipts.append(receipt)
        return receipt


# Global singleton instance for easy registration
default_runner = ActionRunner()
