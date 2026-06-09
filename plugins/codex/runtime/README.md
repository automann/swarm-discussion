# Codex Runtime Wrapper

This directory is the plugin-side integration skeleton for the v2 runtime. The
published skill still uses the legacy in-prompt orchestration path by default.
The wrapper exists so we can exercise the runtime contract from inside the
plugin package without copying runtime logic back into `SKILL.md`.

The wrapper owns only three jobs:

- Resolve a runtime CLI from `--runtime`, `SWARM_DISCUSSION_RUNTIME`, a future
  bundled `runtime/swarm_rt.py`, or `swarm-rt` on `PATH`.
- Verify `runtime-contract` and the `swarm-runtime-v2-alpha` compatibility id.
- Delegate integration gates and runtime primitives such as `prompt-build`,
  `collect-merge`, and WAL commands.

It must not construct prompts, merge wait results, mint message ids, mutate WAL
state, summarize trace/evidence health, install plugins, or manage marketplace
state. Those behaviors belong to the runtime package or the installer.

## Vendored Layout

The installed Codex plugin root mirrors the runtime repository root:

```text
runtime/swarm_runtime_wrapper.py
runtime/swarm_rt.py
runtime/swarm/
runtime/fixtures/minimal-v2/
runtime-contract.json
profiles/
schemas/
```

The runtime code intentionally resolves `runtime-contract.json` and
`profiles/` from the plugin root, so the vendored copy can stay close to the
runtime repository layout.

## Commands

Check the bundled runtime from inside a plugin checkout or installed plugin:

```bash
python3 plugins/codex/runtime/swarm_runtime_wrapper.py doctor
```

Check the bundled runtime and replay the bundled minimal fixture:

```bash
python3 plugins/codex/runtime/swarm_runtime_wrapper.py doctor --smoke-fixture
```

The fixture smoke runs `adapter-smoke` against `runtime/fixtures/minimal-v2`.
It validates host-step metadata, replays `collect-merge`, checks trace/evidence,
and validates the smallest complete runtime loop without spawning agents or
mutating state.

## Development Override

With a local runtime checkout:

```bash
python3 plugins/codex/runtime/swarm_runtime_wrapper.py \
  --runtime /path/to/swarm-discussion-runtime/runtime/swarm_rt.py \
  doctor
```

Run the adapter-facing smoke gate against a completed fixture or live discussion:

```bash
python3 plugins/codex/runtime/swarm_runtime_wrapper.py \
  --runtime /path/to/swarm-discussion-runtime/runtime/swarm_rt.py \
  adapter-smoke --dir /path/to/discussion
```

If the runtime is installed as `swarm-rt`, the `--runtime` flag can be omitted.

## Current Status

This is still a migration bridge. The live skill remains on the existing
bundled-helper flow until the skill prompt is switched to the runtime-backed
adapter path.
