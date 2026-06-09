# Codex Wrapper Migration Plan

The goal is to move orchestration mechanics out of the parent conversation while
keeping the published plugin usable throughout the migration.

## P0: Wrapper Skeleton

- Add a plugin-side wrapper that resolves the runtime CLI.
- Verify the runtime contract before any runtime-dependent flow.
- Delegate non-mutating gates first: `runtime-contract`, `adapter-smoke`, and
  `validate-loop`.
- Keep the current skill behavior as the default path.

Acceptance:

- The wrapper fails closed when no compatible runtime is available.
- Conformance proves the wrapper can call a fake compatible runtime.
- No runtime semantics are copied into the plugin wrapper.

## P1: Package Boundary

- Vendor the runtime package into the Codex plugin; keep external `swarm-rt`
  only as a development override.
- Update the installer to verify the bundled runtime during install/repair.
- Add a smoke fixture that can be run from the installed plugin root.

Acceptance:

- `doctor` can report plugin root, runtime root, compatibility id, and available
  integration gates from a clean install.
- `doctor --smoke-fixture` can replay the bundled minimal fixture without
  spawning agents.
- Missing runtime produces a clear remediation path.

## P2: Adapter-Facing Smoke In The Plugin

- Teach the skill instructions to run wrapper `adapter-smoke` after a discussion
  writes host transport artifacts.
- Keep the parent context limited to the brief path, current phase, agent ids,
  and next helper command.
- Use runtime evidence output as the primary audit summary.

Acceptance:

- A lightweight smoke discussion can be audited without raw session logs.
- Parent context no longer carries full discussion history for smoke validation.

## P3: Runtime-Owned Prompt And WAL

- Replace manual prompt construction with runtime `context-build` and
  `prompt-build` commands.
- Replace manual id minting and checkpointing with runtime WAL commands.
- Keep host spawning and waiting in the plugin/host layer.

Acceptance:

- The parent conversation never constructs expert prompts or mutates round JSON.
- Resume behavior is derived from runtime artifacts, not parent memory.

## P4: Default Runtime Path

- Make the runtime-backed path the default after repeated clean-install smoke
  runs pass.
- Preserve the legacy flow behind an explicit fallback note for one release.
- Remove fallback instructions only after published installer and marketplace
  validation are stable.

Acceptance:

- Clean install, repair, uninstall, and smoke workflows all pass.
- Artifact evidence is sufficient to diagnose a failed run without replaying the
  full parent transcript.
