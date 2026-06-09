# 🐝 swarm-discussion

> **Stop your AI from agreeing with itself.** Convene a panel of expert personas who genuinely *argue* —
> with designed tension, blind position-taking, mandatory steel-manning, and a cited argument graph — then
> hand you a traceable synthesis.

For hard, open, or high-stakes questions, a single model tends to lock onto the first plausible answer.
**swarm-discussion** spins up several expert personas with *structurally opposing* stakes, makes each commit
a position **before** seeing the others (no anchoring), forces them to steel-man before they rebut, tracks
who changed whose mind and why, and closes with a synthesis where every claim cites a message ID.

One skill, two hosts: **Claude Code** and the **Codex desktop app**.

---

## Why it works

Experts role-played inside one model drift toward consensus: they agree with well-argued prior turns, add
instead of challenge, and converge too fast. swarm-discussion engineers disagreement on purpose:

- **🎯 Designed tension** — a *tension map* pairs experts whose roles/stakes genuinely conflict.
- **🙈 Blind position declarations** — each expert commits a stance (with `wouldChangeIf`) before seeing peers.
- **🥊 Mandatory steel-manning** — restate the opposing view at its strongest, *then* counter it.
- **🔗 Argument graph** — every message cites prior ones by ID (`supports` / `counters` / `extends` / `questions`).
- **🔀 Position-shift tracking** — records when an expert changes their mind and the exact message that moved them.
- **🚦 Quality gates** — the Moderator scores genuine disagreement and blocks premature consensus.
- **💾 Crash-safe & resumable** — a per-step write-ahead log; force-quit mid-discussion and pick up where it stopped.

## Good for

Architecture & design decisions · build-vs-buy · rewrite-vs-refactor · stress-testing a risky plan before you
commit · surfacing the blind spots no single perspective would catch.

---

## Install & use — Claude Code

```
/plugin marketplace add automann/swarm-discussion
/plugin install swarm-discussion@swarm-discussion
```

Then invoke the `/swarm-discussion` command with a topic:

```
/swarm-discussion "Should the orders service adopt event sourcing?"
/swarm-discussion --mode deep "Rewrite the monolith, or strangler-fig it?"
/swarm-discussion --mode lightweight "GraphQL or REST for this internal API?"
```

You'll be shown the proposed experts and their designed tensions to confirm before the debate begins; each
round then streams to the conversation. Results are saved under `.swarm/discussions/<id>/` in your workspace.

To upgrade the Claude Code plugin, refresh this marketplace, update the installed plugin, then reload plugins:

```
/plugin marketplace update swarm-discussion
/plugin update swarm-discussion@swarm-discussion
/reload-plugins
```

Check the installed version with:

```
/plugin list
```

If the version still does not change, uninstall and reinstall from the same marketplace. `--keep-data` preserves
the plugin's persistent data while replacing the cached plugin copy:

```
/plugin uninstall swarm-discussion@swarm-discussion --keep-data
/plugin install swarm-discussion@swarm-discussion
/reload-plugins
```

## Install & use — Codex CLI and desktop app

Use the wrapper installer. It installs the Codex plugin, then registers the bundled `swarm-expert.toml` as a
Codex custom agent from the installed plugin directory.

```
npx @automann/swarm-discussion-installer install --global
```

Use a project-scoped install instead when you only want `swarm-expert` available inside one workspace:

```
cd /path/to/your/project
npx @automann/swarm-discussion-installer install --project
```

`install` runs the native Codex commands:

```
codex plugin marketplace add automann/swarm-discussion
codex plugin add swarm-discussion@swarm-discussion
```

Then it copies the plugin's `agents/swarm-expert.toml` template into one of Codex's custom-agent discovery
paths:

- `~/.codex/agents/swarm-expert.toml` for `--global`.
- `./.codex/agents/swarm-expert.toml` for `--project`.

Run the optional real spawn smoke test when you want to verify the full subagent path:

```
npx @automann/swarm-discussion-installer install --global --verify-spawn
```

After installing, restart Codex and start a new top-level thread/session so the plugin picker, bundled skill,
and custom-agent registry refresh.

Use `doctor` to inspect an existing install without changing files:

```
npx @automann/swarm-discussion-installer doctor
npx @automann/swarm-discussion-installer doctor --verify-spawn
```

To upgrade or repair Codex registration, rerun the installer with the same scope:

```
npx @automann/swarm-discussion-installer repair --global
npx @automann/swarm-discussion-installer repair --project
```

To uninstall only the custom-agent registration file:

```
npx @automann/swarm-discussion-installer uninstall --global
npx @automann/swarm-discussion-installer uninstall --project
```

For a clean reinstall test, remove the custom-agent registration, Codex plugin, and Codex marketplace entry:

```
npx @automann/swarm-discussion-installer uninstall --global --all
```

`--all` is destructive and does not create backups. Use `--project --all` from a project root to remove the
project-scoped custom-agent file instead of the global one.

You can still install only the Codex plugin with native Codex commands:

```
codex plugin marketplace add automann/swarm-discussion
codex plugin add swarm-discussion@swarm-discussion
```

That plugin-only path installs the `swarm-discussion` skill and keeps `agents/swarm-expert.toml` inside the
plugin package, but it does not by itself copy the file into `~/.codex/agents/` or `.codex/agents/`. Run
`npx @automann/swarm-discussion-installer repair --global` or `--project` afterward if you need
`multi_agent_v1.spawn_agent(agent_type = "swarm-expert")` to work.

Verify the installed Codex plugin version with:

```
codex plugin list | rg swarm-discussion
```

In the Codex desktop app, start it on a **top-level thread** — type `@` and pick **swarm-discussion**, or just
ask in plain language:

```
@ swarm-discussion — run a lightweight discussion on: append-only event log vs mutable rows
```
> *"Use swarm-discussion to stress-test this decision: should we shard the database now or after launch? Go deep."*

In Codex CLI, run `codex` from the workspace, use `/plugins` if you want to verify or toggle the installed
plugin, then start a new top-level session and ask Codex to use **swarm-discussion** for your topic.

Codex spawns the expert personas as subagents and writes the discussion under `.swarm/discussions/<id>/` in
your workspace.

**Codex notes**
- Run it on the **root thread** — the orchestrator coordinates subagents and can't itself be a subagent
  (`agents.max_depth = 1`).
- Codex needs write access to your workspace; it only ever writes under `.swarm/discussions/`.
- To turn the plugin off without uninstalling, disable it from Codex's plugin controls or remove it with
  `codex plugin remove swarm-discussion@swarm-discussion`, then restart Codex.

**Codex known issues**
- The Codex app's Plugins page can still show **Swarm Discussion** after you uninstall or delete every local
  install. In this repo, that usually means the app is discovering the repo-scoped marketplace at
  `.agents/plugins/marketplace.json`; the entry is catalog availability, not proof that the plugin is still
  installed. Use `codex plugin list | rg swarm-discussion` and the installed roots under `~/.codex/plugins/`
  to verify actual install state.

---

## Modes

Pick a tier by stakes and budget (`--mode` on Claude Code, or say it in your request on Codex):

| Mode | Experts | Rounds | Calls/round | Use when |
|------|---------|--------|-------------|----------|
| `lightweight` | 2 dynamic + Moderator & Contrarian | 1–2 | 3–5 | quick sanity check, idea validation |
| `standard` *(default)* | 2–3 dynamic + 4 fixed | 2–3 | 5–8 | typical design decision, tradeoff analysis |
| `deep` | 3–4 dynamic + 4 fixed | 3–5 | 8–12 | unprecedented problems, high-stakes calls |

> Quality over quantity: two rounds of *genuine* disagreement beat five rounds of polite agreement.

**Roles.** Every panel has a **Moderator** (frames real fault lines, runs the quality gate) and a
**Contrarian** (attacks the *strongest* consensus). Standard/Deep add a **Cross-Domain** thinker (analogies
from other fields) and a **Historian** (argument graph + synthesis). The **dynamic experts** are generated
per topic, each with explicit *stakes* and *blind spots* so they argue with conviction.

## What a run produces

Everything is saved, inspectable, and resumable, under `.swarm/discussions/<id>/`:

```
manifest.json            # topic, mode, personas, tension map, status
progress.md              # live per-step log you can tail
personas/<id>.json       # each expert: expertise, bias, stakes, blind spots
rounds/NNN.json          # messages + argument graph + position shifts + quality score
artifacts/               # synthesis, open questions, argument graph, position evolution
```

You can validate any committed round with the bundled `protocol/validate_round.py`:

```
python3 .../skills/swarm-discussion/protocol/validate_round.py .swarm/discussions/<id>/rounds/001.json
```

## How it works (under the hood)

The orchestrator runs on your main thread and coordinates ephemeral persona subagents over a **shared on-disk
write-ahead log** — a *blackboard*, not peer-to-peer messaging. It mints durable message IDs (so a resume
never restarts numbering), windows each persona's view of the log (you always see your own history in full;
peers are summarized past a budget), and runs a **provenance gate** — a recorded "I changed my mind because
of `r1-msg-006`" must cite a message that persona was actually shown. The discussion *content* differs by
host; the *structure* (ID chains, argument graph, round schema) is identical across both — verified by the
bundled cross-adapter conformance test (`python3 conformance/conformance.py`).

It ships **no server** ("native blackboard").

## Footprint & cost

- Spawns several persona subagents per round (the dynamic experts + Contrarian, plus Moderator framing). A
  **lightweight** run is ~7–8 subagents and runs its quality gate + synthesis *inline* (a single concise
  `synthesis.md`); `standard`/`deep` add more rounds, a Cross-Domain expert, and the full Historian synthesis
  (5 artifacts). Real token/API cost: even lightweight runs into the low hundreds of thousands of tokens and a
  few minutes — it's the *cheapest* tier, **not free**. Reach for it for genuine decisions, not casual queries;
  use `deep` only when the call earns it.
- **Writes files** under `.swarm/discussions/` in the current workspace. No network calls.

## Layout

```
.claude-plugin/marketplace.json   # Claude Code marketplace entry
.agents/plugins/marketplace.json  # Codex marketplace entry
plugins/claude/                   # Claude Code plugin (skill + /swarm-discussion command)
plugins/codex/                    # Codex plugin (skill + swarm-expert agent)
plugins/codex/runtime/            # vendored v2 runtime CLI + plugin wrapper bridge
conformance/                      # cross-bundle conformance test
```

Both bundles vendor the shared `protocol/` core; it is a vendored build artifact — don't edit it here.

The Codex package also contains a vendored v2 runtime bridge under `plugins/codex/runtime/`. The current skill
still uses the stable bundled-helper flow, but the wrapper can already verify the bundled runtime contract and
delegate adapter-facing smoke gates without copying runtime orchestration logic into `SKILL.md`.

## Credits

swarm-discussion is an independent, **self-contained** reimplementation that builds on and improves the
original **[swarm-discussion skill by Ischca](https://github.com/Ischca/swarm-discussion-skill)** (MIT).
Improvements over the original: a shared core with thin Claude/Codex adapters (one skill, two hosts), per-step
write-ahead-log durability with crash-safe resume, context windowing with shift-provenance, and a
cross-adapter conformance test. This plugin does **not** depend on or require the original skill — it ships
everything it needs.

## License

MIT — see [`LICENSE`](LICENSE).
