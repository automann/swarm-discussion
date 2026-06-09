# Codex Runtime Wrapper

This directory is the plugin-side integration skeleton for the v2 runtime. The
published skill still uses the legacy in-prompt orchestration path by default.
The wrapper exists so we can exercise the runtime contract from inside the
plugin package without copying runtime logic back into `SKILL.md`.

The wrapper owns only three jobs:

- Resolve a runtime CLI from `--runtime`, `SWARM_DISCUSSION_RUNTIME`, a future
  bundled `runtime/swarm_rt.py`, or `swarm-rt` on `PATH`.
- Verify `runtime-contract` and the `swarm-runtime-v2-alpha` compatibility id.
- Delegate integration gates such as `adapter-smoke` and `validate-loop`.

It must not construct prompts, merge wait results, mint message ids, mutate WAL
state, summarize trace/evidence health, install plugins, or manage marketplace
state. Those behaviors belong to the runtime package or the installer.

## Development Commands

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

This is a skeleton. It is safe to ship because it is inert unless explicitly
called. The live skill remains on the existing bundled helper flow until the
runtime package is embedded or installed by the Codex installer.
