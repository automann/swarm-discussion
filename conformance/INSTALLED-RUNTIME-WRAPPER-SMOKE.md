# Installed Runtime Wrapper Smoke

This gate verifies that the Codex plugin works after a clean marketplace
install, not only from the source checkout.

## Latest Run

- Date: 2026-06-10
- Workspace: `/Users/syfq/dev/harness/swarm-discussion`
- Marketplace source: `automann/swarm-discussion --ref main`
- Temporary `CODEX_HOME`: `/private/tmp/swarm-installed-wrapper-audit.vJM2Te`
- Installed plugin root:
  `/private/tmp/swarm-installed-wrapper-audit.vJM2Te/plugins/cache/swarm-discussion/swarm-discussion/0.1.10`
- Installed wrapper:
  `/private/tmp/swarm-installed-wrapper-audit.vJM2Te/plugins/cache/swarm-discussion/swarm-discussion/0.1.10/runtime/swarm_runtime_wrapper.py`
- Installed plugin version: `0.1.10`

## Commands

```sh
TMP_CODEX_HOME="$(mktemp -d /tmp/swarm-installed-wrapper-audit.XXXXXX)"
CODEX_HOME="$TMP_CODEX_HOME" codex plugin marketplace add automann/swarm-discussion --ref main
CODEX_HOME="$TMP_CODEX_HOME" codex plugin add swarm-discussion@swarm-discussion
CODEX_HOME="$TMP_CODEX_HOME" codex plugin list --json --available

INSTALLED_WRAPPER="$TMP_CODEX_HOME/plugins/cache/swarm-discussion/swarm-discussion/0.1.10/runtime/swarm_runtime_wrapper.py"
python3 "$INSTALLED_WRAPPER" doctor --smoke-fixture
python3 conformance/runtime_flow_smoke.py --wrapper "$INSTALLED_WRAPPER"
python3 conformance/live_runtime_flow.py --wrapper "$INSTALLED_WRAPPER" self-test
```

## Evidence

`codex plugin list --json --available` reported one installed plugin:

```json
{
  "pluginId": "swarm-discussion@swarm-discussion",
  "version": "0.1.10",
  "installed": true,
  "enabled": true
}
```

`doctor --smoke-fixture` resolved the bundled runtime from the installed plugin
cache, reported `compatibility = swarm-runtime-v2-alpha`, and passed the bundled
fixture smoke with:

```json
{
  "ok": true,
  "runtimeSource": "bundled",
  "fixtureSmokeOk": true,
  "transportReplayOk": true,
  "loopOk": true
}
```

`runtime_flow_smoke.py --wrapper "$INSTALLED_WRAPPER"` passed from an empty
discussion directory through the installed wrapper:

```json
{
  "promptBuildCount": 2,
  "partialMissingAgentIds": ["agent-contrarian"],
  "messageIds": ["r1-msg-001", "r1-msg-002"],
  "adapterSmokeOk": true,
  "validateLoopOk": true,
  "health": "on-track"
}
```

`live_runtime_flow.py --wrapper "$INSTALLED_WRAPPER" self-test` passed the
operator-harness checks:

```json
{
  "missingSpawnOrderFails": true,
  "partialFanInFailsBeforeWal": true,
  "prepareWritesTwoPromptArtifacts": true,
  "finishRecordsPartialCollectAttempt": true,
  "finishMintsWalMessageIds": true,
  "finishValidatesCompletedLoop": true
}
```

## Scope

This gate proves the installed plugin wrapper and its bundled runtime can run
the runtime-backed flow. It does not itself spawn real `swarm-expert` agents;
real host-boundary spawn/wait evidence is tracked in
`LIVE-RUNTIME-FLOW-SMOKE.md`.
