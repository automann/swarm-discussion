#!/usr/bin/env python3
"""
Cross-bundle conformance for the marketplace package.

This is intentionally local to the packaged repo: it imports the vendored protocol helpers from
plugins/claude and the Codex collect helper from plugins/codex. Given identical persona outputs, the
Claude-style and Codex-style paths must produce the same round record.
"""
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wal = _load("plugins/claude/skills/swarm-discussion/protocol/wal.py", "wal")
window = _load("plugins/claude/skills/swarm-discussion/protocol/window.py", "window")
collect = _load("plugins/codex/skills/swarm-discussion/collect.py", "collect")
validate_round = _load("plugins/claude/skills/swarm-discussion/protocol/validate_round.py", "validate_round")

fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


TOPIC = "JSON round records vs append-only JSONL"
EXPERTS = ["schema-architect", "ops-engineer"]
DECL = {
    "schema-architect": {"name": "schema-architect", "position": "prefer JSONL", "confidence": 0.6},
    "ops-engineer": {"name": "ops-engineer", "position": "prefer JSON", "confidence": 0.7},
}
ARG = {
    "schema-architect": {
        "name": "schema-architect",
        "position": "JSONL appends are crash-safe",
        "references": [{"targetId": "r1-msg-002", "relation": "counters"}],
    },
    "ops-engineer": {
        "name": "ops-engineer",
        "position": "JSON is simpler to consume",
        "references": [{"targetId": "r1-msg-001", "relation": "counters"}],
    },
}
CONTRA = {
    "name": "contrarian",
    "targetConsensus": "both assume one writer",
    "references": [
        {"targetId": "r1-msg-004", "relation": "questions"},
        {"targetId": "r1-msg-005", "relation": "questions"},
    ],
}
RESP = {
    "schema-architect": {
        "name": "schema-architect",
        "positionShift": "minor",
        "previousPosition": "prefer JSONL",
        "currentPosition": "JSONL + periodic JSON projection",
        "shiftReason": "multi-writer point",
        "shiftTriggerIds": ["r1-msg-006"],
        "references": [{"targetId": "r1-msg-006", "relation": "extends"}],
    },
    "ops-engineer": {
        "name": "ops-engineer",
        "positionShift": "none",
        "previousPosition": "prefer JSON",
        "currentPosition": "prefer JSON",
        "shiftReason": "",
        "shiftTriggerIds": [],
        "references": [{"targetId": "r1-msg-006", "relation": "questions"}],
    },
}


def claude_collect(personas, canned):
    return [{"persona": persona, "result": canned[persona]} for persona in personas]


def codex_collect(personas, canned):
    spawn = [{"agentId": f"aid-{persona}", "persona": persona} for persona in personas]
    status = {
        f"aid-{persona}": {"completed": json.dumps(canned[persona])}
        for persona in reversed(personas)
    }
    out = collect.demux({"status": status, "timed_out": False}, spawn)
    assert not out["errors"] and not out["timedOut"], out
    return [{"persona": item["persona"], "result": item["result"]} for item in out["results"]]


def assemble(dirpath, collect_fn):
    shutil.rmtree(dirpath, ignore_errors=True)
    messages, graph, shifts, persona_context_log = [], [], [], {}

    def add(sender, typ, content, refs=None):
        mid = f"r1-msg-{len(messages) + 1:03d}"
        message = {"id": mid, "from": sender, "type": typ, "content": content}
        if refs:
            message["references"] = refs
            for ref in refs:
                graph.append({"from": mid, "to": ref["targetId"], "relation": ref["relation"]})
        messages.append(message)
        return mid

    for item in collect_fn(EXPERTS, DECL):
        add(item["persona"], "position_declaration", item["result"])
    add("moderator", "opening", {"summary": "frame the fault line"})
    for item in collect_fn(EXPERTS, ARG):
        add(item["persona"], "argument", item["result"], item["result"].get("references"))
    add("contrarian", "stress_test", CONTRA, CONTRA.get("references"))
    for item in collect_fn(EXPERTS, RESP):
        projection = window.slice_for_persona(messages, item["persona"], "response")
        persona_context_log[item["persona"]] = projection["visibility"]
        add(item["persona"], "response", item["result"], item["result"].get("references"))
        if item["result"]["positionShift"] != "none":
            shifts.append(
                {
                    "type": "position_shift",
                    "expert": item["persona"],
                    "from": item["result"]["previousPosition"],
                    "to": item["result"]["currentPosition"],
                    "trigger": item["result"]["shiftTriggerIds"],
                    "reasoning": item["result"]["shiftReason"],
                }
            )

    provenance = window.provenance(shifts, persona_context_log)
    record = {
        "roundId": 1,
        "topic": TOPIC,
        "mode": "lightweight",
        "timestamp": "2026-06-05T00:00:00Z",
        "messages": messages,
        "argumentGraph": graph,
        "positionShifts": shifts,
        "synthesis": {"qualityScore": {"overall": 4}, "recommendation": "synthesize"},
        "metadata": {
            "messageCount": len(messages),
            "participants": sorted({message["from"] for message in messages}),
            "referenceCount": len(graph),
        },
        "personaContextLog": persona_context_log,
    }
    wal.flush(dirpath, 1, "quality", record)
    wal.commit(dirpath, 1)
    return json.loads((Path(dirpath) / "rounds" / "001.json").read_text()), provenance


claude_record, claude_provenance = assemble(Path("/tmp/swarm-discussion-conf-claude"), claude_collect)
codex_record, codex_provenance = assemble(Path("/tmp/swarm-discussion-conf-codex"), codex_collect)

check(
    [message["id"] for message in claude_record["messages"]]
    == [message["id"] for message in codex_record["messages"]],
    "identical message-id chain across bundles",
)
check(
    [message["from"] for message in claude_record["messages"]]
    == [message["from"] for message in codex_record["messages"]],
    "identical sender order under shuffled Codex arrival",
)
check(
    {
        (edge["from"], edge["to"], edge["relation"])
        for edge in claude_record["argumentGraph"]
    }
    == {
        (edge["from"], edge["to"], edge["relation"])
        for edge in codex_record["argumentGraph"]
    },
    "identical argument-graph edge set",
)
check(
    claude_record["personaContextLog"] == codex_record["personaContextLog"],
    "identical per-persona visibility",
)
check(
    claude_provenance == codex_provenance == {"violations": []},
    "provenance clean and identical",
)
check(claude_record == codex_record, "full round record identical across bundles")

for label, record in (("claude", claude_record), ("codex", codex_record)):
    with contextlib.redirect_stdout(io.StringIO()):
        failures = len(validate_round.validate(record))
    check(failures == 0, f"{label} record passes validate_round.py")

for label, rel in (
    ("claude", "plugins/claude/skills/swarm-discussion/protocol/wal.py"),
    ("codex", "plugins/codex/skills/swarm-discussion/protocol/wal.py"),
):
    wal_cli = REPO / rel
    for cmd in ("valid_discussion_id", "valid-discussion-id"):
        ok = subprocess.run(
            [sys.executable, str(wal_cli), cmd, "append-only-event-log-vs-mutable-rows"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        check(ok.returncode == 0, f"{label} wal.py {cmd} accepts safe discussion id")
    bad = subprocess.run(
        [sys.executable, str(wal_cli), "valid_discussion_id", "../bad"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(bad.returncode != 0, f"{label} wal.py valid_discussion_id rejects traversal id")

spawn_order = [
    {"agentId": "aid-schema", "persona": "schema-architect"},
    {"agentId": "aid-ops", "persona": "ops-engineer"},
]
wait_result = {
    "status": {
        "aid-ops": {"completed": json.dumps(DECL["ops-engineer"])},
        "aid-schema": {"completed": json.dumps(DECL["schema-architect"])},
    },
    "timed_out": False,
}
codex_protocol_collect = subprocess.run(
    [
        sys.executable,
        str(REPO / "plugins/codex/skills/swarm-discussion/protocol/collect.py"),
        "--spawn-order",
        json.dumps(spawn_order),
    ],
    input=json.dumps(wait_result),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
check(codex_protocol_collect.returncode == 0, "codex protocol/collect.py wrapper exits cleanly")
if codex_protocol_collect.returncode == 0:
    demuxed = json.loads(codex_protocol_collect.stdout)
    check(
        [item["persona"] for item in demuxed["results"]] == ["schema-architect", "ops-engineer"],
        "codex protocol/collect.py preserves spawn order",
    )

shutil.rmtree("/tmp/swarm-discussion-conf-claude", ignore_errors=True)
shutil.rmtree("/tmp/swarm-discussion-conf-codex", ignore_errors=True)

print("\nALL PASS - marketplace bundles are conformant" if not fails else f"\n{len(fails)} FAILURE(S)")
sys.exit(1 if fails else 0)
