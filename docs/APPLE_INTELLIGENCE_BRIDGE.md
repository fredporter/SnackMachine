# SnackMachine Apple Intelligence bridge

Status: proposed. The first milestone is a user-initiated capture on macOS with a
uFlow receipt. It should work with typed or dictated text. Apple Intelligence
can optionally help transform the text before the user reviews it.

## Pilot

1. In Shortcuts, accept typed or dictated text. Optionally use Writing Tools
   before handoff or add a Use Model action when available. Show the final text
   and destination for review.
2. Validate on the target Mac whether Shortcuts can call a scoped uCore
   loopback endpoint and present its result. Reuse the existing authentication
   boundary if it supports a scoped grant. If Shortcuts cannot store or present
   that grant safely, use an authenticated uCore UI handoff for the pilot and
   defer direct submission.
3. Admit one reviewed capture action. Accept only bounded UTF-8 text and a
   client request ID. Derive the active profile and destination on the server.
   Save to a profile-approved Vault folder through uFlow and return a run ID
   and status. A receipt can report the resulting file after a successful write.

Illustrative contract for direct submission:

| Concern | Proposed behavior |
| --- | --- |
| Admission | uCore authenticates the client and checks the profile grant, installed capability, text size and permitted effect. |
| Destination | Resolve the configured directory through the profile's Vault settings. Generate a unique filename and verify resolved containment before writing. |
| Retry | Deduplicate by profile and request ID. Return the existing run for an identical replay and report a conflict if its input differs. |
| Errors | Surface unavailable service, missing grant, invalid input, and failed run in Shortcuts or uCore. Preserve reviewed text for user retry. |
| Records | Store the output in Vault and the receipt in the existing uFlow store under settings-resolved `UDOS_HOME`. Keep capture text, tokens, and absolute user paths out of operational logs. |

SnackMachine owns the capture capability metadata and action lifecycle. uCore
owns the service, session and profile boundary. uFlow owns submission,
execution and receipts. Shortcuts supplies input and user review. Apple model
output is plain text, with no authority to choose actions, destinations,
execution parameters or grants. Keep the bridge within the existing uCore
service lifecycle. Budget the pilot for one small text payload and one write per
request, with bounded time and no uDOS model call. Optional Apple model use is
subject to the selected Shortcuts action and device availability.

## Acceptance and rollout

- Verify typed and dictated capture on the M2 Mac, including a model-free run
  with networking disabled. Verify the actual file and receipt.
- Exercise duplicate submission, conflicting replay, over-limit text, service
  interruption, cancellation, denied or revoked grant, profile switch, and
  directory escape through symbolic links.
- Ship behind a capability that is advertised only when the bridge is available.
  Disable it by revoking the profile grant and withdrawing the capability.
  Remove the shortcut independently. Preserve existing Vault files and receipts
  according to their normal retention rules.
- Consider native App Intents after the pilot demonstrates demand for native
  action discovery and the installation, signing and update lifecycle has an
  owner. Verify Siri and Apple Intelligence availability on supported devices
  before promising invocation from either surface.

[Apple Intelligence in Shortcuts](https://support.apple.com/guide/shortcuts-mac/use-apple-intelligence-in-shortcuts-mchl91750563/mac)
· [Apple App Intents documentation](https://developer.apple.com/documentation/appintents)
