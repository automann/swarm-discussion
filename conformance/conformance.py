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
import tempfile
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

wrapper = REPO / "plugins/codex/runtime/swarm_runtime_wrapper.py"
bundled_doctor = subprocess.run(
    [sys.executable, str(wrapper), "doctor"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
check(bundled_doctor.returncode == 0, "codex runtime wrapper doctor accepts bundled runtime")
if bundled_doctor.returncode == 0:
    payload = json.loads(bundled_doctor.stdout)
    check(payload["runtime"]["source"] == "bundled", "codex runtime wrapper defaults to bundled runtime")
    check(
        payload["contractSummary"]["compatibility"] == "swarm-runtime-v2-alpha",
        "bundled runtime reports expected compatibility",
    )

bundled_fixture_smoke = subprocess.run(
    [sys.executable, str(wrapper), "doctor", "--smoke-fixture"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
check(bundled_fixture_smoke.returncode == 0, "codex runtime wrapper bundled fixture smoke passes")
if bundled_fixture_smoke.returncode == 0:
    payload = json.loads(bundled_fixture_smoke.stdout)
    check(payload["fixtureSmoke"]["ok"] is True, "codex runtime wrapper reports fixture smoke ok")
    check(
        payload["fixtureSmoke"]["summary"]["transportReplayOk"] is True,
        "codex runtime wrapper fixture smoke replays transport",
    )

codex_skill_text = (REPO / "plugins/codex/skills/swarm-discussion/SKILL.md").read_text()
check(
    "$CODEX_HOME/.tmp/marketplaces" in codex_skill_text,
    "codex skill lookup covers marketplace-installed plugin roots",
)
check(
    "doctor --smoke-fixture" in codex_skill_text,
    "codex skill runs bundled runtime preflight",
)
check(
    "adapter-smoke --dir .swarm/discussions/{id}" in codex_skill_text,
    "codex skill documents bundled runtime transport smoke gate",
)
check(
    "do not silently downgrade to legacy validation" in codex_skill_text,
    "codex skill fails missing runtime transport artifacts instead of downgrading",
)
for invariant, message in (
    (
        "The Codex entry path is runtime-backed by default.",
        "codex skill declares runtime-backed entry as default",
    ),
    (
        "The root thread may only prepare compact temp input files",
        "codex skill keeps root thread as thin host operator",
    ),
    (
        "derive persona prompt text without `prompt-build`",
        "codex skill forbids parent-built prompts",
    ),
    (
        "merge `wait_agent` statuses outside `transport-collect` / runtime `collect-merge`",
        "codex skill forbids parent-side fan-in merge",
    ),
    (
        "mint message IDs, edit committed round files, or patch WAL partial files directly",
        "codex skill forbids parent-side WAL/message-id mutation",
    ),
    (
        "call legacy `wal.py flush` / `commit` for runtime-backed runs",
        "codex skill forbids legacy WAL commit path",
    ),
    (
        "If a runtime primitive fails, stop and repair that primitive's inputs or output.",
        "codex skill fails closed instead of hand-building runtime artifacts",
    ),
):
    check(invariant in codex_skill_text, message)
check(
    "standard protocol artifacts in the parent context" in codex_skill_text,
    "codex skill forbids parent-built fallback artifacts",
)
check(
    "protocol/collect.py" not in codex_skill_text,
    "codex skill natural entry does not route through legacy protocol collect helper",
)
for primitive in (
    "prompt-build",
    "transport-init",
    "transport-append-batch",
    "transport-collect",
    "collect-merge",
    "append-message",
    "finalize-round",
):
    check(
        primitive in codex_skill_text,
        f"codex skill routes real flow through runtime {primitive}",
    )

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    fake_runtime = tmp_path / "fake_swarm_rt.py"
    discussion_dir = tmp_path / "discussion"
    calls_path = tmp_path / "calls.jsonl"
    discussion_dir.mkdir()
    fake_runtime.write_text(
        f"""#!/usr/bin/env python3
import json
import sys
from pathlib import Path

calls = Path({str(calls_path)!r})
with calls.open("a") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\\n")

command = sys.argv[1] if len(sys.argv) > 1 else ""
if command == "runtime-contract":
    required_commands = [
        "context-build",
        "prompt-build",
        "collect-merge",
        "transport-init",
        "transport-append-batch",
        "transport-collect",
        "append-message",
        "checkpoint",
        "finalize-round",
        "resume-plan",
        "validate-round",
        "validate-discussion",
        "trace",
        "evidence",
        "validate-host-step",
        "capability-doctor",
        "adapter-smoke",
        "validate-loop",
    ]
    print(json.dumps({{
        "ok": True,
        "contract": {{
            "kind": "swarm.runtime_contract",
            "runtime": {{"compatibility": "swarm-runtime-v2-alpha"}},
            "commands": {{name: {{}} for name in required_commands}},
        }},
        "validation": {{
            "summary": {{
                "compatibility": "swarm-runtime-v2-alpha",
                "integrationGates": ["adapter-smoke", "validate-loop"],
            }}
        }},
    }}))
    raise SystemExit(0)
if command == "adapter-smoke":
    print(json.dumps({{"ok": True, "received": sys.argv[1:]}}))
    raise SystemExit(0)
if command == "validate-loop":
    print(json.dumps({{"ok": True, "received": sys.argv[1:]}}))
    raise SystemExit(0)
print(json.dumps({{"ok": False, "error": "unknown command", "argv": sys.argv[1:]}}))
raise SystemExit(1)
"""
    )

    doctor = subprocess.run(
        [sys.executable, str(wrapper), "--runtime", str(fake_runtime), "doctor"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(doctor.returncode == 0, "codex runtime wrapper doctor accepts compatible fake runtime")
    if doctor.returncode == 0:
        payload = json.loads(doctor.stdout)
        check(payload["ok"] is True, "codex runtime wrapper doctor reports ok")
        check(
            payload["wrapper"]["compatibility"] == "swarm-runtime-v2-alpha",
            "codex runtime wrapper reports expected compatibility",
        )

    smoke = subprocess.run(
        [
            sys.executable,
            str(wrapper),
            "--runtime",
            str(fake_runtime),
            "adapter-smoke",
            "--dir",
            str(discussion_dir),
            "--host-step",
            "transport/r001/response/host-step.json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(smoke.returncode == 0, "codex runtime wrapper delegates adapter-smoke")
    if smoke.returncode == 0:
        payload = json.loads(smoke.stdout)
        check(payload["ok"] is True, "codex runtime wrapper adapter-smoke reports ok")
        check(
            payload["result"]["received"][-2:] == ["--host-step", "transport/r001/response/host-step.json"],
            "codex runtime wrapper preserves adapter-smoke host-step argument",
        )

    loop = subprocess.run(
        [sys.executable, str(wrapper), "--runtime", str(fake_runtime), "validate-loop", str(discussion_dir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(loop.returncode == 0, "codex runtime wrapper delegates validate-loop")
    calls = [json.loads(line) for line in calls_path.read_text().splitlines()]
    check(
        calls.count(["runtime-contract"]) == 3,
        "codex runtime wrapper checks contract before each delegated gate",
    )

flow_smoke = subprocess.run(
    [sys.executable, str(REPO / "conformance/runtime_flow_smoke.py")],
    cwd=str(REPO),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
check(flow_smoke.returncode == 0, "codex runtime-backed discussion flow smoke passes")
if flow_smoke.returncode == 0:
    payload = json.loads(flow_smoke.stdout)
    summary = payload["summary"]
    check(summary["promptBuildCount"] == 2, "codex runtime flow smoke builds persona prompts")
    check(
        summary["partialMissingAgentIds"] == ["agent-contrarian"],
        "codex runtime flow smoke catches partial fan-in before completion",
    )
    check(summary["messageIds"] == ["r1-msg-001", "r1-msg-002"], "codex runtime flow smoke mints WAL ids")
    check(summary["adapterSmokeOk"] is True, "codex runtime flow smoke passes adapter-smoke")
    check(summary["validateLoopOk"] is True, "codex runtime flow smoke passes validate-loop")

live_harness = subprocess.run(
    [sys.executable, str(REPO / "conformance/live_runtime_flow.py"), "self-test"],
    cwd=str(REPO),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
check(live_harness.returncode == 0, "codex live runtime flow harness self-test passes")
if live_harness.returncode == 0:
    payload = json.loads(live_harness.stdout)
    checks = {item["name"]: item["ok"] for item in payload["checks"]}
    check(checks.get("missing spawn-order fails") is True, "live harness rejects missing spawn-order")
    check(checks.get("partial fan-in fails before WAL") is True, "live harness rejects incomplete fan-in")
    check(checks.get("finish validates completed loop") is True, "live harness validates completed loop")

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    prompt_out = tmp_path / "prompt"
    prompt = subprocess.run(
        [
            sys.executable,
            str(wrapper),
            "prompt-build",
            "--request",
            str(REPO / "plugins/codex/runtime/fixtures/minimal-v2/prompts/r001/response/architect/request.json"),
            "--out-dir",
            str(prompt_out),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(prompt.returncode == 0, "codex runtime wrapper delegates prompt-build primitive")
    if prompt.returncode == 0:
        payload = json.loads(prompt.stdout)
        check(payload["result"]["ok"] is True, "codex runtime wrapper prompt-build result ok")
        check((prompt_out / "prompt.txt").exists(), "codex runtime wrapper prompt-build writes prompt artifact")

    collect_merge = subprocess.run(
        [
            sys.executable,
            str(wrapper),
            "collect-merge",
            "--spawn-order",
            str(REPO / "plugins/codex/runtime/fixtures/minimal-v2/transport/r001/response/spawn-order.json"),
            "--wait-result",
            str(REPO / "plugins/codex/runtime/fixtures/minimal-v2/transport/r001/response/wait-batches.jsonl"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(collect_merge.returncode == 0, "codex runtime wrapper delegates collect-merge primitive")
    if collect_merge.returncode == 0:
        payload = json.loads(collect_merge.stdout)
        check(payload["result"]["complete"] is True, "codex runtime wrapper collect-merge completes fixture fan-in")

    transport_dir = tmp_path / "transport-discussion"
    spawn_order = tmp_path / "spawn-order.json"
    wait_result = tmp_path / "wait-result.json"
    spawn_order.write_text(
        json.dumps(
            [
                {"agentId": "agent-architect", "persona": "architect"},
                {"agentId": "agent-contrarian", "persona": "contrarian"},
            ]
        )
        + "\n"
    )
    wait_result.write_text(
        json.dumps(
            {
                "status": {
                    "agent-architect": {
                        "completed": json.dumps({"name": "architect", "claim": "transport works"})
                    },
                    "agent-contrarian": {
                        "completed": json.dumps({"name": "contrarian", "claim": "smoke the failure path"})
                    },
                },
                "timed_out": False,
            }
        )
        + "\n"
    )
    transport_init = subprocess.run(
        [
            sys.executable,
            str(wrapper),
            "transport-init",
            "--dir",
            str(transport_dir),
            "--host",
            "codex",
            "--discussion-id",
            "wrapper-transport",
            "--round",
            "1",
            "--phase",
            "response",
            "--spawn-order",
            str(spawn_order),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(transport_init.returncode == 0, "codex runtime wrapper delegates transport-init primitive")
    if transport_init.returncode == 0:
        payload = json.loads(transport_init.stdout)
        check(
            payload["result"]["hostStep"]["parentContext"]["nextHelperCommand"].endswith(
                "transport-collect --dir . --round 1 --phase response"
            ),
            "codex runtime wrapper transport-init writes transport-collect next helper",
        )
        check(
            (transport_dir / "transport/r001/response/host-step.json").exists(),
            "codex runtime wrapper transport-init writes host-step",
        )

    transport_append = subprocess.run(
        [
            sys.executable,
            str(wrapper),
            "transport-append-batch",
            "--dir",
            str(transport_dir),
            "--round",
            "1",
            "--phase",
            "response",
            "--wait-result",
            str(wait_result),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(transport_append.returncode == 0, "codex runtime wrapper delegates transport-append-batch primitive")

    transport_collect = subprocess.run(
        [
            sys.executable,
            str(wrapper),
            "transport-collect",
            "--dir",
            str(transport_dir),
            "--round",
            "1",
            "--phase",
            "response",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(transport_collect.returncode == 0, "codex runtime wrapper delegates transport-collect primitive")
    if transport_collect.returncode == 0:
        payload = json.loads(transport_collect.stdout)
        check(payload["result"]["result"]["complete"] is True, "codex runtime wrapper transport-collect completes fan-in")
        check(
            (transport_dir / "transport/r001/response/collect-result.json").exists(),
            "codex runtime wrapper transport-collect writes collect-result",
        )

    discussion_dir = tmp_path / "discussion"
    message1 = tmp_path / "message1.json"
    message1.write_text(
        json.dumps(
            {
                "from": "architect",
                "type": "position_declaration",
                "content": {"summary": "Use runtime WAL."},
                "references": [],
            }
        )
    )
    append1 = subprocess.run(
        [
            sys.executable,
            str(wrapper),
            "append-message",
            "--dir",
            str(discussion_dir),
            "--round",
            "1",
            "--phase",
            "declaration",
            "--message",
            str(message1),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(append1.returncode == 0, "codex runtime wrapper delegates append-message primitive")
    if append1.returncode == 0:
        payload = json.loads(append1.stdout)
        check(
            payload["result"]["message"]["id"] == "r1-msg-001",
            "codex runtime wrapper append-message mints first id",
        )

    message2 = tmp_path / "message2.json"
    message2.write_text(
        json.dumps(
            {
                "from": "contrarian",
                "type": "argument",
                "content": {"summary": "Probe the WAL boundary."},
                "references": [{"targetId": "r1-msg-001", "relation": "questions"}],
            }
        )
    )
    append2 = subprocess.run(
        [
            sys.executable,
            str(wrapper),
            "append-message",
            "--dir",
            str(discussion_dir),
            "--round",
            "1",
            "--phase",
            "argumentation",
            "--message",
            str(message2),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    check(append2.returncode == 0, "codex runtime wrapper append-message accepts references")

    if append2.returncode == 0:
        state = json.loads((discussion_dir / "rounds/001.json.partial").read_text())
        state.update(
            {
                "topic": "Wrapper WAL smoke",
                "mode": "lightweight",
                "timestamp": "2026-06-10T00:00:00Z",
                "synthesis": {"qualityScore": {"overall": 4}, "recommendation": "continue"},
                "metadata": {
                    "messageCount": len(state["messages"]),
                    "participants": ["architect", "contrarian"],
                    "referenceCount": len(state["argumentGraph"]),
                },
            }
        )
        final_state = tmp_path / "final.json"
        final_state.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
        finalize = subprocess.run(
            [
                sys.executable,
                str(wrapper),
                "finalize-round",
                "--dir",
                str(discussion_dir),
                "--round",
                "1",
                "--state",
                str(final_state),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        check(finalize.returncode == 0, "codex runtime wrapper delegates finalize-round primitive")
        if finalize.returncode == 0:
            payload = json.loads(finalize.stdout)
            check(payload["result"]["ok"] is True, "codex runtime wrapper finalize-round result ok")
            check((discussion_dir / "rounds/001.json").exists(), "codex runtime wrapper finalize-round commits")

shutil.rmtree("/tmp/swarm-discussion-conf-claude", ignore_errors=True)
shutil.rmtree("/tmp/swarm-discussion-conf-codex", ignore_errors=True)

print("\nALL PASS - marketplace bundles are conformant" if not fails else f"\n{len(fails)} FAILURE(S)")
sys.exit(1 if fails else 0)
