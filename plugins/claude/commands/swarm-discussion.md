---
description: Multi-expert swarm discussion for unsolved problems — designed tension, blind position declarations, steel-manning, an argument graph, and quality gates.
argument-hint: [--mode lightweight|standard|deep] "<topic>"
---

Run the **swarm-discussion** skill on the following topic (parse an optional leading `--mode
lightweight|standard|deep`; default `standard`):

$ARGUMENTS

Follow the skill protocol (`skills/swarm-discussion/SKILL.md` → the shared `protocol/`): generate dynamic
experts + a tension map, run blind position declarations → moderator framing → cited argumentation →
contrarian stress-test → responses with position-shift tracking → (standard/deep) cross-domain → quality
gate, with per-step WAL checkpointing and the provenance gate, then synthesize. Confirm expert composition
with the user before starting.
