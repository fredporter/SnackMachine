"""Bounded Apple Activity Capture Engine.

Complies with UDOS_PRODUCT_REFACTOR_PLAN_2026-09-12 Section 10:
- Bounded read-only capture of Calendar, Reminders, Notes, and Mail.
- Deduplication against ~/Vault/Activity/events.jsonl by external ID.
- Generates ~/Vault/Activity/Daily_Activity.md with anti-drift preservation of user annotations.
- Works standalone without a running uCore daemon.
"""
from __future__ import annotations

import hashlib
import json
import logging
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

log = logging.getLogger("snackmachine.activity_capture")

VAULT_ROOT = Path.home() / "Vault"
ACTIVITY_DIR = VAULT_ROOT / "Activity"
EVENTS_FILE = ACTIVITY_DIR / "events.jsonl"
DAILY_ACTIVITY_FILE = ACTIVITY_DIR / "Daily_Activity.md"


def get_activity_dir() -> Path:
    ACTIVITY_DIR.mkdir(parents=True, exist_ok=True)
    return ACTIVITY_DIR


def _default_jxa_runner(script: str) -> List[Dict[str, Any]]:
    """Execute a JXA (JavaScript for Automation) script producing JSON."""
    if platform.system().lower() != "darwin" or shutil.which("osascript") is None:
        return []
    proc = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if proc.returncode != 0:
        log.warning("JXA script execution returned code %s: %s", proc.returncode, proc.stderr.strip())
        return []
    try:
        data = json.loads(proc.stdout.strip() or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


JXA_SCRIPTS = {
    "calendar": """
    (() => {
        try {
            const app = Application("Calendar");
            if (!app.running()) return JSON.stringify([]);
            const rows = [];
            const cutoff = new Date(Date.now() - 7 * 86400000);
            for (const cal of app.calendars()) {
                for (const ev of cal.events()) {
                    const start = ev.startDate();
                    if (start >= cutoff) {
                        rows.push({
                            external_id: "cal-" + String(ev.uid()),
                            title: String(ev.summary() || "Untitled Event"),
                            content: String(ev.description() || ""),
                            timestamp: start.toISOString(),
                            source: "calendar"
                        });
                        if (rows.length >= 25) break;
                    }
                }
                if (rows.length >= 25) break;
            }
            return JSON.stringify(rows);
        } catch(e) { return JSON.stringify([]); }
    })()
    """,
    "reminders": """
    (() => {
        try {
            const app = Application("Reminders");
            if (!app.running()) return JSON.stringify([]);
            const rows = [];
            const list = app.defaultList();
            const items = list.reminders.whose({ completed: false })();
            for (let i = 0; i < Math.min(items.length, 25); i++) {
                const r = items[i];
                rows.push({
                    external_id: "rem-" + String(r.id()),
                    title: String(r.name() || "Untitled Reminder"),
                    content: String(r.body() || ""),
                    timestamp: new Date().toISOString(),
                    source: "reminders"
                });
            }
            return JSON.stringify(rows);
        } catch(e) { return JSON.stringify([]); }
    })()
    """,
    "notes": """
    (() => {
        try {
            const app = Application("Notes");
            if (!app.running()) return JSON.stringify([]);
            const rows = [];
            const notes = app.notes();
            for (let i = 0; i < Math.min(notes.length, 15); i++) {
                const n = notes[i];
                rows.push({
                    external_id: "note-" + String(n.id()),
                    title: String(n.name() || "Untitled Note"),
                    content: String(n.body() || "").slice(0, 300),
                    timestamp: new Date().toISOString(),
                    source: "notes"
                });
            }
            return JSON.stringify(rows);
        } catch(e) { return JSON.stringify([]); }
    })()
    """,
    "mail": """
    (() => {
        try {
            const app = Application("Mail");
            if (!app.running()) return JSON.stringify([]);
            const rows = [];
            const msgs = app.inbox.messages();
            for (let i = 0; i < Math.min(msgs.length, 25); i++) {
                const m = msgs[i];
                if (!m.readStatus()) {
                    rows.push({
                        external_id: "mail-" + String(m.messageId()),
                        title: String(m.subject() || "No Subject"),
                        content: "From: " + String(m.sender() || "") + "\\n" + String(m.content() || "").slice(0, 200),
                        timestamp: new Date().toISOString(),
                        source: "mail"
                    });
                }
            }
            return JSON.stringify(rows);
        } catch(e) { return JSON.stringify([]); }
    })()
    """
}


class ActivityCaptureEngine:
    """Captures Apple activity data into ~/Vault/Activity with deduplication and Markdown view."""

    def __init__(
        self,
        vault_root: Optional[Path] = None,
        runner: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
    ) -> None:
        self.vault_root = vault_root or VAULT_ROOT
        self.activity_dir = self.vault_root / "Activity"
        self.events_file = self.activity_dir / "events.jsonl"
        self.markdown_file = self.activity_dir / "Daily_Activity.md"
        self.runner = runner or _default_jxa_runner

    def _load_existing_ids(self) -> Set[str]:
        """Read all previously captured external_ids from events.jsonl."""
        existing_ids = set()
        if self.events_file.is_file():
            try:
                for line in self.events_file.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        item = json.loads(line)
                        if "external_id" in item:
                            existing_ids.add(item["external_id"])
            except Exception as exc:
                log.warning("Failed reading existing activity events: %s", exc)
        return existing_ids

    def capture_source(self, source: str) -> List[Dict[str, Any]]:
        """Capture items for a single source."""
        script = JXA_SCRIPTS.get(source)
        if not script:
            return []
        return self.runner(script)

    def run_sync(self, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run idempotent capture across selected sources."""
        self.activity_dir.mkdir(parents=True, exist_ok=True)
        target_sources = sources or ["calendar", "reminders", "notes", "mail"]
        existing_ids = self._load_existing_ids()

        new_events: List[Dict[str, Any]] = []
        captured_counts: Dict[str, int] = {}
        now_iso = datetime.now(UTC).isoformat()

        for src in target_sources:
            items = self.capture_source(src)
            captured_counts[src] = 0
            for item in items:
                ext_id = item.get("external_id")
                if not ext_id:
                    # Fallback hash-based ID
                    payload = f"{src}:{item.get('title')}:{item.get('timestamp')}"
                    ext_id = f"{src}-{hashlib.sha256(payload.encode()).hexdigest()[:16]}"
                    item["external_id"] = ext_id

                if ext_id in existing_ids:
                    continue

                event_record = {
                    "external_id": ext_id,
                    "source": src,
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "timestamp": item.get("timestamp", now_iso),
                    "captured_at": now_iso,
                    "privacy": "private",
                }
                new_events.append(event_record)
                existing_ids.add(ext_id)
                captured_counts[src] += 1

        # Append new records to events.jsonl
        if new_events:
            with open(self.events_file, "a", encoding="utf-8") as f:
                for ev in new_events:
                    f.write(json.dumps(ev) + "\n")

        # Regenerate human-readable Daily_Activity.md preserving user annotations
        self.update_activity_markdown()

        return {
            "ok": True,
            "new_events_count": len(new_events),
            "sources_captured": captured_counts,
            "events_file": str(self.events_file),
            "markdown_file": str(self.markdown_file),
        }

    def update_activity_markdown(self) -> None:
        """Render Daily_Activity.md preserving any user notes in the USER ANNOTATIONS section."""
        user_annotations = ""
        if self.markdown_file.is_file():
            content = self.markdown_file.read_text(encoding="utf-8")
            if "<!-- BEGIN USER ANNOTATIONS -->" in content and "<!-- END USER ANNOTATIONS -->" in content:
                parts = content.split("<!-- BEGIN USER ANNOTATIONS -->")
                if len(parts) > 1:
                    subparts = parts[1].split("<!-- END USER ANNOTATIONS -->")
                    user_annotations = subparts[0].strip()

        if not user_annotations:
            user_annotations = "- Add custom priorities, reflections, and follow-ups here.\n- This block is preserved across all automatic activity refreshes."

        # Load recent events from jsonl
        events: List[Dict[str, Any]] = []
        if self.events_file.is_file():
            try:
                for line in self.events_file.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        events.append(json.loads(line))
            except Exception:
                pass

        # Sort descending by timestamp
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        recent_events = events[:40]

        generated_lines = [
            f"> *Last synchronized: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}* · *Total events: {len(events)}*\n",
        ]

        by_source: Dict[str, List[Dict[str, Any]]] = {}
        for ev in recent_events:
            src = ev.get("source", "other")
            by_source.setdefault(src, []).append(ev)

        for src_title, src_key in [("Calendar Events", "calendar"), ("Reminders & Tasks", "reminders"), ("Unread Mail", "mail"), ("Recent Notes", "notes")]:
            items = by_source.get(src_key, [])
            generated_lines.append(f"### {src_title} ({len(items)})")
            if not items:
                generated_lines.append("_No items recorded._\n")
            else:
                for it in items:
                    t = it.get("timestamp", "")[:16].replace("T", " ")
                    generated_lines.append(f"- **{it.get('title')}** ({t})")
                    snippet = it.get("content", "").strip().split("\n")[0]
                    if snippet:
                        generated_lines.append(f"  > {snippet[:120]}")
                generated_lines.append("")

        generated_body = "\n".join(generated_lines)

        full_document = f"""# Daily Activity & Host PIM Feed

<!-- BEGIN GENERATED ACTIVITY -->
{generated_body}
<!-- END GENERATED ACTIVITY -->

## Personal Annotations & Review Notes
<!-- BEGIN USER ANNOTATIONS -->
{user_annotations}
<!-- END USER ANNOTATIONS -->
"""
        self.markdown_file.write_text(full_document, encoding="utf-8")
