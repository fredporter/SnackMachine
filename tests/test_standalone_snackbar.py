"""Tests for Standalone Snackbar & Apple Activity (Milestone P6).

Verifies:
1. Product launcher discovery: Installed products present, absent products strictly hidden.
2. Action runner execution, input validation, and receipt generation.
3. Activity capture deduplication against events.jsonl.
4. User annotation preservation across markdown view refreshes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from snackmachine_ext.action_runner import ActionDefinition, ActionPermissions, ActionRunner
from snackmachine_ext.activity_capture import ActivityCaptureEngine
from snackmachine_ext.launcher import discover_launchers, get_all_product_definitions


class TestProductLauncher(unittest.TestCase):
    def test_absent_products_are_hidden(self):
        # By default, only installed/present products are returned
        launchers = discover_launchers(include_absent=False)
        all_defs = get_all_product_definitions()

        # Should never return more than the total definitions
        self.assertLessEqual(len(launchers), len(all_defs))
        # Every returned launcher must be installed
        for l in launchers:
            self.assertTrue(l["installed"])

        # When include_absent=True, returns all
        all_launchers = discover_launchers(include_absent=True)
        self.assertEqual(len(all_launchers), len(all_defs))


class TestActionRunner(unittest.TestCase):
    def test_action_execution_and_receipt(self):
        runner = ActionRunner()

        def sample_handler(inputs):
            return {"doubled": inputs.get("value", 0) * 2}

        action = ActionDefinition(
            id="math.double",
            version="1.0.0",
            title="Double a number",
            description="Multiplies input value by 2",
            platform="all",
            inputs={"value": 21},
            permissions=ActionPermissions(effects=["read_only"]),
            handler=sample_handler,
        )
        runner.register(action)

        receipt = runner.execute("math.double", {"value": 50})
        self.assertEqual(receipt.status, "success")
        self.assertEqual(receipt.output["doubled"], 100)
        self.assertTrue(receipt.duration_ms >= 0)
        self.assertTrue(len(receipt.idempotency_key) > 0)


class TestActivityCaptureEngine(unittest.TestCase):
    def test_idempotent_capture_and_annotation_preservation(self):
        with TemporaryDirectory(prefix="snack-test-vault-") as tmp:
            vault_dir = Path(tmp)
            engine = ActivityCaptureEngine(vault_root=vault_dir)

            # Mock JXA output for calendar and reminders
            def mock_runner(script: str):
                if "Calendar" in script:
                    return [
                        {
                            "external_id": "cal-uuid-101",
                            "title": "Architecture Review",
                            "content": "Reviewing Milestone P6",
                            "timestamp": "2026-09-13T10:00:00Z",
                            "source": "calendar",
                        }
                    ]
                elif "Reminders" in script:
                    return [
                        {
                            "external_id": "rem-uuid-202",
                            "title": "Publish Release Notes",
                            "content": "Verify clean output",
                            "timestamp": "2026-09-13T12:00:00Z",
                            "source": "reminders",
                        }
                    ]
                return []

            engine.runner = mock_runner

            # 1. First sync run
            result1 = engine.run_sync(sources=["calendar", "reminders"])
            self.assertTrue(result1["ok"])
            self.assertEqual(result1["new_events_count"], 2)

            events_file = vault_dir / "Activity" / "events.jsonl"
            md_file = vault_dir / "Activity" / "Daily_Activity.md"
            self.assertTrue(events_file.is_file())
            self.assertTrue(md_file.is_file())

            md_content = md_file.read_text(encoding="utf-8")
            self.assertIn("Architecture Review", md_content)
            self.assertIn("Publish Release Notes", md_content)

            # 2. User writes personal annotations to the markdown file
            custom_user_notes = (
                "- Follow up with team regarding offline bundles.\n"
                "- Verify EventKit permissions on staging machine."
            )
            annotated_md = md_content.replace(
                "<!-- BEGIN USER ANNOTATIONS -->\n- Add custom priorities, reflections, and follow-ups here.\n- This block is preserved across all automatic activity refreshes.\n<!-- END USER ANNOTATIONS -->",
                f"<!-- BEGIN USER ANNOTATIONS -->\n{custom_user_notes}\n<!-- END USER ANNOTATIONS -->"
            )
            md_file.write_text(annotated_md, encoding="utf-8")

            # 3. Second sync run with identical items
            result2 = engine.run_sync(sources=["calendar", "reminders"])
            self.assertTrue(result2["ok"])
            # Idempotency check: duplicate external IDs skipped!
            self.assertEqual(result2["new_events_count"], 0)

            # 4. Check user annotations survived the refresh
            refreshed_md = md_file.read_text(encoding="utf-8")
            self.assertIn(custom_user_notes, refreshed_md)
            self.assertIn("Architecture Review", refreshed_md)


if __name__ == "__main__":
    unittest.main()
